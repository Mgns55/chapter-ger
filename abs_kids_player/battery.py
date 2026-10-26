"""Battery status from a PiSugar 3 / 3 Plus UPS board (I2C address 0x57).

Nothing here is required: without a PiSugar (or with I2C switched off) every
read returns None and the player simply shows no battery.

The values come from the PiSugar 3 I2C register map:
  0x02 bit 7   external power connected (charger plugged in)
  0x22, 0x23   battery voltage in mV (high, low byte)
  0x2A         battery level in percent
"""
from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass
from typing import Callable

PISUGAR_BUS = 1
PISUGAR_ADDRESS = 0x57
REG_STATUS = 0x02
REG_VOLTAGE_HIGH = 0x22
REG_VOLTAGE_LOW = 0x23
REG_PERCENT = 0x2A

LOW_BATTERY_WARNING_PERCENT = 15
CRITICAL_BATTERY_PERCENT = 5

# Single-cell LiPo, voltage under light load -> charge (used when 0x2A is not plausible)
VOLTAGE_CURVE = ((4160, 100), (4050, 90), (3950, 80), (3870, 70), (3800, 60), (3750, 50),
                 (3710, 40), (3680, 30), (3640, 20), (3580, 10), (3450, 5), (3300, 0))

Runner = Callable[[list[str]], subprocess.CompletedProcess]


@dataclass(frozen=True)
class BatteryStatus:
    percent: int
    charging: bool
    voltage_mv: int = 0

    @property
    def low(self) -> bool:
        return not self.charging and self.percent <= LOW_BATTERY_WARNING_PERCENT

    @property
    def critical(self) -> bool:
        return not self.charging and self.percent <= CRITICAL_BATTERY_PERCENT


def run_command(args: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(args, capture_output=True, text=True, timeout=3, check=False)


class PiSugarBattery:
    def __init__(self, runner: Runner = run_command, bus: int = PISUGAR_BUS, address: int = PISUGAR_ADDRESS) -> None:
        self.runner = runner
        self.bus = bus
        self.address = address
        self.available = shutil.which("i2cget") is not None or runner is not run_command

    def read_register(self, register: int) -> int | None:
        result = self.runner(["i2cget", "-y", str(self.bus), hex(self.address), hex(register), "b"])
        if result.returncode != 0:
            return None
        try:
            return int(result.stdout.strip(), 16)
        except ValueError:
            return None

    def read(self) -> BatteryStatus | None:
        if not self.available:
            return None
        try:
            status = self.read_register(REG_STATUS)
            if status is None:
                return None
            high = self.read_register(REG_VOLTAGE_HIGH)
            low = self.read_register(REG_VOLTAGE_LOW)
            percent = self.read_register(REG_PERCENT)
        except (OSError, subprocess.SubprocessError):
            return None
        voltage = ((high or 0) << 8) | (low or 0)
        if percent is None or not 0 <= percent <= 100:
            if not 2500 <= voltage <= 4500:
                return None
            percent = percent_from_voltage(voltage)
        return BatteryStatus(percent=int(percent), charging=bool(status & 0x80), voltage_mv=voltage)


def percent_from_voltage(voltage_mv: int) -> int:
    if voltage_mv >= VOLTAGE_CURVE[0][0]:
        return 100
    for (v_high, p_high), (v_low, p_low) in zip(VOLTAGE_CURVE, VOLTAGE_CURVE[1:]):
        if voltage_mv >= v_low:
            return round(p_low + (p_high - p_low) * (voltage_mv - v_low) / (v_high - v_low))
    return 0


class BatteryMonitor:
    """Polls the battery and decides when to warn and when to shut down."""

    def __init__(self, battery: PiSugarBattery | None = None, poll_seconds: float = 30.0) -> None:
        self.battery = battery or PiSugarBattery()
        self.poll_seconds = poll_seconds
        self.status: BatteryStatus | None = None
        self.last_poll = -1e9
        self.warned = False
        self.misses = 0
        self.critical_readings = 0

    def update(self, now: float) -> str:
        """Returns "" , "warn" (once per discharge) or "shutdown"."""
        if now - self.last_poll < self.poll_seconds:
            return ""
        self.last_poll = now
        status = self.battery.read()
        if status is None:
            self.misses += 1
            if self.misses >= 3:          # board removed or I2C off
                self.status = None
            return ""
        self.misses = 0
        self.status = status
        if status.charging or status.percent > LOW_BATTERY_WARNING_PERCENT + 3:
            self.warned = False
        self.critical_readings = self.critical_readings + 1 if status.critical else 0
        if self.critical_readings >= 2:          # two readings in a row, not a voltage dip
            return "shutdown"
        if status.low and not self.warned:
            self.warned = True
            return "warn"
        return ""

    @property
    def display_state(self) -> tuple[int, bool] | None:
        return (self.status.percent, self.status.charging) if self.status else None
