"""Manage a shared, opt-in MQTT broker independently of CCU configuration flows.

The manager starts one broker for all registered CCUs, distributes incoming
messages to their listeners, and stops the broker after its last user releases
it. Constructing the manager does not open a network listener.
"""

import asyncio
import hmac
import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field

from amqtt.broker import Broker
from amqtt.plugins.base import BaseAuthPlugin
from amqtt.session import Session

_LOGGER = logging.getLogger(__name__)

# Each listener receives an MQTT topic and its raw payload asynchronously.
MessageCallback = Callable[[str, bytes], Awaitable[None]]


class CredentialsAuthPlugin(BaseAuthPlugin):
    """Authenticate MQTT clients and forward received messages.

    Both the configured username and password are required. Authentication
    failures are logged without exposing either credential.
    """

    @dataclass
    class Config:
        """Hold credentials and the message callback in memory.

        The password and callback are excluded from the generated
        representation. This class does not write credentials to disk.
        """

        username: str = ""
        password: str = field(default="", repr=False)

        # dacite, used by aMQTT, cannot validate parameterized Callable types.
        message_callback: Callable | None = field(default=None, repr=False)

    async def on_broker_message_received(  # pylint: disable=unused-argument
        self, *, client_id: str, message
    ) -> None:
        """Forward a received MQTT message to the integration.

        Args:
            client_id: Publishing client identifier required by the aMQTT
                callback interface; unused by this handler.
            message: Received message containing its topic and payload.
                Missing messages and empty topics are ignored.
        """
        if message is None or not message.topic:
            return

        # Log message metadata without exposing the payload.
        _LOGGER.debug("Internal MQTT received topic %s (%s bytes)", message.topic, len(message.data))

        if self.config.message_callback is not None:
            await self.config.message_callback(message.topic, bytes(message.data))

    async def on_broker_client_connected(  # pylint: disable=unused-argument
        self, *, client_id: str, client_session: Session
    ) -> None:
        """Log a successful client connection without exposing credentials.

        Args:
            client_id: Identifier of the connected MQTT client.
            client_session: Session required by the aMQTT callback interface;
                unused by this handler.
        """
        _LOGGER.info("Internal MQTT client connected: %s", client_id)

    async def on_broker_client_disconnected(  # pylint: disable=unused-argument
        self, *, client_id: str, client_session: Session
    ) -> None:
        """Log a client disconnection separately from message processing.

        Args:
            client_id: Identifier of the disconnected MQTT client.
            client_session: Session required by the aMQTT callback interface;
                unused by this handler.
        """
        _LOGGER.info("Internal MQTT client disconnected: %s", client_id)

    async def authenticate(self, *, session: Session) -> bool:
        """Validate the session against the configured credentials.

        Compare credential bytes using timing-resistant comparisons.
        Missing credentials are rejected before comparison.

        Args:
            session: Client session containing the supplied credentials.

        Returns:
            True when both credentials match; otherwise False.
        """
        if not session or not session.username or not session.password:
            _LOGGER.warning("Internal MQTT login rejected: username or password missing")
            return False

        authenticated = hmac.compare_digest(
            session.username.encode(), self.config.username.encode()
        ) and hmac.compare_digest(session.password.encode(), self.config.password.encode())

        if not authenticated:
            _LOGGER.warning("Internal MQTT login rejected: credentials do not match")

        return authenticated


@dataclass(frozen=True)
class MqttBrokerConfig:
    """Define the shared listener and account used by registered CCUs.

    Instances are immutable and compared when additional entries acquire the
    broker. The password is excluded from the generated representation.
    """

    username: str
    password: str = field(repr=False)
    port: int = 1883
    host: str = "0.0.0.0"

    def __post_init__(self) -> None:
        """Validate required credentials and listener settings.

        Raises:
            ValueError: If credentials or the listen host are empty, or the
                port is not an integer between 1 and 65535. Boolean port
                values are explicitly rejected.
        """
        if not self.username or not self.password:
            raise ValueError("MQTT username and password are required")

        # Booleans subclass int but are not valid port settings.
        if isinstance(self.port, bool) or not isinstance(self.port, int) or not 1 <= self.port <= 65535:
            raise ValueError("MQTT port must be between 1 and 65535")

        if not self.host:
            raise ValueError("MQTT listen host is required")


class MqttBrokerManager:
    """Serialize lifecycle changes for a broker shared by multiple CCUs.

    The caller maintains one manager per Home Assistant instance. Entries
    using an external broker do not acquire this manager.

    All registered entries must use identical broker settings. Changing those
    settings requires releasing all entries first. The broker stops when the
    last registered entry releases it.
    """

    def __init__(self) -> None:
        """Initialize lifecycle synchronization and entry registrations.

        No broker is created or started until the first acquisition.
        """
        self._lock = asyncio.Lock()
        self._broker: Broker | None = None
        self._config: MqttBrokerConfig | None = None
        self._entries: set[str] = set()
        self._listeners: dict[str, MessageCallback] = {}

    @property
    def running(self) -> bool:
        """Return whether a broker is registered after successful startup."""
        return self._broker is not None

    async def async_acquire(
        self, entry_id: str, config: MqttBrokerConfig, message_callback: MessageCallback | None = None
    ) -> None:
        """Start the broker or register an entry with the running broker.

        Repeated acquisition by the same entry does not create an additional
        registration. A supplied callback replaces that entry's existing
        listener; omitting it leaves an existing listener unchanged.

        Args:
            entry_id: Config entry identifier acquiring the shared broker.
            config: Listener and account settings required by this entry.
            message_callback: Optional asynchronous listener for received
                MQTT messages.

        Raises:
            ValueError: If a running broker uses different settings.

        Broker startup failures propagate after cleanup is attempted.
        """
        async with self._lock:
            if self._broker is not None:
                # All entries share one listener and authentication account.
                if config != self._config:
                    raise ValueError("All internal MQTT entries must use the same broker settings")

                self._entries.add(entry_id)
                if message_callback is not None:
                    self._listeners[entry_id] = message_callback
                return

            # Supply credentials and message forwarding directly to the plugin.
            broker = Broker(
                {
                    "listeners": {"default": {"type": "tcp", "bind": f"{config.host}:{config.port}"}},
                    "plugins": {
                        f"{__name__}.CredentialsAuthPlugin": {
                            "username": config.username,
                            "password": config.password,
                            "message_callback": self._async_message_received,
                        },
                    },
                }
            )

            try:
                await broker.start()
            except BaseException:
                # Attempt cleanup for startup failures and cancellation.
                # With one listener, a failed bind leaves no open server.
                # aMQTT cannot shutdown() from its not_started state.
                try:
                    if broker.transitions.state == "started":
                        await broker.shutdown()
                    await broker.plugins_manager.close()

                # Cleanup failures must not replace the original startup error.
                except Exception:  # pylint: disable=broad-exception-caught
                    _LOGGER.exception("Failed to clean up MQTT broker after unsuccessful startup")
                raise

            # Publish the running state only after startup succeeds.
            self._broker = broker
            self._config = config
            self._entries.add(entry_id)

            if message_callback is not None:
                self._listeners[entry_id] = message_callback

            _LOGGER.info("Internal MQTT broker started on port %s", config.port)

    async def async_release(self, entry_id: str) -> None:
        """Remove an entry and stop the broker if no registrations remain.

        Releasing an already released or unknown entry is harmless.

        Args:
            entry_id: Config entry identifier releasing the shared broker.
        """
        async with self._lock:
            self._entries.discard(entry_id)
            self._listeners.pop(entry_id, None)

            if not self._entries:
                await self._async_stop()

    async def async_shutdown(self) -> None:
        """Stop the shared broker and clear all entry registrations.

        This supports application-wide shutdown, such as when Home Assistant
        stops. Registrations and listeners are cleared after shutdown succeeds.
        """
        async with self._lock:
            await self._async_stop()
            self._entries.clear()
            self._listeners.clear()

    async def _async_message_received(self, topic: str, payload: bytes) -> None:
        """Forward a received message to every registered listener.

        Iterate over a snapshot so registration changes do not affect the
        current delivery. Handle listener failures individually so remaining
        listeners still receive the message.

        Args:
            topic: MQTT topic on which the message was received.
            payload: Raw message payload.
        """
        for listener in tuple(self._listeners.values()):
            try:
                await listener(topic, payload)

            # One listener failure must not interrupt delivery to the others.
            except Exception:  # pylint: disable=broad-exception-caught
                _LOGGER.exception("Error processing internal MQTT telemetry on %s", topic)

    async def async_publish(self, entry_id: str, topic: str, payload: bytes) -> None:
        """Broadcast a non-retained command through aMQTT's public API.

        Hold the lifecycle lock during publication to prevent concurrent
        shutdown of the broker.

        Args:
            entry_id: Registered config entry requesting publication.
            topic: MQTT topic to which the command is published.
            payload: Raw command payload.

        Raises:
            RuntimeError: If the broker is stopped or the entry is not
                registered.
        """
        async with self._lock:
            if self._broker is None or entry_id not in self._entries:
                raise RuntimeError("Internal MQTT broker is not available for this entry")

            await self._broker.internal_message_broadcast(topic, payload, qos=0)

    def retained_messages(self, entry_id: str) -> dict[str, bytes]:
        """Return a snapshot of retained messages for a registered entry.

        Use the broker's public retained-message collection and convert each
        payload to bytes. The returned dictionary is independent of the
        broker's collection.

        Args:
            entry_id: Config entry requesting the retained-message snapshot.

        Returns:
            A mapping of MQTT topics to retained payloads, or an empty
            dictionary if the broker is stopped or the entry is unregistered.
        """
        if self._broker is None or entry_id not in self._entries:
            return {}

        return {topic: bytes(message.data) for topic, message in self._broker.retained_messages.items()}

    async def _async_stop(self) -> None:
        """Shut down the broker and close its plugins if it is running.

        The caller must hold the lifecycle lock. Clear the broker reference
        and configuration only after both shutdown operations succeed.
        Calling this method without a broker has no effect.
        """
        if self._broker is not None:
            await self._broker.shutdown()
            await self._broker.plugins_manager.close()

            self._broker = None
            self._config = None

            _LOGGER.info("Internal MQTT broker stopped")
