"""Testmodul für die Klasse `BatteryTodayEnergyCharge`.

Dieses Modul enthält Unit-Tests zur Validierung des täglichen Energie-Resets
der `BatteryTodayEnergyCharge`-Entität innerhalb der Home Assistant-Integration
`maxxi_charge_connect`.

Testfall:
- Prüft, ob `last_reset` korrekt aktualisiert wird und der Zustand geschrieben wird,
  wenn der tägliche Reset durchgeführt wird.

Verwendete Bibliotheken:
- datetime, unittest.mock, pytest
"""

from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock
import sys
import pytest

from custom_components.maxxi_charge_connect.devices.battery_today_energy_charge import (
    BatteryTodayEnergyCharge,
)

sys.path.append(str(Path(__file__).resolve().parents[3]))


@pytest.mark.asyncio
async def test_reset_energy_daily_resets_last_reset_and_writes_state(caplog):
    """Teste den täglichen Energie-Reset der BatteryTodayEnergyCharge-Entität.

    Dieser Test prüft:
    - Ob `last_reset` auf Mitternacht gesetzt wird, wenn ein neuer Tag beginnt.
    - Ob `async_write_ha_state()` korrekt aufgerufen wird.
    - Ob ein entsprechender Log-Eintrag erzeugt wird.

    Args:
        caplog (pytest.LogCaptureFixture): Pytest-Log-Fixture zur Analyse von Logausgaben.

    Raises:
        AssertionError: Falls `last_reset` nicht aktualisiert wurde,

    """

    # 🧪 Setup
    hass = MagicMock()
    hass.async_add_job = AsyncMock()

    entry = MagicMock()
    entry.entry_id = "test_entry"
    entry.title = "Test Entry"

    sensor = BatteryTodayEnergyCharge(hass, entry, "sensor.pv_power")
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
