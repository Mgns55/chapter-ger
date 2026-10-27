import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from abs_kids_player import oled_service
from abs_kids_player.api import AudiobookshelfClient, AudiobookshelfError
from abs_kids_player.audio_cache import AudioCache, OfflineProgressClient, cacheable
from abs_kids_player.models import AudioTrack, Chapter, PlaybackSession
from abs_kids_player.playback import GStreamerPlayback


def make_session(item_id="li_1", current_time=12.0, paths=("/api/items/li_1/file/111", "/api/items/li_1/file/222")):
    tracks = [
        AudioTrack(index=i + 1, start_offset=i * 100.0, duration=100.0,
                   url=f"https://abs.example.com{p}?token=abc", title=f"Teil {i + 1}")
        for i, p in enumerate(paths)
    ]
    return PlaybackSession(
        id="sess", library_item_id=item_id, title="Die drei ??? Kids", author="Ulf Blanck",
        duration=100.0 * len(paths), current_time=current_time, cover_url="/cover",
        tracks=tracks, chapters=[Chapter(index=1, title="Kapitel 1", start=0, end=200)],
    )


class FakeResponse(io.BytesIO):
    def __init__(self, data: bytes):
        super().__init__(data)
        self.headers = {"Content-Length": str(len(data))}

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()


class FakeClient:
    def __init__(self):
        self.progress = []

    def authenticated_media_url(self, path):
        return "https://abs.example.com" + path + "?token=abc"

    def update_progress(self, item_id, current_time, duration, session_id="", time_listened=0):
        self.progress.append((item_id, current_time))


class AudioCacheTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name) / "audio"
        self.opened = []

        def opener(request, timeout=30):
            self.opened.append(request.full_url)
            return FakeResponse(b"ID3" + b"x" * 997)

        self.cache = AudioCache(root=self.root, max_bytes=10**9, min_free_bytes=0, opener=opener, start_delay=0)

    def tearDown(self):
        self.tmp.cleanup()

    def test_only_direct_play_urls_are_cached(self):
        self.assertTrue(cacheable("https://x/api/items/li_1/file/123?token=t"))
        self.assertFalse(cacheable("https://x/hls/abc/output.m3u8"))
        hls = make_session(paths=("/hls/abc/output.m3u8",))
        self.assertFalse(self.cache.remember_session(hls))

    def test_download_then_local_uri(self):
        session = make_session()
        self.cache.remember_session(session)
        self.assertIsNone(self.cache.local_uri("li_1", session.tracks[0]))
        self.assertTrue(self.cache.download_item("li_1", FakeClient()))
        self.assertEqual(len(self.opened), 2)
        uri = self.cache.local_uri("li_1", session.tracks[0])
        self.assertTrue(uri.startswith("file://") and uri.endswith("track-001.audio"))
        self.assertTrue(self.cache.is_complete("li_1"))
        # second run downloads nothing
        self.cache.download_item("li_1", FakeClient())
        self.assertEqual(len(self.opened), 2)

    def test_replaced_server_file_is_not_used(self):
        self.cache.remember_session(make_session())
        self.cache.download_item("li_1", FakeClient())
        changed = make_session(paths=("/api/items/li_1/file/999", "/api/items/li_1/file/222"))
        self.cache.remember_session(changed)
        self.assertIsNone(self.cache.local_uri("li_1", changed.tracks[0]))
        self.assertIsNotNone(self.cache.local_uri("li_1", changed.tracks[1]))

    def test_offline_session_uses_local_files_and_progress(self):
        self.cache.remember_session(make_session())
        self.assertIsNone(self.cache.offline_session("li_1"))      # not downloaded yet
        self.cache.download_item("li_1", FakeClient())
        self.cache.record_progress("li_1", 150.0, pending=False)
        offline = self.cache.offline_session("li_1")
        self.assertEqual(offline.current_time, 150.0)
        self.assertEqual(offline.title, "Die drei ??? Kids")
        self.assertTrue(all(t.url.startswith("file://") for t in offline.tracks))
        self.assertEqual(self.cache.offline_session("li_1", start_over=True).current_time, 0.0)

    def test_offline_progress_is_flushed_later(self):
        self.cache.remember_session(make_session())
        OfflineProgressClient(self.cache).update_progress("li_1", 88.0, 200.0)
        self.assertEqual(self.cache.pending_progress(), [("li_1", 88.0, 200.0)])
        client = FakeClient()
        self.cache.flush_pending_progress(client)
        self.assertEqual(client.progress, [("li_1", 88.0)])
        self.assertEqual(self.cache.pending_progress(), [])

    def test_least_recently_played_book_is_evicted(self):
        clock = iter(range(100, 1000))
        self.cache.clock = lambda: next(clock)
        for item in ("old", "new"):
            self.cache.remember_session(make_session(item_id=item, paths=(f"/api/items/{item}/file/1",)))
            self.cache.download_item(item, FakeClient())
        self.cache.max_bytes = self.cache.usage_bytes() + 500
        self.assertTrue(self.cache.make_room(1000, keep={"new"}))
        self.assertEqual(self.cache.cached_item_ids(), ["new"])


class ValidationTest(unittest.TestCase):
    def test_non_audio_download_is_rejected_and_bad_copies_are_dropped(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        html = b"<!doctype html><html>login</html>"
        cache = AudioCache(root=Path(tmp.name), max_bytes=10**9, min_free_bytes=0,
                           opener=lambda r, timeout=30: FakeResponse(html), start_delay=0)
        session = make_session(paths=("/api/items/li_1/file/1",))
        cache.remember_session(session)
        with self.assertRaises(OSError):
            cache.download_item("li_1", FakeClient())
        self.assertFalse(cache.is_complete("li_1"))
        # a broken file that is already on disk is removed on lookup
        bad = cache.item_dir("li_1") / "track-001.audio"
        bad.write_bytes(html)
        self.assertIsNone(cache.local_uri("li_1", session.tracks[0]))
        self.assertFalse(bad.exists())


class PlaybackUsesCacheTest(unittest.TestCase):
    def test_load_current_track_prefers_local_file(self):
        playback = GStreamerPlayback()
        playback.Gst = Mock()
        playback.playbin = Mock()
        playback.session = make_session()
        playback.client = Mock(spec=AudiobookshelfClient)
        playback.audio_cache = Mock()
        playback.audio_cache.local_uri.return_value = "file:///cache/li_1/track-001.audio"
        with patch.object(playback, "configure_audio_sink"), patch.object(playback, "wait_for_state_change"), \
                patch.object(playback, "seek_track"):
            playback.load_current_track(apply_audio=False)
        playback.playbin.set_property.assert_any_call("uri", "file:///cache/li_1/track-001.audio")
        playback.client.authenticated_media_url.assert_not_called()


class OfflineFallbackTest(unittest.TestCase):
    def test_server_unreachable_plays_local_copy(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        cache = AudioCache(root=Path(tmp.name), max_bytes=10**9, min_free_bytes=0,
                           opener=lambda r, timeout=30: FakeResponse(b"ID3" + b"x" * 9), start_delay=0)
        cache.remember_session(make_session())
        cache.download_item("li_1", FakeClient())
        playback = Mock()
        playback.audio_cache = cache
        client = Mock()
        client.start_playback.side_effect = AudiobookshelfError("Could not reach Audiobookshelf: offline")
        command = Mock(book_id="li_1", start_over=False, resume_time=0)
        config = Mock(is_ready=True, podcasts=[])
        with patch("abs_kids_player.oled_service.load_config", return_value=config), \
                patch("abs_kids_player.oled_service.podcast_by_book_id", return_value=None), \
                patch("abs_kids_player.oled_service.client_from_config", return_value=client):
            result = oled_service.play_book_command_result(command, playback)
        self.assertIsNone(result.error_frame)
        self.assertTrue(result.session.id.startswith("offline-"))
        self.assertIsInstance(result.client, OfflineProgressClient)
        playback.start.assert_called_once()


if __name__ == "__main__":
    unittest.main()
