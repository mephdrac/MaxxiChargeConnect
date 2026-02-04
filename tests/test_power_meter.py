"""Tests für das power_meter-Modul der MaxxiChargeConnect-Integration.

Dieses Testmodul prüft die Initialisierung, das Verhalten bei Zustandsänderungen
sowie das Entfernen des PowerMeter-Sensors aus Home Assistant. Dabei wird auf
korrekte Verarbeitung der Daten geachtet, insbesondere abhängig von `isPrOk()`.
"""

import logging
import sys
from pathlib import Path

from unittest.mock import MagicMock, patch
from homeassistant.components.sensor import SensorDeviceClass, SensorStateClass
from homeassistant.const import UnitOfPower

import pytest

from custom_components.maxxi_charge_connect.const import DOMAIN
from custom_components.maxxi_charge_connect.devices.power_meter import PowerMeter

sys.path.append(str(Path(__file__).resolve().parents[3]))

_LOGGER = logging.getLogger(__name__)

# Dummy-Konstanten
WEBHOOK_ID = "abc123"


@pytest.fixture
def sensor():
    """Gibt ein Mock-Konfigurationsobjekt für einen Sensor zurück.

    Returns:
        MagicMock: Ein simuliertes Konfigurationsobjekt mit Entry-ID und Webhook-ID.

    """
    entry = MagicMock()
    entry.entry_id = "test_entry_id"
    entry.title = "Maxxi Entry"
    entry.data = {"webhook_id": WEBHOOK_ID}

    sensor_obj = PowerMeter(entry)
    sensor_obj.hass = MagicMock()
    sensor_obj.async_on_remove = MagicMock()

    return sensor_obj


@pytest.mark.asyncio
async def test_power_meter_initialization(sensor):  # pylint: disable=redefined-outer-name
    """Testet die Initialisierung des power_meter-Sensors.

    Stellt sicher, dass alle Attribute korrekt gesetzt werden.
    """
    assert sensor._attr_unique_id == "test_entry_id_power_meter"  # pylint: disable=protected-access
    assert sensor._attr_icon == "mdi:gauge"  # pylint: disable=protected-access
    assert sensor._attr_native_value is None  # pylint: disable=protected-access
    assert sensor._attr_device_class == SensorDeviceClass.POWER  # pylint: disable=protected-access
    assert sensor._attr_state_class == SensorStateClass.MEASUREMENT  # pylint: disable=protected-access
    # pylint: disable=protected-access
    assert sensor._attr_native_unit_of_measurement == UnitOfPower.WATT
    # pylint: disable=protected-access


@pytest.mark.asyncio
async def test_power_meter_add_and_handle_update1(sensor):  # pylint: disable=redefined-outer-name
    """Testet Verarbeitung von Daten, wenn isPrOk True zurückgibt.

    Erwartet, dass der Sensorwert korrekt aktualisiert wird.

    Simuliert einen gültigen Leistungswert (`Pr`) und überprüft,
    ob dieser gesetzt wird.
    """
    with (
        patch(
            "custom_components.maxxi_charge_connect.devices.power_meter.is_pr_ok"
        ) as mock_is_pr_ok,
    ):
        mock_is_pr_ok.return_value = True
        await sensor.handle_update({"Pr": 234.675})  # pylint: disable=protected-access
        assert sensor.native_value == 234.675


@pytest.mark.asyncio
async def test_power_meter_add_and_handle_update2(sensor):  # pylint: disable=redefined-outer-name
    """Testet Verhalten, wenn isPrOk False zurückgibt.

    Erwartet, dass der Sensorwert nicht gesetzt wird.
    """
    with (
        patch(
            "custom_components.maxxi_charge_connect.devices.power_meter.is_pr_ok"
        ) as mock_is_pr_ok,
    ):
        mock_is_pr_ok.return_value = False

        await sensor.handle_update({"Pr": 234.675})  # pylint: disable=protected-access
        assert sensor.native_value is None


@pytest.mark.asyncio
async def test_power_meter_missing_pr_key(sensor):   # pylint: disable=redefined-outer-name
    """Testet Verhalten, wenn Pr-Schlüssel komplett fehlt."""
    sensor._attr_native_value = 100.0  # Startwert setzen
    await sensor.handle_update({})
    assert sensor.native_value == 100.0  # Sollte unverändert bleiben


@pytest.mark.asyncio
async def test_power_meter_pr_zero(sensor):  # pylint: disable=redefined-outer-name
    """Testet Verhalten, wenn Pr explizit 0 ist."""
    await sensor.handle_update({"Pr": 0})
    assert sensor.native_value == 0


@pytest.mark.asyncio
async def test_power_meter_invalid_pr_values(sensor):  # pylint: disable=redefined-outer-name
    """Testet Verhalten bei ungültigen Pr-Werten."""
    # Test mit None
    sensor._attr_native_value = 100.0  # Startwert
    await sensor.handle_update({"Pr": None})
    assert sensor.native_value == 100.0  # Sollte unverändert bleiben

    # Test mit String
    await sensor.handle_update({"Pr": "invalid"})
    assert sensor.native_value == 100.0  # Sollte unverändert bleiben


def test_device_info(sensor):  # pylint: disable=redefined-outer-name
    """Testet die `device_info`-Eigenschaft des power_meter-Sensors.

    Erwartet die korrekte Rückgabe der Geräteinformationen.
    """
    info = sensor.device_info
    assert info["identifiers"] == {(DOMAIN, "test_entry_id")}
    assert info["name"] == "Maxxi Entry"
    assert info["manufacturer"] == "mephdrac"
    assert info["model"] == "CCU - Maxxicharge"

