"""Home Assistant integration over MQTT (with MQTT discovery).

Runs as its own small service. It reads the player status that the OLED
service already writes for the setup page and publishes it to MQTT; commands
from Home Assistant go into the same command queue the setup page uses.

Entities (all grouped under one device "Chapter Player <hostname>"):
  sensors        Status, Titel, Autor, Kapitel, Fortschritt, Akku, Profil, Hörzeit heute
  binary sensor  Lädt
  number         Lautstärke (settable)
  buttons        Abspielen, Pause
  select         Profil (only when profiles are configured)
"""
from __future__ import annotations

import json
import re
import socket
import time
from typing import Any

from . import __version__
from .config import AppConfig, load_config
from .listening_log import today_seconds
from .player_control import WebPlayerStatus, load_web_player_status, queue_web_player_command

DISCOVERY_PREFIX = "homeassistant"
STATUS_INTERVAL_SECONDS = 2.0
FULL_REPUBLISH_SECONDS = 300.0
CONFIG_CHECK_SECONDS = 30.0
STALE_STATUS_SECONDS = 120.0


def device_id() -> str:
    return "chapter_" + re.sub(r"[^a-z0-9_]", "_", socket.gethostname().lower())


def base_topic() -> str:
    return f"chapter/{device_id()}"


def playback_state(status: WebPlayerStatus) -> str:
    if not status.has_session:
        return "idle"
    return "playing" if status.is_playing else "paused"


def status_payload(status: WebPlayerStatus, profile_seconds_today: float) -> dict[str, Any]:
    progress = round(100 * status.current_time / status.duration, 1) if status.duration else 0
    return {
        "state": playback_state(status),
        "title": status.title,
        "author": status.author,
        "chapter": status.chapter,
        "progress": progress,
        "volume": 0 if status.muted else status.volume_percent,
        "battery": status.battery_percent if status.battery_percent >= 0 else None,
        "charging": "ON" if status.charging else "OFF",
        "profile": status.profile,
        "listened_today": round(profile_seconds_today / 60),
    }


def discovery_messages(status: WebPlayerStatus) -> list[tuple[str, dict[str, Any]]]:
    node = device_id()
    base = base_topic()
    device = {
        "identifiers": [node],
        "name": f"Chapter Player {socket.gethostname()}",
        "manufacturer": "Chapter (Mgns55/chapter-ger)",
        "model": "Audiobookshelf player",
        "sw_version": __version__,
    }
    common = {"availability_topic": f"{base}/availability", "device": device}

    def sensor(key: str, name: str, **extra: Any) -> tuple[str, dict[str, Any]]:
        return (
            f"{DISCOVERY_PREFIX}/sensor/{node}/{key}/config",
            {
                **common,
                "name": name,
                "unique_id": f"{node}_{key}",
                "state_topic": f"{base}/state",
                "value_template": "{{ value_json.%s }}" % key,
                **extra,
            },
        )

    messages = [
        sensor("state", "Status", icon="mdi:book-music"),
        sensor("title", "Titel", icon="mdi:book-open-variant"),
        sensor("author", "Autor", icon="mdi:account"),
        sensor("chapter", "Kapitel", icon="mdi:format-list-numbered"),
        sensor("progress", "Fortschritt", unit_of_measurement="%", icon="mdi:progress-clock"),
        sensor("listened_today", "Hörzeit heute", unit_of_measurement="min", icon="mdi:timer-outline"),
        sensor("profile", "Profil", icon="mdi:account-child"),
        (
            f"{DISCOVERY_PREFIX}/number/{node}/volume/config",
            {
                **common,
                "name": "Lautstärke",
                "unique_id": f"{node}_volume",
                "state_topic": f"{base}/state",
                "value_template": "{{ value_json.volume }}",
                "command_topic": f"{base}/volume/set",
                "min": 0,
                "max": 100,
                "step": 5,
                "unit_of_measurement": "%",
                "icon": "mdi:volume-high",
            },
        ),
        (
            f"{DISCOVERY_PREFIX}/button/{node}/play/config",
            {**common, "name": "Abspielen", "unique_id": f"{node}_play",
             "command_topic": f"{base}/command", "payload_press": "play", "icon": "mdi:play"},
        ),
        (
            f"{DISCOVERY_PREFIX}/button/{node}/pause/config",
            {**common, "name": "Pause", "unique_id": f"{node}_pause",
             "command_topic": f"{base}/command", "payload_press": "pause", "icon": "mdi:pause"},
        ),
    ]
    if status.battery_percent >= 0:
        messages.append(sensor("battery", "Akku", unit_of_measurement="%", device_class="battery",
                               state_class="measurement"))
        messages.append(
            (
                f"{DISCOVERY_PREFIX}/binary_sensor/{node}/charging/config",
                {**common, "name": "Lädt", "unique_id": f"{node}_charging",
                 "state_topic": f"{base}/state", "value_template": "{{ value_json.charging }}",
                 "device_class": "battery_charging"},
            )
        )
    if status.profiles:
        messages.append(
            (
                f"{DISCOVERY_PREFIX}/select/{node}/profile_select/config",
                {**common, "name": "Profil wählen", "unique_id": f"{node}_profile_select",
                 "state_topic": f"{base}/state", "value_template": "{{ value_json.profile }}",
                 "command_topic": f"{base}/profile/set", "options": list(status.profiles),
                 "icon": "mdi:account-switch"},
            )
        )
    return messages


def handle_message(topic: str, payload: str) -> None:
    base = base_topic()
    payload = payload.strip()
    if topic == f"{base}/command" and payload in {"play", "pause"}:
        queue_web_player_command(payload)
    elif topic == f"{base}/volume/set":
        try:
            queue_web_player_command("volume", min(max(int(float(payload)), 0), 100))
        except ValueError:
            pass
    elif topic == f"{base}/profile/set" and payload:
        queue_web_player_command("switch_profile", text=payload)


def make_client(config: AppConfig):
    import paho.mqtt.client as mqtt

    try:
        client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=device_id())
    except AttributeError:          # paho-mqtt 1.x
        client = mqtt.Client(client_id=device_id())
    if config.mqtt_username:
        client.username_pw_set(config.mqtt_username, config.mqtt_password or None)
    client.will_set(f"{base_topic()}/availability", "offline", retain=True)
    return client


def mqtt_settings(config: AppConfig) -> tuple:
    return (config.mqtt_enabled, config.mqtt_host, config.mqtt_port, config.mqtt_username, config.mqtt_password)


def run_bridge() -> None:
    client = None
    settings: tuple = ()
    last_config_check = -1e9
    last_payload: dict | None = None
    last_discovery_key: tuple = ()
    last_full_publish = 0.0
    while True:
        now = time.monotonic()
        if now - last_config_check >= CONFIG_CHECK_SECONDS:
            last_config_check = now
            config = load_config()
            wanted = mqtt_settings(config)
            if wanted != settings:
                if client is not None:
                    try:
                        client.publish(f"{base_topic()}/availability", "offline", retain=True)
                        client.loop_stop()
                        client.disconnect()
                    except Exception:
                        pass
                    client = None
                settings = wanted
                last_payload = None
                last_discovery_key = ()
                if config.mqtt_enabled and config.mqtt_host:
                    try:
                        client = make_client(config)
                        client.on_message = lambda _c, _u, msg: handle_message(
                            msg.topic, msg.payload.decode("utf-8", "replace")
                        )

                        def on_connect(c, _userdata, _flags, *rest):
                            nonlocal last_discovery_key, last_payload
                            base = base_topic()
                            c.subscribe([(f"{base}/command", 0), (f"{base}/volume/set", 0), (f"{base}/profile/set", 0)])
                            c.publish(f"{base}/availability", "online", retain=True)
                            last_discovery_key = ()
                            last_payload = None

                        client.on_connect = on_connect
                        client.connect_async(config.mqtt_host, config.mqtt_port, keepalive=60)
                        client.loop_start()
                        print(f"MQTT: connecting to {config.mqtt_host}:{config.mqtt_port}")
                    except Exception as error:
                        print(f"MQTT: could not start: {error}")
                        client = None
        if client is not None and client.is_connected():
            status = load_web_player_status()
            if status.updated_at and time.time() - status.updated_at > STALE_STATUS_SECONDS:
                status = WebPlayerStatus(volume_percent=status.volume_percent, profile=status.profile,
                                         profiles=status.profiles, battery_percent=status.battery_percent,
                                         charging=status.charging)
            discovery_key = (status.battery_percent >= 0, status.profiles)
            if discovery_key != last_discovery_key:
                for topic, payload in discovery_messages(status):
                    client.publish(topic, json.dumps(payload, ensure_ascii=False), retain=True)
                last_discovery_key = discovery_key
            payload = status_payload(status, today_seconds(status.profile))
            if payload != last_payload or now - last_full_publish >= FULL_REPUBLISH_SECONDS:
                client.publish(f"{base_topic()}/state", json.dumps(payload, ensure_ascii=False), retain=True)
                last_payload = payload
                last_full_publish = now
        time.sleep(STATUS_INTERVAL_SECONDS)


def main() -> None:
    try:
        import paho.mqtt.client  # noqa: F401
    except ImportError:
        print("MQTT: python3-paho-mqtt is not installed; Home Assistant integration disabled.")
        while True:
            time.sleep(3600)
    run_bridge()


if __name__ == "__main__":
    main()
