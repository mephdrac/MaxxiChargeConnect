"""Parser for CCU V2 MQTT messages."""

import math

from ..const import MQTT_SENSOR_VALUES


def parse_powermeter(data: dict) -> dict:
    """Parse powermeter telemetry."""
    power = data.get("power")

    if power is None:
        return {}

    return {
        "Pr": power,
    }


def parse_battery(data: dict) -> dict:
    """Parse CCU V2 battery telemetry."""

    batteries = data.get("batteries", [])

    batteries_info = []
    soc_values = []

    identifiers = [battery.get("id") for battery in batteries]
    indexed = any(identifier is not None for identifier in identifiers)
    if indexed:
        if any(type(identifier) is not int or not 1 <= identifier <= 16 for identifier in identifiers) or len(
            set(identifiers)
        ) != len(identifiers):
            raise ValueError("CCU battery IDs must be unique integers between 1 and 16")
        batteries_info = [{} for _ in range(max(identifiers, default=0))]

    for position, battery in enumerate(batteries):
        battery_info = {}

        soc = battery.get("soc")
        if soc is not None:
            soc = float(soc)
            soc_values.append(soc)
            battery_info["batterySOC"] = soc

        voltage = battery.get("voltage")
        if voltage is not None:
            # CCU2 liefert V, BatteryVoltageSensor erwartet mV.
            battery_info["batteryVoltage"] = float(voltage) * 1000

        input_power = battery.get("pvPower", battery.get("inputPower"))
        if input_power is not None:
            battery_info["pvPower"] = float(input_power)

        if battery.get("remainWh") is not None:
            battery_info["batteryCapacity"] = float(battery["remainWh"])
        if indexed:
            batteries_info[battery["id"] - 1] = battery_info
        else:
            batteries_info.append(battery_info)

    result = {
        "batteriesInfo": batteries_info,
    }

    if data.get("socTotal") is not None:
        result["SOC"] = float(data["socTotal"])
    elif soc_values:
        result["SOC"] = sum(soc_values) / len(soc_values)

    input_power_total = data.get("pvPowerTotal", data.get("inputPowerTotal"))

    if input_power_total is not None:
        result["PV_power_total"] = float(input_power_total)

    native = {}
    for field, key in (
        ("chargePowerTotal", "battery_power_charge"),
        ("dischargePowerTotal", "battery_power_discharge"),
        ("remainWhTotal", "battery_soe"),
    ):
        if data.get(field) is not None:
            value = float(data[field])
            if math.isfinite(value) and value >= 0:
                native[key] = value
    if "battery_power_charge" in native and "battery_power_discharge" in native:
        native["battery_power"] = native["battery_power_charge"] - native["battery_power_discharge"]
    if native:
        result[MQTT_SENSOR_VALUES] = native

    return result


def parse_inverter(data: dict) -> dict:
    power = float(data["power"])
    temperature = data.get("temperature")

    result = {
        "Pccu": max(power, 0),
        "GridChargePower": abs(min(power, 0)),
        "InverterPowerSigned": power,
    }

    if temperature is not None:
        result["convertersInfo"] = [
            {
                "ccuTemperature": temperature,
            }
        ]

    return result


SUBSCRIPTIONS = {
    "powermeter/telemetry": parse_powermeter,
    "battery/telemetry": parse_battery,
    "inverter/telemetry": parse_inverter,
}
