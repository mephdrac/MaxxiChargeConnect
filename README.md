# ICH BIN IM URLAUB vom 04.07.2025 bis 29.07.2025
In der Zeit kann ich keine Bugfixe vornehmen. Falls ein Bug auftritt - bitte als Issue hinterlegen. Sobald ich zurück bin, kümmere ich mich drum.

![MaxxiChargeConnect](images/logo.png)

# MaxxiChargeConnect


MaxxiChargeConnect ist eine benutzerdefinierte Home Assistant Integration, die das MaxxiCharge-System von Maxxisun unterstützt. Die Integration empfängt Statuswerte über einen lokalen Webhook und stellt sie in Home Assistant als Sensoren bereit.

## 📌 Hinweis

Diese Integration wurde nicht von Maxxisun bzw. der Maxxihandel GmbH, 04509 Wiedemar entwickelt oder unterstützt.
Ich, @mephdrac, stehe in keinerlei Verbindung von Maxxisun bzw. der Maxxihandel GmbH. Die Verwendung der Begriffe MaxxiCharge und Maxxisun dient ausschließlich der Beschreibung der Kompatibilität.

## Update - Hiweist für Version 1.2.0

**ACHTUNG:** beim Wechsel auf Version 1.2.0 von einer früheren Version kann es u.U. zu Datenverlusten kommen. Beim Betrieb der Version 1.2.0 kommt es selbstverständlich nicht mehr zu Datenverlusten. Bitte vorher Backup machen - und mir Bescheid geben - wenn es ein Problem gab.


## ⚠️ Limitationen:

Für folgende Sensoren gilt:
- Hausverbrauch
- Hausverbrauch gesamt
- Hausverbrauch heute

- PV Eigenverbrauch
- PV Eigenverbrauch gesamt
- PV Eigenverbrauch gesamt

Falls der User diese Sensoren nutzen möchte, so muss er sie selbst aktivieren. Grundsätzlich gilt, dass die Sensoren nur gute Werte liefer,
sofern nur 1 CCU verwendet wird und keine weiten PV-Anlagen. Denn es kann nicht ermittelt werden, welchen Einfluss weitere PV-Anlagen haben.
Der User soll selbst entscheiden, ob er diese Sensoren nutzen möchte.


## ✅ Funktionen
Empfang von Daten über einen lokalen Webhook

- Darstellung folgender Informationen:
- Gerätedaten (ID, Firmware-Version)
- WiFi-Signalstärke
- Ladeleistung (CCU, PV, Batterie)
- Ladezustand in Wh und %

Icons & Device Class für Home Assistant optimiert

## 🚫 Haftungsausschluss
Diese Software wird ohne jegliche Gewährleistung bereitgestellt.
Die Nutzung erfolgt auf eigene Gefahr. Ich übernehme keine Haftung für:

Schäden an Hardware oder Software

Datenverluste

fehlerhafte oder veraltete Messwerte

Kompatibilitätsprobleme mit zukünftigen Home Assistant-Versionen

## 🛠️ Installation / Dokumentation usw.

siehe hier [Beschreibung](documentation/doc.md)


## 🙌 Mitwirken
Pull Requests, Fehlerberichte und Vorschläge sind willkommen!
Bitte eröffne ein Issue, wenn du etwas beitragen oder melden möchtest.

## 📄 Lizenz
Veröffentlicht unter der MIT-Lizenz.
