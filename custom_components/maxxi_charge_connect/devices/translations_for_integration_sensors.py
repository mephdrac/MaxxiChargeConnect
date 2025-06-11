"""Lokalisierte Namen für Energie-Sensoren in einer Home Assistant-Integration.

Dieses Modul stellt ein Mapping bereit, um technische Klassennamen in lokalisierte
Anzeigenamen zu übersetzen – basierend auf der in Home Assistant eingestellten Sprache.

Funktionen:
    get_localized_name(hass, key): Gibt den lokalisierten Anzeigenamen für einen Sensor zurück.
"""

from homeassistant.core import HomeAssistant

LOCALIZED_NAMES = {
    "de": {
        "BatteryTotalEnergyCharge": "Batterie Laden gesamt",
        "BatteryTotalEnergyDischarge": "Batterie Entladen gesamt",
        "BatteryTodayEnergyCharge": "Batterie Laden heute",
        "BatteryTodayEnergyDischarge": "Batterie Entladen heute",
        "CcuEnergyToday": "CCU Energie heute",
        "CcuEnergyTotal": "CCU Energie gesamt",
        "GridImportEnergyToday": "Netzbezug heute",
        "GridImportEnergyTotal": "Netzbezug gesamt",
        "GridExportEnergyToday": "Netzeinspeisung heute",
        "GridExportEnergyTotal": "Netzeinspeisung gesamt",
        "PvSelfConsumptionEnergyToday": "Eigenverbrauch heute",
        "PvSelfConsumptionEnergyTotal": "Eigenverbrauch gesamt",
        "PvTodayEnergy": "PV Produktion heute",
        "PvTotalEnergy": "PV Produktion gesamt",
    },
    "en": {
        "BatteryTotalEnergyCharge": "Battery Charge Total",
        "BatteryTotalEnergyDischarge": "Battery Discharge Total",
        "BatteryTodayEnergyCharge": "Battery Charge Today",
        "BatteryTodayEnergyDischarge": "Battery Discharge Today",
        "CcuEnergyToday": "CCU Energy Today",
        "CcuEnergyTotal": "CCU Energy Total",
        "GridImportEnergyToday": "Grid Import Today",
        "GridImportEnergyTotal": "Grid Import Energy Total",
        "GridExportEnergyToday": "Grid Export Energy Today",
        "GridExportEnergyTotal": "Grid Export Energy Total",
        "PvSelfConsumptionEnergyToday": "PV Self Cons. Today",
        "PvSelfConsumptionEnergyTotal": "PV Self Cons. Total",
        "PvTodayEnergy": "PV Energy Today",
        "PvTotalEnergy": "PV Energy Total",
    },
}


def get_localized_name(hass: HomeAssistant, key: str) -> str:
    """Gibt den lokalisierten Namen für einen Sensor anhand der HA-Sprache zurück.

    Wenn keine Übersetzung verfügbar ist, wird der Schlüssel selbst zurückgegeben.

    Args:
        hass (HomeAssistant): Die Home Assistant-Instanz zur Bestimmung der Sprache.
        key (str): Der interne Name bzw. Klassename des Sensors.

    Returns:
        str: Der lokalisierte Anzeigename (z. B. „PV Produktion heute“),
             oder der Originalschlüssel, falls keine Übersetzung vorhanden ist.

    """

    lang = getattr(hass.config, "language", "en") or "en"
    return LOCALIZED_NAMES.get(lang, {}).get(key, key)
