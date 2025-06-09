import pytest
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime, UTC

from ..devices.PvSelfConsumptionEnergyToday import PvSelfConsumptionEnergyToday


@pytest.mark.asyncio
async def test_BatteryTodayEnergyCharge_reset_energy_daily_logs_and_resets(caplog):
    hass = MagicMock()
    hass.async_add_job = AsyncMock()

    class EntryMock:
        entry_id = "test_entry"
        title = "Test Entry"

    entry = EntryMock()
    source_entity_id = "sensor.pv_power"

    sensor = PvSelfConsumptionEnergyToday(hass, entry, source_entity_id)
    sensor.hass = hass
    sensor.entity_id = "sensor.test_pv_today_energy"

    sensor._integration = MagicMock()
    sensor._integration.reset = MagicMock()

    sensor.async_write_ha_state = AsyncMock()  # <== HIER MOCKEN!

    caplog.set_level("INFO")
    now = datetime.now(UTC)

    await sensor._reset_energy_daily(now)

    sensor._integration.reset.assert_called_once()
    sensor.async_write_ha_state.assert_awaited_once()

    assert any("resetting daily energy" in rec.message for rec in caplog.records)
