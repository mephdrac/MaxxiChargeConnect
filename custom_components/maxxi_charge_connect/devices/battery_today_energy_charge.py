"""Modul für die BatteryTodayEnergyCharge-Entität der maxxi_charge_connect Integration.

Dieses Modul definiert eine IntegrationSensor-Entität, die den heutigen Lade-Energieverbrauch
der Batterie misst. Die Werte werden per Trapezregel integriert und täglich um Mitternacht
zurückgesetzt.
"""

from .today_integral_sensor import TodayIntegralSensor


class BatteryTodayEnergyCharge(TodayIntegralSensor):
    """Sensor zur Messung der aufgeladenen Energie der Batterie für den aktuellen Tag.

    Verwendet eine Integration (Trapezregel) zur Berechnung der heutigen Gesamtenergie
    und setzt sich täglich um Mitternacht zurück.

    Attribute:
        _entry (ConfigEntry): Der Konfigurationseintrag der Integration.
        _unsub_time_reset (Callable | None): Funktion zum Abmelden des Mitternachtsresets.
        _last_reset (datetime): Der letzte Zeitpunkt des Tagesresets (UTC).

    """
