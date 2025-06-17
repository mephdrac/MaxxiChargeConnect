"""IntegrationSensor zur Erfassung der insgesamt exportierten Energie ins Netz.

Diese Entität berechnet auf Basis eines Quell-Sensors (z. B. Momentanleistung)
die exportierte Energie ins Stromnetz über die Zeit. Sie verwendet dafür die
trapezförmige Integrationsmethode und speichert das Ergebnis als kumulativen Zähler.

Die Einheit der Messung ist Kilowattstunden (kWh).
"""

from .total_integral_sensor import TotalIntegralSensor


class GridExportEnergyTotal(TotalIntegralSensor):
    """Sensor zur Berechnung der gesamten Netzeinspeisung (kWh)."""

    _attr_entity_registry_enabled_default = True
