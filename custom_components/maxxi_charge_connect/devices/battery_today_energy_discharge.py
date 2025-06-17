"""Sensor für die heutige Batterieentladung (BatteryTodayEnergyDischarge).

Dieser Sensor integriert die aus der Batterie entladene Energie über den Tag hinweg.
Er setzt sich täglich um Mitternacht zurück, um nur die tagesaktuelle Entladung zu zeigen.

Verwendet die IntegrationSensor-Basis aus Home Assistant.
"""

import logging
from homeassistant.core import HomeAssistant
from .today_integral_sensor import TodayIntegralSensor

_LOGGER = logging.getLogger(__name__)


class BatteryTodayEnergyDischarge(TodayIntegralSensor):
    """Sensorentität zur Anzeige der täglichen Batterieentladung in kWh.

    Diese Entität berechnet die entladene Energie über den Tag (Integration) und setzt
    sich täglich um Mitternacht zurück. Sie nutzt die Datenquelle `source_entity_id`.

    Attributes:
        _unsub_time_reset (Callable | None): Callback zum Abmelden des Zeit-Triggers.
        _entry (ConfigEntry): Konfigurations-Eintrag der Integration.
        _last_reset (datetime): Zeitpunkt des letzten Resets (Mitternacht lokal).

    """

    def __init__(self, hass: HomeAssistant, entry, source_entity_id: str) -> None:
        """Initialisiert die Sensorentität.

        Args:
            hass (HomeAssistant): Die Home Assistant-Instanz.
            entry (ConfigEntry): Konfigurationseintrag der Integration.
            source_entity_id (str): Entity-ID der Quelle, aus der Energie integriert wird.

        """
        super().__init__(hass, entry, source_entity_id)
