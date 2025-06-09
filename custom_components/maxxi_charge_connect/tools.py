import logging

_LOGGER = logging.getLogger(__name__)


def isPccuOk(pccu: float):
    ok = False
    if pccu >= 0 and pccu <= (2300 * 1.5):
        ok = True
    else:
        _LOGGER.error("Pccu-Wert ist nicht plausibel und wird verworfen")
    return ok


def isPrOk(pr: float):
    ok = False

    # Hausauschlussleistung bei 63 A Hausanschluss (was in DE nicht sehr verbreitet, aber möglich ist)
    if pr >= -43600 and pr <= 43600:
        ok = True
    else:
        _LOGGER.error("Pr-Wert ist nicht plausibel und wird verworfen")
    return ok


def isPowerTotalOk(power_total: float, batterien):
    ok = False
    anzahlBatterien = len(batterien)

    if (anzahlBatterien > 0 and anzahlBatterien < 17) and (
        power_total >= 0 and power_total <= (60 * 138 * anzahlBatterien)
    ):
        ok = True
    else:
        _LOGGER.error(
            f"Power_total Wert ({power_total}) ist nicht plausibel und wird verworfen"
        )
    return ok
