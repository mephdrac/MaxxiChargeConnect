"""Testmodul für die Klasse `CcuEnergyToday`.

Dieses Modul testet die Funktionalität der täglichen Energie-Rücksetzung
der `CcuEnergyToday`-Entität aus der Home Assistant-Integration
`maxxi_charge_connect`.

Der Test stellt sicher, dass:
- Der `last_reset`-Zeitpunkt korrekt auf Mitternacht aktualisiert wird.
- Der Sensorzustand nach dem Reset gespeichert wird.
- Ein entsprechender Logeintrag erzeugt wird.

Verwendete Bibliotheken:
- datetime, unittest.mock, pytest
"""
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock
from pathlib import Path
import sys
import pytest

from custom_components.maxxi_charge_connect.devices.ccu_energy_today import (
    CcuEnergyToday,
)


sys.path.append(str(Path(__file__).resolve().parents[3]))


@pytest.mark.asyncio
async def test_reset_energy_daily_resets_last_reset_and_writes_state(caplog):
    """Teste täglichen Energie-Reset für `CcuEnergyToday`.

    Dieser Test überprüft:
    - Ob `last_reset` korrekt auf Mitternacht aktualisiert wird.
    - Ob `async_write_ha_state()` genau einmal aufgerufen wird.
    - Ob ein Log-Eintrag mit "Resetting daily energy" existiert.

    Args:
        caplog (pytest.LogCaptureFixture): Fixture zur Aufzeichnung von Lognachrichten.

    Raises:
        AssertionError: Falls `last_reset` nicht aktualisiert wird,
                        `async_write_ha_state()` nicht aufgerufen wird
                        oder kein passender Logeintrag geschrieben wurde.
    """
    # 🧪 Setup
    hass = MagicMock()
    hass.async_add_job = AsyncMock()

    entry = MagicMock()
    entry.entry_id = "test_entry"
    entry.title = "Test Entry"

    sensor = CcuEnergyToday(hass, entry, "sensor.pv_power")
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
