import io
import os
import queue
import unittest
from unittest.mock import Mock, patch

from PIL import Image

from abs_kids_player import oled_service
from abs_kids_player.appliance_io import InputEvent, pack_sh1122
from abs_kids_player.config import AppConfig
from abs_kids_player.player_control import WebPlayerStatus
from abs_kids_player.setup_server import (
    SetupHandler,
    apply_bluetooth_radio,
    bluetooth_status,
    render_settings_card,
    save_bluetooth_setting,
)


class BluetoothSettingTest(unittest.TestCase):
    def test_bluetooth_is_enabled_by_default(self) -> None:
        self.assertTrue(AppConfig().bluetooth_enabled)

    def test_save_bluetooth_setting_keeps_login(self) -> None:
        config = AppConfig(server_url="https://books.example.com", token="token")
        with (
            patch("abs_kids_player.setup_server.load_config", return_value=config),
            patch("abs_kids_player.setup_server.save_config") as save_config,
        ):
            updated = save_bluetooth_setting(False)
        self.assertFalse(updated.bluetooth_enabled)
        self.assertEqual(updated.token, "token")
        save_config.assert_called_once_with(updated)

    def test_post_saves_and_switches_radio(self) -> None:
        body = b"enabled=0"
        handler = object.__new__(SetupHandler)
        handler.headers = {"Content-Length": str(len(body))}
        handler.rfile = io.BytesIO(body)
        handler.redirect_home = Mock()
        with (
            patch("abs_kids_player.setup_server.save_bluetooth_setting") as save_setting,
            patch("abs_kids_player.setup_server.apply_bluetooth_radio") as apply_radio,
        ):
            handler.handle_bluetooth_setting_post()
        save_setting.assert_called_once_with(False)
        apply_radio.assert_called_once_with(False)
        handler.redirect_home.assert_called_once_with()

    def test_apply_bluetooth_radio_uses_rfkill(self) -> None:
        runner = Mock()
        apply_bluetooth_radio(False, runner=runner)
        apply_bluetooth_radio(True, runner=runner)
        runner.assert_any_call(["rfkill", "block", "bluetooth"])
        runner.assert_any_call(["rfkill", "unblock", "bluetooth"])

    def test_status_skips_bluetoothctl_when_off(self) -> None:
        with (
            patch("abs_kids_player.setup_server.load_config", return_value=AppConfig(bluetooth_enabled=False)),
            patch("abs_kids_player.setup_server.connected_bluetooth_audio_device") as device,
        ):
            self.assertEqual(bluetooth_status(), (False, "Off"))
        device.assert_not_called()

    def test_settings_card_has_bluetooth_toggle(self) -> None:
        html = render_settings_card(AppConfig(bluetooth_enabled=False))
        self.assertIn('action="/settings/bluetooth"', html)
        self.assertIn("Enable Bluetooth", html)

    def test_hold_does_not_open_bluetooth_menu_when_off(self) -> None:
        events: queue.SimpleQueue[InputEvent] = queue.SimpleQueue()
        events.put(InputEvent("nav_hold"))
        menu = Mock()
        result = oled_service.handle_oled_input_events(events, menu, bluetooth_available=False)
        menu.hold_nav.assert_not_called()
        self.assertEqual(result[4], [])


class PerformanceTest(unittest.TestCase):
    def test_fast_pack_matches_pixel_loop(self) -> None:
        image = Image.frombytes("L", (256, 64), os.urandom(256 * 64))
        pixels = image.load()
        expected = bytearray()
        for y in range(image.height):
            for x in range(0, image.width, 2):
                expected.append(((pixels[x, y] >> 4) << 4) | (pixels[x + 1, y] >> 4))
        self.assertEqual(pack_sh1122(image), expected)

    def test_web_status_written_only_when_needed(self) -> None:
        playback = Mock()
        statuses = [
            WebPlayerStatus(title="Buch", current_time=10, is_playing=True),
            WebPlayerStatus(title="Buch", current_time=10.2, is_playing=True),
            WebPlayerStatus(title="Buch", current_time=10.4, is_playing=False),
        ]
        oled_service._last_web_status = None
        with (
            patch("abs_kids_player.oled_service.web_status_for_playback", side_effect=statuses),
            patch("abs_kids_player.oled_service.save_web_player_status") as save,
        ):
            oled_service.publish_web_player_status(playback, 50, False)
            oled_service.publish_web_player_status(playback, 50, False)
            oled_service.publish_web_player_status(playback, 50, False)
        self.assertEqual(save.call_count, 2)


if __name__ == "__main__":
    unittest.main()
