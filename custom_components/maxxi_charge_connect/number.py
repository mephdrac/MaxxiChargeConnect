"""Number-Plattform für MaxxiChargeConnect."""

from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity_platform import AddEntitiesCallback

#from .const import DOMAIN
from .http_post.number_config_entity import NumberConfigEntity  # Importiere deine Entity-Klasse


# Beispielhafte Liste konfigurierbarer Parameter
NUMBER_ENTITY_DESCRIPTIONS = [
    {
        "translation_key": "max_soc",
        "key": "maxSOC",
        "min": 20,
        "max": 100,
        "step": 1,
        "unit": "%",
    },
    {
        "translation_key": "min_soc",
        "key": "minSOC",
        "min": 5,
        "max": 50,
        "step": 1,
        "unit": "%",
    },
    {
        "translation_key": "threshold",
        "key": "threshold",
        "min": 0,
        "max": 1000,
        "step": 10,
        "unit": "W",
    },
]


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Richte Number-Entities für MaxxiChargeConnect ein."""

    entities = []

    for desc in NUMBER_ENTITY_DESCRIPTIONS:
        entity = NumberConfigEntity(
            entry=entry,
            translation_key=desc["translation_key"],
            key=desc["key"],
            min_value=desc["min"],
            max_value=desc["max"],
            step=desc["step"],
            unit=desc["unit"],
        )
        entities.append(entity)

    async_add_entities(entities)
