"""Tests für das Rssi-Sensorgerät von MaxxiChargeConnect.

Dieses Modul enthält Tests für die Klasse `Rssi`, die die WLAN-Signalstärke
als Sensorwert in Home Assistant abbildet.
Geprüft werden:
- die Initialisierung des Sensors,
- das korrekte Registrieren von Updates über den Dispatcher,
- das Verhalten beim Entfernen aus Home Assistant,
- und die bereitgestellten Gerätedaten.
"""
import sys
from pathlib import Path

from unittest.mock import MagicMock
from homeassistant.const import CONF_WEBHOOK_ID, SIGNAL_STRENGTH_DECIBELS_MILLIWATT
from homeassistant.components.sensor import SensorDeviceClass
from homeassistant.helpers.entity import EntityCategory

import pytest
from custom_components.maxxi_charge_connect.const import DOMAIN
from custom_components.maxxi_charge_connect.devices.rssi import Rssi

sys.path.append(str(Path(__file__).resolve().parents[3]))

# Dummy-Konstanten
WEBHOOK_ID = "abc123"


@pytest.fixture
def sensor():
    """Erstellt einen gefälschten ConfigEntry für die Tests."""
    mock_entry = MagicMock()
    mock_entry.entry_id = "abc123"
    mock_entry.title = "My Device"
    mock_entry.data = {CONF_WEBHOOK_ID: "webhook456"}

    sensor_obj = Rssi(mock_entry)
    sensor_obj.hass = MagicMock()
    sensor_obj.async_on_remove = MagicMock()

    return sensor_obj


@pytest.mark.asyncio
async def test_rssi_initialization(sensor):  # pylint: disable=redefined-outer-name
    """Testet die Initialisierung des Rssi-Sensors.

    Überprüft, ob alle erwarteten Eigenschaften (unique_id, Icon, Klasse, Einheit etc.)
    korrekt gesetzt werden.
    """
    assert sensor._attr_unique_id == "abc123_rssi"  # pylint: disable=protected-access
    assert sensor._attr_icon == "mdi:wifi"  # pylint: disable=protected-access
    assert sensor._attr_native_value is None  # pylint: disable=protected-access
    assert sensor._attr_device_class == SensorDeviceClass.SIGNAL_STRENGTH  # pylint: disable=protected-access
    # pylint: disable=protected-access
    assert sensor._attr_native_unit_of_measurement == SIGNAL_STRENGTH_DECIBELS_MILLIWATT
    # pylint: disable=protected-access
    assert sensor._attr_entity_category == EntityCategory.DIAGNOSTIC
    # pylint: disable=protected-access


@pytest.mark.asyncio
async def test_rssi_add_and_handle_update(sensor):  # pylint: disable=redefined-outer-name
    """Testet das Registrieren und Verarbeiten von Updates via Dispatcher.

    Es wird simuliert, dass ein Dispatcher-Signal empfangen wird und
    der Sensorwert (`native_value`) aktualisiert wird.
    """
    await sensor.handle_update({"wifiStrength": -42})  # pylint: disable=protected-access
    assert sensor.native_value == -42.0


@pytest.mark.asyncio
async def test_rssi_missing_value_keeps_previous(sensor):  # pylint: disable=redefined-outer-name
    """Fehlender wifiStrength soll den letzten Wert beibehalten."""
    sensor._attr_native_value = -50.0  # pylint: disable=protected-access
    await sensor.handle_update({})
    assert sensor.native_value == -50.0


@pytest.mark.asyncio
async def test_rssi_invalid_value_keeps_previous(sensor):  # pylint: disable=redefined-outer-name
    """Ungültiger wifiStrength soll den letzten Wert beibehalten."""
    sensor._attr_native_value = -50.0  # pylint: disable=protected-access
    await sensor.handle_update({"wifiStrength": "invalid"})
    assert sensor.native_value == -50.0


@pytest.mark.asyncio
async def test_rssi_implausible_value_keeps_previous(sensor):  # pylint: disable=redefined-outer-name
    """Unplausibler wifiStrength soll den letzten Wert beibehalten."""
    sensor._attr_native_value = -50.0  # pylint: disable=protected-access
    await sensor.handle_update({"wifiStrength": -200})
    assert sensor.native_value == -50.0


def test_device_info(sensor):  # pylint: disable=redefined-outer-name
    """Testet die vom Sensor bereitgestellten Geräteinformationen.

    Stellt sicher, dass die richtigen Hersteller- und Identifikationsinformationen geliefert werden.
    """
    info = sensor.device_info
    assert info["identifiers"] == {(DOMAIN, "abc123")}
    assert info["name"] == "My Device"
    assert info["manufacturer"] == "mephdrac"
    assert info["model"] == "CCU - Maxxicharge"
