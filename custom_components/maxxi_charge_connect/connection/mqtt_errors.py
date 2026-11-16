"""Create translatable MQTT errors with an English fallback message.

Translation keys and placeholders allow Home Assistant to display localized
messages. The fallback provides an English message for logs and clients that
do not use the translation metadata.
"""

from homeassistant.exceptions import HomeAssistantError

from ..const import DOMAIN


def mqtt_error(key: str, fallback: str, **placeholders) -> HomeAssistantError:
    """Create a Home Assistant error with MQTT translation metadata.

    This function constructs the exception without raising it. The caller
    decides when and where to raise the returned error.

    Args:
        key: Translation key identifying the error within the integration's
            exception translations.
        fallback: English message used when displaying the exception without
            translation support.
        **placeholders: Named values to insert into the translated message.
            Each value is converted to a string.

    Returns:
        A HomeAssistantError containing the fallback message, integration
        translation domain, translation key, and normalized placeholders.
    """
    return HomeAssistantError(
        fallback,
        translation_domain=DOMAIN,
        translation_key=key,
        # Normalize placeholder values to the strings expected by translations.
        translation_placeholders={key: str(value) for key, value in placeholders.items()},
    )
