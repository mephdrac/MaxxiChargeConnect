"""Testmodul für den GridExport Sensor.

Dieses Modul enthält Tests zur Initialisierung, Ereignisverarbeitung und
Lebenszyklusverwaltung des GridExport Sensors in der MaxxiChargeConnect
Home Assistant Integration.

Fixtures:
    mock_entry: Liefert einen gemockten Config-Eintrag für die Tests.

Testfunktionen:
    test_GridExport_initialization(mock_entry):
        Testet die korrekte Initialisierung und Attribute des Sensors.

    test_GridExport_add_and_handle_update1():
        Testet das Hinzufügen des Sensors und das Handling von Updates,
        wenn isPrOk True zurückgibt (gültige Leistungswerte).

    test_GridExport_add_and_handle_update2():
        Testet das Hinzufügen und Handling von Updates, wenn isPrOk False zurückgibt.

    test_GridExport_will_remove_from_hass(mock_entry):
        Testet den Aufräumprozess beim Entfernen des Sensors.

    test_device_info(mock_entry):
        Testet die device_info Eigenschaft des Sensors und validiert die Geräte-Metadaten.
"""

import logging
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[3]))
from unittest.mock import MagicMock, patch
import pytest

from homeassistant.components.sensor import SensorDeviceClass, SensorStateClass
from homeassistant.const import CONF_WEBHOOK_ID, UnitOfPower

from custom_components.maxxi_charge_connect.const import DOMAIN
from custom_components.maxxi_charge_connect.devices.grid_export import GridExport


_LOGGER = logging.getLogger(__name__)

# Dummy-Konstanten
WEBHOOK_ID = "abc123"


@pytest.fixture
def mock_entry():
    """Fixture, die einen gemockten Config-Eintrag für den Sensor zurückgibt.

    Returns:
        MagicMock: Gemockter Konfigurationseintrag mit entry_id, Titel und webhook_id.

    """
    entry = MagicMock()
    entry.entry_id = "test_entry_id"
    entry.title = "Maxxi Entry"
    entry.data = {"webhook_id": WEBHOOK_ID}
    return entry


@pytest.mark.asyncio
async def test_grid_export_initialization(mock_entry):
    """Testet die Initialisierung des GridExport Sensors.

    Überprüft die Attribute wie unique_id, icon, native_value, device_class,
    state_class und native_unit_of_measurement.
    """
    sensor = GridExport(mock_entry)

    assert sensor._attr_unique_id == "test_entry_id_grid_export"  # pylint: disable=protected-access
    assert sensor._attr_icon == "mdi:transmission-tower-import"  # pylint: disable=protected-access
    assert sensor._attr_native_value is None  # pylint: disable=protected-access
    assert sensor._attr_device_class == SensorDeviceClass.POWER  # pylint: disable=protected-access
    assert sensor._attr_state_class == SensorStateClass.MEASUREMENT
    # pylint: disable=protected-access
    assert sensor._attr_native_unit_of_measurement == UnitOfPower.WATT
    # pylint: disable=protected-access


@pytest.mark.asyncio
async def test_grid_export_add_and_handle_update1():
    """Testet das Hinzufügen des Sensors und das Verarbeiten eines Updates.

    Simuliert, dass isPrOk True zurückgibt, und prüft,
    ob native_value korrekt aus dem übergebenen Pr-Wert berechnet wird.
    """

    mock_entry = MagicMock()
    mock_entry.entry_id = "abc123"
    mock_entry.title = "My Device"
    mock_entry.data = {CONF_WEBHOOK_ID: "webhook456"}

    sensor = GridExport(mock_entry)
    sensor.hass = MagicMock()
    sensor.async_on_remove = MagicMock()

    # async_write_ha_state mocken
    sensor.async_write_ha_state = MagicMock()

    dispatcher_called = {}

    with (
        patch(
            "custom_components.maxxi_charge_connect.devices.grid_export.async_dispatcher_connect"
        ) as mock_connect,
        patch(
            "custom_components.maxxi_charge_connect.devices.grid_export.isPrOk"
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

        pr = 234.675
        await sensor._handle_update({"Pr": pr})  # pylint: disable=protected-access
        assert sensor.native_value == round(max(-pr, 0), 2)


@pytest.mark.asyncio
async def test_grid_export_add_and_handle_update2():
    """Testet das Hinzufügen des Sensors und das Verarbeiten eines Updates.

    Simuliert, dass isPrOk False zurückgibt und überprüft,
    dass native_value dann None bleibt.
    """

    mock_entry = MagicMock()
    mock_entry.entry_id = "abc123"
    mock_entry.title = "My Device"
    mock_entry.data = {CONF_WEBHOOK_ID: "webhook456"}

    sensor = GridExport(mock_entry)
    sensor.hass = MagicMock()
    sensor.async_on_remove = MagicMock()

    # async_write_ha_state mocken
    sensor.async_write_ha_state = MagicMock()

    dispatcher_called = {}

    with (
        patch(
            "custom_components.maxxi_charge_connect.devices.grid_export.async_dispatcher_connect"
        ) as mock_connect,
        patch(
            "custom_components.maxxi_charge_connect.devices.grid_export.isPrOk"
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

        pr = 234.675
        await sensor._handle_update({"Pr": pr})  # pylint: disable=protected-access
        assert sensor.native_value is None


def test_device_info(mock_entry):
    """Testet die device_info-Eigenschaft des GridExport Sensors.

    Verifiziert, dass die Geräte-Identifikatoren, der Name, Hersteller und Modell korrekt sind.
    """
    sensor = GridExport(mock_entry)
    info = sensor.device_info
    assert info["identifiers"] == {(DOMAIN, "test_entry_id")}
    assert info["name"] == "Maxxi Entry"
    assert info["manufacturer"] == "mephdrac"
    assert info["model"] == "CCU - Maxxicharge"
