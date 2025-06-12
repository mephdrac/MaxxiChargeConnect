"""Tests für den täglichen Reset des PvSelfConsumptionEnergyToday-Sensors.

Dieses Modul testet die `_reset_energy_daily`-Methode, die täglich um Mitternacht
den internen `last_reset`-Zeitstempel aktualisiert und den Sensorzustand neu schreibt.
"""

import sys
from pathlib import Path

from unittest.mock import AsyncMock, MagicMock
from datetime import datetime, timedelta, UTC
import pytest

from custom_components.maxxi_charge_connect.devices.pv_self_consumption_energy_today import (
    PvSelfConsumptionEnergyToday
)

sys.path.append(str(Path(__file__).resolve().parents[3]))


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

    sensor = PvSelfConsumptionEnergyToday(hass, entry, "sensor.pv_power")
    sensor.hass = hass
    sensor.async_write_ha_state = AsyncMock()

    # 🎯 Simuliere "alten" Reset-Zeitpunkt
    yesterday = datetime.now(UTC) - timedelta(days=1)
    sensor._last_reset = yesterday  # pylint: disable=protected-access
    old_reset = sensor.last_reset

    # 🕛 Simuliere Reset-Zeitpunkt
    fake_now = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
    caplog.set_level("INFO")

    # 🔁 Reset aufrufen
    await sensor._reset_energy_daily(fake_now)  # pylint: disable=protected-access

    # ✅ Überprüfungen
    assert sensor.last_reset > old_reset, "last_reset wurde nicht aktualisiert"
    sensor.async_write_ha_state.assert_awaited_once()
    assert any("Resetting daily energy" in r.message for r in caplog.records), (
        "Reset-Log nicht gefunden"
    )
