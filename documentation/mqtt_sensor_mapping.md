# Vollständiger CCU-V2-Sensorabgleich

Beispiel mit vier Batterien, geprüft anhand von 99 anonymisierten tatsächlichen Discovery-Beschreibungen.
Alle IDs sind die Suffixe hinter der jeweiligen Home-Assistant-Config-Entry-ID. Der Abgleich verändert keine bestehenden IDs.

Ergebnis: 53 eigene Sensoren und 20 zusätzliche native CCU-Zähler; Quellenabdeckung 100.0 %.

## Eigene Sensoren

| ID-Suffix | Sensorklasse | Zuordnung | Quellen / Abhängigkeiten |
| --- | --- | --- | --- |
| `battery_power` | `BatteryPower` | calculated | battery_power_charge, battery_power_discharge |
| `battery_power_charge` | `BatteryPowerCharge` | direct | Battery Charging Power |
| `battery_power_discharge` | `BatteryPowerDischarge` | direct | Battery Discharging Power |
| `battery_pv_power_sensor_0` | `BatteryPVPowerSensor` | direct | Battery 1 PV Power |
| `battery_pv_power_sensor_1` | `BatteryPVPowerSensor` | direct | Battery 2 PV Power |
| `battery_pv_power_sensor_2` | `BatteryPVPowerSensor` | direct | Battery 3 PV Power |
| `battery_pv_power_sensor_3` | `BatteryPVPowerSensor` | direct | Battery 4 PV Power |
| `battery_soc` | `BatterySoc` | direct | Local Battery SOC |
| `battery_soc_sensor_0` | `BatterySOCSensor` | direct | Battery 1 SOC |
| `battery_soc_sensor_1` | `BatterySOCSensor` | direct | Battery 2 SOC |
| `battery_soc_sensor_2` | `BatterySOCSensor` | direct | Battery 3 SOC |
| `battery_soc_sensor_3` | `BatterySOCSensor` | direct | Battery 4 SOC |
| `battery_soe` | `BatterySoE` | direct | Usable Energy Remaining |
| `battery_soe_0` | `BatterySoESensor` | direct | Battery 1 Stored Energy |
| `battery_soe_1` | `BatterySoESensor` | direct | Battery 2 Stored Energy |
| `battery_soe_2` | `BatterySoESensor` | direct | Battery 3 Stored Energy |
| `battery_soe_3` | `BatterySoESensor` | direct | Battery 4 Stored Energy |
| `battery_voltage_sensor_0` | `BatteryVoltageSensor` | direct | Battery 1 Voltage |
| `battery_voltage_sensor_1` | `BatteryVoltageSensor` | direct | Battery 2 Voltage |
| `battery_voltage_sensor_2` | `BatteryVoltageSensor` | direct | Battery 3 Voltage |
| `battery_voltage_sensor_3` | `BatteryVoltageSensor` | direct | Battery 4 Voltage |
| `batterytodayenergycharge` | `BatteryTodayEnergyCharge` | calculated | battery_power_charge |
| `batterytodayenergydischarge` | `BatteryTodayEnergyDischarge` | calculated | battery_power_discharge |
| `batterytotalenergycharge` | `BatteryTotalEnergyCharge` | calculated | battery_power_charge |
| `batterytotalenergydischarge` | `BatteryTotalEnergyDischarge` | calculated | battery_power_discharge |
| `ccu_power` | `CcuPower` | direct | CCU AC Power |
| `ccu_temperatur_sensor` | `CCUTemperaturSensor` | direct | CCU Temperature |
| `ccuenergytoday` | `CcuEnergyToday` | calculated | ccu_power |
| `ccuenergytotal` | `CcuEnergyTotal` | calculated | ccu_power |
| `consumptionenergytoday` | `ConsumptionEnergyToday` | calculated | power_consumption |
| `consumptionenergytotal` | `ConsumptionEnergyTotal` | calculated | power_consumption |
| `deviceid` | `DeviceId` | identity | device.identifiers |
| `firmware_version` | `FirmwareVersion` | direct | CCU ver |
| `grid_export` | `GridExport` | calculated | power_meter |
| `grid_import` | `GridImport` | calculated | power_meter |
| `gridexportenergytoday` | `GridExportEnergyToday` | calculated | grid_export |
| `gridexportenergytotal` | `GridExportEnergyTotal` | calculated | grid_export |
| `gridimportenergytoday` | `GridImportEnergyToday` | calculated | grid_import |
| `gridimportenergytotal` | `GridImportEnergyTotal` | calculated | grid_import |
| `mqtt_discovered_entities` | `MqttDiscoveredEntitiesSensor` | local | lokal erzeugt |
| `mqtt_last_received` | `MqttLastReceivedSensor` | local | lokal erzeugt |
| `mqtt_received_count` | `MqttReceivedCountSensor` | local | lokal erzeugt |
| `mqtt_sensor_coverage` | `MqttSensorCoverageSensor` | local | lokal erzeugt |
| `online_status_sensor` | `OnlineStatusSensor` | derived | CCU2-0000-0000-0001/battery/telemetry, CCU2-0000-0000-0001/device/state, CCU2-0000-0000-0001/powermeter/telemetry, CCU2-0000-0000-0001/system/telemetry |
| `power_consumption` | `PowerConsumption` | calculated | power_meter, ccu_power |
| `power_meter` | `PowerMeter` | direct | Grid Power |
| `pv_consumption` | `PvSelfConsumption` | calculated | pv_power, power_meter |
| `pv_power` | `PvPower` | direct | PV Power |
| `pvselfconsumptionenergytoday` | `PvSelfConsumptionEnergyToday` | calculated | pv_consumption |
| `pvselfconsumptionenergytotal` | `PvSelfConsumptionEnergyTotal` | calculated | pv_consumption |
| `pvtodayenergy` | `PvTodayEnergy` | calculated | pv_power |
| `pvtotalenergy` | `PvTotalEnergy` | calculated | pv_power |
| `uptime_sensor` | `UptimeSensor` | direct | CCU Uptime |

## Zusätzliche native CCU-Zähler

Diese Sensoren tragen den Namenszusatz „CCU-Zähler“ und ersetzen keine berechneten Zählerstände.

| ID-Suffix | CCU-Discovery-Wert |
| --- | --- |
| `battery_pv_energy_today_0_ccu_counter` | Battery 1 PV Energy Today |
| `battery_pv_energy_today_1_ccu_counter` | Battery 2 PV Energy Today |
| `battery_pv_energy_today_2_ccu_counter` | Battery 3 PV Energy Today |
| `battery_pv_energy_today_3_ccu_counter` | Battery 4 PV Energy Today |
| `battery_pv_energy_total_0_ccu_counter` | Battery 1 PV Energy Total |
| `battery_pv_energy_total_1_ccu_counter` | Battery 2 PV Energy Total |
| `battery_pv_energy_total_2_ccu_counter` | Battery 3 PV Energy Total |
| `battery_pv_energy_total_3_ccu_counter` | Battery 4 PV Energy Total |
| `batterytotalenergycharge_ccu_counter` | Battery Charging Energy |
| `batterytotalenergydischarge_ccu_counter` | Battery Discharging Energy |
| `ccuenergytoday_ccu_counter` | CCU AC Output Energy Today |
| `ccuenergytotal_ccu_counter` | CCU AC Output Energy Total |
| `ccuinputenergytoday_ccu_counter` | CCU AC Input Energy Today |
| `ccuinputenergytotal_ccu_counter` | CCU AC Input Energy Total |
| `gridexportenergytoday_ccu_counter` | Grid Export Energy Today |
| `gridexportenergytotal_ccu_counter` | Grid Export Energy Total |
| `gridimportenergytoday_ccu_counter` | Grid Import Energy Today |
| `gridimportenergytotal_ccu_counter` | Grid Import Energy Total |
| `pvtodayenergy_ccu_counter` | PV Energy Today |
| `pvtotalenergy_ccu_counter` | PV Energy Total |

Weitere Discovery-Werte ohne eigene passende Sensorklasse werden im Attribut `unmapped_discovery` des Diagnose-Sensors gemeldet. Sie erzeugen keine generischen Sensoren.

100 % beschreibt die Quellenzuordnung. Aktuelle Verfügbarkeit und Zahlenwerte müssen weiterhin im laufenden System geprüft werden.
