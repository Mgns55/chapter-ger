"""Local record of listening time, shown to parents on the setup page.

Stored as one small JSON file in the player's state directory:

    {"days": {"2026-10-26": {"<profile>": {"seconds": 1830, "last": "20:41",
                                           "evening_seconds": 300,
                                           "books": {"<item id>": {"title": "...", "seconds": 1830}}}}}}

Only the last ``KEEP_DAYS`` days are kept.
"""
from __future__ import annotations

import json
import os
import threading
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Callable

KEEP_DAYS = 60
EVENING_HOUR = 20                 # listening from 20:00 on counts as "evening"
MAX_CHUNK_SECONDS = 120.0         # ignore implausible jumps (e.g. after suspend)
_LOCK = threading.Lock()


def log_path() -> Path:
    configured = os.environ.get("ABS_KIDS_PLAYER_STATE_DIR", "").strip()
    base = Path(configured).expanduser() if configured else Path.home() / ".local" / "state" / "abs-kids-player"
    return base / "listening-log.json"


def load_log(path: Path | None = None) -> dict:
    try:
        data = json.loads((path or log_path()).read_text(encoding="utf-8"))
        return data if isinstance(data, dict) and isinstance(data.get("days"), dict) else {"days": {}}
    except (OSError, ValueError):
        return {"days": {}}


def record_listening(
    item_id: str,
    title: str,
    seconds: float,
    profile: str = "",
    now: Callable[[], datetime] = datetime.now,
    path: Path | None = None,
) -> None:
    if seconds <= 0 or not item_id:
        return
    seconds = min(float(seconds), MAX_CHUNK_SECONDS)
    moment = now()
    path = path or log_path()
    with _LOCK:
        data = load_log(path)
        days = data["days"]
        day = days.setdefault(moment.date().isoformat(), {})
        entry = day.setdefault(profile or "-", {"seconds": 0.0, "last": "", "evening_seconds": 0.0, "books": {}})
        entry["seconds"] = float(entry.get("seconds", 0)) + seconds
        entry["last"] = moment.strftime("%H:%M")
        if moment.hour >= EVENING_HOUR or moment.hour < 5:
            entry["evening_seconds"] = float(entry.get("evening_seconds", 0)) + seconds
        book = entry.setdefault("books", {}).setdefault(item_id, {"title": title, "seconds": 0.0})
        book["title"] = title or book.get("title", "")
        book["seconds"] = float(book.get("seconds", 0)) + seconds
        cutoff = (moment.date() - timedelta(days=KEEP_DAYS)).isoformat()
        for key in [k for k in days if k < cutoff]:
            del days[key]
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            tmp = path.with_suffix(".tmp")
            tmp.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
            tmp.replace(path)
        except OSError as error:
            print(f"Listening log could not be saved: {error}")


@dataclass
class ProfileSummary:
    name: str
    today_seconds: float = 0.0
    today_last: str = ""
    today_evening_seconds: float = 0.0
    week_seconds: float = 0.0
    daily: list[tuple[str, float]] = field(default_factory=list)      # last 7 days, oldest first
    top_books: list[tuple[str, float]] = field(default_factory=list)  # last 30 days


def summarize(data: dict | None = None, today: date | None = None) -> list[ProfileSummary]:
    data = data if data is not None else load_log()
    today = today or date.today()
    days = data.get("days", {})
    profiles = sorted({name for day in days.values() for name in day})
    summaries = []
    for name in profiles:
        summary = ProfileSummary(name="" if name == "-" else name)
        books: dict[str, list] = {}
        for offset in range(30):
            key = (today - timedelta(days=offset)).isoformat()
            entry = days.get(key, {}).get(name)
            seconds = float(entry.get("seconds", 0)) if entry else 0.0
            if offset < 7:
                summary.daily.insert(0, (key, seconds))
                summary.week_seconds += seconds
            if offset == 0 and entry:
                summary.today_seconds = seconds
                summary.today_last = str(entry.get("last", ""))
                summary.today_evening_seconds = float(entry.get("evening_seconds", 0))
            for item_id, book in (entry or {}).get("books", {}).items():
                slot = books.setdefault(item_id, [book.get("title", ""), 0.0])
                slot[0] = book.get("title", "") or slot[0]
                slot[1] += float(book.get("seconds", 0))
        summary.top_books = sorted(((t, s) for t, s in books.values()), key=lambda b: -b[1])[:5]
        summaries.append(summary)
    return summaries


def today_seconds(profile: str = "", data: dict | None = None, today: date | None = None) -> float:
    data = data if data is not None else load_log()
    day = data.get("days", {}).get((today or date.today()).isoformat(), {})
    if profile:
        return float(day.get(profile, {}).get("seconds", 0))
    return sum(float(entry.get("seconds", 0)) for entry in day.values())
