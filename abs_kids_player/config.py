from __future__ import annotations

import json
import os
import threading
from dataclasses import asdict, dataclass, field, replace
from pathlib import Path

from .storage import ensure_storage_directory, finalize_storage_file


CONFIG_DIR = Path.home() / ".config" / "abs-kids-player"
CONFIG_PATH = CONFIG_DIR / "config.json"
SCREEN_SAVER_CHAPTER = "chapter"
SCREEN_SAVER_BOOKS = "books"
SCREEN_SAVER_CLOCK = "clock"
SCREEN_SAVER_MODES = (SCREEN_SAVER_CHAPTER, SCREEN_SAVER_BOOKS, SCREEN_SAVER_CLOCK)
LIBRARY_SORT_TITLE = "title"
LIBRARY_SORT_AUTHOR = "author"
LIBRARY_SORT_MODES = (LIBRARY_SORT_TITLE, LIBRARY_SORT_AUTHOR)
PLAYBACK_SPEEDS = (1.0, 1.5, 2.0)
DEFAULT_PLAYBACK_SPEED = 1.0
SCREEN_SAVER_DIM_LEVELS = (10, 15, 20, 25, 35, 50)
DEFAULT_SCREEN_SAVER_DIM_PERCENT = 15
DEFAULT_SLEEP_TIMER_MINUTES = 30
MIN_SLEEP_TIMER_MINUTES = 1
MAX_SLEEP_TIMER_MINUTES = 240
DISPLAY_SH1122 = "sh1122"                 # original 2.08" OLED
DISPLAY_SSD1322 = "ssd1322"               # 3.12" OLED (Chapter Pro)
DISPLAY_SSD1322_FLIPPED = "ssd1322_flipped"
DISPLAY_TYPES = (DISPLAY_SH1122, DISPLAY_SSD1322, DISPLAY_SSD1322_FLIPPED)
AMP_SHUTDOWN_GPIO = 17                    # physical pin 11 -> SD pin of the MAX98357A
DEFAULT_MQTT_PORT = 1883
HEADPHONE_MAX_PERCENTS = (30, 40, 50, 60, 70, 80, 100)
DEFAULT_HEADPHONE_MAX_PERCENT = 50
_CONFIG_LOCK = threading.RLock()


@dataclass(frozen=True)
class PodcastConfig:
    url: str
    title: str = ""
    author: str = ""
    feed_url: str = ""
    book_id: str = ""


def default_podcasts() -> list[PodcastConfig]:
    return []


@dataclass(frozen=True)
class ProfileConfig:
    """A saved Audiobookshelf login, e.g. one per child."""

    name: str
    username: str = ""
    token: str = ""
    refresh_token: str = ""
    library_id: str = ""


@dataclass
class AppConfig:
    server_url: str = ""
    token: str = ""
    refresh_token: str = ""
    library_id: str = ""
    username: str = ""
    control_click_enabled: bool = True
    spoken_navigation_enabled: bool = False
    library_sort_mode: str = LIBRARY_SORT_TITLE
    playback_speed: float = DEFAULT_PLAYBACK_SPEED
    screen_saver_mode: str = SCREEN_SAVER_CHAPTER
    screen_saver_dim_percent: int = DEFAULT_SCREEN_SAVER_DIM_PERCENT
    sleep_timer_enabled: bool = False
    sleep_timer_minutes: int = DEFAULT_SLEEP_TIMER_MINUTES
    bluetooth_enabled: bool = True
    podcasts: list[PodcastConfig] = field(default_factory=default_podcasts)
    display_type: str = DISPLAY_SH1122
    group_series: bool = True
    amp_idle_off: bool = False
    profiles: list[ProfileConfig] = field(default_factory=list)
    active_profile: str = ""
    mqtt_enabled: bool = False
    mqtt_host: str = ""
    mqtt_port: int = DEFAULT_MQTT_PORT
    mqtt_username: str = ""
    mqtt_password: str = ""
    headphones_enabled: bool = False                 # a headphone socket is wired to the Pi's jack
    headphone_max_percent: int = DEFAULT_HEADPHONE_MAX_PERCENT
    screen_saver_word: str = ""                      # empty = device name (hostname), e.g. "Franz"

    @property
    def is_ready(self) -> bool:
        return bool(self.server_url.strip() and self.token.strip())


def load_config() -> AppConfig:
    with _CONFIG_LOCK:
        path = config_path()
        if not path.exists():
            return AppConfig()

        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return AppConfig()

    return AppConfig(
        server_url=str(data.get("server_url", "")),
        token=str(data.get("token", "")),
        refresh_token=str(data.get("refresh_token", "")),
        library_id=str(data.get("library_id", "")),
        username=str(data.get("username", "")),
        control_click_enabled=bool(data.get("control_click_enabled", True)),
        spoken_navigation_enabled=bool(data.get("spoken_navigation_enabled", False)),
        library_sort_mode=valid_library_sort_mode(str(data.get("library_sort_mode", ""))),
        playback_speed=valid_playback_speed(data.get("playback_speed")),
        screen_saver_mode=valid_screen_saver_mode(str(data.get("screen_saver_mode", ""))),
        screen_saver_dim_percent=valid_screen_saver_dim_percent(data.get("screen_saver_dim_percent")),
        sleep_timer_enabled=bool(data.get("sleep_timer_enabled", False)),
        sleep_timer_minutes=valid_sleep_timer_minutes(data.get("sleep_timer_minutes")),
        bluetooth_enabled=bool(data.get("bluetooth_enabled", True)),
        podcasts=podcast_configs_from_json(data["podcasts"]) if "podcasts" in data else default_podcasts(),
        display_type=valid_display_type(str(data.get("display_type", ""))),
        group_series=bool(data.get("group_series", True)),
        amp_idle_off=bool(data.get("amp_idle_off", False)),
        profiles=profile_configs_from_json(data.get("profiles")),
        active_profile=str(data.get("active_profile", "")),
        mqtt_enabled=bool(data.get("mqtt_enabled", False)),
        mqtt_host=str(data.get("mqtt_host", "")).strip(),
        mqtt_port=valid_port(data.get("mqtt_port")),
        mqtt_username=str(data.get("mqtt_username", "")),
        mqtt_password=str(data.get("mqtt_password", "")),
        headphones_enabled=bool(data.get("headphones_enabled", False)),
        headphone_max_percent=valid_headphone_max_percent(data.get("headphone_max_percent")),
        screen_saver_word=valid_screen_saver_word(data.get("screen_saver_word")),
    )


def save_config(config: AppConfig) -> None:
    with _CONFIG_LOCK:
        path = config_path()
        temporary_path = path.with_name(
            f".{path.name}.{os.getpid()}.{threading.get_ident()}.tmp"
        )
        ensure_storage_directory(path.parent)
        try:
            temporary_path.write_text(json.dumps(asdict(config), indent=2), encoding="utf-8")
            finalize_storage_file(temporary_path)
            temporary_path.replace(path)
            finalize_storage_file(path)
        finally:
            temporary_path.unlink(missing_ok=True)


def saved_auth_tokens(server_url: str, username: str) -> tuple[str, str]:
    with _CONFIG_LOCK:
        config = load_config()
        if not same_login(config, server_url, username):
            return "", ""
        return config.token, config.refresh_token


def update_auth_tokens(
    server_url: str,
    username: str,
    token: str,
    refresh_token: str,
) -> bool:
    with _CONFIG_LOCK:
        config = load_config()
        if not same_login(config, server_url, username):
            return False
        if config.token == token and config.refresh_token == refresh_token:
            return True
        save_config(replace(config, token=token, refresh_token=refresh_token))
        return True


def same_login(config: AppConfig, server_url: str, username: str) -> bool:
    configured_server = config.server_url.strip().rstrip("/").casefold()
    expected_server = server_url.strip().rstrip("/").casefold()
    configured_username = config.username.strip().casefold()
    expected_username = username.strip().casefold()
    return configured_server == expected_server and configured_username == expected_username


def config_path() -> Path:
    configured_path = os.environ.get("ABS_KIDS_PLAYER_CONFIG_PATH", "").strip()
    if configured_path:
        return Path(configured_path).expanduser()

    configured_dir = os.environ.get("ABS_KIDS_PLAYER_CONFIG_DIR", "").strip()
    if configured_dir:
        return Path(configured_dir).expanduser() / "config.json"

    return CONFIG_PATH


def valid_screen_saver_mode(value: str) -> str:
    return value if value in SCREEN_SAVER_MODES else SCREEN_SAVER_CHAPTER


def valid_library_sort_mode(value: str) -> str:
    return value if value in LIBRARY_SORT_MODES else LIBRARY_SORT_TITLE


def valid_playback_speed(value: object) -> float:
    try:
        speed = float(value)
    except (TypeError, ValueError):
        return DEFAULT_PLAYBACK_SPEED
    return speed if speed in PLAYBACK_SPEEDS else DEFAULT_PLAYBACK_SPEED


def valid_screen_saver_word(value: object) -> str:
    return " ".join(str(value or "").split())[:16]


def default_screen_saver_word() -> str:
    """The device name, e.g. hostname "franz" -> "Franz"; generic names fall back to "chapter"."""
    import socket

    name = socket.gethostname().split(".")[0].strip()
    if not name or name.lower() in {"raspberrypi", "localhost", "chapter"}:
        return "chapter"
    return name[:1].upper() + name[1:]


def screen_saver_word(config: "AppConfig") -> str:
    return config.screen_saver_word or default_screen_saver_word()


def valid_screen_saver_dim_percent(value: object) -> int:
    try:
        percent = int(value)
    except (TypeError, ValueError):
        return DEFAULT_SCREEN_SAVER_DIM_PERCENT
    return percent if percent in SCREEN_SAVER_DIM_LEVELS else DEFAULT_SCREEN_SAVER_DIM_PERCENT


def valid_sleep_timer_minutes(value: object) -> int:
    try:
        minutes = int(value)
    except (TypeError, ValueError):
        return DEFAULT_SLEEP_TIMER_MINUTES
    return min(max(minutes, MIN_SLEEP_TIMER_MINUTES), MAX_SLEEP_TIMER_MINUTES)


def podcast_configs_from_json(value: object) -> list[PodcastConfig]:
    if not isinstance(value, list):
        return default_podcasts()

    podcasts: list[PodcastConfig] = []
    for item in value:
        if isinstance(item, str):
            url = item.strip()
            if url:
                podcasts.append(PodcastConfig(url=url))
            continue
        if not isinstance(item, dict):
            continue
        podcast = PodcastConfig(
            url=str(item.get("url", "")).strip(),
            title=str(item.get("title", "")).strip(),
            author=str(item.get("author", "")).strip(),
            feed_url=str(item.get("feed_url", "")).strip(),
            book_id=str(item.get("book_id", "")).strip(),
        )
        if podcast.url or podcast.feed_url:
            podcasts.append(podcast)
    return podcasts


def valid_display_type(value: str) -> str:
    return value if value in DISPLAY_TYPES else DISPLAY_SH1122


def valid_headphone_max_percent(value: object) -> int:
    try:
        percent = int(value)
    except (TypeError, ValueError):
        return DEFAULT_HEADPHONE_MAX_PERCENT
    return percent if percent in HEADPHONE_MAX_PERCENTS else DEFAULT_HEADPHONE_MAX_PERCENT


def valid_port(value: object) -> int:
    try:
        port = int(value)
    except (TypeError, ValueError):
        return DEFAULT_MQTT_PORT
    return port if 0 < port < 65536 else DEFAULT_MQTT_PORT


def profile_configs_from_json(value: object) -> list[ProfileConfig]:
    if not isinstance(value, list):
        return []
    profiles: list[ProfileConfig] = []
    seen: set[str] = set()
    for item in value:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name", "")).strip()
        if not name or name.casefold() in seen:
            continue
        seen.add(name.casefold())
        profiles.append(
            ProfileConfig(
                name=name,
                username=str(item.get("username", "")),
                token=str(item.get("token", "")),
                refresh_token=str(item.get("refresh_token", "")),
                library_id=str(item.get("library_id", "")),
            )
        )
    return profiles


def profile_by_name(config: AppConfig, name: str) -> ProfileConfig | None:
    wanted = name.strip().casefold()
    return next((p for p in config.profiles if p.name.casefold() == wanted), None)


def with_current_login_in_profile(config: AppConfig) -> AppConfig:
    """Copy the active login (tokens may have been refreshed) back into its profile entry."""
    active = profile_by_name(config, config.active_profile)
    if active is None or not config.token:
        return config
    updated = replace(
        active,
        username=config.username,
        token=config.token,
        refresh_token=config.refresh_token,
        library_id=config.library_id,
    )
    return replace(config, profiles=[updated if p is active else p for p in config.profiles])


def save_profile_from_login(config: AppConfig, name: str) -> AppConfig:
    """Store the login that is currently in `config` as profile `name` and make it active."""
    name = name.strip() or config.username.strip() or "Profil"
    profile = ProfileConfig(
        name=name,
        username=config.username,
        token=config.token,
        refresh_token=config.refresh_token,
        library_id=config.library_id,
    )
    others = [p for p in config.profiles if p.name.casefold() != name.casefold()]
    return replace(config, profiles=[*others, profile], active_profile=name)


def activate_profile(config: AppConfig, name: str) -> AppConfig:
    """Switch the player login to profile `name`; raises KeyError if it does not exist."""
    config = with_current_login_in_profile(config)
    target = profile_by_name(config, name)
    if target is None:
        raise KeyError(name)
    return replace(
        config,
        username=target.username,
        token=target.token,
        refresh_token=target.refresh_token,
        library_id=target.library_id,
        active_profile=target.name,
    )


def remove_profile(config: AppConfig, name: str) -> AppConfig:
    remaining = [p for p in config.profiles if p.name.casefold() != name.strip().casefold()]
    active = config.active_profile if profile_by_name(config, config.active_profile) in remaining else ""
    return replace(config, profiles=remaining, active_profile=active)
