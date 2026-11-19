# CCU V1 mit Home Assistant testen

`server.py` simuliert eine CCU V1. Es sendet regelmäßig Webhook-Telegramme, liefert die vom HTTP-Scan erwartete HTML-Seite und nimmt Konfigurationsänderungen von Home Assistant an. Python 3 genügt.

## Starten

1. Einen separaten **CCU-V1-Eintrag** in MaxxiChargeConnect anlegen. Als Gerätename z. B. `Test-CCU`, als Device-ID `Maxxi-Test-V1` und als Webhook-ID einen eigenen Testwert eingeben. Für einen schnellen Ausfalltest den Empfangstimeout auf **10 Sekunden** setzen.
2. Als CCU-Adresse die LAN-IP des Simulators eintragen, z. B. `192.168.1.42`. Sie muss aus Home Assistant erreichbar sein. Der Simulator verwendet wie die CCU standardmäßig HTTP-Port 80. Für diesen Test **IP-Beschränkung** und **lokalen Cloud-Proxy** deaktivieren.
3. Im Terminal auf dem Simulator-Rechner starten:

   ```bash
   python3 testCCU/CCUv1/server.py --bind 192.168.1.42 --ha-url http://homeassistant.local:8123 --paused
   ```

   Die Webhook-ID wird verdeckt abgefragt. Für einen Start ohne interaktives Terminal kann sie über `MAXXI_TEST_WEBHOOK_ID` übergeben werden. Falls Linux das Öffnen von Port 80 verweigert, starte denselben Aufruf mit `sudo`. Standardmäßig sendet die Simulation alle zwei Sekunden. Ohne `--bind` lauscht der Konfigurationsserver nur auf `127.0.0.1`. Bei HA im Container ist dessen Loopback vom Simulator getrennt. Wenn du für einen Sondertest explizit `--port` setzt, gehört dieser Port auch zur CCU-Adresse in HA.

## HTTP-Scan prüfen

Home Assistant ruft die im CCU-Eintrag gespeicherte **IP-Adresse der MaxxiCharge** per HTTP ab, zum Beispiel `192.168.1.42`. `--ha-url` ist das Ziel für die ausgehenden Webhooks. Nutze `server.py` für beide Richtungen. Das ältere `webhook_server.py` sendet nur Webhooks.

Öffne zunächst `http://192.168.1.42/` im Browser. Im Simulator-Terminal erscheint `HTTP-Scan GET / von <IP-des-Aufrufers>`. Lade dann den CCU-V1-Testeintrag in HA neu. Der Absender im Terminal zeigt, ob auch HA die Seite abruft. Die Ergebnisse findest du unter **Entwicklerwerkzeuge → Zustände** bei den `sensor.`-Entitäten des Testgeräts, etwa **CCU-Geschwindigkeit** und **API-Route**. Die simulierte CCU-Geschwindigkeit wechselt bei jedem Seitenabruf zwischen 3 und 7. HA fragt die Seite etwa alle 30 Sekunden ab. Die Abfrage läuft auch bei pausiertem Webhook-Versand.

Der **Status**-Sensor zeigt in seinen Attributen `http_scan_target` und `http_scan_result` das tatsächlich verwendete Ziel und das Ergebnis des letzten Scans. So lässt sich ein HTTP-Scan-Fehler auch bei funktionierenden Webhooks erkennen. Beim Simulator sollte das Ergebnis `15/15 Felder gelesen` lauten.

## Testabläufe

| Prüfen | Aktion | In Home Assistant beobachten |
| --- | --- | --- |
| Start ohne Daten | Simulator mit `--paused` starten und HA oder den Eintrag neu laden. | Status `Offline`, Live-Messwerte `Nicht verfügbar`, Telegrammzähler bei 0, gespeicherte Energiezähler bleiben verfügbar. |
| Einzelnes Telegramm | Im pausierten Modus `once` eingeben. | Der Zähler erhöht sich um 1 und der Status wechselt auf `OK`. |
| Ausfall und Wiederanlauf | `resume`, dann `pause` eingeben. Empfangstimeout plus bis zu vier Sekunden abwarten, dann `resume`. | Live-Sensoren und Status gehen offline und erholen sich beim nächsten Telegramm. Der Telegrammzähler läuft weiter. Der HTTP-Scan bleibt während der Sendepause erreichbar. |
| Wechselnde Live-Daten | `resume` eingeben. Das Profil kann mit `profile charge`, `profile discharge` oder `profile idle` gewechselt werden. | Netzleistung, Signalstärke und Temperatur variieren mit jedem Telegramm. In den aktiven Profilen ändern sich außerdem die jeweils anliegenden PV-, Batterie- und Ausgangsleistungen. Der SOC lässt sich für reproduzierbare Tests separat setzen. |
| Konfiguration schreiben | Z. B. maximale Leistung oder Mindest-SOC in HA ändern, dann `show` eingeben. | Der Simulator protokolliert den Schreibzugriff und gibt den neuen Wert beim nächsten HTTP-Scan zurück. |
| Winterbetrieb | Wintermodus in HA einschalten. `soc 10` und anschließend `soc 80` bei den Standardgrenzen ausprobieren. | Die SOC-Änderung und den jeweiligen Schreibzugriff auf `minSOC` im Terminal verfolgen. |
| Paketlücken und CCU-Neustart | Nach mehreren Paketen `gap 3` bzw. `reboot` eingeben. | `missing_packets` steigt um 3 oder `resets` steigt beim Rücksprung der CCU-Sequenznummer. Der HA-Telegrammzähler zählt weiter. |

Zum Beenden `quit` oder **Strg+C** verwenden. Konfigurationsänderungen gelten bis zum Beenden des Simulators. `reboot` setzt CCU-Sequenznummer und Uptime zurück. Telegramme und Befehle werden im Takt des Sendeintervalls verarbeitet. Ein HTTP-200 allein bestätigt beim HA-Webhook noch keine Verarbeitung. Prüfe dafür den Telegrammzähler oder den Status in HA.

## Optional über den lokalen Cloud-Proxy senden

Im Testeintrag **Home Assistant übernimmt die Cloud-Funktion?** und **Messdaten abfangen statt an Cloud zu senden?** einschalten. **Messdaten an die Maxxisun-Cloud senden?** deaktivieren. Dieselbe Device-ID und die tatsächliche Quell-IP der Simulator-Verbindung im Testeintrag hinterlegen. Für den Proxy muss die CCU-Adresse eine reine IP ohne Port sein. Wenn du dabei auch HTTP-Scan und Konfigurationszugriffe prüfen willst, muss der Simulator auf dieser IP auf Port 80 erreichbar sein.

```bash
python3 testCCU/CCUv1/server.py --bind 192.168.1.42 --proxy-url http://homeassistant.local:3001 --paused
```

Dabei gehen die Telegramme an `/text` des HA-Proxys. Die direkte CCU-Konfiguration wird weiterhin vom Simulator bereitgestellt. Der Simulator fragt für diesen Test keine Cloud-Konfiguration ab.

`simple_webhook.py` und `webhook_server.py` bleiben als ältere Einzelbeispiele erhalten.
