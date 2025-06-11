"""Testklasse."""

from pathlib import Path
import sys

sys.path.append(str(Path(__file__).resolve().parents[3]))

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

from custom_components.maxxi_charge_connect.devices.battery_today_energy_discharge import (
    BatteryTodayEnergyDischarge,
)
import pytest


@pytest.mark.asyncio
async def test_reset_energy_daily_resets_last_reset_and_writes_state(caplog):
    """Testfall."""
    # 🧪 Setup
    hass = MagicMock()
    hass.async_add_job = AsyncMock()

    entry = MagicMock()
    entry.entry_id = "test_entry"
    entry.title = "Test Entry"

    sensor = BatteryTodayEnergyDischarge(hass, entry, "sensor.pv_power")
    sensor.hass = hass
    sensor.async_write_ha_state = AsyncMock()

    # 🎯 Simuliere "alten" Reset-Zeitpunkt
    yesterday = datetime.now(UTC) - timedelta(days=1)
    sensor._last_reset = yesterday  # noqa: SLF001
    old_reset = sensor.last_reset

    # 🕛 Simuliere Reset-Zeitpunkt
    fake_now = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
    caplog.set_level("INFO")

    # 🔁 Reset aufrufen
    await sensor._reset_energy_daily(fake_now)  # noqa: SLF001

    # ✅ Überprüfungen
    assert sensor.last_reset > old_reset, "last_reset wurde nicht aktualisiert"
    sensor.async_write_ha_state.assert_awaited_once()
    assert any("Resetting daily energy" in r.message for r in caplog.records), (
        "Reset-Log nicht gefunden"
    )
