"""Testmodul für GridExportEnergyToday.

Dieses Modul testet das Verhalten des GridExportEnergyToday Sensors,
insbesondere das Zurücksetzen der Tagesenergie und die Aktualisierung
des letzten Reset-Zeitpunkts.
"""

import sys
from pathlib import Path
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock
from homeassistant.util import dt as dt_util
import pytest
from custom_components.maxxi_charge_connect.devices.grid_export_energy_today import (
    GridExportEnergyToday,
)

sys.path.append(str(Path(__file__).resolve().parents[3]))


@pytest.mark.asyncio
async def test_reset_energy_daily_resets_last_reset_and_writes_state(caplog):
    """Methode _reset_energy_daily und den letzten Reset-Zeitpunkt.

    Testet, ob die Methode _reset_energy_daily den letzten Reset-Zeitpunkt aktualisiert
    und den Zustand korrekt schreibt.

    Dabei wird ein "alter" Reset-Zeitpunkt simuliert und geprüft, ob nach dem Aufruf
    von _reset_energy_daily der Wert von last_reset erhöht wurde und
    async_write_ha_state aufgerufen wurde.

    Zusätzlich wird überprüft, ob ein entsprechender Log-Eintrag erzeugt wurde.

    Args:
        caplog: Pytest Fixture zum Abfangen von Log-Ausgaben.

    """
    # 🧪 Setup
    hass = MagicMock()
    hass.async_add_job = AsyncMock()

    entry = MagicMock()
    entry.entry_id = "test_entry"
    entry.title = "Test Entry"

    sensor = GridExportEnergyToday(hass, entry, "sensor.pv_power")
    sensor.hass = hass
    sensor.async_write_ha_state = MagicMock()
    sensor._state = 200  # pylint: disable=protected-access

    # 🎯 Simuliere "alten" Reset-Zeitpunkt
    yesterday = dt_util.start_of_local_day() - timedelta(days=1)
    sensor._last_reset = yesterday  # pylint: disable=protected-access
    old_reset = sensor.last_reset

    # 🕛 Simuliere Reset-Zeitpunkt
    fake_now = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
    caplog.set_level("INFO")

    # 🔁 Reset aufrufen
    await sensor._reset_energy_daily(fake_now)  # pylint: disable=protected-access

    # ✅ Überprüfungen
    assert sensor.last_reset > old_reset, "last_reset wurde nicht aktualisiert"
    sensor.async_write_ha_state.assert_called_once()
    assert sensor._state == 0.0  # pylint: disable=protected-access
    assert sensor.native_value == 0.0
    assert any("Resetting daily energy" in r.message for r in caplog.records), (
        "Reset-Log nicht gefunden"
    )
