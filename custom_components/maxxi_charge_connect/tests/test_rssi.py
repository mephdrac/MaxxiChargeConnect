"""Tests für das Rssi-Sensorgerät von MaxxiChargeConnect.

Dieses Modul enthält Tests für die Klasse `Rssi`, die die WLAN-Signalstärke
als Sensorwert in Home Assistant abbildet.
Geprüft werden:
- die Initialisierung des Sensors,
- das korrekte Registrieren von Updates über den Dispatcher,
- das Verhalten beim Entfernen aus Home Assistant,
- und die bereitgestellten Gerätedaten.
"""

import logging
import sys
from pathlib import Path

from unittest.mock import MagicMock, patch
from homeassistant.const import CONF_WEBHOOK_ID, SIGNAL_STRENGTH_DECIBELS_MILLIWATT
from homeassistant.components.sensor import SensorDeviceClass
from homeassistant.helpers.entity import EntityCategory

import pytest
from custom_components.maxxi_charge_connect.const import DOMAIN
from custom_components.maxxi_charge_connect.devices.rssi import Rssi

sys.path.append(str(Path(__file__).resolve().parents[3]))

_LOGGER = logging.getLogger(__name__)

# Dummy-Konstanten
WEBHOOK_ID = "abc123"


@pytest.fixture
def mock_entry_entry():
    """Erstellt einen gefälschten ConfigEntry für die Tests."""
    entry = MagicMock()
    entry.entry_id = "test_entry_id"
    entry.title = "Maxxi Entry"
    entry.data = {"webhook_id": WEBHOOK_ID}
    return entry


@pytest.mark.asyncio
async def test_rssi_initialization(mock_entry):
    """Testet die Initialisierung des Rssi-Sensors.

    Überprüft, ob alle erwarteten Eigenschaften (unique_id, Icon, Klasse, Einheit etc.)
    korrekt gesetzt werden.
    """
    sensor = Rssi(mock_entry)

    assert sensor._attr_unique_id == "test_entry_id_rssi"  # pylint: disable=protected-access
    assert sensor._attr_icon == "mdi:wifi"  # pylint: disable=protected-access
    assert sensor._attr_native_value is None  # pylint: disable=protected-access
    assert sensor._attr_device_class == SensorDeviceClass.SIGNAL_STRENGTH\
        # pylint: disable=protected-access
    assert sensor._attr_native_unit_of_measurement == SIGNAL_STRENGTH_DECIBELS_MILLIWATT\
        # pylint: disable=protected-access
    assert sensor._attr_entity_category == EntityCategory.DIAGNOSTIC\
        # pylint: disable=protected-access


@pytest.mark.asyncio
async def test_rssi_add_and_handle_update():
    """Testet das Registrieren und Verarbeiten von Updates via Dispatcher.

    Es wird simuliert, dass ein Dispatcher-Signal empfangen wird und
    der Sensorwert (`native_value`) aktualisiert wird.
    """
    mock_entry = MagicMock()
    mock_entry.entry_id = "abc123"
    mock_entry.title = "My Device"
    mock_entry.data = {CONF_WEBHOOK_ID: "webhook456"}

    sensor = Rssi(mock_entry)
    sensor.hass = MagicMock()
    sensor.async_on_remove = MagicMock()
    sensor.async_write_ha_state = MagicMock()

    dispatcher_called = {}

    with patch(
        "custom_components.maxxi_charge_connect.devices.Rssi.async_dispatcher_connect"
    ) as mock_connect:

        def fake_unsub():
            dispatcher_called["disconnected"] = True

        mock_connect.return_value = fake_unsub

        await sensor.async_added_to_hass()

        signal = f"{DOMAIN}_webhook456_update_sensor"
        mock_connect.assert_called_once_with(sensor.hass, signal, sensor._handle_update)\
            # pylint: disable=protected-access
        sensor.async_on_remove.assert_called_once_with(fake_unsub)

        await sensor._handle_update({"wifiStrength": -42})  # pylint: disable=protected-access
        assert sensor.native_value == -42


@pytest.mark.asyncio
async def test_rssi_will_remove_from_hass(mock_entry):
    """Testet das Entfernen des Sensors aus Home Assistant.

    Verifiziert, dass der Dispatcher abgemeldet wird, wenn
    `async_will_remove_from_hass` aufgerufen wird.
    """
    sensor = Rssi(mock_entry)

    disconnected = {"called": False}

    def unsub():
        disconnected["called"] = True

    sensor._unsub_dispatcher = unsub  # pylint: disable=protected-access
    await sensor.async_will_remove_from_hass()

    assert disconnected["called"]
    assert sensor._unsub_dispatcher is None  # pylint: disable=protected-access


def test_device_info(mock_entry):
    """Testet die vom Sensor bereitgestellten Geräteinformationen.

    Stellt sicher, dass die richtigen Hersteller- und Identifikationsinformationen geliefert werden.
    """
    sensor = Rssi(mock_entry)
    info = sensor.device_info
    assert info["identifiers"] == {(DOMAIN, "test_entry_id")}
    assert info["name"] == "Maxxi Entry"
    assert info["manufacturer"] == "mephdrac"
    assert info["model"] == "CCU - Maxxicharge"
