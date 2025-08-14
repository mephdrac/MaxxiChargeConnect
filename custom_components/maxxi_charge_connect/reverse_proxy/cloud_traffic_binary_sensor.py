# sensors/cloud_traffic.py
from __future__ import annotations

import asyncio
from datetime import datetime

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.components.sensor import SensorEntity
from homeassistant.const import EntityCategory
from homeassistant.helpers.entity import DeviceInfo

from ..const import DEVICE_INFO, DOMAIN


class CloudTrafficBinarySensor(BinarySensorEntity):
    """Zeigt an, ob gerade Daten zur Cloud gesendet werden."""

    _attr_name = "Cloud Traffic"
    _attr_icon = "mdi:cloud-upload"
    _attr_device_class = "connectivity"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, device_info: DeviceInfo) -> None:
        self._attr_device_info = device_info
        self._attr_is_on = False

    async def trigger(self) -> None:
        """Setzt für 5 Sekunden auf 'on'."""
        self._attr_is_on = True
        self.async_write_ha_state()
        await asyncio.sleep(5)
        self._attr_is_on = False
        self.async_write_ha_state()


class LastCloudPayloadSensor(SensorEntity):
    """Zeigt die letzte Payload, die an die Cloud gesendet wurde."""

    _attr_name = "Letzte Cloud Payload"
    _attr_icon = "mdi:file-code"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, device_info: DeviceInfo) -> None:
        self._attr_device_info = device_info
        self._attr_native_value = None
        self._attr_extra_state_attributes = {}

    def update_payload(self, payload: dict) -> None:
        """Aktualisiert den Sensor mit neuer Payload."""
        self._attr_native_value = datetime.now().isoformat(timespec="seconds")
        self._attr_extra_state_attributes = {
            "type": payload.get("type", "unbekannt"),
            "data": payload,
        }
        self.async_write_ha_state()
