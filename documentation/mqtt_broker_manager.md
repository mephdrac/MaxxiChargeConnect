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

## MQTT-Discovery und zusätzliche Entitäten

CCU-V2-Einträge lesen zusätzlich die Discovery-Beschreibungen unter
`homeassistant/+/+/config` und `homeassistant/+/+/+/config`. Unterstützt werden
Einzelbeschreibungen und Gerätebeschreibungen mit `components`/`cmps`, inklusive
der MQTT-Discovery-Kurzschreibweisen und des Topic-Platzhalters `~`.

Die Geräte-ID muss in `device.identifiers` bzw. `dev.ids` genau übereinstimmen.
Zustands-, Verfügbarkeits- und Befehlstopics müssen diese Geräte-ID als eigenes
Pfadsegment enthalten. Damit sind auch Topics wie `maxxi/<Geräte-ID>/state`
möglich. Wildcards in diesen Topics werden nicht akzeptiert.

Aus den Beschreibungen entstehen zusätzliche Sensoren, Binärsensoren,
Zahlenfelder, Auswahllisten und Schalter am vorhandenen CCU-Gerät. Ihre Namen,
Einheiten, Vorlagen, Wertebereiche und Optionen kommen aus der CCU-Beschreibung.
Die vorhandenen Sensoren und ihre IDs bleiben erhalten. Bekannte Gegenstücke
werden auf diese Sensoren abgebildet und nicht als zusätzliche Discovery-Sensoren
angelegt. Der Abgleich berücksichtigt bekannte Messwertrollen sowie Topic und
JSON-Wertepfad; Punkt- und Klammerschreibweise in einfachen Vorlagen werden
gleich behandelt. Einheiten und Geräteklassen müssen passen. Die Zuordnung
funktioniert auch nach einem Umbenennen der vorhandenen HA-Entitäten.

Abgeglichen werden unter anderem Netz-, PV- und CCU-Leistung, SOC,
CCU-Temperatur und Batteriesensoren mit ihrem Batterieindex. Passende aktuelle
Discovery-Werte fließen in den bisherigen Sensor-Datenweg, einschließlich der
Umrechnung von kW in W und von Batteriespannung in das bisherige Eingabeformat.
Die Vorzeichenbehandlung der bestehenden CCU-Sensoren bleibt erhalten.
Bereits berechnete Energiezähler werden weiterhin berechnet; native
Discovery-Energiezähler ersetzen weder deren Historie noch deren Zählerstand.
Eine eigene neue Entität entsteht für zusätzliche oder nicht eindeutig
zuordenbare Messwerte. Gleiche Discovery-Quellen mit mehreren IDs werden
zusätzlich anhand von Topic, Vorlage und Metadaten zusammengefasst.

Falls eine frühere Version bereits eine zuordenbare Discovery-Dublette angelegt
hat, wird nur diese von MaxxiChargeConnect erzeugte Kopie deaktiviert. Die
ursprünglichen Sensoren und ihre Historien werden nicht gelöscht; andere
Integrationseinträge und vom Nutzer deaktivierte Entitäten werden nicht geändert.

Beschreibungen werden im Home-Assistant-Speicher pro Eintrag gesichert.
Der Cache stellt nach einem Neustart die Entitäten wieder her; er ersetzt keine
aktuellen Zustandsmeldungen. Beim internen Broker werden vorhandene retained
Beschreibungen und Werte beim Anbinden einer weiteren CCU aus aMQTT übernommen.
Geänderte Beschreibungen aktualisieren die Entitäten und ihre Abonnements.
Eine leere Discovery-Nachricht zieht eine Beschreibung zurück; die zugehörige
Entität bleibt mit ihrer bisherigen ID erhalten, wird aber nicht verfügbar.

Die Implementierung unterstützt eine einzelne Verfügbarkeitsbeschreibung pro
Entität. Komplexe Mehrfach-Verfügbarkeitsregeln werden derzeit nicht übernommen.
Maximal 256 Discovery-Entitäten pro CCU und 64 KiB pro Beschreibung werden
angenommen. Andere Discovery-Komponenten wie `button`, `light` und `climate`
werden nicht eingerichtet.

Beim externen Broker können zusätzlich die normalen, von Home Assistants
MQTT-Integration erstellten Entitäten existieren. Diese werden von uns nicht
automatisch deaktiviert. Für die hier beschriebene Befehlsbestätigung die
Einstellungen am MaxxiChargeConnect-Gerät verwenden.

## Bestätigte MQTT-Steuerung

Die von der CCU entdeckten Zahlenfelder, Auswahllisten und Schalter verwenden
deren `command_topic` und gegebenenfalls `command_template`. Die Steuerung:

1. Prüft, ob eine aktuelle Zustandsmeldung vorliegt und die gemeldete
   Verfügbarkeit einen Schreibzugriff zulässt.
2. Verlangt eine bekannte Firmware ab `2.43.0`, entweder aus der
   Gerätebeschreibung (`sw_version`/`sw`) oder einem entdeckten Firmware-Sensor
   mit dem Namen `CCU ver`, `Firmware` oder `Firmware version`.
3. Prüft Wertebereich, Schrittweite bzw. Auswahloptionen.
4. Sendet den Befehl ohne retained-Flag und wartet bis zu zehn Sekunden auf
   den passenden Wert am angekündigten Zustandstopic.

Erst eine passende Rückmeldung bestätigt den Schreibzugriff. Bei einem Timeout
wird ein Fehler angezeigt; die Entität zeigt weiterhin den tatsächlich gemeldeten
Zustand. Eine gemeldete Offline-Verfügbarkeit, ein Empfangs-Timeout, das Zurückziehen einer
Beschreibung oder das Entladen des Eintrags bricht wartende Befehle ab.
Gleichzeitige Änderungen derselben Einstellung werden nacheinander ausgeführt.
Zustands- und Befehlstopic müssen verschieden sein, damit ein bloßes Echo des
eigenen Befehls nicht als Bestätigung gewertet werden kann.

Für die Konzepte Discovery und bestätigte Steuerung wurde
[ha-maxxicharge](https://github.com/DerSpletti/ha-maxxicharge/tree/d17423a5f888373d25ba391ef4c8b4e7c49099fa)
als Vergleich herangezogen. Dessen Firmware-Untergrenze ist ebenfalls `2.43.0`.
Der dortige MiniBroker wird nicht verwendet: MQTT-Protokoll und Zustellung
übernimmt weiterhin aMQTT.

Nach Übernahme der Änderungen Home Assistant neu starten. Falls die CCU bisher
noch keine Discovery-Beschreibungen gesendet hat, deren MQTT-Verbindung neu
aufbauen lassen. Die bloße Existenz eines Telemetrie-Topics reicht nicht aus,
um daraus eine steuerbare Einstellung abzuleiten.

## Empfang in Home Assistant prüfen

Auf der Geräteseite jeder CCU V2 erscheinen unter **Diagnose** standardmäßig
drei Sensoren:

- **MQTT letzter Empfang**: Zeitpunkt der letzten gültigen, verarbeiteten
  MQTT-Nachricht. Vor der ersten Nachricht ist der Wert unbekannt.
- **MQTT empfangene Nachrichten**: Anzahl gültiger Nachrichten seit dem Laden
  der CCU-Verbindung. Auch Nachrichten mit unveränderten Messwerten zählen.
  Bei einem Neustart oder Neuladen des Eintrags beginnt der Zähler wieder bei null.
- **MQTT erkannte Entitäten**: Aktuelle Anzahl zugeordneter Discovery-Beschreibungen.
  Auch Werte, die auf bestehende Sensoren abgebildet werden, zählen dazu. Der
  Sensor aktualisiert sich beim Hinzufügen oder Zurückziehen einer Beschreibung,
  auch ohne neue Telemetrie. Ohne erkannte Beschreibungen zeigt er `0`.

In den Sensorattributen stehen `last_topic` (zuletzt verarbeitetes Topic),
`counting_since` (Beginn der Zählung), `broker` (`internal` oder `external`)
und `discovered_entities` (Anzahl der zugeordneten Discovery-Entitäten).
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
Weitere Tests prüfen Discovery-Zuordnung, Cache, Vorlagen, Topics mit
Herstellerpräfix, geänderte Beschreibungen, Befehlsbestätigung, falsche Antworten,
parallele Schreibzugriffe, Firmware-Sperren und den vollständigen Befehlsweg
über echte lokale aMQTT-Verbindungen.
Die Integrationstests wurden mit Python 3.12 und Home Assistant 2025.1.4
geprüft, zusätzlich mit aMQTT 0.12.1 und PyYAML 6.0.3. Die Paketauflösung
für die Integrationsabhängigkeiten wurde gegen `homeassistant/package_constraints.txt`
des lokalen Home-Assistant-2026.12-Entwicklungsstands geprüft.
Broker und Telemetrie wurden bereits mit einer echten CCU verwendet. Die neue
Discovery- und Steuerungsfunktion muss noch mit der echten CCU und deren
Discovery-Beschreibungen geprüft werden.

## Installationsfehler durch PyYAML-Konflikt

aMQTT 0.11.3 verlangte exakt PyYAML 6.0.2. Das verhindert die Installation
unter Home-Assistant-Versionen, die PyYAML 6.0.3 vorgeben. Deshalb verwendet
die Integration jetzt aMQTT 0.12.1 mit der flexiblen Vorgabe `PyYAML>=6.0.2`.
Die Home-Assistant-Vorgaben werden dabei nicht überschrieben.

Bei diesem Fehler die aktualisierten Integrationsdateien einschließlich
`manifest.json` übernehmen und Home Assistant neu starten. Home Assistant
installiert die neue aMQTT-Version anhand des Manifests.
