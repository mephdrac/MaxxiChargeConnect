# Lokalisierte Namen
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


def get_localized_name(hass, key: str) -> str:
    lang = getattr(hass.config, "language", "en") or "en"
    return LOCALIZED_NAMES.get(lang, {}).get(key, key)
