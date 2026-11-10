"""Match discovered CCU measurements to the existing CCU V2 entity model."""

import math
import re
from dataclasses import dataclass
from functools import lru_cache

from jinja2 import Environment, TemplateSyntaxError, nodes

from ..const import MQTT_SENSOR_VALUES

_ENVIRONMENT = Environment()
_MAX_LEGACY_BATTERIES = 16


@lru_cache(maxsize=512)
def template_path(source: str | None) -> tuple | None:
    """Recognize simple JSON access, independent of spacing and dot/bracket syntax.

    Arithmetic and arbitrary filters are deliberately not treated as raw values.
    """
    if not source:
        return ("value",)
    try:
        tree = _ENVIRONMENT.parse(source)
    except TemplateSyntaxError:
        return None
    if len(tree.body) != 1 or not isinstance(tree.body[0], nodes.Output):
        return None
    expressions = [node for node in tree.body[0].nodes if not isinstance(node, nodes.TemplateData) or node.data.strip()]
    if len(expressions) != 1:
        return None
    node = expressions[0]
    while isinstance(node, nodes.Filter) and node.name in ("float", "int"):
        node = node.node
    # CCU firmware selects a battery by hardware ID, not list position.
    if isinstance(node, nodes.Call) and isinstance(node.node, nodes.Getattr) and node.node.attr == "get" and node.args:
        field = node.args[0]
        selected = node.node.node
        if isinstance(selected, nodes.Filter) and selected.name in ("d", "default"):
            selected = selected.node
        if isinstance(selected, nodes.Filter) and selected.name == "first":
            selected = selected.node
        if isinstance(selected, nodes.Filter) and selected.name == "selectattr" and len(selected.args) == 3:
            args = selected.args
            parent = selected.node
            valid_selector = (
                all(isinstance(arg, nodes.Const) for arg in args)
                and [args[0].value, args[1].value] == ["id", "eq"]
                and isinstance(args[2].value, int)
                and not isinstance(args[2].value, bool)
                and 1 <= args[2].value <= _MAX_LEGACY_BATTERIES
            )
            valid_parent = (
                isinstance(parent, nodes.Getattr)
                and parent.attr == "batteries"
                and isinstance(parent.node, nodes.Name)
                and parent.node.name == "value_json"
            )
            valid_field = isinstance(field, nodes.Const) and isinstance(field.value, str)
            if valid_selector and valid_parent and valid_field:
                return ("value_json", "batteries", args[2].value - 1, field.value)
    path = []
    while isinstance(node, (nodes.Getattr, nodes.Getitem)):
        if isinstance(node, nodes.Getattr):
            path.append(node.attr)
        elif isinstance(node.arg, nodes.Const) and isinstance(node.arg.value, (str, int)):
            path.append(node.arg.value)
        else:
            return None
        node = node.node
    if not isinstance(node, nodes.Name) or node.name not in ("value_json", "value"):
        return None
    return (node.name, *reversed(path))


@dataclass(frozen=True)
class SensorBinding:
    """Existing unique-ID suffix, expected physical dimension, and input projection."""

    sensor_key: str
    dimension: str
    field: str | None = None
    index: int | None = None


_NAMED = {
    "grid power": SensorBinding("power_meter", "power", "Pr"),
    "pv power": SensorBinding("pv_power", "power", "PV_power_total"),
    "local battery soc": SensorBinding("battery_soc", "soc", "SOC"),
    "ccu ac power": SensorBinding("ccu_power", "power", "inverter"),
    "ccu temperature": SensorBinding("ccu_temperatur_sensor", "temperature", "temperature"),
    "ccu id": SensorBinding("deviceid", "identity"),
    "ccu ver": SensorBinding("firmware_version", "identity", "firmwareVersion"),
    "firmware version": SensorBinding("firmware_version", "identity", "firmwareVersion"),
    "ccu uptime": SensorBinding("uptime_sensor", "duration", "uptime"),
    "usable energy remaining": SensorBinding("battery_soe", "stored_energy", "batteryCapacityTotal"),
    "battery charging power": SensorBinding("battery_power_charge", "power"),
    "battery discharging power": SensorBinding("battery_power_discharge", "power"),
    "battery power": SensorBinding("battery_power", "power"),
    "power consumption": SensorBinding("power_consumption", "power"),
    "house consumption": SensorBinding("power_consumption", "power"),
    "pv self consumption": SensorBinding("pv_consumption", "power"),
    "grid import power": SensorBinding("grid_import", "power"),
    "grid export power": SensorBinding("grid_export", "power"),
}

# Keep the established HA integration sensors and their accumulated history.
_ENERGY = {
    "ccu ac output energy today": "ccuenergytoday",
    "ccu ac output energy total": "ccuenergytotal",
    "grid export energy today": "gridexportenergytoday",
    "grid export energy total": "gridexportenergytotal",
    "grid import energy today": "gridimportenergytoday",
    "grid import energy total": "gridimportenergytotal",
    "pv energy today": "pvtodayenergy",
    "pv energy total": "pvtotalenergy",
    "battery charging energy": "batterytotalenergycharge",
    "battery discharging energy": "batterytotalenergydischarge",
    "battery charging energy today": "batterytodayenergycharge",
    "battery discharging energy today": "batterytodayenergydischarge",
    "consumption energy today": "consumptionenergytoday",
    "consumption energy total": "consumptionenergytotal",
    "pv self consumption energy today": "pvselfconsumptionenergytoday",
    "pv self consumption energy total": "pvselfconsumptionenergytotal",
}
_NAMED.update({name: SensorBinding(key, "energy") for name, key in _ENERGY.items()})
_UNITS = {
    "power": {None: 1, "W": 1, "kW": 1000},
    "soc": {None: 1, "%": 1},
    "voltage": {None: 1, "V": 1, "mV": 0.001},
    "temperature": {None: 1, "°C": 1},
    "energy": {None: 1, "kWh": 1, "Wh": 0.001},
    "identity": {None: 1},
    "duration": {None: 1000, "s": 1000, "ms": 1},
    "stored_energy": {None: 1, "Wh": 1, "kWh": 1000},
}
_DEVICE_CLASSES = {"soc": "battery", "identity": None, "stored_energy": "energy"}


def _compatible(spec, binding: SensorBinding) -> bool:
    cfg = spec.config
    expected = _DEVICE_CLASSES.get(binding.dimension, binding.dimension)
    return (
        cfg.get("unit_of_measurement") in _UNITS[binding.dimension]
        and (cfg.get("device_class") is None or cfg["device_class"] == expected)
        and (binding.dimension == "energy" or cfg.get("state_class") not in ("total", "total_increasing"))
    )


def legacy_binding(spec) -> SensorBinding | None:
    """Use telemetry structure first, then known firmware measurement roles."""
    if spec.component != "sensor":
        return None
    path = template_path(spec.config.get("value_template"))
    suffix = "/".join(spec.state_topic.split("/")[-2:])
    binding = None
    if suffix == "powermeter/telemetry" and path == ("value_json", "power"):
        binding = _NAMED["grid power"]
    elif suffix in ("inverter/telemetry", "system/telemetry"):
        if path == ("value_json", "power"):
            binding = _NAMED["ccu ac power"]
        elif path == ("value_json", "temperature"):
            binding = _NAMED["ccu temperature"]
    elif suffix == "battery/telemetry":
        if path == ("value_json", "pvPowerTotal"):
            binding = _NAMED["pv power"]
        elif path == ("value_json", "socTotal"):
            binding = _NAMED["local battery soc"]
        elif path and len(path) == 4 and path[:2] == ("value_json", "batteries") and isinstance(path[2], int):
            index, field = path[2:]
            if 0 <= index < _MAX_LEGACY_BATTERIES and field in ("soc", "voltage", "pvPower", "remainWh"):
                binding = _battery_binding(index, field)
    elif suffix == "device/state":
        if path == ("value_json", "CCU", "ccuVersion"):
            binding = _NAMED["ccu ver"]
        elif path == ("value_json", "CCU", "ccuId"):
            binding = _NAMED["ccu id"]
    if binding is None:
        name = re.sub(r"[\s_-]+", " ", spec.name.casefold()).strip()
        binding = _NAMED.get(name)
        battery = re.fullmatch(r"battery (\d+) (soc|voltage|pv power|stored energy)", name)
        if battery and 1 <= int(battery[1]) <= _MAX_LEGACY_BATTERIES:
            binding = _battery_binding(
                int(battery[1]) - 1, {"pv power": "pvPower", "stored energy": "remainWh"}.get(battery[2], battery[2])
            )
    return binding if binding and _compatible(spec, binding) else None


def _battery_binding(index: int, field: str) -> SensorBinding:
    suffix, dimension, key = {
        "soc": ("battery_soc_sensor", "soc", "batterySOC"),
        "voltage": ("battery_voltage_sensor", "voltage", "batteryVoltage"),
        "inputPower": ("battery_pv_power_sensor", "power", "pvPower"),
        "pvPower": ("battery_pv_power_sensor", "power", "pvPower"),
        "remainWh": ("battery_soe", "stored_energy", "batteryCapacity"),
    }[field]
    return SensorBinding(f"{suffix}_{index}", dimension, key, index)


def apply_legacy_value(state: dict, spec, value: str) -> bool:
    """Project live discovery values into the old sensor input representation."""
    binding = legacy_binding(spec)
    if binding is None or binding.dimension == "energy":
        return False
    if binding.dimension == "identity":
        if binding.field:
            state[binding.field] = str(value).strip()
            return True
        return False
    try:
        value = float(value) * _UNITS[binding.dimension][spec.config.get("unit_of_measurement")]
    except (TypeError, ValueError):
        return False
    if not math.isfinite(value):
        return False
    if binding.dimension in ("duration", "stored_energy") and value < 0:
        return False
    if binding.sensor_key in ("battery_power_charge", "battery_power_discharge") and value < 0:
        return False
    if binding.field is None:
        state.setdefault(MQTT_SENSOR_VALUES, {})[binding.sensor_key] = value
        return True
    if binding.field == "batteryCapacityTotal":
        state.setdefault(MQTT_SENSOR_VALUES, {})[binding.sensor_key] = value
        return True
    if binding.index is not None:
        batteries = state.setdefault("batteriesInfo", [])
        while len(batteries) <= binding.index:
            batteries.append({})
        # Legacy battery voltage sensors expect millivolts as their input.
        batteries[binding.index][binding.field] = value * 1000 if binding.dimension == "voltage" else value
    elif binding.field == "inverter":
        state.update({"Pccu": max(value, 0), "GridChargePower": max(-value, 0), "InverterPowerSigned": value})
    elif binding.field == "temperature":
        converters = state.setdefault("convertersInfo", [{}])
        if not converters:
            converters.append({})
        converters[0]["ccuTemperature"] = value
    else:
        state[binding.field] = value
    return True


def binding_priority(spec) -> tuple:
    """Prefer an explicitly named measurement over an old telemetry fallback."""
    name = re.sub(r"[\s_-]+", " ", spec.name.casefold()).strip()
    path = template_path(spec.config.get("value_template"))
    return (
        100 if name in _NAMED else 50 if path and path[-1] in ("pvPower", "pvPowerTotal", "socTotal") else 0,
        spec.key,
    )


def native_energy_key(spec) -> str | None:
    """Counter roles have separate identities from stored or remaining energy."""
    if spec.component != "sensor" or spec.config.get("unit_of_measurement") not in ("Wh", "kWh", "MWh"):
        return None
    name = re.sub(r"[\s_-]+", " ", spec.name.casefold()).strip()
    if name in _ENERGY:
        return _ENERGY[name]
    if name in ("ccu ac input energy today", "ccu ac input energy total"):
        return "ccuinputenergytoday" if name.endswith("today") else "ccuinputenergytotal"
    match = re.fullmatch(r"battery (\d+) pv energy (today|total)", name)
    if match and 1 <= int(match[1]) <= _MAX_LEGACY_BATTERIES:
        return f"battery_pv_energy_{match[2]}_{int(match[1]) - 1}"
    return None


def measurement_identity(spec) -> tuple:
    """Different discovery IDs must not create the same reading twice."""
    path = template_path(spec.config.get("value_template"))
    expression = path if path is not None else spec.config.get("value_template")
    if path is None and expression:
        try:
            expression = _ENVIRONMENT.parse(expression).dump()
        except TemplateSyntaxError:
            pass
    return (
        spec.component,
        spec.state_topic,
        expression,
        spec.config.get("unit_of_measurement"),
        spec.config.get("device_class"),
        spec.config.get("state_class"),
        spec.config.get("payload_on"),
        spec.config.get("payload_off"),
        spec.config.get("state_on"),
        spec.config.get("state_off"),
    )
