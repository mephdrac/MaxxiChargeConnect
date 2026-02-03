"""Tests für die BatteryPowerDischarge Sensor Entität."""

from unittest.mock import AsyncMock, MagicMock, patch
from homeassistant.const import UnitOfPower
from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorStateClass,
)
import pytest
from custom_components.maxxi_charge_connect.devices.battery_power_discharge import (
    BatteryPowerDischarge,
)


@pytest.mark.asyncio
async def test_battery_power_discharge__init():
    """Testet die Initialisierung der BatteryPowerDischarge Entität."""

    dummy_config_entry = MagicMock()
    dummy_config_entry.entry_id = "1234abcd"
    dummy_config_entry.title = "Test Entry"

    sensor = BatteryPowerDischarge(dummy_config_entry)
    # Grundlegende Attribute prüfen
    assert sensor._entry == dummy_config_entry  # pylint: disable=protected-access
    assert sensor._attr_suggested_display_precision == 2  # pylint: disable=protected-access
    assert sensor._attr_device_class == SensorDeviceClass.POWER  # pylint: disable=protected-access
    assert sensor._attr_state_class == SensorStateClass.MEASUREMENT  # pylint: disable=protected-access
    assert sensor._attr_native_unit_of_measurement == UnitOfPower.WATT  # pylint: disable=protected-access
    assert sensor.icon == "mdi:battery-minus-variant"
    assert sensor._attr_unique_id == "1234abcd_battery_power_discharge"  # pylint: disable=protected-access
    assert sensor._attr_native_value is None  # pylint: disable=protected-access


@pytest.mark.asyncio
async def test_battery_power_discharge__device_info():
    """Testet die device_info Eigenschaft der BatteryPowerDischarge Entität."""

    dummy_config_entry = MagicMock()
    dummy_config_entry.title = "Test Entry"

    sensor = BatteryPowerDischarge(dummy_config_entry)

    # device_info liefert Dict mit erwarteten Keys
    device_info = sensor.device_info
    assert "identifiers" in device_info
    assert device_info["name"] == dummy_config_entry.title


@pytest.mark.asyncio
async def test_battery_power_discharge__handle_update_positive_power():
    """Testet die _handle_update Methode, wenn die Batterieleistung positiv ist (keine Entladung)."""

    dummy_config_entry = MagicMock()
    dummy_config_entry.data = {}

    pccu = 37.623
    pv_power = 218  # PV > CCU = keine Entladung

    data = {
        "Pccu": pccu,
        "PV_power_total": pv_power,
        "batteriesInfo": [
            {
                "batteryCapacity": 1187.339966
            }
        ]
    }
    sensor = BatteryPowerDischarge(dummy_config_entry)

    await sensor.handle_update(data)  # pylint: disable=protected-access

    assert sensor._attr_native_value is None  # pylint: disable=protected-access


@pytest.mark.asyncio
async def test_battery_power_discharge__handle_update_negative_power():
    """Testet die _handle_update Methode, wenn die Batterieleistung negativ ist (Entladung)."""

    dummy_config_entry = MagicMock()
    dummy_config_entry.data = {}

    pccu = 100.0
    pv_power = 50.0  # PV < CCU = Entladung

    data = {
        "Pccu": pccu,
        "PV_power_total": pv_power,
        "batteriesInfo": [
            {
                "batteryCapacity": 1187.339966
            }
        ]
    }

    sensor = BatteryPowerDischarge(dummy_config_entry)

    await sensor.handle_update(data)  # pylint: disable=protected-access

    assert sensor._attr_native_value == 50.0  # abs(50 - 100) = 50  # pylint: disable=protected-access


@pytest.mark.asyncio
async def test_battery_power_discharge__handle_update_zero_power():
    """Testet die _handle_update Methode, wenn die Batterieleistung 0 ist."""

    dummy_config_entry = MagicMock()
    dummy_config_entry.data = {}

    pccu = 100.0
    pv_power = 100.0  # PV == CCU = 0 Entladeleistung

    data = {
        "Pccu": pccu,
        "PV_power_total": pv_power,
        "batteriesInfo": [
            {
                "batteryCapacity": 1187.339966
            }
        ]
    }

    sensor = BatteryPowerDischarge(dummy_config_entry)

    await sensor.handle_update(data)  # pylint: disable=protected-access

    assert sensor._attr_native_value is None  # pylint: disable=protected-access


@pytest.mark.asyncio
async def test_battery_power_discharge__handle_update_missing_pccu():
    """Testet Verhalten bei fehlendem Pccu Feld."""
    
    dummy_config_entry = MagicMock()
    dummy_config_entry.data = {}

    data = {
        "PV_power_total": 200.0,
        "batteriesInfo": [
            {
                "batteryCapacity": 1187.339966
            }
        ]
    }

    sensor = BatteryPowerDischarge(dummy_config_entry)

    await sensor.handle_update(data)  # pylint: disable=protected-access

    assert sensor._attr_native_value is None  # pylint: disable=protected-access


@pytest.mark.asyncio
async def test_battery_power_discharge__handle_update_missing_pv_power():
    """Testet Verhalten bei fehlendem PV_power_total Feld."""
    
    dummy_config_entry = MagicMock()
    dummy_config_entry.data = {}

    data = {
        "Pccu": 50.0,
        "batteriesInfo": [
            {
                "batteryCapacity": 1187.339966
            }
        ]
    }

    sensor = BatteryPowerDischarge(dummy_config_entry)

    await sensor.handle_update(data)  # pylint: disable=protected-access

    assert sensor._attr_native_value is None  # pylint: disable=protected-access


@pytest.mark.asyncio
async def test_battery_power_discharge__handle_update_string_values():
    """Testet Konvertierung von String-Werten."""
    
    dummy_config_entry = MagicMock()
    dummy_config_entry.data = {}

    data = {
        "Pccu": "150.5",
        "PV_power_total": "50.5",
        "batteriesInfo": [
            {
                "batteryCapacity": 1187.339966
            }
        ]
    }

    sensor = BatteryPowerDischarge(dummy_config_entry)

    await sensor.handle_update(data)  # pylint: disable=protected-access
    
    assert sensor._attr_native_value == 100.0  # abs(50.5 - 150.5) = 100.0  # pylint: disable=protected-access


@pytest.mark.asyncio
async def test_battery_power_discharge__handle_update_invalid_string_values():
    """Testet Verhalten bei ungültigen String-Werten."""
    
    dummy_config_entry = MagicMock()
    dummy_config_entry.data = {}

    data = {
        "Pccu": "invalid",
        "PV_power_total": "150.5",
        "batteriesInfo": [
            {
                "batteryCapacity": 1187.339966
            }
        ]
    }

    sensor = BatteryPowerDischarge(dummy_config_entry)

    await sensor.handle_update(data)  # pylint: disable=protected-access

    assert sensor._attr_native_value is None  # pylint: disable=protected-access


@pytest.mark.asyncio
async def test_battery_power_discharge__handle_update_pccu_nicht_ok():
    """Testet die _handle_update Methode der BatteryPowerDischarge Entität, wenn PCCU nicht ok ist."""
    # is_pccu_ok(ccu) == false
    # is_power_total_ok(pv_power, batteries) == true

    dummy_config_entry = MagicMock()

    pccu = 36500
    pv_power = 218

    data = {
        "Pccu": pccu,
        "PV_power_total": pv_power,
        "batteriesInfo": [
            {
                "batteryCapacity": 1187.339966
            }
        ]
    }

    sensor1 = BatteryPowerDischarge(dummy_config_entry)

    with (
        patch(
            "custom_components.maxxi_charge_connect.devices.battery_power_discharge."
            "is_pccu_ok",
            return_value=False,
        ) as mock_is_pccu_ok1,
        patch(
            "custom_components.maxxi_charge_connect.devices.battery_power_discharge."
            "is_power_total_ok",
            return_value=True,
        ) as mock_is_power_ok1,
    ):
        await sensor1.handle_update(data)  # pylint: disable=protected-access

    mock_is_power_ok1.assert_not_called()
    mock_is_pccu_ok1.assert_called_once()

    args, kwargs = mock_is_pccu_ok1.call_args  # pylint: disable=unused-variable

    assert args[0] == pccu
    assert sensor1._attr_native_value is None  # pylint: disable=protected-access


@pytest.mark.asyncio
async def test_battery_power_discharge__handle_update_alles_nicht_ok():
    """Testet die _handle_update Methode der BatteryPowerDischarge Entität, wenn weder PCCU noch Leistung ok sind."""
    # is_pccu_ok(ccu) == false
    # is_power_total_ok(pv_power, batteries) == false

    dummy_config_entry = MagicMock()

    pccu = 36500
    pv_power = 218

    data = {
        "Pccu": pccu,
        "PV_power_total": pv_power,
        "batteriesInfo": [
            {
                "batteryCapacity": 1187.339966
            }
        ]
    }

    sensor1 = BatteryPowerDischarge(dummy_config_entry)

    with (
        patch(
            "custom_components.maxxi_charge_connect.devices.battery_power_discharge."
            "is_pccu_ok",
            return_value=False
        ) as mock_is_pccu_ok1,
        patch(
            "custom_components.maxxi_charge_connect.devices.battery_power_discharge."
            "is_power_total_ok",
            return_value=False
        ) as mock_is_power_ok1
    ):
        await sensor1.handle_update(data)  # pylint: disable=protected-access

        mock_is_power_ok1.assert_not_called()
        mock_is_pccu_ok1.assert_called_once()

        args, kwargs = mock_is_pccu_ok1.call_args  # pylint: disable=unused-variable

        assert args[0] == pccu
        assert sensor1._attr_native_value is None  # pylint: disable=protected-access


@pytest.mark.asyncio
async def test_battery_power_discharge__handle_update_power_total_nicht_ok():
    """Testet die _handle_update Methode der BatteryPowerDischarge Entität, wenn die Leistung nicht ok ist."""
    # is_pccu_ok(ccu) == true
    # is_power_total_ok(pv_power, batteries) == false
    dummy_config_entry = MagicMock()

    pccu = 45.345
    pv_power = 218

    data = {
        "Pccu": pccu,
        "PV_power_total": pv_power,
        "batteriesInfo": [
            {
                "batteryCapacity": 1187.339966
            }
        ]
    }

    sensor1 = BatteryPowerDischarge(dummy_config_entry)

    with (
        patch(
            "custom_components.maxxi_charge_connect.devices.battery_power_discharge."
            "is_pccu_ok",
            return_value=True
        ) as mock_is_pccu_ok1,
        patch(
            "custom_components.maxxi_charge_connect.devices.battery_power_discharge."
            "is_power_total_ok",
            return_value=False
        ) as mock_is_power_ok1
    ):

        await sensor1.handle_update(data)  # pylint: disable=protected-access

        mock_is_power_ok1.assert_called_once()
        mock_is_pccu_ok1.assert_called_once()

        args1, kwargs1 = mock_is_pccu_ok1.call_args  # pylint: disable=unused-variable
        args2, kwargs2 = mock_is_power_ok1.call_args  # pylint: disable=unused-variable
        assert args1[0] == pccu
        assert args2[0] == pv_power
        assert sensor1._attr_native_value is None  # pylint: disable=protected-access
