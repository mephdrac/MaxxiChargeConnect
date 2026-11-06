# MQTT-Betrieb für CCU V2

Die Implementierung liegt auf dem Branch `62-feat-ccu-v2-mqtt`.
CCU V1 verwendet weiterhin ihren bisherigen Webhook-/Proxy-Weg.

## Internen Broker verwenden

1. Die geänderte Integration einschließlich `manifest.json` in Home Assistant
   installieren und Home Assistant neu starten. Home Assistant installiert
   `amqtt==0.12.1` als Integrationsabhängigkeit.
2. Eine CCU V2 hinzufügen oder ihren Eintrag über **Neu konfigurieren** öffnen.
3. Geräte-ID (gleichzeitig MQTT-Basistopic) eintragen und
   **Internen MQTT-Broker verwenden** aktivieren.
4. Port, Benutzername und Passwort festlegen. Standardport ist `1883`.
5. In der CCU die LAN-IP von Home Assistant als Broker-Adresse sowie denselben
   Port, Benutzernamen und dasselbe Passwort eintragen. Die Integration ändert
   diese Geräteeinstellungen nicht automatisch.

Der Listener bindet auf `0.0.0.0` und verwendet MQTT 3.1.1 über TCP ohne TLS.
Bei Home Assistant Container muss der Port auch vom Container erreichbar sein
(zum Beispiel über Host-Netzwerk oder eine entsprechende Portfreigabe).
Bei der Entwicklung im VS-Code-Devcontainer muss der MQTT-Port zusätzlich in
`.devcontainer/devcontainer.json` unter `appPort` veröffentlicht werden,
beispielsweise `"1884:1884"` für Broker-Port 1884. Anschließend in VS Code
**Dev Containers: Rebuild Container** ausführen. Ein Neustart von Home Assistant
übernimmt geänderte Container-Portfreigaben nicht.
Ist `1883` bereits durch einen anderen Broker belegt, einen freien Port wählen.
Bei einem Startfehler meldet Home Assistant den Eintrag als noch nicht bereit
und versucht den Start erneut.

Mehrere interne CCUs teilen einen Broker, Port und Zugangsdaten. Für jede CCU
wird ein eigener Eintrag mit eigener Geräte-ID angelegt. Beim zweiten Eintrag
werden die gemeinsamen Einstellungen vorbelegt; ein leeres Passwortfeld
übernimmt das bereits konfigurierte Passwort. Abweichende Einstellungen werden
zurückgewiesen. Um gemeinsame Einstellungen zu ändern, zunächst bei den anderen
CCU-Einträgen den internen Broker deaktivieren und sie anschließend mit den
neuen Einstellungen wieder aktivieren. Bei der einzigen internen CCU können
Port und Zugangsdaten direkt über Neu konfigurieren geändert werden.

Der Broker startet mit dem ersten internen CCU-Eintrag. Er stoppt beim
Entladen des letzten internen Eintrags oder beim Beenden von Home Assistant.
Fehlgeschlagener Aufbau einer Verbindung gibt bereits erworbene Ressourcen
wieder frei. Zugangsdaten werden in der Home-Assistant-Eintragskonfiguration
gespeichert; das Passwort erscheint nicht als Formular-Vorgabe oder in den
Konfigurations-Debugmeldungen.

## Externen Broker verwenden

**Internen MQTT-Broker verwenden** ausgeschaltet lassen (Voreinstellung,
auch für vorhandene CCU-V2-Einträge). Die externe Broker-Adresse und Anmeldung
werden weiterhin in der normalen MQTT-Integration von Home Assistant
konfiguriert. Die CCU muss denselben externen Broker verwenden.
Interne und externe CCU-Einträge können gleichzeitig existieren.

## Verarbeitete Topics

Die vorhandenen CCU-V2-Parser werden für beide Broker-Wege verwendet:

| Topic | Beispielnachricht |
| --- | --- |
| `<Geräte-ID>/powermeter/telemetry` | `{"power":125}` |
| `<Geräte-ID>/inverter/telemetry` | `{"power":300,"temperature":35}` |
| `<Geräte-ID>/battery/telemetry` | `{"batteries":[{"soc":70,"voltage":52,"inputPower":80}],"inputPowerTotal":80}` |

Nur die exakten Topics der jeweiligen CCU aktualisieren deren Sensoren.
Fehlerhafte JSON-Nachrichten werden ignoriert. Nach dem ersten gültigen Empfang
setzt der konfigurierbare Empfangs-Timeout die Sensoren bei ausbleibenden Daten
auf nicht verfügbar; neue Nachrichten aktualisieren sie wieder.

## Empfang in Home Assistant prüfen

Auf der Geräteseite jeder CCU V2 erscheinen unter **Diagnose** standardmäßig
zwei Sensoren:

- **MQTT letzter Empfang**: Zeitpunkt der letzten gültigen, verarbeiteten
  MQTT-Nachricht. Vor der ersten Nachricht ist der Wert unbekannt.
- **MQTT empfangene Nachrichten**: Anzahl gültiger Nachrichten seit dem Laden
  der CCU-Verbindung. Auch Nachrichten mit unveränderten Messwerten zählen.
  Bei einem Neustart oder Neuladen des Eintrags beginnt der Zähler wieder bei null.

In den Sensorattributen stehen `last_topic` (zuletzt verarbeitetes Topic),
`counting_since` (Beginn der Zählung) und `broker` (`internal` oder `external`).
Die Sensoren funktionieren für beide Broker-Wege. Ungültige Nachrichten und
Topics anderer CCUs zählen nicht. Auch nach einem Empfangs-Timeout bleiben
Zeitpunkt und Zähler sichtbar, damit ein ausgefallener Empfang erkennbar bleibt.
Home Assistant zeigt den Zeitstempel in der eingestellten lokalen Zeitzone an.

Nach Installation dieser Änderung die Integration neu laden oder Home Assistant
neu starten. Die Sensoren finden sich auch unter **Entwicklerwerkzeuge → Zustände**
über den Gerätenamen und „MQTT“.

## Tests

```sh
.venv/bin/python -m unittest discover -s tests -p 'test_mqtt*.py'
```

Die Tests verwenden echte lokale Broker-/Client-Verbindungen und simulieren
Home Assistants Konfigurations- und Dispatcher-Schnittstellen. Sie prüfen
unter anderem Anmeldung, zwei getrennte CCUs, externe Abonnements,
Konfigurationskonflikte, Setup-Rollback, Shutdown, Neustart und Empfangs-Timeout.
Die Integrationstests wurden mit Python 3.12 und Home Assistant 2025.1.4
geprüft, zusätzlich mit aMQTT 0.12.1 und PyYAML 6.0.3. Die Paketauflösung
für die Integrationsabhängigkeiten wurde gegen `homeassistant/package_constraints.txt`
des lokalen Home-Assistant-2026.12-Entwicklungsstands geprüft.
Ein vollständiger Lauf mit dieser Home-Assistant-Version und echter CCU
steht noch aus.

## Installationsfehler durch PyYAML-Konflikt

aMQTT 0.11.3 verlangte exakt PyYAML 6.0.2. Das verhindert die Installation
unter Home-Assistant-Versionen, die PyYAML 6.0.3 vorgeben. Deshalb verwendet
die Integration jetzt aMQTT 0.12.1 mit der flexiblen Vorgabe `PyYAML>=6.0.2`.
Die Home-Assistant-Vorgaben werden dabei nicht überschrieben.

Bei diesem Fehler die aktualisierten Integrationsdateien einschließlich
`manifest.json` übernehmen und Home Assistant neu starten. Home Assistant
installiert die neue aMQTT-Version anhand des Manifests.
