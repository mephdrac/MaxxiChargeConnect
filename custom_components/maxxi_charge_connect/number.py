"""Number-Plattform für MaxxiChargeConnect."""

import logging
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.const import UnitOfPower, PERCENTAGE
from .http_post.number_config_entity import (
    NumberConfigEntity,
)  # Importiere deine Entity-Klasse

from .const import DOMAIN

from .winterbetrieb.winter_min_charge import WinterMinCharge
from .winterbetrieb.winter_max_charge import WinterMaxCharge

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Richte Number-Entities für MaxxiChargeConnect ein."""

    entities = []

    # self._attr_unique_id = f"{entry.entry_id}_MaximumBatteryCharge"
    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    await coordinator.async_config_entry_first_refresh()
    
    min_soc_entity = NumberConfigEntity(
            hass,
            entry,
            "min_soc",
            "minSOC",
            "MinimumBatteryDischarge",
            0,
            100,
            1,
            PERCENTAGE,
        )

    entities.append(
        NumberConfigEntity(
            hass,
            entry,
            "maxOutputPower",
            "maxOutputPower",
            "MaximumPower",
            0,
            3000,
            1,
            UnitOfPower.WATT,
        )
    )
    entities.append(
        NumberConfigEntity(
            hass,
            entry,
            "offlinePower",
            "offlinePower",
            "OfflineOutputPower",
            0,
            3000,
            1,
            UnitOfPower.WATT,
        )
    )
    entities.append(
        NumberConfigEntity(
            hass,
            entry,
            "max_soc",
            "maxSOC",
            "MaximumBatteryCharge",
            0,
            100,
            1,
            PERCENTAGE,
        )
    )
    entities.append(
        min_soc_entity
    )
    entities.append(
        NumberConfigEntity(
            hass,
            entry,
            "baseLoad",
            "baseLoad",
            "OutputOffset",
            -1000,
            1000,
            1,
            UnitOfPower.WATT,
        )
    )
    entities.append(
        NumberConfigEntity(
            hass,
            entry,
            "threshold",
            "threshold",
            "ResponseTolerance",
            -1000,
            1000,
            1,
            UnitOfPower.WATT,
        )
    )

    async_add_entities(entities)

    winter_min_charge = WinterMinCharge(entry)
    winter_max_charge = WinterMaxCharge(entry)

    async_add_entities([winter_min_charge, winter_max_charge])
