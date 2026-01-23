"""Testmodul für die FirmwareVersion Sensor-Entität.

Dieses Modul enthält Tests zur Überprüfung der Initialisierung, Ereignisverarbeitung
und Lebenszyklusverwaltung des FirmwareVersion Sensors in der MaxxiChargeConnect
Home Assistant Integration.

Fixtures:
    mock_entry: Stellt einen gemockten Config-Eintrag für Tests bereit.

Testfunktionen:
    test_FirmwareVersion_initialization(mock_entry):
        Testet den Initialzustand und die Attribute des FirmwareVersion Sensors.

    test_FirmwareVersion_add_and_handle_update():
        Testet das asynchrone Setup und die Verarbeitung von Update-Ereignissen,
        prüft, ob Firmware-Versionen korrekt als native Werte gesetzt werden.

    test_FirmwareVersion_will_remove_from_hass(mock_entry):
        Testet die Aufräumlogik beim Entfernen des Sensors aus Home Assistant.

    test_device_info(mock_entry):
        Testet die device_info Eigenschaft des FirmwareVersion Sensors und
        verifiziert die korrekten Geräte-Metadaten.
"""

import sys
from unittest.mock import MagicMock, patch
from pathlib import Path
from homeassistant.const import CONF_WEBHOOK_ID, EntityCategory
import pytest
from custom_components.maxxi_charge_connect.const import DOMAIN
from custom_components.maxxi_charge_connect.devices.firmware_version import (
    FirmwareVersion,
)
sys.path.append(str(Path(__file__).resolve().parents[3]))

# Dummy-Konstanten
WEBHOOK_ID = "abc123"


@pytest.fixture
def mock_entry():
    """Stellt einen gemockten Konfigurationseintrag für den Sensor bereit.

    Returns:
        MagicMock: Gemockter Config-Eintrag mit entry_id, title und webhook_id-Daten.

    """
    entry = MagicMock()
    entry.entry_id = "test_entry_id"
    entry.title = "Maxxi Entry"
    entry.data = {"webhook_id": WEBHOOK_ID}
    return entry


@pytest.mark.asyncio
async def test_device_id__set_value(mock_entry):  # pylint: disable=redefined-outer-name
    """Teste die `set_value`-Methode von `FirmwareVersion`."""
    test_text = "HalloText"
    sensor = FirmwareVersion(mock_entry)
    sensor.set_value(test_text)

    assert sensor._attr_native_value == test_text  # pylint: disable=protected-access


@pytest.mark.asyncio
async def test_firmware_version_initialization(mock_entry):  # pylint: disable=redefined-outer-name
    """Testet die Initialisierung des FirmwareVersion Sensors.

    Überprüft, ob Attribute wie unique_id, icon, native_value und entity_category
    beim Erstellen korrekt gesetzt werden.
    """
    sensor = FirmwareVersion(mock_entry)

    assert sensor._attr_unique_id == "test_entry_id_firmware_version"  # pylint: disable=protected-access
    # pylint: disable=protected-access
    assert sensor._attr_icon == "mdi:information-outline"  # pylint: disable=protected-access
    # pylint: disable=protected-access
    assert sensor._attr_native_value is None  # pylint: disable=protected-access
    assert sensor._attr_entity_category == EntityCategory.DIAGNOSTIC
    # pylint: disable=protected-access


@pytest.mark.asyncio
async def test_firmware_version_add_and_handle_update():
    """FirmwareVersion add und update.

    Testet das Hinzufügen des FirmwareVersion Sensors
    und die Verarbeitung von Update-Ereignissen.

    Mockt die Verbindung zum Home Assistant Dispatcher und überprüft,
    ob der Sensor das korrekte Signal abonniert, Update-Callbacks richtig behandelt
    und seinen native_value bei empfangenen Firmware-Version-Daten aktualisiert.

    Test, wenn isPrOk(True).
    """

    mock_obj = MagicMock()
    mock_obj.entry_id = "abc123"
    mock_obj.title = "My Device"
    mock_obj.data = {CONF_WEBHOOK_ID: "webhook456"}

    sensor = FirmwareVersion(mock_obj)
    sensor.hass = MagicMock()
    sensor.async_on_remove = MagicMock()

    # async_write_ha_state mocken
    sensor.async_write_ha_state = MagicMock()

    dispatcher_called = {}

    with patch(
        "custom_components.maxxi_charge_connect.devices.firmware_version.async_dispatcher_connect"
    ) as mock_connect:

        def fake_unsub():
            dispatcher_called["disconnected"] = True

        mock_connect.return_value = fake_unsub

        await sensor.async_added_to_hass()

        signal = f"{DOMAIN}_webhook456_update_sensor"
        mock_connect.assert_called_once_with(sensor.hass, signal, sensor._handle_update)
        # pylint: disable=protected-access
        sensor.async_on_remove.assert_called_once_with(fake_unsub)

        firmwareversion = "MyVersion"
        await sensor._handle_update({"firmwareVersion": firmwareversion})
        # pylint: disable=protected-access
        assert sensor.native_value == firmwareversion


def test_device_info(mock_entry):  # pylint: disable=redefined-outer-name
    """Testet die device_info Eigenschaft des FirmwareVersion Sensors.

    Validiert, dass Geräte-IDs, Name, Hersteller und Modell korrekt gesetzt sind.
    """
    sensor = FirmwareVersion(mock_entry)
    info = sensor.device_info
    assert info["identifiers"] == {(DOMAIN, "test_entry_id")}
    assert info["name"] == "Maxxi Entry"
    assert info["manufacturer"] == "mephdrac"
    assert info["model"] == "CCU - Maxxicharge"
