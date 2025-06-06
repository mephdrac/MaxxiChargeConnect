from .HttpScanTextClass import HttpScanTextClass


class OutputOffset(HttpScanTextClass):
    def __init__(self, coordinator):
        super().__init__(
            coordinator, self.__class__.__name__, "Output Offset", "mdi:flash"
        )
