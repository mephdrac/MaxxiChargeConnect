"""Tests für das SendCount-Modul der MaxxiChargeConnect-Integration.

Dieses Testmodul prüft die Lückenerkennung und Reset-Erkennung
des SendCount-Sensors.
"""

import logging
import sys
from pathlib import Path

from unittest.mock import MagicMock
import pytest
from homeassistant.components.sensor import SensorStateClass

from custom_components.maxxi_charge_connect.const import DOMAIN
from custom_components.maxxi_charge_connect.devices.send_count import SendCount

sys.path.append(str(Path(__file__).resolve().parents[3]))

_LOGGER = logging.getLogger(__name__)


@pytest.fixture
def sensor():
    """Gibt ein Mock-Konfigurationsobjekt für den Sensor zurück."""
    entry = MagicMock()
    entry.entry_id = "test_entry_id"
    entry.title = "Maxxi Entry"
    entry.data = {"webhook_id": "abc123"}

    sensor_obj = SendCount(entry)
    sensor_obj.hass = MagicMock()

    return sensor_obj


@pytest.mark.asyncio
async def test_send_count_initialization(sensor):
    """Testet die Initialisierung des SendCount-Sensors."""
    assert sensor._attr_unique_id == "test_entry_id_send_count"  # pylint: disable=protected-access
    assert sensor._attr_icon == "mdi:counter"  # pylint: disable=protected-access
    assert sensor._attr_native_value is None  # pylint: disable=protected-access
    assert sensor._attr_state_class == SensorStateClass.TOTAL_INCREASING  # pylint: disable=protected-access
    assert sensor._last_sendcount is None  # pylint: disable=protected-access
    assert sensor._missing_packets == 0  # pylint: disable=protected-access
    assert sensor._resets == 0  # pylint: disable=protected-access


@pytest.mark.asyncio
async def test_send_count_first_value(sensor):
    """Testet das erste empfangene sendCount."""
    await sensor.handle_update({"sendCount": 100})
    
    assert sensor.native_value == 100
    assert sensor._last_sendcount == 100  # pylint: disable=protected-access
    assert sensor._missing_packets == 0  # pylint: disable=protected-access
    assert sensor._resets == 0  # pylint: disable=protected-access


@pytest.mark.asyncio
async def test_send_count_normal_increment(sensor):
    """Testet normales Inkrement (keine Lücke)."""
    # Erster Wert
    await sensor.handle_update({"sendCount": 100})
    
    # Normaler Zähler
    await sensor.handle_update({"sendCount": 101})
    
    assert sensor.native_value == 101
    assert sensor._missing_packets == 0  # pylint: disable=protected-access
    assert sensor._resets == 0  # pylint: disable=protected-access
    assert sensor._last_delta == 1  # pylint: disable=protected-access


@pytest.mark.asyncio
async def test_send_count_gap_detection(sensor):
    """Testet Lückenerkennung bei Sprung > 1."""
    # Erster Wert
    await sensor.handle_update({"sendCount": 100})
    
    # Lücke von 3 Telegrammen
    await sensor.handle_update({"sendCount": 104})
    
    assert sensor.native_value == 104
    assert sensor._missing_packets == 3  # pylint: disable=protected-access (104 - 100 - 1)
    assert sensor._resets == 0  # pylint: disable=protected-access
    assert sensor._last_delta == 4  # pylint: disable=protected-access


@pytest.mark.asyncio
async def test_send_count_reset_detection(sensor):
    """Testet Reset-Erkennung bei delta <= 0."""
    # Erster Wert
    await sensor.handle_update({"sendCount": 100})
    
    # Reset (Zähler beginnt von vorne)
    await sensor.handle_update({"sendCount": 5})
    
    assert sensor.native_value == 5
    assert sensor._missing_packets == 0  # pylint: disable=protected-access
    assert sensor._resets == 1  # pylint: disable=protected-access
    assert sensor._last_delta == -95  # pylint: disable=protected-access


@pytest.mark.asyncio
async def test_send_count_multiple_gaps(sensor):
    """Testet mehrere Lücken hintereinander."""
    await sensor.handle_update({"sendCount": 100})
    await sensor.handle_update({"sendCount": 102})  # Lücke von 1
    await sensor.handle_update({"sendCount": 105})  # Lücke von 2
    
    assert sensor._missing_packets == 3  # pylint: disable=protected-access (1 + 2)
    assert sensor._resets == 0  # pylint: disable=protected-access


@pytest.mark.asyncio
async def test_send_count_multiple_resets(sensor):
    """Testet mehrere Resets hintereinander."""
    await sensor.handle_update({"sendCount": 100})
    await sensor.handle_update({"sendCount": 10})   # Reset 1
    await sensor.handle_update({"sendCount": 5})    # Reset 2
    
    assert sensor._resets == 2  # pylint: disable=protected-access


@pytest.mark.asyncio
async def test_send_count_missing_field(sensor):
    """Testet Verhalten bei fehlendem sendCount-Feld."""
    await sensor.handle_update({})
    
    # Sollte nichts ändern
    assert sensor.native_value is None
    assert sensor._last_sendcount is None  # pylint: disable=protected-access


@pytest.mark.asyncio
async def test_send_count_none_value(sensor):
    """Testet Verhalten bei sendCount = None."""
    await sensor.handle_update({"sendCount": None})
    
    # Sollte nichts ändern
    assert sensor.native_value is None
    assert sensor._last_sendcount is None  # pylint: disable=protected-access


@pytest.mark.asyncio
async def test_send_count_string_value(sensor):
    """Testet Konvertierung von String zu int."""
    await sensor.handle_update({"sendCount": "100"})
    await sensor.handle_update({"sendCount": "102"})
    
    assert sensor.native_value == 102
    assert sensor._missing_packets == 1  # pylint: disable=protected-access


def test_send_count_extra_attributes(sensor):
    """Testet die zusätzlichen Attribute."""
    # Setup mit einigen Werten
    sensor._missing_packets = 5
    sensor._last_delta = 3
    sensor._resets = 2
    
    attrs = sensor.extra_state_attributes
    
    assert attrs["missing_packets"] == 5
    assert attrs["last_delta"] == 3
    assert attrs["resets"] == 2


def test_device_info(sensor):
    """Testet die device_info Eigenschaft."""
    info = sensor.device_info
    assert info["identifiers"] == {(DOMAIN, "test_entry_id")}
    assert info["name"] == "Maxxi Entry"


@pytest.mark.asyncio
async def test_send_count_handle_stale(sensor):
    """Testet, dass stale den Sensor verfügbar lässt und den letzten Wert behält."""
    sensor._attr_available = True  # pylint: disable=protected-access
    sensor._attr_native_value = 123  # pylint: disable=protected-access
    await sensor.handle_stale()

    assert sensor.available is True
    assert sensor.native_value == 123
