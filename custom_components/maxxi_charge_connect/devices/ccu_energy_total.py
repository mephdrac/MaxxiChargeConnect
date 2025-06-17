"""Sensor zur Gesamtenergieintegration der CCU.

Dieses Modul definiert eine benutzerdefinierte IntegrationSensor-Entität für Home Assistant,
die die gesamte Energie berechnet, die über einen Zeitraum verbraucht oder erzeugt wurde.
Die Integration erfolgt über eine trapezförmige Methode mit automatischer Einheitenskalierung.

Classes:
    CcuEnergyTotal: Sensorentität für die kumulierte Energieintegration der CCU.

"""

from .total_integral_sensor import TotalIntegralSensor


class CcuEnergyTotal(TotalIntegralSensor):
    """Sensor für die kumulierte Energieintegration (z. B. einer CCU).

    Diese Entität summiert die Energie über die Zeit durch Integration
    der Leistungsmessung. Sie eignet sich zur Anzeige des Gesamtverbrauchs
    oder der Gesamteinspeisung.

    Attributes:
        _entry (ConfigEntry): Der Konfigurationseintrag dieser Entität.

    """

    _attr_entity_registry_enabled_default = True
