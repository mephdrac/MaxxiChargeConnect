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
    """Parse battery telemetry."""
    batteries = data.get("batteries", [])

    soc_values = [
        battery["soc"]
        for battery in batteries
        if battery.get("soc") is not None
    ]

    if not soc_values:
        return {}

    return {
        "SOC": sum(soc_values) / len(soc_values),
    }

def parse_inverter(data: dict) -> dict:
    power = float(data["power"])

    return {
        "Pccu": max(power, 0),
        "GridChargePower": abs(min(power, 0)),
    }

SUBSCRIPTIONS = {
    "powermeter/telemetry": parse_powermeter,
    "battery/telemetry": parse_battery,
    "inverter/telemetry": parse_inverter,
}