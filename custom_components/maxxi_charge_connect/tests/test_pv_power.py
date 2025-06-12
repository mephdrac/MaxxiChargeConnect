"""Tests für das PvPower-Modul der MaxxiChargeConnect-Integration.

Dieses Modul enthält Unit-Tests zur Überprüfung der Funktionalität des
PvPower-Sensors, insbesondere hinsichtlich:
- korrekter Initialisierung,
- Verarbeitung eingehender Daten über Webhook,
- Entfernung aus Home Assistant,
- korrekter Rückgabe von Geräteinformationen.
"""

import logging
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[3]))

from unittest.mock import MagicMock, patch
from homeassistant.const import CONF_WEBHOOK_ID, UnitOfPower
from homeassistant.components.sensor import SensorDeviceClass, SensorStateClass
import pytest

from custom_components.maxxi_charge_connect.const import DOMAIN
from custom_components.maxxi_charge_connect.devices.pv_power import PvPower


_LOGGER = logging.getLogger(__name__)


# Dummy-Konstanten
WEBHOOK_ID = "abc123"


@pytest.fixture
def mock_entry():
    """Gibt ein Mock-Konfigurationsobjekt für den Sensor zurück.

    Returns:
        MagicMock: Ein simuliertes Home Assistant-Konfigurationsobjekt.

    """
    entry = MagicMock()
    entry.entry_id = "test_entry_id"
    entry.title = "Maxxi Entry"
    entry.data = {"webhook_id": WEBHOOK_ID}
    return entry


@pytest.mark.asyncio
async def test_pv_power_initialization(mock_entry):
    """Testet die Initialisierung des PvPower-Sensors.

    Überprüft, ob alle relevanten Entitätsattribute korrekt gesetzt sind.
    """
    sensor = PvPower(mock_entry)

    assert sensor._attr_unique_id == "test_entry_id_pv_power"  # pylint: disable=protected-access
    assert sensor._attr_icon == "mdi:solar-power"  # pylint: disable=protected-access
    assert sensor._attr_native_value is None  # pylint: disable=protected-access
    assert sensor._attr_device_class == SensorDeviceClass.POWER  # pylint: disable=protected-access
    assert sensor._attr_state_class == SensorStateClass.MEASUREMENT
    # pylint: disable=protected-access
    assert sensor._attr_native_unit_of_measurement == UnitOfPower.WATT
    # pylint: disable=protected-access


@pytest.mark.asyncio
async def test_pv_power_add_and_handle_update1():
    """Testet den Update-Mechanismus, wenn `isPowerTotalOk` True ergibt.

    Erwartet, dass der Sensorwert korrekt auf die empfangene Leistung gesetzt wird.
    """

    mock_entry = MagicMock()
    mock_entry.entry_id = "abc123"
    mock_entry.title = "My Device"
    mock_entry.data = {CONF_WEBHOOK_ID: "webhook456"}

    sensor = PvPower(mock_entry)
    sensor.hass = MagicMock()
    sensor.async_on_remove = MagicMock()

    # async_write_ha_state mocken
    sensor.async_write_ha_state = MagicMock()

    dispatcher_called = {}

    with (
        patch(
            "custom_components.maxxi_charge_connect.devices.pv_power.async_dispatcher_connect"
        ) as mock_connect,
        patch(
            "custom_components.maxxi_charge_connect.devices.pv_power.isPowerTotalOk"
        ) as mock_is_power_total_ok,
    ):
        mock_is_power_total_ok.return_value = True

        def fake_unsub():
            dispatcher_called["disconnected"] = True

        mock_connect.return_value = fake_unsub

        await sensor.async_added_to_hass()

        signal = f"{DOMAIN}_webhook456_update_sensor"
        mock_connect.assert_called_once_with(sensor.hass, signal, sensor._handle_update)
        # pylint: disable=protected-access
        sensor.async_on_remove.assert_called_once_with(fake_unsub)

        await sensor._handle_update({"PV_power_total": 234.675})  # pylint: disable=protected-access
        assert sensor.native_value == 234.675


@pytest.mark.asyncio
async def test_pv_power_add_and_handle_update2():
    """Testet Verhalten bei ungültiger Leistung, wenn `isPowerTotalOk` False ergibt.

    Erwartet, dass der Sensorwert in diesem Fall nicht gesetzt wird (None).
    """

    mock_entry = MagicMock()
    mock_entry.entry_id = "abc123"
    mock_entry.title = "My Device"
    mock_entry.data = {CONF_WEBHOOK_ID: "webhook456"}

    sensor = PvPower(mock_entry)
    sensor.hass = MagicMock()
    sensor.async_on_remove = MagicMock()

    # async_write_ha_state mocken
    sensor.async_write_ha_state = MagicMock()

    dispatcher_called = {}

    with (
        patch(
            "custom_components.maxxi_charge_connect.devices.pv_power.async_dispatcher_connect"
        ) as mock_connect,
        patch(
            "custom_components.maxxi_charge_connect.devices.pv_power.isPowerTotalOk"
        ) as mock_is_power_total_ok,
    ):
        mock_is_power_total_ok.return_value = False

        def fake_unsub():
            dispatcher_called["disconnected"] = True

        mock_connect.return_value = fake_unsub

        await sensor.async_added_to_hass()

        signal = f"{DOMAIN}_webhook456_update_sensor"
        mock_connect.assert_called_once_with(sensor.hass, signal, sensor._handle_update)
        # pylint: disable=protected-access
        sensor.async_on_remove.assert_called_once_with(fake_unsub)

        await sensor._handle_update({"PV_power_total": 234})  # pylint: disable=protected-access
        assert sensor.native_value is None


def test_device_info(mock_entry):
    """Testet die `device_info`-Eigenschaft des Sensors.

    Erwartet korrekte Rückgabe der Geräteinformationen.
    """
    sensor = PvPower(mock_entry)
    info = sensor.device_info
    assert info["identifiers"] == {(DOMAIN, "test_entry_id")}
    assert info["name"] == "Maxxi Entry"
    assert info["manufacturer"] == "mephdrac"
    assert info["model"] == "CCU - Maxxicharge"
