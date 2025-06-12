"""Testmodul für GridImportEnergyToday.

Dieses Modul testet das tägliche Zurücksetzen der Energiezählung
des GridImportEnergyToday-Sensors.
"""

from unittest.mock import AsyncMock, MagicMock
from datetime import datetime, timedelta, UTC
import sys
from pathlib import Path

import pytest

from custom_components.maxxi_charge_connect.devices.grid_import_energy_today import (
    GridImportEnergyToday,
)

sys.path.append(str(Path(__file__).resolve().parents[3]))


@pytest.mark.asyncio
async def test_reset_energy_daily_resets_last_reset_and_writes_state(caplog):
    """Testet das tägliche Zurücksetzen des Energiewerts.

    Simuliert einen vergangenen Reset-Zeitpunkt und prüft,
    ob beim Aufruf von `_reset_energy_daily`:
    - der Reset-Zeitpunkt aktualisiert wird,
    - der neue Zustand gespeichert wird,
    - ein entsprechender Logeintrag erzeugt wird.

    Args:
        caplog: Pytest-Log-Capture-Fixture, um Lognachrichten zu überprüfen.

    """
    # 🧪 Setup
    hass = MagicMock()
    hass.async_add_job = AsyncMock()

    entry = MagicMock()
    entry.entry_id = "test_entry"
    entry.title = "Test Entry"

    sensor = GridImportEnergyToday(hass, entry, "sensor.pv_power")
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
