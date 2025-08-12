# 🛠️ Installation

Über HACS (Empfohlen):

- HACS installieren
In HACS → Integrationen → Drei-Punkte-Menü → Benutzerdefiniertes Repository hinzufügen
URL: https://github.com/mephdrac/MaxxiChargeConnect
Typ: Integration
- *MaxxiChargeConnect*  installieren
- Home Assistant neu starten
- Integration in den Einstellungen hinzufügen

## Manuell
- Repository klonen oder ZIP herunterladen
- Inhalt in das Verzeichnis custom_components/maxxi_charge_connect kopieren
- Home Assistant neu starten
- Integration wie gewohnt 

## Einrichten auf Maxxicharge
Zunächst muss in der maxxisun.app unter Cloudservice "nein" eingestellt ist. Und die Einstellung für "Lokalen Server nutzen" auf "Ja" steht.

Dort muss eine API-Route noch vergeben sein. Z.B.:

```
http://**dein_homeassistant**/api/webhook/**webhook_id**
```

# Einrichten der Integration

Zunächst über HACS installieren (siehe [Installation](# 🛠️ Installation))

Danach ein Gerät hinzufügen und es erscheint folgender Dialog:

![Konfigurationsdialog](config.png)

[Konfiguration](https://github.com/mephdrac/MaxxiChargeConnect/wiki/B-Konfiguration)