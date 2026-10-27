from __future__ import annotations

import subprocess
import unittest

from abs_kids_player.wifi import (
    SETUP_HOTSPOT_SSID,
    active_wifi_connection_name,
    WifiError,
    connect_wifi,
    current_wifi_ssid,
    ensure_wifi_or_hotspot,
    forget_all_wifi_connections_and_start_hotspot,
    forget_current_wifi_and_start_hotspot,
    split_nmcli_fields,
    split_nmcli_pair,
    start_setup_hotspot,
    wifi_devices,
    wifi_is_connected,
    wifi_status,
)


class FakeRunner:
    def __init__(self, stdout: str = "") -> None:
        self.stdout = stdout
        self.calls: list[list[str]] = []

    def __call__(self, args: list[str]) -> subprocess.CompletedProcess:
        self.calls.append(args)
        return subprocess.CompletedProcess(args=args, returncode=0, stdout=self.stdout, stderr="")


class WifiTest(unittest.TestCase):
    def test_wifi_devices_parses_nmcli_output(self) -> None:
        runner = FakeRunner("wlan0:wifi:connected\nlo:loopback:connected\n")

        devices = wifi_devices(runner)

        self.assertEqual(devices[0].name, "wlan0")
        self.assertEqual(devices[0].state, "connected")

    def test_wifi_is_connected(self) -> None:
        runner = FakeRunner("wlan0:wifi:connected\n")

        self.assertTrue(wifi_is_connected(runner))

    def test_current_wifi_ssid_parses_active_network(self) -> None:
        runner = FakeRunner("no:Other Network\nyes:Chapter WiFi\n")

        self.assertEqual(current_wifi_ssid(runner), "Chapter WiFi")

    def test_current_wifi_ssid_unescapes_colons(self) -> None:
        runner = FakeRunner("yes:Kitchen\\: WiFi\n")

        self.assertEqual(current_wifi_ssid(runner), "Kitchen: WiFi")

    def test_wifi_status_reports_connected_ssid(self) -> None:
        runner = FakeRunner("yes:Chapter WiFi\n")

        status = wifi_status(runner)

        self.assertTrue(status.connected)
        self.assertEqual(status.ssid, "Chapter WiFi")

    def test_wifi_status_reports_disconnected(self) -> None:
        runner = FakeRunner("")

        status = wifi_status(runner)

        self.assertFalse(status.connected)
        self.assertEqual(status.message, "Not connected")

    def test_connect_wifi_saves_profile_then_leaves_hotspot(self) -> None:
        runner = FakeRunner()

        connect_wifi("Home WiFi", "secret-pass", device="wlan0", runner=runner, sleep=lambda _s: None)

        self.assertEqual(runner.calls[0], ["nmcli", "connection", "delete", "id", "Home WiFi"])
        add = runner.calls[1]
        self.assertEqual(add[:8], ["nmcli", "connection", "add", "type", "wifi", "ifname", "wlan0", "con-name"])
        self.assertIn("wpa-psk", add)
        self.assertEqual(add[add.index("wifi-sec.psk") + 1], "secret-pass")
        self.assertEqual(add[add.index("connection.autoconnect") + 1], "yes")
        self.assertIn(["nmcli", "connection", "down", "id", "Chapter-Setup"], runner.calls)
        self.assertEqual(runner.calls[-1], ["nmcli", "--wait", "40", "connection", "up", "id", "Home WiFi"])

    def test_connect_wifi_restarts_hotspot_when_joining_fails(self) -> None:
        class FailingUp(FakeRunner):
            def __call__(self, args):
                self.calls.append(args)
                if args[-3:-1] == ["up", "id"]:
                    raise subprocess.CalledProcessError(4, args, "", "Secrets were required")
                return subprocess.CompletedProcess(args=args, returncode=0, stdout="", stderr="")

        runner = FailingUp()
        with self.assertRaises(WifiError):
            connect_wifi("Home WiFi", "wrong", device="wlan0", runner=runner, sleep=lambda _s: None)
        self.assertTrue(any("Chapter-Setup" in call for call in runner.calls[-3:]))

    def test_retry_home_wifi_from_unused_hotspot(self) -> None:
        from abs_kids_player.wifi import retry_home_wifi_from_hotspot

        class Runner(FakeRunner):
            def __init__(self, stations=""):
                super().__init__()
                self.stations = stations

            def __call__(self, args):
                self.calls.append(args)
                out = ""
                if "ACTIVE,SSID" in args:
                    out = "yes:Chapter-Setup\n"
                elif "NAME,TYPE" in args:
                    out = "Chapter-Setup:802-11-wireless\nZuhause:802-11-wireless\n"
                elif "DEVICE,TYPE,STATE" in args:
                    out = "wlan0:wifi:connected\n"
                elif args[:2] == ["iw", "dev"]:
                    out = self.stations
                return subprocess.CompletedProcess(args=args, returncode=0, stdout=out, stderr="")

        busy = Runner(stations="Station aa:bb:cc:dd:ee:ff (on wlan0)")
        self.assertEqual(retry_home_wifi_from_hotspot(busy), "hotspot-in-use")
        idle = Runner()
        self.assertEqual(retry_home_wifi_from_hotspot(idle), "connected:Zuhause")
        self.assertIn(["nmcli", "--wait", "30", "connection", "up", "id", "Zuhause"], idle.calls)

    def test_active_wifi_connection_name_finds_wireless_connection(self) -> None:
        runner = FakeRunner("lo:loopback\nChapter WiFi:802-11-wireless\n")

        self.assertEqual(active_wifi_connection_name(runner), "Chapter WiFi")

    def test_forget_current_wifi_deletes_connection_and_starts_open_hotspot(self) -> None:
        class SequenceRunner:
            def __init__(self) -> None:
                self.calls: list[list[str]] = []

            def __call__(self, args: list[str]) -> subprocess.CompletedProcess:
                self.calls.append(args)
                if args == ["nmcli", "-t", "-f", "NAME,TYPE", "connection", "show", "--active"]:
                    stdout = "Chapter WiFi:802-11-wireless\n"
                elif args == ["nmcli", "-t", "-f", "DEVICE,TYPE,STATE", "device", "status"]:
                    stdout = "wlan0:wifi:connected\n"
                else:
                    stdout = ""
                return subprocess.CompletedProcess(
                    args=args,
                    returncode=0,
                    stdout=stdout,
                    stderr="",
                )

        runner = SequenceRunner()

        forget_current_wifi_and_start_hotspot(runner)

        self.assertEqual(
            runner.calls[2],
            ["nmcli", "connection", "down", "id", "Chapter WiFi"],
        )
        self.assertEqual(
            runner.calls[3],
            ["nmcli", "connection", "delete", "id", "Chapter WiFi"],
        )
        self.assertEqual(
            runner.calls[4],
            ["nmcli", "device", "disconnect", "wlan0"],
        )
        self.assertEqual(
            runner.calls[6],
            [
                "nmcli",
                "connection",
                "add",
                "type",
                "wifi",
                "ifname",
                "wlan0",
                "con-name",
                SETUP_HOTSPOT_SSID,
                "autoconnect",
                "no",
                "ssid",
                SETUP_HOTSPOT_SSID,
            ],
        )

    def test_forget_current_wifi_starts_hotspot_even_without_active_connection(self) -> None:
        class SequenceRunner:
            def __init__(self) -> None:
                self.calls: list[list[str]] = []

            def __call__(self, args: list[str]) -> subprocess.CompletedProcess:
                self.calls.append(args)
                if args == ["nmcli", "-t", "-f", "DEVICE,TYPE,STATE", "device", "status"]:
                    stdout = "wlan0:wifi:disconnected\n"
                else:
                    stdout = ""
                return subprocess.CompletedProcess(
                    args=args,
                    returncode=0,
                    stdout=stdout,
                    stderr="",
                )

        runner = SequenceRunner()

        forget_current_wifi_and_start_hotspot(runner)

        self.assertNotIn(["nmcli", "connection", "down", "id", ""], runner.calls)
        self.assertEqual(runner.calls[2], ["nmcli", "device", "disconnect", "wlan0"])
        self.assertEqual(runner.calls[3], ["nmcli", "connection", "delete", "id", SETUP_HOTSPOT_SSID])
        self.assertEqual(runner.calls[-1], ["nmcli", "connection", "up", SETUP_HOTSPOT_SSID])

    def test_forget_all_wifi_connections_deletes_each_saved_wifi_profile(self) -> None:
        class SequenceRunner:
            def __init__(self) -> None:
                self.calls: list[list[str]] = []

            def __call__(self, args: list[str]) -> subprocess.CompletedProcess:
                self.calls.append(args)
                if args == ["nmcli", "-t", "-f", "DEVICE,TYPE,STATE", "device", "status"]:
                    stdout = "wlan0:wifi:connected\n"
                elif args == ["nmcli", "-t", "-f", "NAME,TYPE", "connection", "show"]:
                    stdout = (
                        "Home WiFi:802-11-wireless\n"
                        "Grandparents WiFi:wifi\n"
                        f"{SETUP_HOTSPOT_SSID}:802-11-wireless\n"
                        "Wired connection:802-3-ethernet\n"
                    )
                else:
                    stdout = ""
                return subprocess.CompletedProcess(args=args, returncode=0, stdout=stdout, stderr="")

        runner = SequenceRunner()

        forget_all_wifi_connections_and_start_hotspot(runner)

        self.assertIn(["nmcli", "connection", "delete", "id", "Home WiFi"], runner.calls)
        self.assertIn(["nmcli", "connection", "delete", "id", "Grandparents WiFi"], runner.calls)
        self.assertNotIn(["nmcli", "connection", "delete", "id", "Wired connection"], runner.calls)
        self.assertEqual(runner.calls[-1], ["nmcli", "connection", "up", SETUP_HOTSPOT_SSID])

    def test_start_setup_hotspot_builds_open_hotspot_commands_by_default(self) -> None:
        runner = FakeRunner()

        start_setup_hotspot(device="wlan0", runner=runner)

        self.assertEqual(
            runner.calls[0],
            ["nmcli", "connection", "delete", "id", SETUP_HOTSPOT_SSID],
        )
        self.assertEqual(
            runner.calls[1],
            [
                "nmcli",
                "connection",
                "add",
                "type",
                "wifi",
                "ifname",
                "wlan0",
                "con-name",
                SETUP_HOTSPOT_SSID,
                "autoconnect",
                "no",
                "ssid",
                SETUP_HOTSPOT_SSID,
            ],
        )
        self.assertNotIn("wifi-sec.key-mgmt", runner.calls[2])
        self.assertEqual(runner.calls[3], ["nmcli", "connection", "up", SETUP_HOTSPOT_SSID])

    def test_start_setup_hotspot_can_build_password_hotspot_command(self) -> None:
        runner = FakeRunner()

        start_setup_hotspot(password="listen1234", device="wlan0", runner=runner)

        self.assertEqual(
            runner.calls[0][0:6],
            ["nmcli", "device", "wifi", "hotspot", "ifname", "wlan0"],
        )
        self.assertIn("password", runner.calls[0])
        self.assertIn("listen1234", runner.calls[0])

    def test_ensure_wifi_starts_hotspot_when_disconnected(self) -> None:
        runner = FakeRunner("wlan0:wifi:disconnected\n")

        result = ensure_wifi_or_hotspot(runner)

        self.assertEqual(result, "hotspot-started")
        self.assertEqual(len(runner.calls), 6)

    def test_ensure_wifi_does_not_start_hotspot_when_connected(self) -> None:
        runner = FakeRunner("wlan0:wifi:connected\n")

        result = ensure_wifi_or_hotspot(runner)

        self.assertEqual(result, "wifi-connected")
        self.assertEqual(len(runner.calls), 1)

    def test_ensure_wifi_waits_for_saved_network_before_hotspot(self) -> None:
        states = iter(["wlan0:wifi:disconnected\n", "Home:802-11-wireless\n", "wlan0:wifi:disconnected\n", "wlan0:wifi:connected\n"])

        def runner(args):
            return subprocess.CompletedProcess(args, 0, stdout=next(states), stderr="")

        clock = iter([0.0, 0.0, 3.0, 6.0])
        result = ensure_wifi_or_hotspot(runner, wait_seconds=90, sleep=lambda _: None, clock=lambda: next(clock))

        self.assertEqual(result, "wifi-connected")

    def test_ensure_wifi_starts_hotspot_after_waiting(self) -> None:
        calls = []

        def runner(args):
            calls.append(args)
            if "connection" in args:
                return subprocess.CompletedProcess(args, 0, stdout="Home:802-11-wireless\n", stderr="")
            return subprocess.CompletedProcess(args, 0, stdout="wlan0:wifi:disconnected\n", stderr="")

        times = iter([0.0, 0.0, 50.0, 100.0])
        result = ensure_wifi_or_hotspot(runner, wait_seconds=90, sleep=lambda _: None, clock=lambda: next(times, 200.0))

        self.assertEqual(result, "hotspot-started")

    def test_split_nmcli_pair_unescapes_colons(self) -> None:
        self.assertEqual(split_nmcli_pair("yes:Kitchen\\: WiFi"), ("yes", "Kitchen: WiFi"))

    def test_split_nmcli_fields_preserves_escaped_colons(self) -> None:
        self.assertEqual(
            split_nmcli_fields("Kitchen\\: WiFi:802-11-wireless"),
            ["Kitchen: WiFi", "802-11-wireless"],
        )


if __name__ == "__main__":
    unittest.main()
