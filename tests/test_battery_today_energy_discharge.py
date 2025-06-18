"""Testmodul für die Klasse `BatteryTodayEnergyDischarge`.

Dieses Modul enthält einen Unit-Test zur Validierung des täglichen Energie-Resets
der `BatteryTodayEnergyDischarge`-Entität aus der Home Assistant-Integration
`maxxi_charge_connect`.

Testfall:
- Stellt sicher, dass der interne `last_reset`-Wert korrekt aktualisiert wird.
- Überprüft, ob der Zustand des Sensors anschließend geschrieben wird.
- Prüft, ob ein entsprechender Log-Eintrag erfolgt.

Verwendete Bibliotheken:
- datetime, unittest.mock, pytest
"""
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock
from homeassistant.util import dt as dt_util
import pytest

from custom_components.maxxi_charge_connect.devices.battery_today_energy_discharge import (
    BatteryTodayEnergyDischarge,
)


@pytest.mark.asyncio
async def test_reset_energy_daily_resets_last_reset_and_writes_state(caplog):
    """Teste täglichen Energie-Reset für `BatteryTodayEnergyDischarge`.

    Dieser Test überprüft:
    - Ob `last_reset` auf Mitternacht aktualisiert wird, wenn ein neuer Tag beginnt.
    - Ob `async_write_ha_state()` genau einmal aufgerufen wird.
    - Ob ein Log-Eintrag mit "Resetting daily energy" vorhanden ist.

    Args:
        caplog (pytest.LogCaptureFixture): Fixture zur Aufzeichnung von Lognachrichten.

    Raises:
        AssertionError: Falls `last_reset` nicht korrekt aktualisiert wird,
                        `async_write_ha_state()` nicht aufgerufen wird oder
                        kein entsprechender Logeintrag vorhanden ist.

    """

    # 🧪 Setup
    hass = MagicMock()
    hass.async_add_job = AsyncMock()

    entry = MagicMock()
    entry.entry_id = "test_entry"
    entry.title = "Test Entry"

    sensor = BatteryTodayEnergyDischarge(hass, entry, "sensor.pv_power")
    sensor.hass = hass
    sensor.async_write_ha_state = MagicMock()
    sensor._state = 200

    # 🎯 Simuliere "alten" Reset-Zeitpunkt
    yesterday = dt_util.start_of_local_day() - timedelta(days=1)
    sensor._last_reset = yesterday
    old_reset = sensor.last_reset

    # 🕛 Simuliere Reset-Zeitpunkt
    fake_now = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
    caplog.set_level("INFO")

    # 🔁 Reset aufrufen
    await sensor._reset_energy_daily(fake_now)

    # ✅ Überprüfungen
    assert sensor.last_reset > old_reset, "last_reset wurde nicht aktualisiert"
    sensor.async_write_ha_state.assert_called_once()
    assert sensor._state == 0.0  # pylint: disable=protected-access
    assert sensor.native_value == 0.0
    assert any("Resetting daily energy" in r.message for r in caplog.records), (
        "Reset-Log nicht gefunden"
    )
