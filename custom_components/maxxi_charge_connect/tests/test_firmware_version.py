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
from pathlib import Path

from unittest.mock import MagicMock, patch
import pytest
from homeassistant.const import CONF_WEBHOOK_ID, EntityCategory

from custom_components.maxxi_charge_connect.const import DOMAIN
from custom_components.maxxi_charge_connect.devices.firmware_version import (
    FirmwareVersion,
)

sys.path.append(str(Path(__file__).resolve().parents[3]))

# Dummy-Konstanten
WEBHOOK_ID = "abc123"


@pytest.fixture
def mock_entr_local():
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
async def test_firmware_version_initialization(mock_entry_local):
    """Testet die Initialisierung des FirmwareVersion Sensors.

    Überprüft, ob Attribute wie unique_id, icon, native_value und entity_category
    beim Erstellen korrekt gesetzt werden.
    """
    sensor = FirmwareVersion(mock_entry_local)

    assert sensor._attr_unique_id == "test_entry_id_firmware_version"\
        # pylint: disable=protected-access
    assert sensor._attr_icon == "mdi:information-outline"  # pylint: disable=protected-access
    # pylint: disable=protected-access
    assert sensor._attr_native_value is None  # pylint: disable=protected-access
    assert sensor._attr_entity_category == EntityCategory.DIAGNOSTIC\
           # pylint: disable=protected-access


@pytest.mark.asyncio
async def test_firmware_version_add_and_handle_update():
    """Testet das Hinzufügen des FirmwareVersion Sensors
    und die Verarbeitung von Update-Ereignissen.

    Mockt die Verbindung zum Home Assistant Dispatcher und überprüft,
    ob der Sensor das korrekte Signal abonniert, Update-Callbacks richtig behandelt
    und seinen native_value bei empfangenen Firmware-Version-Daten aktualisiert.

    Test, wenn isPrOk(True).
    """

    mock_entry = MagicMock()
    mock_entry.entry_id = "abc123"
    mock_entry.title = "My Device"
    mock_entry.data = {CONF_WEBHOOK_ID: "webhook456"}

    sensor = FirmwareVersion(mock_entry)
    sensor.hass = MagicMock()
    sensor.async_on_remove = MagicMock()

    # async_write_ha_state mocken
    sensor.async_write_ha_state = MagicMock()

    dispatcher_called = {}

    with patch(
        "custom_components.maxxi_charge_connect.devices.FirmwareVersion.async_dispatcher_connect"
    ) as mock_connect:

        def fake_unsub():
            dispatcher_called["disconnected"] = True

        mock_connect.return_value = fake_unsub

        await sensor.async_added_to_hass()

        signal = f"{DOMAIN}_webhook456_update_sensor"
        mock_connect.assert_called_once_with(sensor.hass, signal, sensor._handle_update)\
            # pylint: disable=protected-access
        sensor.async_on_remove.assert_called_once_with(fake_unsub)

        firmwareversion = "MyVersion"
        await sensor._handle_update({"firmwareVersion": firmwareversion})\
            # pylint: disable=protected-access
        assert sensor.native_value == firmwareversion


@pytest.mark.asyncio
async def test_firmware_version_will_remove_from_hass(mock_entry):
    """Testet den Aufräumprozess beim Entfernen des FirmwareVersion Sensors.

    Stellt sicher, dass der Unsubscribe-Callback aufgerufen und danach entfernt wird,
    wenn der Sensor aus Home Assistant entfernt wird.
    """
    sensor = FirmwareVersion(mock_entry)

    disconnected = {"called": False}

    def unsub():
        disconnected["called"] = True

    sensor._unsub_dispatcher = unsub  # pylint: disable=protected-access
    await sensor.async_will_remove_from_hass()

    assert disconnected["called"]
    assert sensor._unsub_dispatcher is None  # pylint: disable=protected-access


def test_device_info(mock_entry):
    """Testet die device_info Eigenschaft des FirmwareVersion Sensors.

    Validiert, dass Geräte-IDs, Name, Hersteller und Modell korrekt gesetzt sind.
    """
    sensor = FirmwareVersion(mock_entry)
    info = sensor.device_info
    assert info["identifiers"] == {(DOMAIN, "test_entry_id")}
    assert info["name"] == "Maxxi Entry"
    assert info["manufacturer"] == "mephdrac"
    assert info["model"] == "CCU - Maxxicharge"
