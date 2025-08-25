"""Dieses Modul stellt verschiedene Hilfsfunktionen bereit, die in mehreren Klassen
oder Modulen verwendet werden können.

Die Funktionen dienen hauptsächlich zur Validierung und Plausibilitätsprüfung von Messwerten
(beispielsweise Leistungswerte von Batteriespeichern) sowie zur Unterstützung allgemeiner
Anwendungslogik im Zusammenhang mit Energiesystemen.

Beispiele für enthaltene Funktionen:
- Prüfung von Leistungswerten auf Plausibilität
- Validierung von Eingabedaten

Das Modul ist so konzipiert, dass es unabhängig und wiederverwendbar in unterschiedlichen
Teilen der Anwendung eingebunden werden kann.
"""

import logging
import re

from homeassistant.core import HomeAssistant

from .const import (
    PROXY_ERROR_CCU,
    PROXY_ERROR_CODE,
    PROXY_ERROR_DEVICE_ID,
    PROXY_STATUS_EVENTNAME,
    PROXY_ERROR_IP,
    PROXY_ERROR_MESSAGE,
    PROXY_ERROR_TOTAL,
    PROXY_FORWARDED,
    PROXY_PAYLOAD,
)

_LOGGER = logging.getLogger(__name__)


async def fire_status_event(hass: HomeAssistant, json_data: dict, forwarded: bool):
    """Feuert ein Status-Event zum Anzeigen des Fehlers in der UI."""
    
    if not isinstance(json_data, dict):
        _LOGGER.error("Ungültige Datenstruktur für fire_status_event: %s", json_data)
        return

    hass.bus.async_fire(
        PROXY_STATUS_EVENTNAME,
        {
            PROXY_ERROR_DEVICE_ID: json_data.get(PROXY_ERROR_DEVICE_ID),
            PROXY_ERROR_CCU: json_data.get(PROXY_ERROR_CCU),
            PROXY_ERROR_IP: json_data.get(PROXY_ERROR_IP),
            PROXY_ERROR_CODE: json_data.get(PROXY_ERROR_CODE),
            PROXY_ERROR_MESSAGE: json_data.get(PROXY_ERROR_MESSAGE),
            PROXY_ERROR_TOTAL: json_data.get(PROXY_ERROR_TOTAL),
            PROXY_PAYLOAD: json_data,
            PROXY_FORWARDED: forwarded,
        },
    )


def is_pccu_ok(pccu: float):
    """Prüft, ob der PCCU-Wert im plausiblen Bereich liegt.

    Args:
        pccu (float): Zu prüfender Leistungswert in Watt.

    Returns:
        bool: True, wenn der Wert im erwarteten Bereich (0 bis 3450 W) liegt,
              False, wenn der Wert außerhalb liegt. In diesem Fall wird ein Fehler geloggt.

    """

    ok = False
    if not isinstance(pccu, (int, float)):
        _LOGGER.error("Ungültiger Typ für PCCU: %s", type(pccu))
        return ok

    if 0 <= pccu <= 3450:  # (2300 * 1.5)
        ok = True
    else:
        _LOGGER.error("Pccu-Wert(%s) ist nicht plausibel und wird verworfen", pccu)
    return ok


def is_pr_ok(pr: float):
    """Prüft, ob der Pr-Wert im plausiblen Bereich liegt.

    Annahme: Die maximale Hausanschlussleistung beträgt 63 A
    (ungewöhnlich, aber möglich in Deutschland),
    was etwa ±43.600 W entspricht.

    Args:
        pr (float): Zu prüfender Leistungswert in Watt.

    Returns:
        bool: True, wenn der Wert innerhalb des Bereichs -43.600 bis +43.600 liegt,
              False, wenn der Wert außerhalb liegt. In diesem Fall wird ein Fehler geloggt.

    """

    ok = False
    if not isinstance(pr, (int, float)):
        _LOGGER.error("Ungültiger Typ für PR: %s", type(pr))
        return ok

    if -43600 <= pr <= 43600:
        ok = True
    else:
        _LOGGER.error("Pr-Wert(%s) ist nicht plausibel und wird verworfen", pr)
    return ok


def is_power_total_ok(power_total: float, batterien: list) -> bool:
    """Prüft, ob der Gesamtleistungswert (power_total) im plausiblen Bereich liegt.

    Die maximale Gesamtleistung hängt von der Anzahl der Batteriespeicher ab.
    Es wird angenommen, dass eine einzelne Batterie maximal 60 Zellen mit je 138 W liefern kann.
    Der gültige Bereich liegt daher zwischen 0 und (60 * 138 * Anzahl der Batterien).

    Args:
        power_total (float): Gemessene Gesamtleistung in Watt.
        batterien (list): Liste der Batteriespeicher (jedes beliebige Objekt, die Länge zählt).

    Returns:
        bool: True, wenn der Wert plausibel ist (basierend auf Anzahl der Batterien),
              False sonst. Bei einem ungültigen Wert wird ein Fehler geloggt.

    """

    ok = False
    if not isinstance(power_total, (int, float)):
        _LOGGER.error("Ungültiger Typ für POWER_TOTAL: %s", type(power_total))
        return ok
    
    if not isinstance(batterien, list):
        batterien = []

    anzahl_batterien = len(batterien)

    if (0 < anzahl_batterien <= 16) and (
        0 <= power_total <= (60 * 138 * anzahl_batterien)
    ):
        ok = True
    else:
        _LOGGER.error("Power_total(%s) - Anzahl-Bat.(%s) Wert ist nicht plausibel und wird verworfen", power_total, anzahl_batterien)
    return ok


def clean_title(title: str) -> str:
    """Bereinigt einen Titel-String für die Verwendung als Entitäts-ID.

    Der Titel wird in Kleinbuchstaben umgewandelt, Sonderzeichen durch
    Unterstriche ersetzt, aufeinanderfolgende Unterstriche reduziert und
    führende bzw. abschließende Unterstriche entfernt.

    Args:
        title (str): Der ursprüngliche Titel, z.B. ein Geräte- oder Benutzername.

    Returns:
        str: Ein bereinigter, slug-artiger String, geeignet z.B. für `entity_id`s.

    """
    if not title:
        return ""

    # alles klein machen
    title = title.lower()
    # alle Nicht-Buchstaben und Nicht-Zahlen durch Unterstriche ersetzen
    title = re.sub(r"[^a-z0-9]+", "_", title)
    # mehrere Unterstriche durch einen ersetzen
    title = re.sub(r"_+", "_", title)
    # führende und abschließende Unterstriche entfernen

    return title.strip("_")


def as_float(value: str) -> float | None:
    """Extrahiert ein Float aus einem String.

    Wenn in einem String nur ein Floatwert und andere Zeichen
    angegeben sind, z.B. "800 W" so extrahiert diese Funktion
    den Float-Wert und liefert diesen zurück. Sollte kein
    gültiger Float-Wert gefunden werden, so wird None zurück-
    geliefert.

    Args:
        value (str): Aus dem String soll eine Zahl extrahiert werden

    Returns:
        float: Die extrahierte Zahl oder None

    """
    number = None

    if not isinstance(value, str):
        value = str(value)

    if value is not None:
        # match = re.search(r"[\d.]+", value)
        match = re.search(r"-?\d+(?:\.\d+)?", value)

        if match:
            number = float(match.group())

    return number
