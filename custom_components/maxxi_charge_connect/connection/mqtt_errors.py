"""Translatable MQTT errors with an English fallback for logs and older clients."""

from homeassistant.exceptions import HomeAssistantError

from ..const import DOMAIN


def mqtt_error(key: str, fallback: str, **placeholders) -> HomeAssistantError:
    return HomeAssistantError(
        fallback,
        translation_domain=DOMAIN,
        translation_key=key,
        translation_placeholders={key: str(value) for key, value in placeholders.items()},
    )
