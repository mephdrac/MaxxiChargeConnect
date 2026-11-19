"""
Webhook-Server für MaxxiChargeConnect Integration
Sendet JSON-Daten an Home Assistant Webhook
"""

import json
import random
import time

import requests


class MaxxiWebhookSender:
    """Sendet Maxxi-Daten an Home Assistant Webhook"""

    def __init__(self, hass_url="http://localhost:8123", webhook_id="testWebhook"):
        self.hass_url = hass_url
        self.webhook_url = f"{hass_url}/api/webhook/{webhook_id}"
        self.headers = {"Content-Type": "application/json"}

    def generate_test_data(self):
        """Generiert Testdaten mit zufälligen Werten"""
        return {
            "deviceId": "Maxxi-44A7F8-396-TEST",
            "ip_addr": "192.168.40.203",
            "wifiStrength": random.randint(-80, -20),
            "meterWifiStrength": random.randint(-80, 0),
            "sendCount": random.randint(200000, 300000),
            "Pr": round(random.uniform(95, 100), 3),
            "meterReading": "",
            "PV_power_total": random.randint(0, 5000),
            "SOC": random.randint(0, 100),
            "batteriesInfo": [
                {
                    "batteryVoltage": random.randint(48000, 58000),
                    "batteryCurrent": random.randint(0, 30000),
                    "batteryPower": round(random.uniform(0, 2000), 3),
                    "batterySOC": random.randint(0, 100),
                    "batteryNominalCapacity": 5397,
                    "batteryCapacity": round(random.uniform(4000, 5400), 2),
                    "pvVoltage": random.randint(60000, 90000),
                    "pvCurrent": random.randint(0, 25000),
                    "pvPower": round(random.uniform(0, 2000), 3),
                    "mpptVoltage": random.randint(48000, 58000),
                    "mpptCurrent": random.randint(0, 30000),
                    "mpptPower": round(random.uniform(0, 2000), 3),
                },
                {
                    "batteryVoltage": random.randint(48000, 58000),
                    "batteryCurrent": random.randint(0, 30000),
                    "batteryPower": round(random.uniform(0, 2000), 3),
                    "batterySOC": random.randint(0, 100),
                    "batteryNominalCapacity": 5397,
                    "batteryCapacity": round(random.uniform(4000, 5400), 2),
                    "pvVoltage": random.randint(60000, 90000),
                    "pvCurrent": random.randint(0, 25000),
                    "pvPower": round(random.uniform(0, 2000), 3),
                    "mpptVoltage": random.randint(48000, 58000),
                    "mpptCurrent": random.randint(0, 30000),
                    "mpptPower": round(random.uniform(0, 2000), 3),
                },
            ],
            "v_ccu": round(random.uniform(40, 100), 2),
            "i_ccu": round(random.uniform(0, 1), 3),
            "ccuTotalPower": round(random.uniform(0, 20), 5),
            "microCurve": random.randint(90, 100),
            "convertersInfo": [
                {
                    "ccuTemperature": random.randint(20, 50),
                    "ccuVoltage": round(random.uniform(40, 50), 2),
                    "ccuCurrent": round(random.uniform(0, 1), 3),
                    "ccuPower": round(random.uniform(0, 10), 5),
                    "version": "106",
                    "command": "81 10 0 0 0 2 4 11 94 d cd db b8",
                },
                {
                    "ccuTemperature": random.randint(20, 50),
                    "ccuVoltage": round(random.uniform(40, 50), 2),
                    "ccuCurrent": round(random.uniform(0, 1), 3),
                    "ccuPower": round(random.uniform(0, 10), 5),
                    "version": "106",
                    "command": "82 10 0 0 0 2 4 11 94 d cd d4 fc",
                },
            ],
            "Pccu": round(random.uniform(0, 20), 5) + 5,
            "error": 0,
            "firmwareVersion": 0.44,
            "box_id": "U2hlbGx5IFBybw",
            "uptime": int(time.time()),
        }

    def send_static_data(self):
        """Sendet die statischen Testdaten aus Ihrem Beispiel"""
        static_data = {
            "deviceId": "Maxxi-44A7F8-396-TEST",
            "ip_addr": "192.168.40.203",
            "wifiStrength": -20,
            "meterWifiStrength": 0,
            "sendCount": 231638,
            "Pr": 98.665,
            "meterReading": "",
            "PV_power_total": 2320,
            "SOC": 10,
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

        return self._send_data(static_data)

    def send_dynamic_data(self):
        """Sendet dynamische Testdaten mit zufälligen Werten"""
        data = self.generate_test_data()
        return self._send_data(data)

    def _send_data(self, data):
        """Interne Methode zum Senden der Daten"""
        try:
            response = requests.post(self.webhook_url, data=json.dumps(data), headers=self.headers, timeout=10)

            if response.status_code == 200:
                print(f"✅ Webhook erfolgreich gesendet an {self.webhook_url}")
                print(f"   SendCount: {data['sendCount']}")
                print(f"   Status: {response.status_code}")
                print(f"   DeviceID: {data['deviceId']}")
                print(f"   SOC: {data['SOC']}%")
                print(f"   PV Power: {data['PV_power_total']}W")
                return True
            else:
                print(f"❌ Fehler beim Senden: Status {response.status_code}")
                print(f"   Response: {response.text}")
                return False

        except requests.exceptions.ConnectionError:
            print(f"❌ Verbindung fehlgeschlagen zu {self.hass_url}")
            print("   Stellen Sie sicher, dass Home Assistant läuft")
            return False
        except Exception as e:
            print(f"❌ Unerwarteter Fehler: {e}")
            return False

    def start_continuous_sending(self, interval=1):
        """Startet kontinuierliches Senden im angegebenen Intervall (Sekunden)"""
        print(f"Starte kontinuierliches Senden alle {interval} Sekunden...")
        print("Drücken Sie STRG+C zum Beenden")

        send_counter = 1

        try:
            while True:
                data = self.generate_test_data()
                data["sendCount"] = send_counter
                self._send_data(data)
                send_counter += 1
                time.sleep(interval)
        except KeyboardInterrupt:
            print("\n⏹️  Senden gestoppt")

    def start_continuous_static_sending(self, interval=5):
        """Startet kontinuierliches Senden statischer Werte im angegebenen Intervall (Sekunden)"""
        print(f"Starte kontinuierliches Senden alle {interval} Sekunden...")
        print("Drücken Sie STRG+C zum Beenden")

        send_counter = 1

        try:
            while True:
                data = self.send_static_data()
                data["sendCount"] = send_counter
                self._send_data(data)
                send_counter += 1
                time.sleep(interval)
        except KeyboardInterrupt:
            print("\n⏹️  Senden gestoppt")


def main():
    """Hauptfunktion mit Menü"""
    sender = MaxxiWebhookSender()

    print("=== MaxxiChargeConnect Webhook Sender ===")
    print(f"Home Assistant URL: {sender.hass_url}")
    print(f"Webhook URL: {sender.webhook_url}")
    print()

    while True:
        print("Optionen:")
        print("1. Statische Testdaten senden")
        print("2. Dynamische Testdaten senden")
        print("3. Kontinuierlich senden (alle 5 Sekunden)")
        print("4. Kontinuierlich statische Werte senden (alle 5 Sekunden)")
        print("5. Beenden")

        choice = input("\nWählen Sie eine Option (1-5): ").strip()

        if choice == "1":
            print("\nSende statische Testdaten...")
            sender.send_static_data()
        elif choice == "2":
            print("\nSende dynamische Testdaten...")
            sender.send_dynamic_data()
        elif choice == "3":
            print("\nStarte kontinuierliches Senden...")
            sender.start_continuous_sending()
        elif choice == "4":
            print("\nStarte kontinuierliches Senden statischer Werte...")
            sender.start_continuous_static_sending()
        elif choice == "5":
            print("Auf Wiedersehen!")
            break
        else:
            print("Ungültige Auswahl. Bitte versuchen Sie es erneut.")

        print()


if __name__ == "__main__":
    main()
