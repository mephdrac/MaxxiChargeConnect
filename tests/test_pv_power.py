"""Tests für das PvPower-Modul der MaxxiChargeConnect-Integration.

Dieses Modul enthält Unit-Tests zur Überprüfung der Funktionalität des
PvPower-Sensors, insbesondere hinsichtlich:
- korrekter Initialisierung,
- Verarbeitung eingehender Daten über Webhook,
- Entfernung aus Home Assistant,
- korrekter Rückgabe von Geräteinformationen.
"""

import logging
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from homeassistant.components.sensor import SensorDeviceClass, SensorStateClass
from homeassistant.const import UnitOfPower

from custom_components.maxxi_charge_connect.const import DOMAIN
from custom_components.maxxi_charge_connect.devices.pv_power import PvPower

sys.path.append(str(Path(__file__).resolve().parents[3]))

_LOGGER = logging.getLogger(__name__)


# Dummy-Konstanten
WEBHOOK_ID = "abc123"


@pytest.fixture
def sensor():
    """Gibt ein Mock-Konfigurationsobjekt für den Sensor zurück.

    Returns:
        MagicMock: Ein simuliertes Home Assistant-Konfigurationsobjekt.

    """
    entry = MagicMock()
    entry.entry_id = "test_entry_id"
    entry.title = "Maxxi Entry"
    entry.data = {"webhook_id": WEBHOOK_ID}

    sensor_obj = PvPower(entry)
    sensor_obj.hass = MagicMock()

    # async_write_ha_state mocken
    sensor_obj.async_write_ha_state = MagicMock()

    return sensor_obj


@pytest.mark.asyncio
async def test_pv_power_initialization(sensor):  # pylint: disable=redefined-outer-name
    """Testet die Initialisierung des PvPower-Sensors.

    Überprüft, ob alle relevanten Entitätsattribute korrekt gesetzt sind.
    """
    assert sensor._attr_unique_id == "test_entry_id_pv_power"  # pylint: disable=protected-access
    assert sensor._attr_icon == "mdi:solar-power"  # pylint: disable=protected-access
    assert sensor._attr_native_value is None  # pylint: disable=protected-access
    assert sensor._attr_device_class == SensorDeviceClass.POWER  # pylint: disable=protected-access
    assert sensor._attr_state_class == SensorStateClass.MEASUREMENT  # pylint: disable=protected-access
    assert sensor._attr_native_unit_of_measurement == UnitOfPower.WATT  # pylint: disable=protected-access


@pytest.mark.asyncio
async def test_pv_power_add_and_handle_update1(sensor):  # pylint: disable=redefined-outer-name
    """Testet den Update-Mechanismus, wenn `isPowerTotalOk` True ergibt.

    Erwartet, dass der Sensorwert korrekt auf die empfangene Leistung gesetzt wird.
    """
    with (
        patch(
            "custom_components.maxxi_charge_connect.devices.pv_power.is_power_total_ok"
        ) as mock_is_power_total_ok,
    ):
        mock_is_power_total_ok.return_value = True

        await sensor.handle_update({"PV_power_total": 234.675})  # pylint: disable=protected-access
        assert sensor.native_value == 234.675


@pytest.mark.asyncio
async def test_pv_power_add_and_handle_update2(sensor):  # pylint: disable=redefined-outer-name
    """Testet Verhalten bei ungültiger Leistung, wenn `isPowerTotalOk` False ergibt.

    Erwartet, dass der Sensorwert in diesem Fall nicht gesetzt wird (None).
    """
    with (
        patch(
            "custom_components.maxxi_charge_connect.devices.pv_power.is_power_total_ok"
        ) as mock_is_power_total_ok,
    ):
        mock_is_power_total_ok.return_value = False

        await sensor.handle_update({"PV_power_total": 234})  # pylint: disable=protected-access
        assert sensor.native_value is None


@pytest.mark.asyncio
async def test_pv_power_missing_field(sensor):  # pylint: disable=redefined-outer-name
    """Testet Verhalten, wenn PV_power_total Feld fehlt."""
    sensor._attr_native_value = 500.0  # Startwert
    await sensor.handle_update({})
    assert sensor.native_value == 500.0  # Sollte unverändert bleiben


@pytest.mark.asyncio
async def test_pv_power_none_value(sensor):  # pylint: disable=redefined-outer-name
    """Testet Verhalten, wenn PV_power_total None ist."""
    sensor._attr_native_value = 500.0  # Startwert
    await sensor.handle_update({"PV_power_total": None})
    assert sensor.native_value == 500.0  # Sollte unverändert bleiben


@pytest.mark.asyncio
async def test_pv_power_invalid_string(sensor):  # pylint: disable=redefined-outer-name
    """Testet Verhalten bei ungültigen String-Werten."""
    sensor._attr_native_value = 500.0  # Startwert
    await sensor.handle_update({"PV_power_total": "invalid"})
    assert sensor.native_value == 500.0  # Sollte unverändert bleiben


@pytest.mark.asyncio
async def test_pv_power_explicit_zero(sensor):  # pylint: disable=redefined-outer-name
    """Testet Verhalten bei explizitem 0-Wert."""
    with (
        patch(
            "custom_components.maxxi_charge_connect.devices.pv_power.is_power_total_ok"
        ) as mock_is_power_total_ok,
    ):
        mock_is_power_total_ok.return_value = True
        await sensor.handle_update({"PV_power_total": 0})
        assert sensor.native_value == 0


def test_device_info(sensor):  # pylint: disable=redefined-outer-name
    """Testet die `device_info`-Eigenschaft des Sensors.

    Erwartet korrekte Rückgabe der Geräteinformationen.
    """
    info = sensor.device_info
    assert info["identifiers"] == {(DOMAIN, "test_entry_id")}
    assert info["name"] == "Maxxi Entry"
    assert info["manufacturer"] == "mephdrac"
    assert info["model"] == "CCU - Maxxicharge"
