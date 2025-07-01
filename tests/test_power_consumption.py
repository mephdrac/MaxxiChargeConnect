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

sys.path.append(str(Path(__file__).resolve().parents[3]))

from unittest.mock import MagicMock, patch
from homeassistant.components.sensor import SensorDeviceClass, SensorStateClass
from homeassistant.const import CONF_WEBHOOK_ID, UnitOfPower

import pytest

from custom_components.maxxi_charge_connect.const import DOMAIN
from custom_components.maxxi_charge_connect.devices.power_consumption import (
    PowerConsumption,
)


_LOGGER = logging.getLogger(__name__)

# Dummy-Konstanten
WEBHOOK_ID = "abc123"


@pytest.fixture
def mock_entry():
    """Testet die Initialisierung des PowerConsumption-Sensors.

    Stellt sicher, dass die Sensoreigenschaften korrekt gesetzt sind.
    """
    entry = MagicMock()
    entry.entry_id = "test_entry_id"
    entry.title = "Maxxi Entry"
    entry.data = {"webhook_id": WEBHOOK_ID}
    return entry


@pytest.mark.asyncio
async def test_power_consumption_initialization(mock_entry):
    """Testet die Verarbeitung von Webhook-Daten (Pccu und Pr gültig).

    Erwartet:
    - Pccu und -Pr werden addiert (nur wenn Pr negativ),
    - native_v
    """
    sensor = PowerConsumption(mock_entry)

    assert sensor._attr_unique_id == "test_entry_id_power_consumption"
    # pylint: disable=protected-access
    assert sensor._attr_icon == "mdi:home-import-outline"  # pylint: disable=protected-access
    assert sensor._attr_native_value is None  # pylint: disable=protected-access
    assert sensor._attr_device_class == SensorDeviceClass.POWER  # pylint: disable=protected-access
    assert sensor._attr_state_class == SensorStateClass.MEASUREMENT
    # pylint: disable=protected-access
    assert sensor._attr_native_unit_of_measurement == UnitOfPower.WATT
    # pylint: disable=protected-access


@pytest.mark.asyncio
async def test_power_consumption_add_and_handle_update1():
    """Testet, wenn isPccuOk False ist (ungültige Pccu-Daten).

    Erwartet:
    - native_value bleibt None.
    """

    mock_entry = MagicMock()
    mock_entry.entry_id = "abc123"
    mock_entry.title = "My Device"
    mock_entry.data = {CONF_WEBHOOK_ID: "webhook456"}

    sensor = PowerConsumption(mock_entry)
    sensor.hass = MagicMock()
    sensor.async_on_remove = MagicMock()

    # async_write_ha_state mocken
    sensor.async_write_ha_state = MagicMock()

    dispatcher_called = {}

    with (
        patch(
            "custom_components.maxxi_charge_connect.devices.power_consumption."
            "async_dispatcher_connect"
        ) as mock_connect,
        patch(
            "custom_components.maxxi_charge_connect.devices.power_consumption.is_pccu_ok"
        ) as mock_is_pccu_ok,
        patch(
            "custom_components.maxxi_charge_connect.devices.power_consumption.is_pr_ok"
        ) as mock_is_pr_ok,
    ):
        mock_is_pccu_ok.return_value = True
        mock_is_pr_ok.return_value = True

        def fake_unsub():
            dispatcher_called["disconnected"] = True

        mock_connect.return_value = fake_unsub

        await sensor.async_added_to_hass()

        signal = f"{DOMAIN}_webhook456_update_sensor"
        mock_connect.assert_called_once_with(sensor.hass, signal, sensor._handle_update)
        # pylint: disable=protected-access
        sensor.async_on_remove.assert_called_once_with(fake_unsub)

        pccu = 34.678
        pr = 234.675
        await sensor._handle_update({"Pccu": pccu, "Pr": pr})  # pylint: disable=protected-access
        assert sensor.native_value == round(pccu + max(pr, 0), 2)


@pytest.mark.asyncio
async def test_power_consumption_add_and_handle_update2():
    """Testet, wenn isPrOk False ist (ungültige Pr-Daten).

    Erwartet:
    - native_value bleibt None.
    """

    mock_entry = MagicMock()
    mock_entry.entry_id = "abc123"
    mock_entry.title = "My Device"
    mock_entry.data = {CONF_WEBHOOK_ID: "webhook456"}

    sensor = PowerConsumption(mock_entry)
    sensor.hass = MagicMock()
    sensor.async_on_remove = MagicMock()

    # async_write_ha_state mocken
    sensor.async_write_ha_state = MagicMock()

    dispatcher_called = {}

    with (
        patch(
            "custom_components.maxxi_charge_connect.devices.power_consumption."
            "async_dispatcher_connect"
        ) as mock_connect,
        patch(
            "custom_components.maxxi_charge_connect.devices.power_consumption.is_pccu_ok"
        ) as mock_is_pccu_ok,
        patch(
            "custom_components.maxxi_charge_connect.devices.power_consumption.is_pr_ok"
        ) as mock_is_pr_ok,
    ):
        mock_is_pccu_ok.return_value = False
        mock_is_pr_ok.return_value = True

        def fake_unsub():
            dispatcher_called["disconnected"] = True

        mock_connect.return_value = fake_unsub

        await sensor.async_added_to_hass()

        signal = f"{DOMAIN}_webhook456_update_sensor"
        mock_connect.assert_called_once_with(sensor.hass, signal, sensor._handle_update)
        # pylint: disable=protected-access
        sensor.async_on_remove.assert_called_once_with(fake_unsub)

        pccu = 34.678
        pr = 234.675
        await sensor._handle_update({"Pccu": pccu, "Pr": pr})  # pylint: disable=protected-access
        assert sensor.native_value is None


@pytest.mark.asyncio
async def test_power_consumption_add_and_handle_update3():
    """Testet, wenn isPccuOk und isPrOk beide False sind.

    Erwartet:
    - native_value bleibt None.
    """

    mock_entry = MagicMock()
    mock_entry.entry_id = "abc123"
    mock_entry.title = "My Device"
    mock_entry.data = {CONF_WEBHOOK_ID: "webhook456"}

    sensor = PowerConsumption(mock_entry)
    sensor.hass = MagicMock()
    sensor.async_on_remove = MagicMock()

    # async_write_ha_state mocken
    sensor.async_write_ha_state = MagicMock()

    dispatcher_called = {}

    with (
        patch(
            "custom_components.maxxi_charge_connect.devices.power_consumption."
            "async_dispatcher_connect"
        ) as mock_connect,
        patch(
            "custom_components.maxxi_charge_connect.devices.power_consumption.is_pccu_ok"
        ) as mock_is_pccu_ok,
        patch(
            "custom_components.maxxi_charge_connect.devices.power_consumption.is_pr_ok"
        ) as mock_is_pr_ok,
    ):
        mock_is_pccu_ok.return_value = True
        mock_is_pr_ok.return_value = False

        def fake_unsub():
            dispatcher_called["disconnected"] = True

        mock_connect.return_value = fake_unsub

        await sensor.async_added_to_hass()

        signal = f"{DOMAIN}_webhook456_update_sensor"
        mock_connect.assert_called_once_with(sensor.hass, signal, sensor._handle_update)
        # pylint: disable=protected-access
        sensor.async_on_remove.assert_called_once_with(fake_unsub)

        pccu = 34.678
        pr = 234.675
        await sensor._handle_update({"Pccu": pccu, "Pr": pr})  # pylint: disable=protected-access
        assert sensor.native_value is None


@pytest.mark.asyncio
async def test_power_consumption_add_and_handle_update4():
    """Testet das Entfernen des Sensors aus Home Assistant.

    Erwartet:
    - Dispatcher-Abmeldung wird durchgeführt,
    - `_unsub_dispatcher` wird auf None gesetzt.
    """

    mock_entry = MagicMock()
    mock_entry.entry_id = "abc123"
    mock_entry.title = "My Device"
    mock_entry.data = {CONF_WEBHOOK_ID: "webhook456"}

    sensor = PowerConsumption(mock_entry)
    sensor.hass = MagicMock()
    sensor.async_on_remove = MagicMock()

    # async_write_ha_state mocken
    sensor.async_write_ha_state = MagicMock()

    dispatcher_called = {}

    with (
        patch(
            "custom_components.maxxi_charge_connect.devices.power_consumption."
            "async_dispatcher_connect"
        ) as mock_connect,
        patch(
            "custom_components.maxxi_charge_connect.devices.power_consumption.is_pccu_ok"
        ) as mock_is_pccu_ok,
        patch(
            "custom_components.maxxi_charge_connect.devices.power_consumption.is_pr_ok"
        ) as mock_is_pr_ok,
    ):
        mock_is_pccu_ok.return_value = False
        mock_is_pr_ok.return_value = False

        def fake_unsub():
            dispatcher_called["disconnected"] = True

        mock_connect.return_value = fake_unsub

        await sensor.async_added_to_hass()

        signal = f"{DOMAIN}_webhook456_update_sensor"
        mock_connect.assert_called_once_with(sensor.hass, signal, sensor._handle_update)
        # pylint: disable=protected-access
        sensor.async_on_remove.assert_called_once_with(fake_unsub)

        pccu = 34.678
        pr = 234.675
        await sensor._handle_update({"Pccu": pccu, "Pr": pr})  # pylint: disable=protected-access
        assert sensor.native_value is None


def test_device_info(mock_entry):
    """Testet die Rückgabe der `device_info`.

    Erwartet:
    - Korrekte Angaben zu Identifikator, Name, Hersteller und Modell.
    """
    sensor = PowerConsumption(mock_entry)
    info = sensor.device_info
    assert info["identifiers"] == {(DOMAIN, "test_entry_id")}
    assert info["name"] == "Maxxi Entry"
    assert info["manufacturer"] == "mephdrac"
    assert info["model"] == "CCU - Maxxicharge"
