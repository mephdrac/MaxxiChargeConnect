"""Number-Plattform für MaxxiChargeConnect."""

import logging
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.const import UnitOfPower, PERCENTAGE
from .http_post.number_config_entity import (
    NumberConfigEntity,
)  # Importiere deine Entity-Klasse

from .const import (
    DOMAIN,
    CONF_WINTER_MAX_CHARGE,
    CONF_WINTER_MIN_CHARGE,
    DEFAULT_WINTER_MAX_CHARGE,
    DEFAULT_WINTER_MIN_CHARGE
)

from .winterbetrieb.winter_min_charge import WinterMinCharge
from .winterbetrieb.winter_max_charge import WinterMaxCharge
from .winterbetrieb.summer_min_charge import SummerMinCharge

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Richte Number-Entities für MaxxiChargeConnect ein."""

    entities = []

    # Coordinator initialisieren mit Fehlerbehandlung
    try:
        coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
        await coordinator.async_config_entry_first_refresh()
    except Exception as e:
        _LOGGER.error("Coordinator refresh failed: %s", e)
        return

    # Standard Number-Entities
    entities.extend([
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
        ),
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
        ),
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
        ),
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
        ),
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
        ),
    ])

    # min_soc Entity (wintermodus-abhängig)
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
        depends_on_winter_mode=True
    )
    entities.append(min_soc_entity)

    # Winterbetrieb-Konfiguration
    winter_max = entry.options.get(
        CONF_WINTER_MAX_CHARGE,
        DEFAULT_WINTER_MAX_CHARGE
    )
    winter_min = entry.options.get(
        CONF_WINTER_MIN_CHARGE,
        DEFAULT_WINTER_MIN_CHARGE
    )

    # Winterbetrieb-Daten zentral speichern
    winter_data = {
        CONF_WINTER_MIN_CHARGE: winter_min,
        CONF_WINTER_MAX_CHARGE: winter_max
    }
    hass.data.setdefault(DOMAIN, {}).update(winter_data)

    # Winterbetrieb-Entities
    winter_entities = [
        WinterMinCharge(entry),
        WinterMaxCharge(entry),
        SummerMinCharge(entry)
    ]

    # Entities hinzufügen
    async_add_entities(entities)
    async_add_entities(winter_entities)
