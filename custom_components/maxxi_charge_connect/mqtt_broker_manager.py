"""Shared, opt-in MQTT broker lifecycle, independent of CCU configuration flows."""

import asyncio
import hmac
import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field

from amqtt.broker import Broker
from amqtt.plugins.base import BaseAuthPlugin
from amqtt.session import Session

_LOGGER = logging.getLogger(__name__)
MessageCallback = Callable[[str, bytes], Awaitable[None]]


class CredentialsAuthPlugin(BaseAuthPlugin):
    """Require the configured username AND password; anonymous access is disabled."""

    @dataclass
    class Config:
        """Credentials supplied by the manager, never written to disk."""

        username: str = ""
        password: str = field(default="", repr=False)
        # dacite (used by aMQTT) cannot validate parameterized Callable types.
        message_callback: Callable | None = field(default=None, repr=False)

    async def on_broker_message_received(self, *, client_id: str, message) -> None:
        """Deliver telemetry published by authenticated clients to the integration."""
        if message is None or not message.topic:
            return
        _LOGGER.debug("Internal MQTT received topic %s (%s bytes)", message.topic, len(message.data))
        if self.config.message_callback is not None:
            await self.config.message_callback(message.topic, bytes(message.data))

    async def on_broker_client_connected(self, *, client_id: str, client_session: Session) -> None:
        """Make successful connections visible without exposing credentials."""
        _LOGGER.info("Internal MQTT client connected: %s", client_id)

    async def on_broker_client_disconnected(self, *, client_id: str, client_session: Session) -> None:
        """Record disconnects separately from telemetry parsing."""
        _LOGGER.info("Internal MQTT client disconnected: %s", client_id)

    async def authenticate(self, *, session: Session) -> bool:
        """Reject missing credentials as well as mismatched credentials."""
        if not session or not session.username or not session.password:
            _LOGGER.warning("Internal MQTT login rejected: username or password missing")
            return False
        authenticated = hmac.compare_digest(session.username.encode(), self.config.username.encode()) and hmac.compare_digest(
            session.password.encode(), self.config.password.encode()
        )
        if not authenticated:
            _LOGGER.warning("Internal MQTT login rejected: credentials do not match")
        return authenticated


@dataclass(frozen=True)
class MqttBrokerConfig:
    """One shared listener and account for all registered CCUs."""

    username: str
    password: str = field(repr=False)
    port: int = 1883
    host: str = "0.0.0.0"

    def __post_init__(self) -> None:
        if not self.username or not self.password:
            raise ValueError("MQTT username and password are required")
        if isinstance(self.port, bool) or not isinstance(self.port, int) or not 1 <= self.port <= 65535:
            raise ValueError("MQTT port must be between 1 and 65535")
        if not self.host:
            raise ValueError("MQTT listen host is required")


class MqttBrokerManager:
    """Serialize lifecycle changes; stop only when the last CCU releases the broker.

    The caller keeps one manager per Home Assistant instance. External MQTT
    entries do not acquire this manager. Configuration changes require releasing
    all entries first. No listener is opened by constructing the manager.
    """

    def __init__(self) -> None:
        self._lock = asyncio.Lock()
        self._broker: Broker | None = None
        self._config: MqttBrokerConfig | None = None
        self._entries: set[str] = set()
        self._listeners: dict[str, MessageCallback] = {}

    @property
    def running(self) -> bool:
        """Whether startup completed successfully."""
        return self._broker is not None

    async def async_acquire(
        self, entry_id: str, config: MqttBrokerConfig, message_callback: MessageCallback | None = None
    ) -> None:
        """Start on first use, or register another CCU with matching settings."""
        async with self._lock:
            if self._broker is not None:
                if config != self._config:
                    raise ValueError("All internal MQTT entries must use the same broker settings")
                self._entries.add(entry_id)
                if message_callback is not None:
                    self._listeners[entry_id] = message_callback
                return

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
                # With one listener, a failed bind leaves no open server.
                # aMQTT cannot shutdown() from its not_started state.
                try:
                    if broker.transitions.state == "started":
                        await broker.shutdown()
                    await broker.plugins_manager.close()
                except Exception:  # Preserve the original startup error.
                    _LOGGER.exception("Failed to clean up MQTT broker after unsuccessful startup")
                raise
            self._broker = broker
            self._config = config
            self._entries.add(entry_id)
            if message_callback is not None:
                self._listeners[entry_id] = message_callback
            _LOGGER.info("Internal MQTT broker started on port %s", config.port)

    async def async_release(self, entry_id: str) -> None:
        """Release an entry; duplicate releases are harmless."""
        async with self._lock:
            self._entries.discard(entry_id)
            self._listeners.pop(entry_id, None)
            if not self._entries:
                await self._async_stop()

    async def async_shutdown(self) -> None:
        """Stop all CCUs, for example when Home Assistant shuts down."""
        async with self._lock:
            await self._async_stop()
            self._entries.clear()
            self._listeners.clear()

    async def _async_message_received(self, topic: str, payload: bytes) -> None:
        for listener in tuple(self._listeners.values()):
            try:
                await listener(topic, payload)
            except Exception:
                _LOGGER.exception("Error processing internal MQTT telemetry on %s", topic)

    async def async_publish(self, entry_id: str, topic: str, payload: bytes) -> None:
        """Publish a non-retained command through aMQTT's public API."""
        async with self._lock:
            if self._broker is None or entry_id not in self._entries:
                raise RuntimeError("Internal MQTT broker is not available for this entry")
            await self._broker.internal_message_broadcast(topic, payload, qos=0)

    def retained_messages(self, entry_id: str) -> dict[str, bytes]:
        """Snapshot retained data for a newly attached CCU without private broker APIs."""
        if self._broker is None or entry_id not in self._entries:
            return {}
        return {topic: bytes(message.data) for topic, message in self._broker.retained_messages.items()}

    async def _async_stop(self) -> None:
        if self._broker is not None:
            await self._broker.shutdown()
            await self._broker.plugins_manager.close()
            self._broker = None
            self._config = None
            _LOGGER.info("Internal MQTT broker stopped")
