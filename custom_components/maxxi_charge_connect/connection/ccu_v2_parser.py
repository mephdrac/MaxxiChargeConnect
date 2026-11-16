"""Parse CCU V2 MQTT telemetry into the integration's internal data format.

The parsers translate powermeter, battery, and inverter telemetry into field
names consumed by the integration. Battery telemetry additionally provides
native MQTT sensor values through the MQTT_SENSOR_VALUES result entry.
"""

import math

from ..const import MQTT_SENSOR_VALUES


def parse_powermeter(data: dict) -> dict:
    """Map the powermeter's power reading to the internal Pr field.

    Args:
        data: Decoded powermeter telemetry containing an optional power value.

    Returns:
        A dictionary containing Pr when power is available, or an empty
        dictionary when the field is missing or explicitly set to None.
        The original value and its sign are preserved.
    """
    power = data.get("power")

    # Missing readings must not overwrite an existing reading with zero.
    if power is None:
        return {}

    return {
        "Pr": power,
    }


def parse_battery(data: dict) -> dict:
    """Translate battery telemetry and calculate aggregate sensor values.

    Batteries with explicit IDs are placed at their corresponding zero-based
    positions in batteriesInfo. Missing positions remain empty dictionaries.
    When no IDs are provided, batteries retain their payload order.

    The aggregate state of charge uses socTotal when available. Otherwise,
    it is calculated as the arithmetic mean of the reported battery SOC values.

    Args:
        data: Decoded battery telemetry containing optional per-battery
            readings and aggregate readings.

    Returns:
        A dictionary containing batteriesInfo and any available aggregate
        readings. Valid aggregate charge power, discharge power, and remaining
        energy are included under MQTT_SENSOR_VALUES.

    Raises:
        ValueError: If explicit battery IDs are missing, duplicated, outside
            the range 1 through 16, or are not integers (booleans are excluded). Also raised
            when a supplied numeric string cannot be converted to a float.
        TypeError: If a supplied numeric value cannot be converted to a float.
    """
    batteries = data.get("batteries", [])

    batteries_info = []
    soc_values = []

    # Any explicit ID enables indexed mode for the entire battery list.
    identifiers = [battery.get("id") for battery in batteries]
    indexed = any(identifier is not None for identifier in identifiers)

    if indexed:
        # Require a valid, unique ID for every battery in indexed mode.
        # Exclude booleans, which subclass int.
        if any(
            not isinstance(identifier, int) or isinstance(identifier, bool) or not 1 <= identifier <= 16
            for identifier in identifiers
        ) or len(set(identifiers)) != len(identifiers):
            raise ValueError("CCU battery IDs must be unique integers between 1 and 16")

        # Preserve ID-based positions, including gaps between reported IDs.
        batteries_info = [{} for _ in range(max(identifiers, default=0))]

    for battery in batteries:
        battery_info = {}

        # Collect individual SOC readings for the aggregate fallback.
        soc = battery.get("soc")
        if soc is not None:
            soc = float(soc)
            soc_values.append(soc)
            battery_info["batterySOC"] = soc

        voltage = battery.get("voltage")
        if voltage is not None:
            # CCU V2 reports volts; BatteryVoltageSensor expects millivolts.
            battery_info["batteryVoltage"] = float(voltage) * 1000

        # Prefer pvPower and use inputPower only when pvPower is absent.
        input_power = battery.get("pvPower", battery.get("inputPower"))
        if input_power is not None:
            battery_info["pvPower"] = float(input_power)

        # Map the remaining battery energy in Wh to the internal field.
        if battery.get("remainWh") is not None:
            battery_info["batteryCapacity"] = float(battery["remainWh"])

        if indexed:
            # Convert the one-based battery ID to a zero-based list index.
            batteries_info[battery["id"] - 1] = battery_info
        else:
            # Without explicit IDs, preserve the order from the payload.
            batteries_info.append(battery_info)

    result = {
        "batteriesInfo": batteries_info,
    }

    # Prefer the CCU's aggregate SOC over the calculated arithmetic mean.
    if data.get("socTotal") is not None:
        result["SOC"] = float(data["socTotal"])
    elif soc_values:
        result["SOC"] = sum(soc_values) / len(soc_values)

    # Prefer pvPowerTotal and fall back only when that field is absent.
    input_power_total = data.get("pvPowerTotal", data.get("inputPowerTotal"))

    if input_power_total is not None:
        result["PV_power_total"] = float(input_power_total)

    # Translate aggregate telemetry into native MQTT sensor keys.
    native = {}
    for field, key in (
        ("chargePowerTotal", "battery_power_charge"),
        ("dischargePowerTotal", "battery_power_discharge"),
        ("remainWhTotal", "battery_soe"),
    ):
        if data.get(field) is not None:
            value = float(data[field])

            # Exclude negative values, NaN, and infinity from these sensors.
            if math.isfinite(value) and value >= 0:
                native[key] = value

    # Positive net power represents charging; negative power represents
    # discharging. Calculate it only when both component readings are valid.
    if "battery_power_charge" in native and "battery_power_discharge" in native:
        native["battery_power"] = native["battery_power_charge"] - native["battery_power_discharge"]

    # Add native sensor values only when at least one valid reading exists.
    if native:
        result[MQTT_SENSOR_VALUES] = native

    return result


def parse_inverter(data: dict) -> dict:
    """Split signed inverter power into output and grid charging readings.

    Positive power becomes Pccu. Negative power becomes a positive
    GridChargePower reading. InverterPowerSigned preserves the original sign.

    Args:
        data: Decoded inverter telemetry containing the required power field
            and an optional temperature reading.

    Returns:
        A dictionary containing output power, grid charging power, and signed
        inverter power. If temperature is available, convertersInfo contains
        one converter entry with the original temperature value.

    Raises:
        KeyError: If the required power field is missing.
        ValueError: If power is a string that cannot be converted to a float.
        TypeError: If power cannot be converted to a float.
    """
    power = float(data["power"])
    temperature = data.get("temperature")

    # Separate the two power directions while retaining the signed reading.
    result = {
        "Pccu": max(power, 0),
        "GridChargePower": abs(min(power, 0)),
        "InverterPowerSigned": power,
    }

    # Wrap the temperature in the converter structure expected internally.
    if temperature is not None:
        result["convertersInfo"] = [
            {
                "ccuTemperature": temperature,
            }
        ]

    return result


# Associate each supported MQTT topic suffix with its telemetry parser.
SUBSCRIPTIONS = {
    "powermeter/telemetry": parse_powermeter,
    "battery/telemetry": parse_battery,
    "inverter/telemetry": parse_inverter,
}
