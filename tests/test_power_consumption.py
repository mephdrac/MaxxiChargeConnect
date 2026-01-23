"""Testmodul für PowerConsumption.

Dieses Modul enthält Tests für den PowerConsumption-Sensor
der MaxxiChargeConnect-Integration. Getestet werden:
- die Initialisierung des Sensors,
- das Registrieren und Abmelden am Dispatcher,
- das Verarbeiten von Webhook-Daten,
- die Berechnung des aktuellen Verbrauchswerts basierend auf Pccu und Pr,
- das Entfernen des Sensors aus Home Assistant.
"""

import logging
import sys
from pathlib import Path

from unittest.mock import MagicMock, patch
from homeassistant.components.sensor import SensorDeviceClass, SensorStateClass
from homeassistant.const import UnitOfPower

import pytest

from custom_components.maxxi_charge_connect.const import DOMAIN
from custom_components.maxxi_charge_connect.devices.power_consumption import (
    PowerConsumption,
)
sys.path.append(str(Path(__file__).resolve().parents[3]))

_LOGGER = logging.getLogger(__name__)

# Dummy-Konstanten
WEBHOOK_ID = "abc123"


@pytest.fixture
def sensor():
    """Testet die Initialisierung des PowerConsumption-Sensors.

    Stellt sicher, dass die Sensoreigenschaften korrekt gesetzt sind.
    """
    entry = MagicMock()
    entry.entry_id = "test_entry_id"
    entry.title = "Maxxi Entry"
    entry.data = {"webhook_id": WEBHOOK_ID}

    sensor_obj = PowerConsumption(entry)
    sensor_obj.hass = MagicMock()
    sensor_obj.async_on_remove = MagicMock()

    # # async_write_ha_state mocken
    sensor_obj.async_write_ha_state = MagicMock()
    return sensor_obj


@pytest.mark.asyncio
async def test_power_consumption_initialization(sensor):  # pylint: disable=redefined-outer-name
    """Testet die Verarbeitung von Webhook-Daten (Pccu und Pr gültig).

    Erwartet:
    - Pccu und -Pr werden addiert (nur wenn Pr negativ),
    - native_v
    """
    assert sensor._attr_unique_id == "test_entry_id_power_consumption"  # pylint: disable=protected-access
    # pylint: disable=protected-access
    assert sensor._attr_icon == "mdi:home-import-outline"  # pylint: disable=protected-access
    assert sensor._attr_native_value is None  # pylint: disable=protected-access
    assert sensor._attr_device_class == SensorDeviceClass.POWER  # pylint: disable=protected-access
    assert sensor._attr_state_class == SensorStateClass.MEASUREMENT
    # pylint: disable=protected-access
    assert sensor._attr_native_unit_of_measurement == UnitOfPower.WATT
    # pylint: disable=protected-access


@pytest.mark.asyncio
async def test_power_consumption_add_and_handle_update1(sensor):  # pylint: disable=redefined-outer-name
    """Testet, wenn isPccuOk False ist (ungültige Pccu-Daten).

    Erwartet:
    - native_value bleibt None.
    """
    with (
        patch(
            "custom_components.maxxi_charge_connect.devices.power_consumption.is_pccu_ok"
        ) as mock_is_pccu_ok,
        patch(
            "custom_components.maxxi_charge_connect.devices.power_consumption.is_pr_ok"
        ) as mock_is_pr_ok,
    ):

        mock_is_pccu_ok.return_value = True
        mock_is_pr_ok.return_value = True

        pccu = 34.678
        pr = 234.675
        await sensor.handle_update({"Pccu": pccu, "Pr": pr})  # pylint: disable=protected-access
        assert sensor.native_value == round(pccu + max(pr, 0), 2)


@pytest.mark.asyncio
async def test_power_consumption_add_and_handle_update2(sensor):  # pylint: disable=redefined-outer-name
    """Testet, wenn isPrOk False ist (ungültige Pr-Daten).

    Erwartet:
    - native_value bleibt None.
    """
    with (
        patch(
            "custom_components.maxxi_charge_connect.devices.power_consumption.is_pccu_ok"
        ) as mock_is_pccu_ok,
        patch(
            "custom_components.maxxi_charge_connect.devices.power_consumption.is_pr_ok"
        ) as mock_is_pr_ok,
    ):
        mock_is_pccu_ok.return_value = False
        mock_is_pr_ok.return_value = True

        pccu = 34.678
        pr = 234.675
        await sensor.handle_update({"Pccu": pccu, "Pr": pr})  # pylint: disable=protected-access
        assert sensor.native_value is None


@pytest.mark.asyncio
async def test_power_consumption_add_and_handle_update3(sensor):  # pylint: disable=redefined-outer-name
    """Testet, wenn isPccuOk und isPrOk beide False sind.

    Erwartet:
    - native_value bleibt None.
    """
    with (
        patch(
            "custom_components.maxxi_charge_connect.devices.power_consumption.is_pccu_ok"
        ) as mock_is_pccu_ok,
        patch(
            "custom_components.maxxi_charge_connect.devices.power_consumption.is_pr_ok"
        ) as mock_is_pr_ok,
    ):
        mock_is_pccu_ok.return_value = True
        mock_is_pr_ok.return_value = False

        pccu = 34.678
        pr = 234.675
        await sensor.handle_update({"Pccu": pccu, "Pr": pr})  # pylint: disable=protected-access
        assert sensor.native_value is None


@pytest.mark.asyncio
async def test_power_consumption_add_and_handle_update4(sensor):  # pylint: disable=redefined-outer-name
    """Testet das Entfernen des Sensors aus Home Assistant.

    Erwartet:
    - Dispatcher-Abmeldung wird durchgeführt,
    - `_unsub_dispatcher` wird auf None gesetzt.
    """

    with (
        patch(
            "custom_components.maxxi_charge_connect.devices.power_consumption.is_pccu_ok"
        ) as mock_is_pccu_ok,
        patch(
            "custom_components.maxxi_charge_connect.devices.power_consumption.is_pr_ok"
        ) as mock_is_pr_ok,
    ):
        mock_is_pccu_ok.return_value = False
        mock_is_pr_ok.return_value = False

        pccu = 34.678
        pr = 234.675
        await sensor.handle_update({"Pccu": pccu, "Pr": pr})  # pylint: disable=protected-access
        assert sensor.native_value is None


@pytest.mark.asyncio
def test_device_info(sensor):  # pylint: disable=redefined-outer-name
    """Testet die Rückgabe der `device_info`.

    Erwartet:
    - Korrekte Angaben zu Identifikator, Name, Hersteller und Modell.
    """
    info = sensor.device_info
    assert info["identifiers"] == {(DOMAIN, "test_entry_id")}
    assert info["name"] == "Maxxi Entry"
    assert info["manufacturer"] == "mephdrac"
    assert info["model"] == "CCU - Maxxicharge"
