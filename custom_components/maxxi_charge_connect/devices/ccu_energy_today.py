"""Sensor zur Anzeige der täglichen Energieerfassung der CCU.

Dieses Modul definiert eine benutzerdefinierte IntegrationSensor-Entität für Home Assistant,
die die täglich verbrauchte Energie einer Quelle über den Tag aufsummiert. Der Zähler wird
jeden Tag um Mitternacht zurückgesetzt.

Classes:
    CcuEnergyToday: Sensorentität für die tägliche Energieintegration mit täglichem Reset.
"""

from .today_integral_sensor import TodayIntegralSensor


class CcuEnergyToday(TodayIntegralSensor):
    """Sensor für die tägliche Energieintegration (z.B. durch eine CCU).

    Diese Entität berechnet den täglichen Energieverbrauch, indem sie die Leistung
    über die Zeit integriert. Um Mitternacht wird der Zähler automatisch zurückgesetzt.

    Attributes:
        _entry (ConfigEntry): Der Konfigurationseintrag für diese Entität.
        _last_reset (datetime): Zeitpunkt des letzten täglichen Resets in UTC.
        _unsub_time_reset (Callable | None): Callback zum Abmelden des täglichen Resets.

    """
