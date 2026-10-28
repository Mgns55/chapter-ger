import subprocess
import tempfile
import unittest
from dataclasses import replace
from datetime import date, datetime
from pathlib import Path
from unittest.mock import patch

from PIL import Image, ImageDraw

from abs_kids_player import appliance_io, boot_splash, listening_log, mqtt_bridge
from abs_kids_player.battery import BatteryMonitor, BatteryStatus, PiSugarBattery, percent_from_voltage
from abs_kids_player.config import (
    AppConfig,
    activate_profile,
    remove_profile,
    save_profile_from_login,
    with_current_login_in_profile,
)
from abs_kids_player.models import Book
from abs_kids_player.player_control import WebPlayerStatus
from abs_kids_player.rotary_ui import (
    ApplianceMenu,
    CommandType,
    HomeFrame,
    ProfileMenuFrame,
    Screen,
    library_entries,
    series_member_title,
)


def book(book_id, title, series="", sequence="", author="Ulf Blanck"):
    return Book(id=book_id, title=title, author=author, duration=100, cover_url="",
                series_name=series, series_sequence=sequence)


LIBRARY = [
    book("a", "Anna und der Zirkus", author="X"),
    book("k2", "Die drei ??? Kids: Gruselnacht", "Die drei ??? Kids", "2"),
    book("k1", "Die drei ??? Kids: Panik im Paradies", "Die drei ??? Kids", "1"),
    book("s1", "Solo", "Einzelserie", "1"),
    book("z", "Zebra", author="Y"),
]


class SeriesMenuTest(unittest.TestCase):
    def test_series_collapse_into_one_entry(self):
        entries = library_entries(LIBRARY)
        self.assertEqual(len(entries), 4)
        series = entries[1]
        self.assertEqual(series.series, "Die drei ??? Kids")
        self.assertEqual([LIBRARY[i].id for i in series.book_indexes], ["k1", "k2"])   # by sequence
        self.assertEqual(entries[2].series, "")    # a one-book series stays a book
        self.assertEqual(len(library_entries(LIBRARY, group_series=False)), 5)

    def test_member_title_drops_series_prefix(self):
        self.assertEqual(series_member_title(LIBRARY[1], "Die drei ??? Kids"), "Gruselnacht")

    def test_navigate_into_series_and_back(self):
        menu = ApplianceMenu(list(LIBRARY))
        menu.rotate_nav(1)
        frame = menu.render()
        self.assertIsInstance(frame, HomeFrame)
        self.assertEqual(frame.series_count, 2)
        menu.click_nav()
        self.assertEqual(menu.screen, Screen.SERIES)
        self.assertEqual(menu.render().title, "Panik im Paradies")
        menu.click_nav()
        self.assertEqual(menu.screen, Screen.RESUME_CHOICE)
        self.assertEqual(menu.books[menu.book_index].id, "k1")
        menu.resume_choice_index = 0        # "Home" goes back to the series list
        menu.click_nav()
        self.assertEqual(menu.screen, Screen.SERIES)
        menu.rotate_nav(-1)                 # "Back" entry
        self.assertTrue(menu.render().is_back)
        menu.click_nav()
        self.assertEqual(menu.screen, Screen.LIBRARY)

    def test_play_from_series(self):
        menu = ApplianceMenu(list(LIBRARY))
        menu.rotate_nav(1)
        menu.click_nav()
        menu.rotate_nav(1)
        menu.click_nav()
        commands = menu.click_nav()
        self.assertEqual(commands[0].type, CommandType.PLAY_BOOK)
        self.assertEqual(commands[0].book_id, "k2")

    def test_refresh_keeps_selection(self):
        menu = ApplianceMenu(list(LIBRARY))
        menu.rotate_nav(3)
        selected = menu.books[menu.book_index].id
        menu.set_books(list(reversed(LIBRARY)))
        self.assertEqual(menu.books[menu.book_index].id, selected)


class ProfileTest(unittest.TestCase):
    def test_profiles_switch_logins(self):
        config = AppConfig(server_url="https://abs", token="t-mika", username="mika", library_id="lib")
        config = save_profile_from_login(config, "Mika")
        config = replace(config, token="t-janne", username="janne")
        config = save_profile_from_login(config, "Janne")
        self.assertEqual(config.active_profile, "Janne")
        switched = activate_profile(config, "Mika")
        self.assertEqual((switched.username, switched.token), ("mika", "t-mika"))
        # a refreshed token of the active login is kept when switching away
        refreshed = replace(switched, token="t-mika-2")
        back = activate_profile(refreshed, "Janne")
        self.assertEqual(next(p for p in back.profiles if p.name == "Mika").token, "t-mika-2")
        self.assertEqual(len(remove_profile(back, "Mika").profiles), 1)
        with self.assertRaises(KeyError):
            activate_profile(config, "Nobody")
        plain = AppConfig(token="t")
        self.assertIs(with_current_login_in_profile(plain), plain)   # no profiles: unchanged

    def test_profile_menu_emits_switch(self):
        menu = ApplianceMenu(list(LIBRARY))
        menu.set_profiles(["Mika", "Janne"], "Mika")
        menu.open_profile_menu()
        self.assertIsInstance(menu.render(), ProfileMenuFrame)
        self.assertTrue(menu.render().active)
        menu.rotate_nav(1)
        commands = menu.click_nav()
        self.assertEqual(commands[0].type, CommandType.SWITCH_PROFILE)
        self.assertEqual(commands[0].profile_name, "Janne")
        self.assertEqual(menu.screen, Screen.LIBRARY)


def fake_i2c(values):
    def runner(args):
        register = int(args[4], 16)
        if register not in values:
            return subprocess.CompletedProcess(args, 1, "", "Error")
        return subprocess.CompletedProcess(args, 0, hex(values[register]) + "\n", "")
    return runner


class BatteryTest(unittest.TestCase):
    def test_reads_pisugar_registers(self):
        battery = PiSugarBattery(runner=fake_i2c({0x02: 0x80, 0x22: 0x0F, 0x23: 0xA0, 0x2A: 64}))
        self.assertEqual(battery.read(), BatteryStatus(percent=64, charging=True, voltage_mv=4000))

    def test_falls_back_to_voltage(self):
        battery = PiSugarBattery(runner=fake_i2c({0x02: 0x00, 0x22: 0x0E, 0x23: 0x7E, 0x2A: 0xFF}))
        status = battery.read()
        self.assertFalse(status.charging)
        self.assertEqual(status.percent, percent_from_voltage(3710))

    def test_no_board_means_no_battery(self):
        self.assertIsNone(PiSugarBattery(runner=fake_i2c({})).read())

    def test_monitor_warns_once_and_shuts_down_after_two_critical_readings(self):
        readings = iter([14, 13, 4, 4])
        battery = PiSugarBattery(runner=lambda a: None)
        battery.read = lambda: BatteryStatus(percent=next(readings), charging=False)
        monitor = BatteryMonitor(battery, poll_seconds=0)
        self.assertEqual(monitor.update(1), "warn")
        self.assertEqual(monitor.update(2), "")
        self.assertEqual(monitor.update(3), "")
        self.assertEqual(monitor.update(4), "shutdown")
        self.assertEqual(monitor.display_state, (4, False))


class ListeningLogTest(unittest.TestCase):
    def test_record_and_summarize(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "log.json"
            evening = datetime(2026, 10, 26, 20, 30)
            listening_log.record_listening("b1", "Buch", 60, "Mika", now=lambda: evening, path=path)
            listening_log.record_listening("b1", "Buch", 500, "Mika", now=lambda: evening, path=path)  # capped
            listening_log.record_listening("b2", "Anderes", 30, "Janne", now=lambda: evening, path=path)
            data = listening_log.load_log(path)
            summaries = listening_log.summarize(data, today=date(2026, 10, 26))
            mika = next(s for s in summaries if s.name == "Mika")
            self.assertEqual(mika.today_seconds, 60 + listening_log.MAX_CHUNK_SECONDS)
            self.assertEqual(mika.today_last, "20:30")
            self.assertEqual(mika.today_evening_seconds, mika.today_seconds)
            self.assertEqual(mika.top_books[0][0], "Buch")
            self.assertEqual(listening_log.today_seconds("", data, date(2026, 10, 26)), mika.today_seconds + 30)


class MqttTest(unittest.TestCase):
    def test_discovery_includes_battery_and_profiles_only_when_present(self):
        plain = [topic for topic, _ in mqtt_bridge.discovery_messages(WebPlayerStatus())]
        self.assertFalse(any("battery" in t or "profile_select" in t for t in plain))
        full = mqtt_bridge.discovery_messages(WebPlayerStatus(battery_percent=50, profiles=("Mika", "Janne")))
        topics = [topic for topic, _ in full]
        self.assertTrue(any(t.endswith("/battery/config") for t in topics))
        select = next(p for t, p in full if "profile_select" in t)
        self.assertEqual(select["options"], ["Mika", "Janne"])

    def test_status_payload(self):
        status = WebPlayerStatus(title="Buch", current_time=50, duration=200, is_playing=True,
                                 volume_percent=40, chapter="Kapitel 2", battery_percent=80)
        payload = mqtt_bridge.status_payload(status, 600)
        self.assertEqual(payload["state"], "playing")
        self.assertEqual(payload["progress"], 25.0)
        self.assertEqual(payload["battery"], 80)
        self.assertEqual(payload["listened_today"], 10)

    def test_commands_go_to_the_player_queue(self):
        base = mqtt_bridge.base_topic()
        with patch("abs_kids_player.mqtt_bridge.queue_web_player_command") as queue:
            mqtt_bridge.handle_message(f"{base}/command", "pause")
            mqtt_bridge.handle_message(f"{base}/volume/set", "35")
            mqtt_bridge.handle_message(f"{base}/profile/set", "Janne")
            mqtt_bridge.handle_message(f"{base}/command", "rm -rf")
        queue.assert_any_call("pause")
        queue.assert_any_call("volume", 35)
        queue.assert_any_call("switch_profile", text="Janne")
        self.assertEqual(queue.call_count, 3)


class FakePin:
    def __init__(self, log):
        self.log = log

    def on(self):
        self.log.append("DC1")

    def off(self):
        self.log.append("DC0")


class FakeSpi:
    def __init__(self, log):
        self.log = log

    def xfer2(self, values):
        self.log.append(("x", list(values)))

    def writebytes2(self, values):
        self.log.append(("w", len(values)))


class Ssd1322Test(unittest.TestCase):
    def make(self, flipped=False):
        log = []
        display = appliance_io.Ssd1322Display.__new__(appliance_io.Ssd1322Display)
        display.flipped = flipped
        display.image = Image.new("L", (256, 64), 0)
        display.draw = ImageDraw.Draw(display.image)
        display.dc = FakePin(log)
        display.cs = None
        display.spi = FakeSpi(log)
        return display, log

    def test_commands_and_parameters_use_dc(self):
        display, log = self.make()
        display.cmd(0xA0, 0x14, 0x11)
        self.assertEqual(log, ["DC0", ("x", [0xA0]), "DC1", ("w", 2)])

    def test_flush_writes_full_window(self):
        display, log = self.make()
        display.flush()
        commands = [entry[1][0] for entry in log if isinstance(entry, tuple) and entry[0] == "x"]
        self.assertEqual(commands, [0x15, 0x75, 0x5C])
        self.assertIn(("w", 8192), log)

    def test_create_display_picks_driver(self):
        with patch.object(appliance_io.Ssd1322Display, "__init__", return_value=None) as init:
            display = appliance_io.create_display("ssd1322_flipped", spi_bus=0)
        self.assertIsInstance(display, appliance_io.Ssd1322Display)
        init.assert_called_once_with(flipped=True, spi_bus=0)

    def test_boot_splash_rotation_is_reversible(self):
        packed = bytes(range(256)) * 32
        self.assertEqual(boot_splash.rotate_packed_180(boot_splash.rotate_packed_180(packed)), packed)
        self.assertEqual(boot_splash.rotate_packed_180(b"\x12\x34"), b"\x43\x21")


class HeadphoneTest(unittest.TestCase):
    def test_quick_menu_toggles_output(self):
        menu = ApplianceMenu(list(LIBRARY))
        self.assertFalse(menu.quick_menu_available)
        menu.set_headphones(True, False)
        self.assertTrue(menu.quick_menu_available)
        menu.open_quick_menu()
        self.assertEqual(menu.render().name, "Output: Speaker")
        commands = menu.click_nav()
        self.assertEqual(commands[0].type, CommandType.SET_HEADPHONES)
        self.assertTrue(commands[0].headphones)
        menu.open_quick_menu()
        self.assertEqual(menu.render().name, "Output: Headphones")

    def test_quick_menu_with_profiles_and_output(self):
        menu = ApplianceMenu(list(LIBRARY))
        menu.set_headphones(True, False)
        menu.set_profiles(["Mika", "Janne"], "Mika")
        self.assertEqual(menu.profile_options, ["Back", "Output: Speaker", "Mika", "Janne"])

    def test_playback_caps_headphone_volume(self):
        from abs_kids_player.playback import GStreamerPlayback, volume_amplitude

        playback = GStreamerPlayback()
        playback.volume_percent = 80
        with patch("abs_kids_player.playback.set_headphone_mixer_level") as mixer:
            playback.set_headphones_output(True, 50)
        mixer.assert_called_once()
        self.assertAlmostEqual(playback.target_effective_volume(), volume_amplitude(80) * 0.5)
        self.assertEqual(playback.audio_output_device, "headphones")
        playback.set_headphones_output(False)
        self.assertAlmostEqual(playback.target_effective_volume(), volume_amplitude(80))
        self.assertEqual(playback.audio_output_device, "")

    def test_speech_follows_limit(self):
        from abs_kids_player.oled_service import speech_volume

        class P:
            headphones_output = True
            headphone_volume_scale = 0.5

        self.assertEqual(speech_volume(60, P()), 30)

    def test_mqtt_output_select(self):
        messages = mqtt_bridge.discovery_messages(WebPlayerStatus(headphones_available=True))
        self.assertTrue(any(t.endswith("/output/config") for t, _ in messages))
        payload = mqtt_bridge.status_payload(WebPlayerStatus(output="headphones"), 0)
        self.assertEqual(payload["output"], "Kopfhörer")
        with patch("abs_kids_player.mqtt_bridge.queue_web_player_command") as queue:
            mqtt_bridge.handle_message(f"{mqtt_bridge.base_topic()}/output/set", "Kopfhörer")
        queue.assert_called_once_with("set_output", text="headphones")


if __name__ == "__main__":
    unittest.main()


class ScreenSaverNameTest(unittest.TestCase):
    def test_device_name_is_the_default_word(self):
        from abs_kids_player import config as cfg
        from abs_kids_player.oled_service import screen_saver_frame, screen_saver_words_for_mode
        with patch("socket.gethostname", return_value="franz"):
            self.assertEqual(cfg.screen_saver_word(cfg.AppConfig()), "Franz")
        with patch("socket.gethostname", return_value="raspberrypi"):
            self.assertEqual(cfg.screen_saver_word(cfg.AppConfig()), "chapter")
        self.assertEqual(cfg.screen_saver_word(cfg.AppConfig(screen_saver_word="Ida")), "Ida")
        words = screen_saver_words_for_mode("chapter", [], "Franz")
        self.assertEqual(screen_saver_frame(10, 0, words=words).words, ("Franz",))

    def test_health_snapshot_never_raises(self):
        from abs_kids_player.oled_service import health_snapshot
        self.assertIsInstance(health_snapshot(None), str)


class VolumeFollowsKnobTest(unittest.TestCase):
    def test_quick_knob_turns_do_not_queue_up(self):
        import threading
        import time as real_time
        from unittest.mock import Mock
        from abs_kids_player.playback import GStreamerPlayback, VOLUME_FADE_SECONDS
        playback = GStreamerPlayback()
        playback.playbin = Mock()
        playback._effective_volume = 0.0
        started = real_time.monotonic()
        threads = []
        for percent in range(10, 101, 10):          # ten clicks, each in its own thread like the UI
            playback.volume_percent = percent
            playback.muted = False
            thread = threading.Thread(target=playback.apply_audio_state)
            thread.start()
            threads.append(thread)
        for thread in threads:
            thread.join()
        elapsed = real_time.monotonic() - started
        self.assertLess(elapsed, 3 * VOLUME_FADE_SECONDS)    # used to be ~10 fades in a row
        self.assertAlmostEqual(playback._effective_volume, playback.target_effective_volume())


class VolumeCurveTest(unittest.TestCase):
    def test_knob_steps_are_even_in_decibels(self):
        import math
        from abs_kids_player.playback import volume_amplitude
        self.assertEqual(volume_amplitude(0), 0.0)
        self.assertAlmostEqual(volume_amplitude(100), 1.0)
        self.assertLess(20 * math.log10(volume_amplitude(5)), -40)      # quiet enough to fall asleep
        steps = [20 * math.log10(volume_amplitude(p)) for p in range(5, 101, 5)]
        diffs = {round(b - a, 6) for a, b in zip(steps, steps[1:])}
        self.assertEqual(len(diffs), 1)
