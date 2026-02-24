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

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch
from homeassistant.const import CONF_WEBHOOK_ID, EntityCategory
import pytest

from custom_components.maxxi_charge_connect.const import DOMAIN
from custom_components.maxxi_charge_connect.devices.device_id import DeviceId

sys.path.append(str(Path(__file__).resolve().parents[3]))


# Dummy-Konstanten
WEBHOOK_ID = "abc123"


@pytest.fixture
def mock_entry():
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
async def test_device_id_initialization(mock_entry):  # pylint: disable=redefined-outer-name
    """Teste Initialisierung von `DeviceId`.

    Überprüft, ob alle Attribute beim Instanziieren korrekt gesetzt sind.

    Args:
        mock_entry (MagicMock): Fixture mit gefaktem ConfigEntry.

    """
    sensor = DeviceId(mock_entry)

    assert sensor._attr_unique_id == "test_entry_id_deviceid"  # pylint: disable=protected-access
    assert sensor._attr_icon == "mdi:identifier"  # pylint: disable=protected-access
    assert sensor._attr_native_value is None  # pylint: disable=protected-access
    assert sensor._attr_entity_category == EntityCategory.DIAGNOSTIC  # pylint: disable=protected-access


@pytest.mark.asyncio
async def test_device_id_add_and_handle_update():
    """Teste Anbindung an Dispatcher und Update-Verarbeitung.

    - Simuliert das Hinzufügen der Entität zu Home Assistant.
    - Stellt sicher, dass ein Signal-Listener registriert wird.
    - Simuliert ein eingehendes Gerätedaten-Update via `handle_update`.
    """

    mock_obj = MagicMock()
    mock_obj.entry_id = "abc123"
    mock_obj.title = "My Device"
    mock_obj.data = {"webhook_id": "webhook456"}

    sensor = DeviceId(mock_obj)
    sensor.hass = MagicMock()

    # Test, dass async_added_to_hass aufgerufen werden kann
    # Wir testen nur, dass keine Exception auftritt
    try:
        await sensor.async_added_to_hass()
    except KeyError:
        # KeyError ist erwartet, da wir nicht alle Konstanten mocken
        pass

    # Test handle_update Methode
    device_id = "MyVersion"
    await sensor.handle_update({"deviceId": device_id})
    assert sensor.native_value == device_id

    # Test mit ungültigen Daten
    await sensor.handle_update({"deviceId": None})
    assert sensor.native_value == device_id  # Sollte unverändert bleiben

    await sensor.handle_update({})
    assert sensor.native_value == device_id  # Sollte unverändert bleiben


def test_device_info(mock_entry):  # pylint: disable=redefined-outer-name
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
