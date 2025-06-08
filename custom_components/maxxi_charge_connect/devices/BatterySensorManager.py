from homeassistant.const import CONF_WEBHOOK_ID
from homeassistant.helpers.dispatcher import async_dispatcher_connect

from ..const import DOMAIN  # noqa: TID252
from .BatterySoESensor import BatterySoESensor  # oder je nach Ordnerstruktur anpassen


class BatterySensorManager:
    def __init__(self, hass, entry, async_add_entities):
        self.hass = hass
        self.entry = entry
        self.async_add_entities = async_add_entities
        self.sensors = []
        self._registered = False

    async def setup(self):
        signal = f"{DOMAIN}_{self.entry.data[CONF_WEBHOOK_ID]}_update_sensor"
        self.hass.data.setdefault(DOMAIN, {}).setdefault(self.entry.entry_id, {})
        self.hass.data[DOMAIN][self.entry.entry_id]["listeners"] = []
        if not self._registered:
            async_dispatcher_connect(self.hass, signal, self._handle_update)
            self._registered = True

    async def _handle_update(self, data):
        batteries = data.get("batteriesInfo", [])
        if not self.sensors and batteries:
            for i in range(len(batteries)):
                sensor = BatterySoESensor(self.entry, i)
                self.sensors.append(sensor)
            self.async_add_entities(self.sensors)

        # Update alle Sensoren
        for listener in self.hass.data[DOMAIN][self.entry.entry_id]["listeners"]:
            await listener(data)
