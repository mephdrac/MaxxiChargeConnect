import pytest
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime, UTC, timedelta

from custom_components.maxxi_charge_connect.devices.BatteryTodayEnergyCharge import (
    BatteryTodayEnergyCharge,
)


@pytest.mark.asyncio
async def test_BatteryTodayEnergyCharge_reset_energy_daily_logs_and_resets(caplog):
    hass = MagicMock()
    hass.async_add_job = AsyncMock()

    class EntryMock:
        entry_id = "test_entry"
        title = "Test Entry"

    entry = EntryMock()
    source_entity_id = "sensor.pv_power"

    sensor = BatteryTodayEnergyCharge(hass, entry, source_entity_id)
    sensor.hass = hass
    sensor.entity_id = "sensor.test_pv_today_energy"

    sensor.async_write_ha_state = AsyncMock()  # Vor dem Aufruf mocken

    old_reset = sensor.last_reset
    fake_now = datetime.now(UTC) + timedelta(days=1)

    caplog.set_level("INFO")
    await sensor._reset_energy_daily(fake_now)

    # ✅ Überprüfungen
    sensor.async_write_ha_state.assert_awaited_once()
    assert sensor.last_reset > old_reset
    assert any("resetting daily energy" in rec.message for rec in caplog.records)
