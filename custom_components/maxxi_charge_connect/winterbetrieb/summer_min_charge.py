"""Provide a Home Assistant number entity for summer minimum battery charge.

This module defines the minimum battery charge level used during summer
operation of a MaxxiCharge CCU.

The configured value is stored persistently in the Home Assistant
configuration entry and shared with other integration components.

The entity is only available when winter mode is disabled.
"""

import logging

from homeassistant.components.number import NumberEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE, EntityCategory
from homeassistant.core import callback

from ..const import (
    CCU_V1,
    CONF_CCU_VERSION,
    CONF_SUMMER_MIN_CHARGE,
    CONF_WINTER_MODE,
    DEFAULT_SUMMER_MIN_CHARGE,
    DEVICE_INFO,
    DOMAIN,
    EVENT_SUMMER_MIN_CHARGE_CHANGED,
    WINTER_MODE_CHANGED_EVENT,
)

_LOGGER = logging.getLogger(__name__)


# Home Assistant supports asynchronous entity control methods.
# The abstract-method warning is intentionally disabled.
# pylint: disable=abstract-method
class SummerMinCharge(NumberEntity):
    """Represent the minimum battery charge level during summer operation.

    This entity allows users to configure the minimum battery charge
    percentage used by the CCU during summer mode.

    The configured value is stored in the Home Assistant configuration
    entry and mirrored in hass.data for access by other integration
    components.

    Changes are communicated through Home Assistant events.

    The entity becomes unavailable while winter mode is active.
    """

    _attr_translation_key = "summer_min_charge"
    _attr_has_entity_name = True

    def __init__(self, entry: ConfigEntry) -> None:
        """Initialize the summer minimum charge number entity.

        Configure the entity's unique identifier, icon, measurement
        unit, allowed value range, and configuration category.

        The initial value is loaded from the configuration entry
        options. If no value has been configured, the integration's
        default minimum charge value is used.

        Args:
            entry: Home Assistant configuration entry associated
                with the MaxxiCharge CCU.
        """
        self._entry = entry

        # Generate a stable unique identifier for the configuration entry.
        self._attr_unique_id = f"{entry.entry_id}_summer_min_charge"

        # Configure the entity's appearance and classification.
        self._attr_icon = "mdi:battery-lock"
        self._attr_native_value = None
        self._attr_entity_category = EntityCategory.CONFIG
        self._attr_native_unit_of_measurement = PERCENTAGE

        # Define the allowed percentage range and adjustment step.
        self._attr_native_min_value = 0
        self._attr_native_step = 1
        self._attr_native_max_value = 100

        # Restore the previously configured value or use the default.
        self._attr_native_value = entry.options.get(
            CONF_SUMMER_MIN_CHARGE,
            DEFAULT_SUMMER_MIN_CHARGE,
        )

        # Store event listener cleanup callbacks.
        self._remove_listener = None
        self._remove_listener_max_charge = None

    def set_native_value(self, value):
        """Forward a synchronous value change to the asynchronous handler.

        This method provides the synchronous NumberEntity interface
        and delegates the requested value change to the asynchronous
        implementation.

        Args:
            value: Requested minimum battery charge percentage.

        Returns:
            Coroutine: Awaitable returned by async_set_native_value().
        """
        return self.async_set_native_value(value)

    async def async_set_native_value(self, value: float) -> None:
        """Update and persist the minimum summer battery charge level.

        Store the requested value as the entity's current state
        and mirror it in Home Assistant's shared integration data.

        The configuration entry is updated to preserve the value
        across Home Assistant restarts.

        After saving, the entity state is refreshed immediately
        and dependent integration components are notified.

        Args:
            value: Requested minimum battery charge percentage.
        """
        # Update the current entity value.
        self._attr_native_value = value

        # Mirror the value in shared integration data so that other
        # components can access it without reading configuration options.
        self.hass.data.setdefault(DOMAIN, {})
        self.hass.data[DOMAIN][CONF_SUMMER_MIN_CHARGE] = value

        # Persist the value in the configuration entry while preserving
        # all unrelated configuration options.
        self.hass.config_entries.async_update_entry(
            self._entry,
            options={
                **self._entry.options,
                CONF_SUMMER_MIN_CHARGE: value,
            },
        )

        # Publish the updated state immediately to Home Assistant.
        self.async_write_ha_state()

        # Notify dependent components that the configured value changed.
        self._notify_dependents()

    async def async_added_to_hass(self):
        """Register event listeners when the entity enters Home Assistant.

        Subscribe to winter mode changes so the entity can update
        its availability when the operating mode changes.

        The current entity state is published after registration.
        """
        # Listen for changes to the CCU's winter operating mode.
        self._remove_listener = self.hass.bus.async_listen(
            WINTER_MODE_CHANGED_EVENT,
            self._handle_winter_mode_changed,
        )

        # Publish the initial entity state.
        self.async_write_ha_state()

    async def async_will_remove_from_hass(self):
        """Clean up event listeners before removing the entity.

        Unregister the winter mode event listener to prevent
        callbacks from being invoked after the entity has been
        removed from Home Assistant.

        The listener is removed only if it was previously registered.
        """
        if self._remove_listener:
            self._remove_listener()

    def _notify_dependents(self):
        """Notify dependent components about the summer charge setting.

        Emit an integration-specific Home Assistant event containing
        the current minimum summer charge percentage.

        The event allows other entities and integration components
        to react to changes without directly depending on this
        number entity.

        No event is emitted when the current value is None.
        """
        # Ignore notifications when no valid state is available.
        if self._attr_native_value is None:
            return

        # Broadcast the current minimum charge value.
        self.hass.bus.async_fire(
            EVENT_SUMMER_MIN_CHARGE_CHANGED,
            {"value": self._attr_native_value},
        )

    @property
    def available(self) -> bool:
        """Determine whether the summer charge setting is available.

        The entity is available only when winter mode is disabled.

        Winter mode is read from the shared Home Assistant
        integration data. If the value has not been initialized,
        winter mode is assumed to be disabled.

        Returns:
            bool: True when winter mode is disabled, otherwise False.
        """
        _LOGGER.debug(
            "WinterMinCharge available abgefragt: %s",
            self.hass.data[DOMAIN].get(CONF_WINTER_MODE, False),
        )

        return not self.hass.data[DOMAIN].get(
            CONF_WINTER_MODE,
            False,
        )

    @callback
    def _handle_winter_mode_changed(self, event):  # pylint: disable=unused-argument
        """Handle a change in the CCU winter operating mode.

        Read the new winter mode state from the received event.

        When winter mode is disabled, notify dependent components
        that the summer minimum charge setting is active again.

        Refresh the entity state in all cases so Home Assistant
        updates the entity's availability.

        Args:
            event: Home Assistant event containing the new winter
                mode state in its "enabled" data field.
        """
        winter_enabled = event.data.get("enabled", False)

        # Notify dependent components when summer operation resumes.
        if not winter_enabled:
            self._notify_dependents()

        # Refresh the entity to reflect its updated availability.
        self.async_write_ha_state()

    @property
    def device_info(self):
        """Return device registry information for the associated CCU.

        Associate this number entity with the corresponding
        MaxxiCharge CCU device in Home Assistant.

        The information includes a stable device identifier,
        the configuration entry title, common device metadata,
        and the configured CCU hardware generation.

        Returns:
            dict: Device registry information containing:
                - identifiers: Unique domain and configuration entry ID.
                - name: Display name of the configured CCU.
                - manufacturer: Device manufacturer from DEVICE_INFO.
                - model: CCU model including the configured version.
                - Additional metadata supplied by DEVICE_INFO.
        """
        # Determine the configured CCU version, falling back to v1.
        ccu_version = self._entry.data.get(
            CONF_CCU_VERSION,
            CCU_V1,
        )

        # Return device metadata used by the Home Assistant registry.
        return {
            "identifiers": {(DOMAIN, self._entry.entry_id)},
            "name": self._entry.title,
            **DEVICE_INFO,
            "model": f"CCU {ccu_version.upper()}",
        }
