"""Base class for CCU telemetry connections."""

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant


class CcuBaseConnection:
    """Define the base interface for CCU telemetry connections."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry):
        """Initialize the telemetry connection.

        Args:
            hass: The Home Assistant instance.
            entry: The configuration entry associated with the connection.
        """
        self.hass = hass
        self.entry = entry

    async def async_setup(self) -> None:
        """Initialize the telemetry connection.

        Subclasses must implement the initialization logic required
        to prepare the connection and its resources.

        Raises:
            NotImplementedError: If the method is not implemented by a subclass.
        """
        raise NotImplementedError

    async def async_setup_entry(self) -> bool:
        """Set up the telemetry connection for the configuration entry.

        Subclasses must implement the logic required to establish
        the connection and activate telemetry processing.

        Returns:
            bool: True if the setup was successful, otherwise False.

        Raises:
            NotImplementedError: If the method is not implemented by a subclass.
        """
        raise NotImplementedError

    async def async_unload(self) -> None:
        """Unload the telemetry connection and release its resources.

        Subclasses must implement the cleanup logic required to stop
        telemetry processing, close active connections, and release
        allocated resources.

        Raises:
            NotImplementedError: If the method is not implemented by a subclass.
        """
        raise NotImplementedError
