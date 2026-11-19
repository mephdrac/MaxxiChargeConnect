"""
Text-Entity-Modul für die MaxxiChargeConnect-Integration in Home Assistant.

Dieses Modul definiert die Klasse `HttpScanText`, die diagnostische Text-Entitäten
bereitstellt, um aus HTML extrahierte Werte anzuzeigen. Die Werte stammen von einem
Koordinator, der die Daten regelmäßig aktualisiert.
"""

from homeassistant.components.sensor import SensorEntity
from homeassistant.const import EntityCategory
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from ..const import CCU_V1, CONF_CCU_VERSION, DEVICE_INFO, DOMAIN  # noqa: TID252


class HttpScanText(CoordinatorEntity, SensorEntity):
    """Read-only diagnostic sensor for a value extracted from the CCU page."""

    _attr_has_entity_name = True

    def __init__(self, coordinator, translate_key, keyname, name, icon) -> None:  # pylint: disable=unused-argument
        """Initialisiert eine neue HttpScanText-Entität.

        Args:
            coordinator: Der DataUpdateCoordinator, der die HTML-Daten liefert.
            keyname (str): Der Schlüssel für die extrahierten Daten, z.B. "PowerMeterIp".
            name (str): Anzeigename der Entität\
                (nicht verwendet, falls `_attr_has_entity_name = True`).
            icon (str): Icon der Entität (Material Design Icon-Name, z.B. "mdi:network").

        """

        super().__init__(coordinator)
        self._attr_translation_key = translate_key
        self._keyname = keyname
        self._entry = coordinator.entry
        self._attr_unique_id = f"{coordinator.entry.entry_id}_{keyname}"

        self._attr_icon = icon
        self._attr_entity_category = EntityCategory.DIAGNOSTIC

    @property
    def native_value(self):
        """Gibt den aktuellen Wert der Text-Entität zurück.

        Returns:
            str | None: Der extrahierte Wert aus dem Koordinator oder None,
                        falls keine Daten vorhanden sind.

        """
        return self.coordinator.data.get(self._keyname) if self.coordinator.data else None

    @property
    def available(self) -> bool:
        """Return whether there is a current reading for this field."""
        return super().available and self.native_value is not None

    @property
    def device_info(self) -> DeviceInfo:
        """Gibt die Geräteinformationen für diese Entität zurück.

        Returns:
            DeviceInfo: Informationen zur Verknüpfung mit dem physischen Gerät,
                        z.B. Name, Hersteller, Modell.

        """
        ccu_version = self._entry.data.get(CONF_CCU_VERSION, CCU_V1)
        return {
            "identifiers": {(DOMAIN, self._entry.entry_id)},
            "name": self._entry.title,
            **DEVICE_INFO,
            "model": f"CCU {ccu_version.upper()}",
        }
