"""Grid Export Energy Sensor für Home Assistant.

Dieses Modul enthält die Klasse `GridExportEnergyToday`, einen spezialisierten
IntegrationSensor, der die heute exportierte Energie ins Stromnetz misst.

Die Energie wird täglich um Mitternacht (lokale Zeit) zurückgesetzt.
"""

from .today_integral_sensor import TodayIntegralSensor


class GridExportEnergyToday(TodayIntegralSensor):
    """Sensor für die täglich exportierte Energie ins Stromnetz.

    Nutzt die IntegrationSensor-Basisfunktionalität von Home Assistant,
    um kontinuierlich Energie über Zeit zu integrieren (Wh), die von einem
    Quellsensor stammt (z. B. Leistungssensor).

    Die Energie wird täglich um Mitternacht zurückgesetzt.
    """
