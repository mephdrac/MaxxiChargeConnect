"""Tests für den täglichen Reset des PvTodayEnergy Sensors.

Dieses Modul testet die `_reset_energy_daily`-Methode, die täglich um Mitternacht
den internen `last_reset`-Zeitstempel aktualisiert und den Sensorzustand neu schreibt.
"""

from unittest.mock import AsyncMock, MagicMock
from datetime import datetime, timedelta, UTC
from homeassistant.util import dt as dt_util
import pytest

from custom_components.maxxi_charge_connect.devices.battery_today_energy_charge import (
    BatteryTodayEnergyCharge,
)


@pytest.mark.asyncio
async def test_reset_energy_daily_resets_last_reset_and_writes_state(caplog):
    """Testet, ob `_reset_energy_daily` den Reset-Zeitpunkt aktualisiert und den Zustand schreibt.

    Dieser Test simuliert einen alten `last_reset`-Wert, ruft dann `_reset_energy_daily`
    mit einem neuen Tageswechsel-Zeitpunkt auf, und überprüft:

    - ob `last_reset` aktualisiert wurde,
    - ob `async_write_ha_state` aufgerufen wurde,
    - ob eine entsprechende Logmeldung geschrieben wurde.

    Args:
        caplog (LogCaptureFixture): Pytest-Funktion zur Überwachung von Logausgaben.

    """
    # 🧪 Setup
    hass = MagicMock()
    hass.async_add_job = AsyncMock()

    entry = MagicMock()
    entry.entry_id = "test_entry"
    entry.title = "Test Entry"

    sensor = BatteryTodayEnergyCharge(hass, entry, "sensor.pv_power")
    # sensor.native_value = 200.0  # pylint: disable=protected-access
    sensor.hass = hass
    sensor.async_write_ha_state = MagicMock()
    sensor._state = 200

    # 🎯 Simuliere "alten" Reset-Zeitpunkt
    yesterday = dt_util.start_of_local_day() - timedelta(days=1)
    sensor._last_reset = yesterday  # pylint: disable=protected-access
    old_reset = sensor.last_reset

    # 🕛 Simuliere Reset-Zeitpunkt
    fake_now = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
    caplog.set_level("INFO")

    # 🔁 Reset aufrufen
    # await sensor._reset_energy_daily(fake_now)  # pylint: disable=protected-access
    await sensor._reset_energy_daily(fake_now)

    # ✅ Überprüfungen
    assert sensor.last_reset > old_reset, "last_reset wurde nicht aktualisiert"
    sensor.async_write_ha_state.assert_called_once()
    assert sensor._state == 0.0  # pylint: disable=protected-access
    assert sensor.native_value == 0.0
    assert any("Resetting daily energy" in r.message for r in caplog.records), (
        "Reset-Log nicht gefunden"
    )
