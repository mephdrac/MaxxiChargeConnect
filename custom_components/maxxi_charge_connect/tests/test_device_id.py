"""Testmodul für die Klasse `DeviceId`.

Dieses Modul testet die Funktionalität des `DeviceId`-Sensors der Integration
`maxxi_charge_connect` für Home Assistant. Der Sensor stellt diagnostische Informationen
zum Gerät bereit, insbesondere die `deviceId`, wie sie per Webhook empfangen wird.

Getestet werden:
- Die Initialisierung und Attributwerte der Entität.
- Die Anbindung an das Home Assistant-Signal-Dispatcher-System.
- Die Reaktion auf eingehende Updates über `_handle_update`.
- Die saubere Abmeldung vom Dispatcher beim Entfernen der Entität.
- Die Korrektheit der `device_info`-Metadaten.

Verwendete Bibliotheken:
- unittest.mock, pytest, logging
"""
from pathlib import Path
import sys
from unittest.mock import MagicMock, patch

import pytest

from homeassistant.const import CONF_WEBHOOK_ID, EntityCategory
from custom_components.maxxi_charge_connect.const import DOMAIN
from custom_components.maxxi_charge_connect.devices.device_id import DeviceId

sys.path.append(str(Path(__file__).resolve().parents[3]))

# Dummy-Konstanten
WEBHOOK_ID = "abc123"


@pytest.fixture
def mock_entry_local():
    """Erzeuge einen Mock für ConfigEntry-Objekte mit Dummy-Daten.

    Returns:
        MagicMock: Mocked ConfigEntry mit Webhook-ID und Titel.

    """

    entry = MagicMock()
    entry.entry_id = "test_entry_id"
    entry.title = "Maxxi Entry"
    entry.data = {"webhook_id": WEBHOOK_ID}
    return entry


@pytest.mark.asyncio
async def test_device_id_initialization(mock_entry):
    """Teste Initialisierung von `DeviceId`.

    Überprüft, ob alle Attribute beim Instanziieren korrekt gesetzt sind.

    Args:
        mock_entry (MagicMock): Fixture mit gefaktem ConfigEntry.

    """
    sensor = DeviceId(mock_entry)

    assert sensor._attr_unique_id == "test_entry_id_deviceid"  # pylint: disable=protected-access
    assert sensor._attr_icon == "mdi:identifier"  # pylint: disable=protected-access
    assert sensor._attr_native_value is None  # pylint: disable=protected-access
    assert sensor._attr_entity_category == \
        EntityCategory.DIAGNOSTIC  # pylint: disable=protected-access


@pytest.mark.asyncio
async def test_device_id_add_and_handle_update():
    """Teste Anbindung an Dispatcher und Update-Verarbeitung.

    - Simuliert das Hinzufügen der Entität zu Home Assistant.
    - Stellt sicher, dass ein Signal-Listener registriert und wieder entfernt wird.
    - Simuliert ein eingehendes Gerätedaten-Update via `_handle_update`.
    """

    mock_entry1 = MagicMock()
    mock_entry1.entry_id = "abc123"
    mock_entry1.title = "My Device"
    mock_entry1.data = {CONF_WEBHOOK_ID: "webhook456"}

    sensor = DeviceId(mock_entry_local)
    sensor.hass = MagicMock()
    sensor.async_on_remove = MagicMock()

    # async_write_ha_state mocken
    sensor.async_write_ha_state = MagicMock()

    dispatcher_called = {}

    with patch(
        "custom_components.maxxi_charge_connect.devices.DeviceId.async_dispatcher_connect"
    ) as mock_connect:

        def fake_unsub():
            dispatcher_called["disconnected"] = True

        mock_connect.return_value = fake_unsub

        await sensor.async_added_to_hass()

        signal = f"{DOMAIN}_webhook456_update_sensor"
        mock_connect.assert_called_once_with(sensor.hass, signal, sensor._handle_update)\
            # pylint: disable=protected-access
        sensor.async_on_remove.assert_called_once_with(fake_unsub)

        device_id = "MyVersion"
        await sensor._handle_update({"deviceId": device_id})  # pylint: disable=protected-access
        assert sensor.native_value == device_id


@pytest.mark.asyncio
async def test_device_id_will_remove_from_hass(mock_entry):
    """Teste Entfernen der Entität aus Home Assistant.

    Verifiziert, dass der Dispatcher unsubscribed wird und das Attribut geleert ist.

    Args:
        mock_entry (MagicMock): Fixture mit gefaktem ConfigEntry.

    """
    sensor = DeviceId(mock_entry)

    disconnected = {"called": False}

    def unsub():
        disconnected["called"] = True

    sensor._unsub_dispatcher = unsub  # pylint: disable=protected-access
    await sensor.async_will_remove_from_hass()

    assert disconnected["called"]
    assert sensor._unsub_dispatcher is None  # pylint: disable=protected-access


def test_device_info(mock_entry):
    """Teste `device_info`-Eigenschaft.

    Stellt sicher, dass die Gerätedaten wie Hersteller, Modell und ID korrekt zurückgegeben werden.

    Args:
        mock_entry (MagicMock): Fixture mit gefaktem ConfigEntry.

    """
    sensor = DeviceId(mock_entry)
    info = sensor.device_info
    assert info["identifiers"] == {(DOMAIN, "test_entry_id")}
    assert info["name"] == "Maxxi Entry"
    assert info["manufacturer"] == "mephdrac"
    assert info["model"] == "CCU - Maxxicharge"
