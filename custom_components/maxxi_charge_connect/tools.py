"""Dieses Modul stellt verschiedene Hilfsfunktionen bereit, die in mehreren Klassen oder Modulen verwendet werden können.

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

_LOGGER = logging.getLogger(__name__)


def isPccuOk(pccu: float):
    """Prüft, ob der PCCU-Wert im plausiblen Bereich liegt.

    Args:
        pccu (float): Zu prüfender Leistungswert in Watt.

    Returns:
        bool: True, wenn der Wert im erwarteten Bereich (0 bis 3450 W) liegt,
              False, wenn der Wert außerhalb liegt. In diesem Fall wird ein Fehler geloggt.

    """

    ok = False
    if pccu >= 0 and pccu <= (2300 * 1.5):
        ok = True
    else:
        _LOGGER.error("Pccu-Wert ist nicht plausibel und wird verworfen")
    return ok


def isPrOk(pr: float):
    """Prüft, ob der Pr-Wert im plausiblen Bereich liegt.

    Annahme: Die maximale Hausanschlussleistung beträgt 63 A (ungewöhnlich, aber möglich in Deutschland),
    was etwa ±43.600 W entspricht.

    Args:
        pr (float): Zu prüfender Leistungswert in Watt.

    Returns:
        bool: True, wenn der Wert innerhalb des Bereichs -43.600 bis +43.600 liegt,
              False, wenn der Wert außerhalb liegt. In diesem Fall wird ein Fehler geloggt.

    """

    ok = False

    if pr >= -43600 and pr <= 43600:
        ok = True
    else:
        _LOGGER.error("Pr-Wert ist nicht plausibel und wird verworfen")
    return ok


def isPowerTotalOk(power_total: float, batterien: list) -> bool:
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
    anzahlBatterien = len(batterien)

    if (anzahlBatterien > 0 and anzahlBatterien < 17) and (
        power_total >= 0 and power_total <= (60 * 138 * anzahlBatterien)
    ):
        ok = True
    else:
        _LOGGER.error(
            f"Power_total Wert ({power_total}) ist nicht plausibel und wird verworfen"  # noqa: G004
        )
    return ok
