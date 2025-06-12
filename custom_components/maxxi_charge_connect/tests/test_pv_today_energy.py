"""Tests für das tägliche Zurücksetzen des PvTodayEnergy-Sensors.

Dieses Modul testet die Methode `_reset_energy_daily` der Klasse `PvTodayEnergy`,
welche täglich um Mitternacht die Energiestatistik zurücksetzt und den Zustand aktualisiert.
"""
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime, UTC
import pytest

from ..devices.pv_today_energy import PvTodayEnergy


@pytest.mark.asyncio
async def test_reset_energy_daily_logs_and_resets(caplog):
    """Testet, ob `_reset_energy_daily` die Energie zurücksetzt und Log-Eintrag schreibt.

    Dieser Test prüft, ob beim täglichen Reset:

    - die `reset()`-Methode der Integration aufgerufen wird,
    - `async_write_ha_state()` ausgeführt wird,
    - ein entsprechender Log-Eintrag erfolgt.

    Args:
        caplog (LogCaptureFixture): Pytest-Funktion zur Erfassung von Logmeldungen.

    """
    hass = MagicMock()
    hass.async_add_job = AsyncMock()

    class EntryMock:
        """Hilfsklasse"""
        entry_id = "test_entry"
        title = "Test Entry"

    entry = EntryMock()
    source_entity_id = "sensor.pv_power"

    sensor = PvTodayEnergy(hass, entry, source_entity_id)
    sensor.hass = hass
    sensor.entity_id = "sensor.test_pv_today_energy"

    sensor._integration = MagicMock()  # pylint: disable=protected-access
    sensor._integration.reset = MagicMock()  # pylint: disable=protected-access

    sensor.async_write_ha_state = AsyncMock()  # <== HIER MOCKEN!

    caplog.set_level("INFO")
    now = datetime.now(UTC)

    await sensor._reset_energy_daily(now)  # pylint: disable=protected-access

    sensor._integration.reset.assert_called_once()  # pylint: disable=protected-access
    sensor.async_write_ha_state.assert_awaited_once()

    assert any("resetting daily energy" in rec.message for rec in caplog.records)
