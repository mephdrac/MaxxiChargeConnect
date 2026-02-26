"""Tests für das BatterySensorManager-Modul der MaxxiChargeConnect-Integration."""

import logging
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
import pytest
from homeassistant.const import STATE_UNKNOWN
from homeassistant.core import HomeAssistant, Event

from custom_components.maxxi_charge_connect.const import (
    CONF_ENABLE_CLOUD_DATA,
    CONF_DEVICE_ID,
    PROXY_ERROR_DEVICE_ID,
    WEBHOOK_SIGNAL_UPDATE,
    WEBHOOK_SIGNAL_STATE,
)
from custom_components.maxxi_charge_connect.devices.battery_sensor_manager import BatterySensorManager

sys.path.append(str(Path(__file__).resolve().parents[3]))

_LOGGER = logging.getLogger(__name__)


@pytest.fixture
def hass():
    """Mock HomeAssistant instance."""
    hass = MagicMock(spec=HomeAssistant)
    hass.data = {}
    return hass


@pytest.fixture
def entry():
    """Mock ConfigEntry."""
    entry = MagicMock()
    entry.entry_id = "test_entry_id"
    entry.title = "Test Entry"
    entry.data = {
        "webhook_id": "abc123",
        CONF_ENABLE_CLOUD_DATA: False,
        CONF_DEVICE_ID: "device123"
    }
    return entry


@pytest.fixture
def async_add_entities():
    """Mock async_add_entities callback."""
    return AsyncMock()


@pytest.fixture
def manager(hass, entry, async_add_entities):
    """BatterySensorManager fixture."""
    return BatterySensorManager(hass, entry, async_add_entities)


class TestBatterySensorManager:
    """Test-Klasse für BatterySensorManager."""

    def test_initialization(self, manager, entry):
        """Testet die Initialisierung des BatterySensorManager."""
        assert manager.hass is not None
        assert manager.entry == entry
        assert manager.async_add_entities is not None
        assert manager.sensors == {}
        assert manager._registered is False
        assert manager._enable_cloud_data is False

    def test_initialization_with_cloud_data(self, hass, entry, async_add_entities):
        """Testet die Initialisierung mit Cloud-Daten."""
        entry.data[CONF_ENABLE_CLOUD_DATA] = True
        manager = BatterySensorManager(hass, entry, async_add_entities)
        assert manager._enable_cloud_data is True

    @pytest.mark.asyncio
    async def test_setup_webhook_mode(self, manager, hass):
        """Testet das Setup im Webhook-Modus."""
        # Setup hass.data mit den erforderlichen Signalen
        hass.data = {
            "maxxi_charge_connect": {
                "test_entry_id": {
                    "listeners": [],
                    WEBHOOK_SIGNAL_UPDATE: "test_update_signal",
                    WEBHOOK_SIGNAL_STATE: "test_stale_signal"
                }
            }
        }

        with patch(
            "custom_components.maxxi_charge_connect.devices.battery_sensor_manager.async_dispatcher_connect"
        ) as mock_connect:
            mock_connect.return_value = AsyncMock()

            await manager.setup()

            assert manager._registered is True
            assert mock_connect.call_count == 2  # update + stale signal

    @pytest.mark.asyncio
    async def test_setup_cloud_mode(self, hass, entry, async_add_entities):
        """Testet das Setup im Cloud-Modus."""
        entry.data[CONF_ENABLE_CLOUD_DATA] = True
        manager = BatterySensorManager(hass, entry, async_add_entities)

        hass.bus = MagicMock()
        with patch.object(hass.bus, "async_listen") as mock_listen:
            await manager.setup()
            mock_listen.assert_called_once()

    @pytest.mark.asyncio
    async def test_setup_error_handling(self, manager):
        """Testet die Fehlerbehandlung beim Setup."""
        with patch(
            "custom_components.maxxi_charge_connect.devices.battery_sensor_manager.async_dispatcher_connect",
            side_effect=Exception("Setup Error")
        ):
            await manager.setup()
            # Sollte keine Exception werfen

    @pytest.mark.asyncio
    async def test_handle_update_no_batteries(self, manager):
        """Testet handle_update ohne Batterie-Informationen."""
        data = {"other": "data"}

        await manager.handle_update(data)

        # Sollte keine Sensoren erstellen
        assert len(manager.sensors) == 0
        manager.async_add_entities.assert_not_called()

    @pytest.mark.asyncio
    async def test_handle_update_with_batteries_first_time(self, manager):
        """Testet handle_update mit Batterien beim ersten Mal."""
        data = {
            "batteriesInfo": [
                {"batteryCapacity": 1000},
                {"batteryCapacity": 2000}
            ]
        }

        await manager.handle_update(data)

        # Sollte 22 Sensoren erstellen (11 pro Batterie)
        assert len(manager.sensors) == 22
        # async_add_entities sollte aufgerufen werden, aber wir prüfen nur die Anzahl
        assert manager.async_add_entities.call_count >= 1

    @pytest.mark.asyncio
    async def test_handle_update_with_batteries_second_time(self, manager):
        """Testet handle_update mit Batterien beim zweiten Mal."""
        data = {
            "batteriesInfo": [
                {"batteryCapacity": 1000}
            ]
        }

        # Erster Aufruf - erstellt Sensoren
        await manager.handle_update(data)
        first_call_count = manager.async_add_entities.call_count

        # Zweiter Aufruf - sollte keine neuen Sensoren erstellen
        await manager.handle_update(data)

        # Sollte keine zusätzlichen Sensoren erstellt haben
        assert manager.async_add_entities.call_count == first_call_count
        assert len(manager.sensors) == 11  # 11 Sensoren für 1 Batterie

    @pytest.mark.asyncio
    async def test_handle_update_listener_distribution(self, manager):
        """Testet die Verteilung von Updates an Listener."""
        data = {
            "batteriesInfo": [
                {"batteryCapacity": 1000}
            ]
        }

        # Mock-Listener hinzufügen
        mock_listener1 = AsyncMock()
        mock_listener2 = AsyncMock()

        manager.hass.data = {
            "maxxi_charge_connect": {
                "test_entry_id": {
                    "listeners": [mock_listener1, mock_listener2]
                }
            }
        }

        await manager.handle_update(data)

        # Beide Listener sollten aufgerufen werden
        mock_listener1.assert_called_once_with(data)
        mock_listener2.assert_called_once_with(data)

    @pytest.mark.asyncio
    async def test_handle_stale(self, manager):
        """Testet das Stale-Handling."""
        # Mock-Sensoren erstellen
        mock_sensor1 = MagicMock()
        mock_sensor1.hass = MagicMock()
        mock_sensor2 = MagicMock()
        mock_sensor2.hass = MagicMock()

        manager.sensors = {
            "sensor1": mock_sensor1,
            "sensor2": mock_sensor2
        }

        await manager.handle_stale()

        # Alle Sensoren sollten auf unavailable gesetzt werden
        assert mock_sensor1._attr_available is False
        assert mock_sensor1._attr_state == STATE_UNKNOWN
        mock_sensor1.async_write_ha_state.assert_called_once()

        assert mock_sensor2._attr_available is False
        assert mock_sensor2._attr_state == STATE_UNKNOWN
        mock_sensor2.async_write_ha_state.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_stale_with_none_sensor(self, manager):
        """Testet Stale-Handling mit None-Sensoren."""
        manager.sensors = {
            "sensor1": None,
            "sensor2": MagicMock()
        }

        # Sollte keine Exception werfen
        await manager.handle_stale()

    @pytest.mark.asyncio
    async def test_async_update_from_event(self, manager):
        """Testet das Update von Proxy-Events."""
        event = MagicMock(spec=Event)
        event.data = {
            "payload": {
                PROXY_ERROR_DEVICE_ID: "device123",
                "deviceId": "device123",
                "test": "data"
            }
        }

        with patch.object(manager, "handle_update") as mock_handle_update:
            await manager.async_update_from_event(event)
            mock_handle_update.assert_called_once_with({"deviceId": "device123", "test": "data"})

    @pytest.mark.asyncio
    async def test_async_update_from_event_wrong_device(self, manager):
        """Testet das Update von Proxy-Events mit falscher Device ID."""
        event = MagicMock(spec=Event)
        event.data = {
            "payload": {
                PROXY_ERROR_DEVICE_ID: "wrong_device",
                "test": "data"
            }
        }

        with patch.object(manager, "handle_update") as mock_handle_update:
            await manager.async_update_from_event(event)
            mock_handle_update.assert_not_called()

    @pytest.mark.asyncio
    async def test_wrapper_update(self, manager):
        """Testet den Update-Wrapper."""
        data = {"test": "data"}

        with patch.object(manager, "handle_update") as mock_handle_update:
            await manager._wrapper_update(data)
            mock_handle_update.assert_called_once_with(data)

    @pytest.mark.asyncio
    async def test_wrapper_update_error(self, manager):
        """Testet die Fehlerbehandlung im Update-Wrapper."""
        data = {"test": "data"}

        with patch.object(manager, "handle_update", side_effect=Exception("Test Error")):
            # Sollte keine Exception werfen
            await manager._wrapper_update(data)

    @pytest.mark.asyncio
    async def test_wrapper_stale(self, manager):
        """Testet den Stale-Wrapper."""
        with patch.object(manager, "handle_stale") as mock_handle_stale:
            await manager._wrapper_stale(None)
            mock_handle_stale.assert_called_once()

    @pytest.mark.asyncio
    async def test_wrapper_stale_error(self, manager):
        """Testet die Fehlerbehandlung im Stale-Wrapper."""
        with patch.object(manager, "handle_stale", side_effect=Exception("Test Error")):
            # Sollte keine Exception werfen
            await manager._wrapper_stale(None)

    def test_get_sensor_count(self, manager):
        """Testet die Sensor-Zählung."""
        assert manager.get_sensor_count() == 0

        manager.sensors = {"sensor1": MagicMock(), "sensor2": MagicMock()}
        assert manager.get_sensor_count() == 2

    def test_get_sensor_info(self, manager):
        """Testet die Sensor-Informationen."""
        mock_sensor = MagicMock()
        mock_sensor.__class__.__name__ = "TestSensor"
        mock_sensor._attr_available = True
        mock_sensor._attr_native_value = 42.5

        manager.sensors = {"test_sensor": mock_sensor}

        info = manager.get_sensor_info()

        assert "test_sensor" in info
        assert info["test_sensor"]["class"] == "TestSensor"
        assert info["test_sensor"]["available"] is True
        assert info["test_sensor"]["state"] == 42.5

    def test_get_sensor_info_with_error(self, manager):
        """Testet Sensor-Informationen mit Fehler."""
        mock_sensor = MagicMock()
        mock_sensor.__class__.__name__ = "TestSensor"
        mock_sensor._attr_available = True
        # Simuliere einen Fehler beim Zugriff mit AttributeError
        
        def side_effect_attr(name):
            if name == "_attr_native_value":
                raise AttributeError("Test error")
            return object.__getattribute__(mock_sensor, name)
        type(mock_sensor).__getattribute__ = side_effect_attr

        manager.sensors = {"test_sensor": mock_sensor}

        info = manager.get_sensor_info()

        assert "test_sensor" in info
        assert "error" in info["test_sensor"]

    @pytest.mark.asyncio
    async def test_create_sensors_for_batteries_error(self, manager):
        """Testet die Sensor-Erstellung mit Fehlern."""
        batteries = [{"batteryCapacity": 1000}]

        # Mock eine Sensor-Klasse, die einen Fehler wirft
        with patch.object(manager, "SENSOR_CLASSES", [("test_sensor", MagicMock(side_effect=Exception("Creation Error")))]):
            new_sensors = await manager._create_sensors_for_batteries(batteries)

            # Sollte leere Liste zurückgeben, trotz Fehler
            assert new_sensors == []

    @pytest.mark.asyncio
    async def test_update_all_listeners_error(self, manager):
        """Testet die Listener-Updates mit Fehlern."""
        data = {"test": "data"}

        # Mock-Listener, der einen Fehler wirft
        mock_listener = AsyncMock(side_effect=Exception("Listener Error"))

        manager.hass.data = {
            "maxxi_charge_connect": {
                "test_entry_id": {
                    "listeners": [mock_listener]
                }
            }
        }

        # Sollte keine Exception werfen
        await manager._update_all_listeners(data)

    def test_sensor_classes_constant(self, manager):
        """Testet die SENSOR_CLASSES Konstante."""
        assert len(manager.SENSOR_CLASSES) == 11

        # Prüfen, ob alle erwarteten Sensorklassen vorhanden sind
        sensor_names = [name for name, _ in manager.SENSOR_CLASSES]
        expected_names = [
            "battery_soe",
            "battery_soc_sensor",
            "battery_voltage_sensor",
            "battery_ampere_sensor",
            "battery_pv_power_sensor",
            "battery_pv_voltage_sensor",
            "battery_pv_ampere_sensor",
            "battery_mppt_voltage_sensor",
            "battery_mppt_ampere_sensor",
            "battery_charge_sensor",
            "battery_discharge_sensor"
        ]

        assert sensor_names == expected_names
