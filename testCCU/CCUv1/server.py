"""Simulate the telemetry and local HTTP configuration interface of a CCU V1."""

import argparse
import getpass
import json
import math
import os
import sys
import threading
import time
from html import escape
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, quote, urlsplit
from urllib.request import Request, urlopen

# POST key, HTML label, default, minimum, maximum, display unit.
SETTINGS = (
    ("maxOutputPower", "Maximale Leistung:", 800, 0, 3000, " W"),
    ("offlinePower", "Offline-Ausgangsleistung:", 200, 0, 3000, " W"),
    ("baseLoad", "Ausgabe korrigieren:", 20, -1000, 1000, " W"),
    ("threshold", "Reaktionstoleranz:", 10, -1000, 1000, " W"),
    ("minSOC", "Minimale Entladung der Batterie:", 20, 0, 100, " %"),
    ("maxSOC", "Maximale Akkuladung:", 100, 0, 100, " %"),
)
LIMITS = {key: (minimum, maximum) for key, _, _, minimum, maximum, _ in SETTINGS}
LABELS = (
    ("Messgerät IP:", "192.0.2.10"),
    ("Messgerät Typ:", "TestCCU"),
    ("Batterien im System:", "2"),
    ("Mikro-Wechselrichter-Typ:", "Hoymiles"),
    ("DC/DC-Algorithmus:", "2"),
    ("Cloudservice:", "Nein"),
    ("Lokalen Server nutzen:", "Ja"),
    ("API-Route:", "/config"),
)
# PV input and battery power per battery, AC output, grid import (negative = export).
PROFILES = {"charge": (400, 250, 300, -75), "discharge": (0, -250, 480, 125), "idle": (0, 0, 0, 150)}
COMMANDS = "pause | resume | once | soc 0..100 | profile charge/discharge/idle | gap N | reboot | show | quit"


class TestCCU:
    """Own the simulated firmware state shared by the HTTP and sender threads."""

    def __init__(self, device_id, ip, soc=55, paused=False):
        self.device_id = device_id
        self.ip = ip
        self.soc = soc
        self.paused = paused
        self.single_packet = False
        self.profile = "charge"
        self.send_count = 0
        self.scan_count = 0
        self.sample_index = 0
        self.booted_at = time.monotonic()
        self.settings = {key: default for key, _, default, _, _, _ in SETTINGS}
        self.lock = threading.Lock()

    def config(self):
        with self.lock:
            return self.settings.copy()

    def apply_config(self, body):
        fields = parse_qs(body, strict_parsing=True, keep_blank_values=True)
        if not fields:
            raise ValueError("Leere Konfiguration")
        changes = {}
        for key, values in fields.items():
            if key not in LIMITS or len(values) != 1:
                raise ValueError("Unbekannte oder doppelte Einstellung")
            value = int(values[0])
            minimum, maximum = LIMITS[key]
            if not minimum <= value <= maximum:
                raise ValueError("Wert außerhalb des erlaubten Bereichs")
            changes[key] = value
        with self.lock:
            self.settings.update(changes)
        print(f"CCU-Konfiguration aktualisiert: {changes}", flush=True)

    def html(self):
        with self.lock:
            settings = self.settings.copy()
            speed = 3 + self.scan_count % 5
            self.scan_count += 1
        labels = [*LABELS, ("CCU-Geschwindigkeit:", str(speed))]
        labels.extend((label, f"{settings[key]}{unit}") for key, label, _, _, _, unit in SETTINGS)
        rows = "\n".join(f"<div><b>{escape(label)}</b> {escape(value)}</div>" for label, value in labels)
        return f'<!doctype html><html lang="de"><meta charset="utf-8"><title>TestCCU V1</title>{rows}</html>'

    def next_packet(self):
        with self.lock:
            if self.paused and not self.single_packet:
                return None
            self.single_packet = False
            self.send_count += 1
            self.sample_index += 1
            step = (self.sample_index - 1) % 9
            pv, battery_power, output, grid = PROFILES[self.profile]
            if pv:
                pv += 25 * step
            if battery_power:
                battery_power += 15 * step if battery_power > 0 else -15 * step
            if output:
                output = min(output + 20 * step, self.settings["maxOutputPower"])
            grid += -10 * step if grid < 0 else 10 * step
            return {
                "deviceId": self.device_id,
                "ip_addr": self.ip,
                "sendCount": self.send_count,
                "uptime": int((time.monotonic() - self.booted_at) * 1000),
                "SOC": self.soc,
                "Pccu": output,
                "Pr": grid,
                "PV_power_total": pv * 2,
                "wifiStrength": -45 - step,
                "meterWifiStrength": -50,
                "firmwareVersion": 0.44,
                "error": 0,
                "batteriesInfo": [
                    {
                        "batteryVoltage": 55000,
                        "batteryCurrent": round(battery_power / 55 * 1000),
                        "batteryPower": battery_power,
                        "batterySOC": self.soc,
                        "batteryNominalCapacity": 5397,
                        "batteryCapacity": round(5397 * self.soc / 100, 2),
                        "pvVoltage": 80000,
                        "pvCurrent": round(pv / 80 * 1000),
                        "pvPower": pv,
                        "mpptVoltage": 55000,
                        "mpptCurrent": round(pv / 55 * 1000),
                        "mpptPower": pv,
                    }
                    for _ in range(2)
                ],
                "convertersInfo": [
                    {"ccuTemperature": 36 + step, "ccuVoltage": 45, "ccuCurrent": output / 90, "ccuPower": output / 2}
                    for _ in range(2)
                ],
            }

    def command(self, command, argument):
        """Apply a local terminal command between packets."""
        with self.lock:
            if command == "pause":
                self.paused = True
                self.single_packet = False
            elif command == "resume":
                self.paused = False
            elif command == "once":
                self.single_packet = True
            elif command == "soc":
                self.soc = percentage(argument)
            elif command == "profile" and argument in PROFILES:
                self.profile = argument
            elif command == "gap":
                skipped = int(argument)
                if skipped < 1:
                    raise ValueError("gap benötigt eine positive Anzahl")
                self.send_count += skipped
            elif command == "reboot":
                self.booted_at = time.monotonic()
                self.send_count = 0
            elif command == "show":
                print(f"SOC={self.soc} %, Profil={self.profile}, sendCount={self.send_count}, pausiert={self.paused}")
                print(self.settings)
            else:
                raise ValueError(COMMANDS)


class CCUHTTPServer(ThreadingHTTPServer):
    """Provide the simulated state to request handlers."""

    def __init__(self, address, ccu):
        self.ccu = ccu
        super().__init__(address, CCUHandler)


class CCUHandler(BaseHTTPRequestHandler):
    """Handle the same HTTP reads and configuration writes as the real CCU."""

    def reply(self, status, body, content_type="text/plain"):
        data = body.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", f"{content_type}; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        path = urlsplit(self.path).path
        if path == "/":
            print(f"HTTP-Scan GET / von {self.client_address[0]}", flush=True)
            self.reply(200, self.server.ccu.html(), "text/html")
        elif path == "/config":
            self.reply(200, json.dumps(self.server.ccu.config()), "application/json")
        else:
            self.reply(404, "Not found")

    def do_POST(self):
        if urlsplit(self.path).path != "/config":
            self.reply(404, "Not found")
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if not 0 < length <= 4096:
                raise ValueError("Ungültige Konfigurationslänge")
            self.server.ccu.apply_config(self.rfile.read(length).decode("utf-8"))
        except ValueError as err:
            self.reply(400, str(err))
            return
        self.reply(200, "OK")

    def log_message(self, *_args):
        """Keep periodic HTTP scans out of the terminal output."""


def percentage(value):
    result = int(value)
    if not 0 <= result <= 100:
        raise ValueError("SOC muss zwischen 0 und 100 liegen")
    return result


def send_packet(url, packet):
    request = Request(url, json.dumps(packet).encode(), {"Content-Type": "application/json"}, method="POST")
    try:
        with urlopen(request, timeout=4) as response:
            # HA can return 200 even when the webhook ID is unknown.
            print(
                f"sendCount={packet['sendCount']} SOC={packet['SOC']} % "
                f"PV={packet['PV_power_total']} W Netz={packet['Pr']} W AC={packet['Pccu']} W "
                f"→ HTTP {response.status}",
                flush=True,
            )
    except HTTPError as err:
        print(f"sendCount={packet['sendCount']} → HTTP {err.code}", flush=True)
    except (URLError, OSError) as err:
        print(f"sendCount={packet['sendCount']} → Ziel nicht erreichbar ({type(err).__name__})", flush=True)


def read_commands(ccu, stop):
    for line in sys.stdin:
        command, _, argument = line.strip().partition(" ")
        if command == "quit":
            stop.set()
            return
        if command:
            try:
                ccu.command(command, argument.strip())
            except ValueError as err:
                print(err, flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ha-url", default="http://127.0.0.1:8123", help="Home Assistant URL für den Webhook")
    parser.add_argument("--proxy-url", help="Alternativ die Basis-URL des lokalen Cloud-Proxys, inklusive Port 3001")
    parser.add_argument("--device-id", default="Maxxi-Test-V1")
    parser.add_argument("--bind", default="127.0.0.1", help="Lokale Bind-Adresse des CCU-HTTP-Servers")
    parser.add_argument("--port", type=int, default=80, help="Port des CCU-HTTP-Servers (Standard: %(default)s)")
    parser.add_argument("--interval", type=float, default=2, help="Sendeintervall in Sekunden")
    parser.add_argument("--soc", type=percentage, default=55)
    parser.add_argument("--paused", action="store_true", help="Ohne Telemetrie starten")
    args = parser.parse_args()
    if not math.isfinite(args.interval) or args.interval <= 0:
        parser.error("--interval muss positiv und endlich sein")

    base = (args.proxy_url or args.ha_url).rstrip("/")
    parsed = urlsplit(base)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname or parsed.query or parsed.fragment:
        parser.error("Ziel als HTTP(S)-Basis-URL angeben")
    if args.proxy_url:
        target = f"{base}/text"
    else:
        webhook_id = os.environ.get("MAXXI_TEST_WEBHOOK_ID")
        if not webhook_id and sys.stdin.isatty():
            webhook_id = getpass.getpass("Webhook-ID der Test-CCU: ")
        if not webhook_id:
            parser.error("MAXXI_TEST_WEBHOOK_ID setzen oder die ID im Terminal eingeben")
        target = f"{base}/api/webhook/{quote(webhook_id, safe='')}"

    ccu = TestCCU(args.device_id, args.bind, args.soc, args.paused)
    stop = threading.Event()
    try:
        server = CCUHTTPServer((args.bind, args.port), ccu)
    except PermissionError:
        parser.exit(1, f"Keine Berechtigung für {args.bind}:{args.port}. Für Port 80 ggf. mit sudo starten.\n")
    except OSError as err:
        parser.exit(1, f"CCU-HTTP-Server kann {args.bind}:{args.port} nicht öffnen: {err.strerror}\n")
    with server:
        worker = threading.Thread(target=server.serve_forever, daemon=True)
        worker.start()
        threading.Thread(target=read_commands, args=(ccu, stop), daemon=True).start()
        print(f"Test-CCU {args.device_id} auf {args.bind}:{server.server_port}", flush=True)
        address = "<Simulator-IP>" if args.bind == "0.0.0.0" else args.bind
        if server.server_port != 80:
            address = f"{address}:{server.server_port}"
        print(f"HTTP-Scan in HA: CCU-Adresse {address} eintragen.", flush=True)
        print(f"Befehle: {COMMANDS}", flush=True)
        try:
            while not stop.is_set():
                packet = ccu.next_packet()
                if packet is not None:
                    send_packet(target, packet)
                stop.wait(args.interval)
        except KeyboardInterrupt:
            pass
        finally:
            server.shutdown()
            worker.join()


if __name__ == "__main__":
    main()
