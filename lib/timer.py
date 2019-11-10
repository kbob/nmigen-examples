from nmigen import *
from nmigen.cli import *

class Timer(Elaboratable):

    """Count a fixed period.  Assert .stb once per period."""

    def __init__(self, period):
        assert isinstance(period, int)
        self.period = period
        self.counter = Signal((period - 1).bit_length())
        self.stb = Signal()
        self.ports = [self.counter, self.stb]

    def elaborate(self, platform):
        m = Module()
        with m.If(self.counter == self.period - 1):
            m.d.sync += [
                self.stb.eq(True),
                self.counter.eq(0),
            ]
        with m.Else():
            m.d.sync += [
                self.stb.eq(False),
                self.counter.eq(self.counter + 1),
            ]
        return m


if __name__ == '__main__':
    timer = Timer(period=5)
    main(timer, ports=timer.ports)
