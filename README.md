![MaxxiChargeConnect](images/logo.png)

# MaxxiChargeConnect


MaxxiChargeConnect ist eine benutzerdefinierte Home Assistant Integration, die das MaxxiCharge-System von Maxxisun unterstützt. Die Integration empfängt Statuswerte über einen lokalen Webhook und stellt sie in Home Assistant als Sensoren bereit.

## 📌 Hinweis

Diese Integration wurde nicht von Maxxisun bzw. der Maxxihandel GmbH, 04509 Wiedemar entwickelt oder unterstützt.
Ich, @mephdrac, stehe in keinerlei Verbindung von Maxxisun bzw. der Maxxihandel GmbH. Die Verwendung der Begriffe MaxxiCharge und Maxxisun dient ausschließlich der Beschreibung der Kompatibilität.

## Warum hat meine Integration kein Logo in Home Assistant
Der Grund ist, es wurde mir nicht erlaubt. Ich habe versucht mein Logo in "https://brands.home-assistant.io/" zu hinterlegen. Das wurde mir verwehrt mit dem Hinweis, dass mein Logo nicht das von Maxxisun ist. An dem Logo von Maxxisun habe ich indes keine Rechte, daher kann ich es nicht verwenden. Als ich daraufhinwies, wurde mir gesagt, dass ich dann kein Logo hinterlegen kann. 


**mittlerweile habe ich die Erlaubnis von Maxxisun ihr Logo zu verwenden. Also demnächst gibt es auch ein Logo.**


Maxxisun Maxxihandel GmbH <support@maxxisun.de>
Mi., 10. Sept. 2025, 10:02
an mich

>Guten Tag Herr xxxx,
>
>Wir bitten vielmals um Entschuldigung für die späte Rückmeldung.
>Gerne dürfen Sie unser Logo für nichtgewerbliche Zwecke, in Ihrem Fall die Homeassistant Github Integration verwenden.
>Unser Logo können Sie unserer Webseite entnehmen. Wir freuen uns über die Unterstützung in diesem spannenden Umfeld der Automatisierung unseres Maxxicharge Systems.
>
>Mit freundlichen Grüßen
>
>-Supportteam-
>
>Maxxihandel GmbH
>Lilienthalstraße 6

>04509 Wiedemar
>Telefon: 0345 54838394
>Mail: support@maxxisun.de
>Amtsgericht Leipzig: HRB 41639
>Unsere Datenschutzerklärung finden Sie hier

## Update - Hiweis für Version 1.2.0

**ACHTUNG:** beim Wechsel auf Version 1.2.0 von einer früheren Version kann es u.U. zu Datenverlusten kommen. Beim Betrieb der Version 1.2.0 kommt es selbstverständlich nicht mehr zu Datenverlusten. Bitte vorher Backup machen - und mir Bescheid geben - wenn es ein Problem gab.


## ⚠️ Limitationen:

Die Integration unterstützt zur Zeit die CCUv1 Version .44, .45, .46, .48
Die **Version .41 nur bedingt.** Der Webhook teil funktioniert. Die weiteren Informationen, die auf maxxi.local erscheinen, bleiben auf **unbekannt**. **(Falls hier eine Unterstützung gewünscht ist. Bitte hier als ISSUE (#77) melden.** 

Die Versionen < .41 werden nicht direkt unterstützt, dennoch ist es machbar (Wer das braucht, einfach bei mir melden.). Da es hier auch noch kein maxxi.local gibt, soweit mir bekannt ist.

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

**nur Version .46**
- die Information der CCU-Temperatur ist nicht mehr in den Daten enthalten, daher erscheint hier ein "nicht verfügbar"

**Version .48**
- die Information der CCU-Temperatur ist wieder in den Daten enthalten, daher ist die Anzeige nun wieder möglich.

## ✅ Funktionen
Empfang von Daten über einen lokalen Webhook

- Darstellung folgender Informationen:
- Gerätedaten (ID, Firmware-Version)
- WiFi-Signalstärke
- Ladeleistung (CCU, PV, Batterie)
- Ladezustand in Wh und %

- Winterbetrieb (am Stück aufladen) ab Version 2.7.0

Icons & Device Class für Home Assistant optimiert

## 🚧 Geplante Features

| Feature                     | Beschreibung                                                                                                                                              | Status                       |
| --------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------- |
| **🔋 Ladeeffizienz-Sensor** | Berechnet die durchschnittliche Ladeeffizienz der Batterie (Verhältnis von entladener zu geladener Energie) – zeigt, wie effizient der Speicher arbeitet. | 🧠 *In Planung*              |
| **⚡ Nettoleistungs-Sensor** | Kombiniert Netzeinspeisung und Netzbezug zu einem einzigen Wert. Positiv = Einspeisung, negativ = Bezug. Ideal für Energiebilanz und Dashboard-Anzeige.   | 🧠 *In Planung*          |
| **🔁 Ladezyklen-Zähler**    | Ermittelt die Gesamtzahl der Batterie-Ladezyklen (inkl. Teilzyklen) und dient als Indikator für die Lebensdauer des Speichers.                            | 🧩 *In Vorbereitung* |

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
