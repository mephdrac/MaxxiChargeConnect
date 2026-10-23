"""Parser for CCU V2 MQTT messages."""

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

    for battery in batteries:
        battery_info = {}

        soc = battery.get("soc")
        if soc is not None:
            soc = float(soc)
            soc_values.append(soc)
            battery_info["soc"] = soc

        voltage = battery.get("voltage")
        if voltage is not None:
            # CCU2 liefert V, BatteryVoltageSensor erwartet mV.
            battery_info["batteryVoltage"] = float(voltage) * 1000

        batteries_info.append(battery_info)

    result = {
        "batteriesInfo": batteries_info,
    }

    if soc_values:
        result["SOC"] = sum(soc_values) / len(soc_values)

    return result

def parse_inverter(data: dict) -> dict:
    power = float(data["power"])
    temperature = data.get("temperature")

    result = {
        "Pccu": max(power, 0),
        "GridChargePower": abs(min(power, 0)),
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