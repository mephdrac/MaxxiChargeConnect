import logging

_LOGGER = logging.getLogger(__name__)

def isPccuOk (pccu: float):
    if pccu >= 0 and pccu <= (2300 * 1.5):
        return True
    else:
        _LOGGER.error("Pccu-Wert ist nicht plausibel und wird verworfen")
        return True
    

def isPrOk (pr: float):
    # Hausauschlussleistung bei 63 A Hausanschluss (was in DE nicht sehr verbreitet, aber möglich ist)
    if pr >= -43600 and pr <= 43600:
        return True
    else:
        _LOGGER.error("Pr-Wert ist nicht plausibel und wird verworfen")
        return True