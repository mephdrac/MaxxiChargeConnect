"""
Testmodul für GridImport.

Dieses Modul testet die Initialisierung, das Hinzufügen, das Handling von Updates
sowie das Entfernen des GridImport-Sensors in Home Assistant.
"""

import logging
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

from homeassistant.components.sensor import SensorDeviceClass, SensorStateClass
from homeassistant.const import UnitOfPower

import pytest

from custom_components.maxxi_charge_connect.const import DOMAIN
from custom_components.maxxi_charge_connect.devices.grid_import import GridImport

sys.path.append(str(Path(__file__).resolve().parents[3]))

_LOGGER = logging.getLogger(__name__)

# Dummy-Konstanten
WEBHOOK_ID = "abc123"


@pytest.fixture
def mock_entry():
    """Fixture zur Erstellung eines Mock-Config-Eintrags.

    Liefert ein MagicMock-Objekt mit den Attributen entry_id, title und data,
    um den Sensor mit Testdaten zu versorgen.
    """
    entry = MagicMock()
    entry.entry_id = "test_entry_id"
    entry.title = "Maxxi Entry"
    entry.data = {"webhook_id": WEBHOOK_ID}
    return entry


@pytest.mark.asyncio
async def test_grid_import_initialization(mock_entry):  # pylint: disable=redefined-outer-name
    """Testet die korrekte Initialisierung des GridImport-Sensors.

    Überprüft, ob alle wichtigen Attribute (unique_id, Icon, device_class, state_class, Einheit)
    wie erwartet gesetzt sind.
    """
    sensor = GridImport(mock_entry)

    assert sensor._attr_unique_id == "test_entry_id_grid_import"  # pylint: disable=protected-access
    assert sensor._attr_icon == "mdi:transmission-tower-export"  # pylint: disable=protected-access
    assert sensor._attr_native_value is None  # pylint: disable=protected-access
    assert sensor._attr_device_class == SensorDeviceClass.POWER  # pylint: disable=protected-access
    assert sensor._attr_state_class == SensorStateClass.MEASUREMENT  # pylint: disable=protected-access
    # pylint: disable=protected-access
    assert sensor._attr_native_unit_of_measurement == UnitOfPower.WATT
    # pylint: disable=protected-access


@pytest.mark.asyncio
async def test_grid_import_add_and_handle_update1(mock_entry):  # pylint: disable=redefined-outer-name
    """Testet das Hinzufügen des Sensors und das Handling eines Updates.

    Testet das Hinzufügen des Sensors und das Handling eines Updates,
    wenn isPrOk(True) zurückgibt.

    Dabei wird geprüft, ob Dispatcher-Verbindung korrekt aufgebaut und das native_value
    nach dem Update richtig gesetzt wird.
    """
    sensor = GridImport(mock_entry)
    sensor.hass = MagicMock()
    sensor.async_on_remove = MagicMock()

    # async_write_ha_state mocken
    sensor.async_write_ha_state = MagicMock()

    with (
        patch(
            "custom_components.maxxi_charge_connect.devices.grid_import.is_pr_ok"
        ) as mock_is_pr_ok,
    ):
        mock_is_pr_ok.return_value = True
        await sensor.handle_update({"Pr": 234.675})  # pylint: disable=protected-access
        assert sensor.native_value == 234.675


@pytest.mark.asyncio
async def test_grid_import_add_and_handle_update2(mock_entry):  # pylint: disable=redefined-outer-name
    """Testet das Hinzufügen des Sensors und das Handling eines Updates.

    Testet das Hinzufügen des Sensors und das Handling eines Updates,
    wenn isPrOk(False) zurückgibt.

    Es wird überprüft, ob native_value in diesem Fall None bleibt.
    """
    sensor = GridImport(mock_entry)
    sensor.hass = MagicMock()
    sensor.async_on_remove = MagicMock()

    # async_write_ha_state mocken
    sensor.async_write_ha_state = MagicMock()

    with (
        patch(
            "custom_components.maxxi_charge_connect.devices.grid_import.is_pr_ok"
        ) as mock_is_pr_ok,
    ):
        mock_is_pr_ok.return_value = False
        await sensor.handle_update({"Pr": 234.675})  # pylint: disable=protected-access
        assert sensor.native_value is None


def test_device_info(mock_entry):  # pylint: disable=redefined-outer-name
    """Testet die Rückgabe der device_info-Eigenschaft des Sensors.

    Überprüft, ob die Identifiers, der Name, der Hersteller und das Modell korrekt sind.
    """
    sensor = GridImport(mock_entry)
    info = sensor.device_info
    assert info["identifiers"] == {(DOMAIN, "test_entry_id")}
    assert info["name"] == "Maxxi Entry"
    assert info["manufacturer"] == "mephdrac"
    assert info["model"] == "CCU - Maxxicharge"
