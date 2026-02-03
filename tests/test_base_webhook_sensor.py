"""Tests für die BaseWebhookSensor Basisklasse."""

import logging
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from custom_components.maxxi_charge_connect.const import DOMAIN, WEBHOOK_SIGNAL_UPDATE, WEBHOOK_SIGNAL_STATE
from custom_components.maxxi_charge_connect.devices.base_webhook_sensor import BaseWebhookSensor

sys.path.append(str(Path(__file__).resolve().parents[3]))

_LOGGER = logging.getLogger(__name__)


class TestSensor(BaseWebhookSensor):
    """Test-Sensor-Klasse für die Basisklasse."""

    def __init__(self, entry):
        super().__init__(entry)
        self._attr_unique_id = f"{entry.entry_id}_test"
        self._attr_native_value = None

    async def handle_update(self, data):
        """Test-Implementierung."""
        value = data.get("test_value")
        if value is not None:
            self._attr_native_value = float(value)


@pytest.fixture
def entry():
    """Mock ConfigEntry."""
    entry = MagicMock()
    entry.entry_id = "test_entry_id"
    entry.title = "Test Entry"
    entry.data = {"webhook_id": "abc123"}
    return entry


@pytest.fixture
def hass():
    """Mock Home Assistant."""
    hass = MagicMock()
    hass.data = {
        DOMAIN: {
            "test_entry_id": {
                WEBHOOK_SIGNAL_UPDATE: "test_update_signal",
                WEBHOOK_SIGNAL_STATE: "test_stale_signal"
            }
        }
    }
    return hass


@pytest.mark.asyncio
async def test_base_sensor_initialization(entry):
    """Testet die Initialisierung der Basisklasse."""
    sensor = TestSensor(entry)

    assert sensor._entry == entry
    assert sensor._attr_available is False
    assert sensor._unsub_update is None
    assert sensor._unsub_stale is None


@pytest.mark.asyncio
async def test_restore_state_float(entry, hass):
    """Testet die Wiederherstellung von Float-Werten."""
    sensor = TestSensor(entry)
    sensor.hass = hass

    # Mock alten Zustand
    old_state = MagicMock()
    old_state.state = "123.45"

    with patch.object(sensor, 'async_get_last_state', return_value=old_state):
        await sensor.async_added_to_hass()

    assert sensor._attr_native_value == 123.45
    assert sensor._attr_available is True


@pytest.mark.asyncio
async def test_restore_state_invalid(entry, hass):
    """Testet die Wiederherstellung bei ungültigen Werten."""
    sensor = TestSensor(entry)
    sensor.hass = hass

    # Mock ungültigen Zustand
    old_state = MagicMock()
    old_state.state = "invalid_number"

    with patch.object(sensor, 'async_get_last_state', return_value=old_state):
        await sensor.async_added_to_hass()

    assert sensor._attr_native_value is None
    assert sensor._attr_available is False


@pytest.mark.asyncio
async def test_wrapper_update_value_change(entry, hass):
    """Testet _wrapper_update bei Wertänderung."""
    sensor = TestSensor(entry)
    sensor.hass = hass
    sensor.async_write_ha_state = MagicMock()

    await sensor._wrapper_update({"test_value": "100"})

    assert sensor._attr_native_value == 100.0
    assert sensor._attr_available is True
    sensor.async_write_ha_state.assert_called_once()


@pytest.mark.asyncio
async def test_wrapper_update_no_change(entry, hass):
    """Testet _wrapper_update ohne Wertänderung."""
    sensor = TestSensor(entry)
    sensor.hass = hass
    sensor._attr_native_value = 100.0
    sensor.async_write_ha_state = MagicMock()

    await sensor._wrapper_update({"test_value": "100"})

    # Sollte nicht aktualisiert werden (keine Änderung)
    sensor.async_write_ha_state.assert_not_called()


@pytest.mark.asyncio
async def test_wrapper_update_error_handling(entry, hass):
    """Testet die Fehlerbehandlung in _wrapper_update."""
    sensor = TestSensor(entry)
    sensor.hass = hass
    sensor.async_write_ha_state = MagicMock()

    # Simuliere Fehler in handle_update
    async def failing_handle_update(data):
        raise ValueError("Test error")

    sensor.handle_update = failing_handle_update

    await sensor._wrapper_update({"test_value": "100"})

    # Sollte Fehler loggen, aber nicht abstürzen
    sensor.async_write_ha_state.assert_not_called()


@pytest.mark.asyncio
async def test_wrapper_stale(entry, hass):
    """Testet _wrapper_stale."""
    sensor = TestSensor(entry)
    sensor.hass = hass
    sensor.async_write_ha_state = MagicMock()

    await sensor._wrapper_stale(None)

    assert sensor._attr_available is False
    # Wird in handle_stale aufgerufen
    assert sensor.async_write_ha_state.call_count >= 1


@pytest.mark.asyncio
async def test_device_info(entry):
    """Testet device_info Property."""
    sensor = TestSensor(entry)

    device_info = sensor.device_info
    assert device_info["identifiers"] == {(DOMAIN, "test_entry_id")}
    assert device_info["name"] == "Test Entry"


def test_restore_state_value_method():
    """Testet die _restore_state_value Methode direkt."""
    sensor = TestSensor(MagicMock())

    # Float-Konvertierung
    assert sensor._restore_state_value("123.45") == 123.45
    assert sensor._restore_state_value("0") == 0.0

    # Ungültige Werte
    assert sensor._restore_state_value("invalid") is None
    assert sensor._restore_state_value("") is None
