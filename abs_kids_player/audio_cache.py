"""Local copies of audiobooks on the SD card.

The first time a book is played it streams from Audiobookshelf as before and is
downloaded in the background. From then on the player opens the local files, so
playback starts almost immediately and also works without Wi-Fi.

* every book lives in ``<cache dir>/<library item id>/`` with a ``manifest.json``
  (title, chapters, tracks, last local position) and one file per audio track
* the least recently played books are removed when the cache would exceed its
  size limit or the card would get too full
* the listening position is always mirrored locally; positions reached while
  offline are pushed to Audiobookshelf the next time the server is reachable
"""
from __future__ import annotations

import json
import os
import queue
import re
import shutil
import threading
import time
from dataclasses import asdict
from pathlib import Path
from typing import Any, Callable, Iterable
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from .models import AudioTrack, Chapter, PlaybackSession

DEFAULT_CACHE_DIR = Path.home() / ".cache" / "chapter" / "audio"
DEFAULT_MAX_GB = 40.0
MIN_FREE_BYTES = 2 * 1024**3
DOWNLOAD_START_DELAY_SECONDS = 10.0
CHUNK_BYTES = 1024 * 1024
MANIFEST = "manifest.json"
OFFLINE_SESSION_PREFIX = "offline-"


def cache_dir() -> Path:
    configured = os.environ.get("CHAPTER_AUDIO_CACHE_DIR", "").strip()
    return Path(configured).expanduser() if configured else DEFAULT_CACHE_DIR


def max_cache_bytes() -> int:
    try:
        gigabytes = float(os.environ.get("CHAPTER_AUDIO_CACHE_MAX_GB", DEFAULT_MAX_GB))
    except ValueError:
        gigabytes = DEFAULT_MAX_GB
    return int(max(gigabytes, 0) * 1024**3)


def cache_enabled() -> bool:
    return os.environ.get("CHAPTER_AUDIO_CACHE", "1").strip().lower() not in {"0", "off", "false", "no"}


def content_path(url: str) -> str:
    """Server path of a track URL without host and token, e.g. /api/items/<id>/file/<ino>."""
    return urlparse(url).path


def cacheable(url: str) -> bool:
    """Direct-play files can be stored; transcoded HLS streams cannot."""
    path = content_path(url)
    return bool(path) and "/hls/" not in path and not path.endswith(".m3u8") and not url.startswith("file:")


def track_file_name(track: AudioTrack) -> str:
    return f"track-{track.index:03d}.audio"


class AudioCache:
    def __init__(
        self,
        root: Path | None = None,
        max_bytes: int | None = None,
        min_free_bytes: int = MIN_FREE_BYTES,
        opener: Callable[..., Any] = urlopen,
        start_delay: float = DOWNLOAD_START_DELAY_SECONDS,
        clock: Callable[[], float] = time.time,
    ) -> None:
        self.root = root or cache_dir()
        self.max_bytes = max_cache_bytes() if max_bytes is None else max_bytes
        self.min_free_bytes = min_free_bytes
        self.opener = opener
        self.start_delay = start_delay
        self.clock = clock
        self._lock = threading.RLock()
        self._jobs: queue.SimpleQueue[tuple[str, Any]] = queue.SimpleQueue()
        self._worker: threading.Thread | None = None
        self.active_item_id = ""

    # ------------------------------------------------------------ manifest
    def item_dir(self, item_id: str) -> Path:
        safe = re.sub(r"[^A-Za-z0-9_.-]", "_", item_id)
        return self.root / safe

    def load_manifest(self, item_id: str) -> dict[str, Any] | None:
        try:
            return json.loads((self.item_dir(item_id) / MANIFEST).read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return None

    def save_manifest(self, item_id: str, manifest: dict[str, Any]) -> None:
        directory = self.item_dir(item_id)
        directory.mkdir(parents=True, exist_ok=True)
        tmp = directory / (MANIFEST + ".tmp")
        tmp.write_text(json.dumps(manifest, ensure_ascii=False, indent=1), encoding="utf-8")
        tmp.replace(directory / MANIFEST)

    def remember_session(self, session: PlaybackSession) -> bool:
        """Store the session metadata. Returns False when the book cannot be cached (e.g. HLS)."""
        if not cache_enabled() or not session.tracks or not all(cacheable(t.url) for t in session.tracks):
            return False
        with self._lock:
            old = self.load_manifest(session.library_item_id) or {}
            tracks = [
                {
                    "index": t.index,
                    "start_offset": t.start_offset,
                    "duration": t.duration,
                    "title": t.title,
                    "content_path": content_path(t.url),
                    "file": track_file_name(t),
                }
                for t in session.tracks
            ]
            old_paths = {t.get("file"): t.get("content_path") for t in old.get("tracks", [])}
            for track in tracks:   # the server replaced a file -> drop the stale local copy
                if old_paths.get(track["file"]) not in (None, track["content_path"]):
                    (self.item_dir(session.library_item_id) / track["file"]).unlink(missing_ok=True)
            manifest = {
                "item_id": session.library_item_id,
                "title": session.title,
                "author": session.author,
                "duration": session.duration,
                "cover_url": session.cover_url,
                "chapters": [asdict(c) for c in session.chapters],
                "tracks": tracks,
                "last_used": self.clock(),
                "progress": old.get("progress") or {"current_time": session.current_time, "updated": 0, "pending": False},
            }
            self.save_manifest(session.library_item_id, manifest)
        return True

    # ------------------------------------------------------------ lookup
    def local_track_path(self, item_id: str, track: AudioTrack) -> Path | None:
        path = self.item_dir(item_id) / track_file_name(track)
        manifest = self.load_manifest(item_id)
        if manifest is None or not path.is_file() or path.stat().st_size == 0:
            return None
        expected = {t["file"]: t["content_path"] for t in manifest.get("tracks", [])}
        if track.url.startswith("file:") or expected.get(path.name) == content_path(track.url):
            return path
        return None

    def local_uri(self, item_id: str, track: AudioTrack) -> str | None:
        path = self.local_track_path(item_id, track)
        return path.as_uri() if path else None

    def is_complete(self, item_id: str) -> bool:
        manifest = self.load_manifest(item_id)
        if not manifest or not manifest.get("tracks"):
            return False
        directory = self.item_dir(item_id)
        return all((directory / t["file"]).is_file() for t in manifest["tracks"])

    def cached_item_ids(self) -> list[str]:
        if not self.root.is_dir():
            return []
        return [p.name for p in self.root.iterdir() if (p / MANIFEST).is_file()]

    # ------------------------------------------------------------ progress
    def record_progress(self, item_id: str, current_time: float, pending: bool) -> None:
        with self._lock:
            manifest = self.load_manifest(item_id)
            if manifest is None:
                return
            manifest["progress"] = {"current_time": float(current_time), "updated": self.clock(), "pending": pending}
            manifest["last_used"] = self.clock()
            self.save_manifest(item_id, manifest)

    def local_progress(self, item_id: str) -> dict[str, Any] | None:
        manifest = self.load_manifest(item_id)
        return manifest.get("progress") if manifest else None

    def pending_progress(self) -> list[tuple[str, float, float]]:
        result = []
        for item_id in self.cached_item_ids():
            manifest = self.load_manifest(item_id) or {}
            progress = manifest.get("progress") or {}
            if progress.get("pending"):
                result.append((item_id, float(progress.get("current_time") or 0), float(manifest.get("duration") or 0)))
        return result

    def flush_pending_progress(self, client: Any) -> None:
        for item_id, current_time, duration in self.pending_progress():
            try:
                client.update_progress(item_id, current_time, duration)
            except Exception as error:   # still offline - try again later
                print(f"Offline progress sync failed: {error}")
                return
            with self._lock:
                manifest = self.load_manifest(item_id)
                if manifest and manifest.get("progress", {}).get("current_time") == current_time:
                    manifest["progress"]["pending"] = False
                    self.save_manifest(item_id, manifest)

    # ------------------------------------------------------------ offline session
    def offline_session(self, item_id: str, start_over: bool = False) -> PlaybackSession | None:
        if not self.is_complete(item_id):
            return None
        manifest = self.load_manifest(item_id) or {}
        directory = self.item_dir(item_id)
        tracks = [
            AudioTrack(
                index=int(t["index"]),
                start_offset=float(t["start_offset"]),
                duration=float(t["duration"]),
                url=(directory / t["file"]).as_uri(),
                title=str(t.get("title") or ""),
            )
            for t in manifest["tracks"]
        ]
        chapters = [Chapter(**c) for c in manifest.get("chapters", [])]
        progress = manifest.get("progress") or {}
        current_time = 0.0 if start_over else float(progress.get("current_time") or 0)
        duration = float(manifest.get("duration") or 0)
        if duration and current_time >= duration - 5:
            current_time = 0.0
        return PlaybackSession(
            id=OFFLINE_SESSION_PREFIX + item_id,
            library_item_id=item_id,
            title=str(manifest.get("title") or ""),
            author=str(manifest.get("author") or ""),
            duration=duration,
            current_time=current_time,
            cover_url=str(manifest.get("cover_url") or ""),
            tracks=tracks,
            chapters=chapters,
        )

    # ------------------------------------------------------------ size limit
    def usage_bytes(self) -> int:
        if not self.root.is_dir():
            return 0
        return sum(f.stat().st_size for f in self.root.rglob("*") if f.is_file())

    def free_bytes(self) -> int:
        self.root.mkdir(parents=True, exist_ok=True)
        return shutil.disk_usage(self.root).free

    def make_room(self, needed: int, keep: Iterable[str] = ()) -> bool:
        """Delete least recently played books until `needed` more bytes fit."""
        keep = set(keep)
        while True:
            fits_limit = self.usage_bytes() + needed <= self.max_bytes
            fits_card = self.free_bytes() - needed >= self.min_free_bytes
            if fits_limit and fits_card:
                return True
            candidates = sorted(
                (i for i in self.cached_item_ids() if i not in keep),
                key=lambda i: (self.load_manifest(i) or {}).get("last_used", 0),
            )
            if not candidates:
                return False
            victim = candidates[0]
            print(f"Audio cache: removing {victim} to free space")
            shutil.rmtree(self.item_dir(victim), ignore_errors=True)

    # ------------------------------------------------------------ downloads
    def start_download(self, session: PlaybackSession, client: Any) -> None:
        """Queue the missing tracks of `session` for a background download."""
        if not self.remember_session(session):
            return
        self.active_item_id = session.library_item_id
        self._jobs.put((session.library_item_id, client))
        with self._lock:
            if self._worker is None or not self._worker.is_alive():
                self._worker = threading.Thread(target=self._run, daemon=True, name="audio-cache")
                self._worker.start()

    def _run(self) -> None:
        while True:
            item_id, client = self._jobs.get()
            time.sleep(self.start_delay)
            try:
                self.flush_pending_progress(client)
                self.download_item(item_id, client)
            except Exception as error:
                print(f"Audio cache download failed for {item_id}: {error}")

    def download_item(self, item_id: str, client: Any) -> bool:
        manifest = self.load_manifest(item_id)
        if manifest is None:
            return False
        directory = self.item_dir(item_id)
        for track in manifest["tracks"]:
            target = directory / track["file"]
            if target.is_file():
                continue
            url = client.authenticated_media_url(track["content_path"])
            part = target.with_suffix(".part")
            with self.opener(Request(url), timeout=30) as response:
                size = int(response.headers.get("Content-Length") or 0)
                if not self.make_room(size, keep={item_id, self.active_item_id}):
                    print("Audio cache: not enough space, skipping download")
                    return False
                with part.open("wb") as handle:
                    while True:
                        chunk = response.read(CHUNK_BYTES)
                        if not chunk:
                            break
                        handle.write(chunk)
            if size and part.stat().st_size != size:
                part.unlink(missing_ok=True)
                raise OSError(f"incomplete download of track {track['index']}")
            part.replace(target)
        print(f"Audio cache: {manifest.get('title') or item_id} is stored locally")
        return True


class OfflineProgressClient:
    """Stand-in for AudiobookshelfClient while the server cannot be reached."""

    def __init__(self, cache: AudioCache) -> None:
        self.cache = cache

    def update_progress(self, item_id: str, current_time: float, _duration: float,
                        session_id: str = "", time_listened: float = 0) -> None:
        self.cache.record_progress(item_id, current_time, pending=True)


_shared: AudioCache | None = None


def shared_cache() -> AudioCache:
    global _shared
    if _shared is None:
        _shared = AudioCache()
    return _shared
