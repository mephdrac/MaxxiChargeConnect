"""Tests für das power_meter-Modul der MaxxiChargeConnect-Integration.

Dieses Testmodul prüft die Initialisierung, das Verhalten bei Zustandsänderungen
sowie das Entfernen des PowerMeter-Sensors aus Home Assistant. Dabei wird auf
korrekte Verarbeitung der Daten geachtet, insbesondere abhängig von `isPrOk()`.
"""

import logging
import sys
from pathlib import Path

from unittest.mock import MagicMock, patch
from homeassistant.components.sensor import SensorDeviceClass, SensorStateClass
from homeassistant.const import CONF_WEBHOOK_ID, UnitOfPower

import pytest

from custom_components.maxxi_charge_connect.const import DOMAIN
from custom_components.maxxi_charge_connect.devices.power_meter import PowerMeter

sys.path.append(str(Path(__file__).resolve().parents[3]))

_LOGGER = logging.getLogger(__name__)

# Dummy-Konstanten
WEBHOOK_ID = "abc123"


@pytest.fixture
def mock_entry():
    """Gibt ein Mock-Konfigurationsobjekt für einen Sensor zurück.

    Returns:
        MagicMock: Ein simuliertes Konfigurationsobjekt mit Entry-ID und Webhook-ID.

    """
    entry = MagicMock()
    entry.entry_id = "test_entry_id"
    entry.title = "Maxxi Entry"
    entry.data = {"webhook_id": WEBHOOK_ID}
    return entry


@pytest.mark.asyncio
async def test_power_meter_initialization(mock_entry):
    """Testet die Initialisierung des power_meter-Sensors.

    Stellt sicher, dass alle Attribute korrekt gesetzt werden.
    """
    sensor = PowerMeter(mock_entry)

    assert sensor._attr_unique_id == "test_entry_id_power_meter"  # pylint: disable=protected-access
    assert sensor._attr_icon == "mdi:gauge"  # pylint: disable=protected-access
    assert sensor._attr_native_value is None  # pylint: disable=protected-access
    assert sensor._attr_device_class == SensorDeviceClass.POWER  # pylint: disable=protected-access
    assert sensor._attr_state_class == SensorStateClass.MEASUREMENT
    # pylint: disable=protected-access
    assert sensor._attr_native_unit_of_measurement == UnitOfPower.WATT
    # pylint: disable=protected-access


@pytest.mark.asyncio
async def test_power_meter_add_and_handle_update1():
    """Testet Verarbeitung von Daten, wenn isPrOk True zurückgibt.

    Erwartet, dass der Sensorwert korrekt aktualisiert wird.

    Simuliert einen gültigen Leistungswert (`Pr`) und überprüft,
    ob dieser gesetzt wird.
    """

    mock_entry = MagicMock()
    mock_entry.entry_id = "abc123"
    mock_entry.title = "My Device"
    mock_entry.data = {CONF_WEBHOOK_ID: "webhook456"}

    sensor = PowerMeter(mock_entry)
    sensor.hass = MagicMock()
    sensor.async_on_remove = MagicMock()

    # async_write_ha_state mocken
    sensor.async_write_ha_state = MagicMock()

    dispatcher_called = {}

    with (
        patch(
            "custom_components.maxxi_charge_connect.devices.power_meter.async_dispatcher_connect"
        ) as mock_connect,
        patch(
            "custom_components.maxxi_charge_connect.devices.power_meter.is_pr_ok"
        ) as mock_is_pr_ok,
    ):
        mock_is_pr_ok.return_value = True

        def fake_unsub():
            dispatcher_called["disconnected"] = True

        mock_connect.return_value = fake_unsub

        await sensor.async_added_to_hass()

        signal = f"{DOMAIN}_webhook456_update_sensor"
        mock_connect.assert_called_once_with(sensor.hass, signal, sensor._handle_update)
        # pylint: disable=protected-access
        sensor.async_on_remove.assert_called_once_with(fake_unsub)

        await sensor._handle_update({"Pr": 234.675})  # pylint: disable=protected-access
        assert sensor.native_value == 234.675


@pytest.mark.asyncio
async def test_power_meter_add_and_handle_update2():
    """Testet Verhalten, wenn isPrOk False zurückgibt.

    Erwartet, dass der Sensorwert nicht gesetzt wird.
    """
    mock_entry = MagicMock()
    mock_entry.entry_id = "abc123"
    mock_entry.title = "My Device"
    mock_entry.data = {CONF_WEBHOOK_ID: "webhook456"}

    sensor = PowerMeter(mock_entry)
    sensor.hass = MagicMock()
    sensor.async_on_remove = MagicMock()

    # async_write_ha_state mocken
    sensor.async_write_ha_state = MagicMock()

    dispatcher_called = {}

    with (
        patch(
            "custom_components.maxxi_charge_connect.devices.power_meter.async_dispatcher_connect"
        ) as mock_connect,
        patch(
            "custom_components.maxxi_charge_connect.devices.power_meter.is_pr_ok"
        ) as mock_is_pr_ok,
    ):
        mock_is_pr_ok.return_value = False

        def fake_unsub():
            dispatcher_called["disconnected"] = True

        mock_connect.return_value = fake_unsub

        await sensor.async_added_to_hass()

        signal = f"{DOMAIN}_webhook456_update_sensor"
        mock_connect.assert_called_once_with(sensor.hass, signal, sensor._handle_update)
        # pylint: disable=protected-access
        sensor.async_on_remove.assert_called_once_with(fake_unsub)

        await sensor._handle_update({"Pr": 234.675})  # pylint: disable=protected-access
        assert sensor.native_value is None


def test_device_info(mock_entry):
    """Testet die `device_info`-Eigenschaft des power_meter-Sensors.

    Erwartet die korrekte Rückgabe der Geräteinformationen.
    """
    sensor = PowerMeter(mock_entry)
    info = sensor.device_info
    assert info["identifiers"] == {(DOMAIN, "test_entry_id")}
    assert info["name"] == "Maxxi Entry"
    assert info["manufacturer"] == "mephdrac"
    assert info["model"] == "CCU - Maxxicharge"
