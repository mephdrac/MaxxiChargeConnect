"""
Einfacher Webhook-Sender für MaxxiChargeConnect
Sendet die exakten JSON-Daten an Home Assistant
"""

import json

import requests


def send_maxxi_webhook():
    """Sendet die statischen Maxxi-Daten an Home Assistant"""

    url = "http://localhost:8123/api/webhook/Maxxi-44A7F8-Test"
    headers = {"Content-Type": "application/json"}

    data = {
        "deviceId": "Maxxi-44A7F8-396-TEST",
        "ip_addr": "192.168.40.203",
        "wifiStrength": -20,
        "meterWifiStrength": 0,
        "sendCount": 231638,
        "Pr": 98.665,
        "meterReading": "",
        "PV_power_total": 2320,
        "SOC": 97,
        "batteriesInfo": [
            {
                "batteryVoltage": 55214,
                "batteryCurrent": 24234,
                "batteryPower": 1338.056,
                "batterySOC": 19,
                "batteryNominalCapacity": 5397,
                "batteryCapacity": 5235.09,
                "pvVoltage": 80157,
                "pvCurrent": 19726,
                "pvPower": 1581.177,
                "mpptVoltage": 55315,
                "mpptCurrent": 27557,
                "mpptPower": 1524.315,
            },
            {
                "batteryVoltage": 54773,
                "batteryCurrent": 11444,
                "batteryPower": 626.8222,
                "batterySOC": 97,
                "batteryNominalCapacity": 5397,
                "batteryCapacity": 5235.09,
                "pvVoltage": 86181,
                "pvCurrent": 8573,
                "pvPower": 738.8297,
                "mpptVoltage": 54813,
                "mpptCurrent": 13301,
                "mpptPower": 729.0677,
            },
        ],
        "v_ccu": 90.61,
        "i_ccu": 0.157,
        "ccuTotalPower": 7.11257,
        "microCurve": 99,
        "convertersInfo": [
            {
                "ccuTemperature": 36,
                "ccuVoltage": 45.31,
                "ccuCurrent": 0.047,
                "ccuPower": 2.12957,
                "version": "106",
                "command": "81 10 0 0 0 2 4 11 94 d cd db b8",
            },
            {
                "ccuTemperature": 36,
                "ccuVoltage": 45.3,
                "ccuCurrent": 0.11,
                "ccuPower": 4.983,
                "version": "106",
                "command": "82 10 0 0 0 2 4 11 94 d cd d4 fc",
            },
        ],
        "Pccu": 7.11257,
        "error": 0,
        "firmwareVersion": 0.44,
        "box_id": "U2hlbGx5IFBybw",
        "uptime": 1469726575,
    }

    try:
        response = requests.post(url, data=json.dumps(data), headers=headers)

        if response.status_code == 200:
            print("✅ Webhook erfolgreich gesendet!")
            print(f"Status: {response.status_code}")
            print(f"DeviceID: {data['deviceId']}")
            print(f"SOC: {data['SOC']}%")
            print(f"PV Power: {data['PV_power_total']}W")
        else:
            print(f"❌ Fehler: Status {response.status_code}")
            print(f"Response: {response.text}")

    except requests.exceptions.ConnectionError:
        print("❌ Verbindung zu Home Assistant fehlgeschlagen")
        print("Stellen Sie sicher, dass HA auf localhost:8123 läuft")
    except Exception as e:
        print(f"❌ Fehler: {e}")


if __name__ == "__main__":
    print("Sende MaxxiChargeConnect Webhook...")
    send_maxxi_webhook()
