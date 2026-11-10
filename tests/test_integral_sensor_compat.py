"""Check energy sensor construction across Home Assistant constructor APIs."""

from inspect import signature
from unittest.mock import MagicMock

import pytest
from homeassistant.components.integration.sensor import IntegrationSensor
from homeassistant.components.sensor import SensorDeviceClass

from custom_components.maxxi_charge_connect.devices.today_integral_sensor import TodayIntegralSensor
from custom_components.maxxi_charge_connect.devices.total_integral_sensor import TotalIntegralSensor


@pytest.mark.parametrize("sensor_class", [TodayIntegralSensor, TotalIntegralSensor])
@pytest.mark.parametrize("requires_device_class", [False, True])
def test_constructor_compatibility(monkeypatch, sensor_class, requires_device_class):
    """Accept the installed API and the newer required device_class keyword."""
    original_init = IntegrationSensor.__init__
    received = []

    if requires_device_class:

        def init(self, *, device_class, **kwargs):
            received.append(device_class)
            if "device_class" in signature(original_init).parameters:
                kwargs["device_class"] = device_class
            original_init(self, **kwargs)

        monkeypatch.setattr(IntegrationSensor, "__init__", init)

    entry = MagicMock(entry_id="test_entry")
    sensor = sensor_class(MagicMock(), entry, "sensor.power")

    assert sensor.device_class == SensorDeviceClass.ENERGY
    assert sensor.unique_id.startswith("test_entry_")
    if requires_device_class:
        assert received == [SensorDeviceClass.ENERGY]
