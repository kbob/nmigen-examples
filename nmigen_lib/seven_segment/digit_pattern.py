from nmigen import *
from nmigen.cli import *
from nmigen_lib.util.main import Main

class DigitPattern(Elaboratable):

    """map four bit binary digit to the pattern representing
       that value on a seven segment display."""

    def __init__(self):
        self.digit_in = Signal(4)
        self.segments_out = Signal(7)
        self.ports = [self.digit_in, self.segments_out]

    def elaborate(self, platform):
        m = Module()
        with m.Switch(self.digit_in):

            with m.Case(0x0):
                m.d.comb += self.segments_out.eq(0b0111111)

            with m.Case(0x1):
                m.d.comb += self.segments_out.eq(0b0000110)

            with m.Case(0x2):
                m.d.comb += self.segments_out.eq(0b1011011)

            with m.Case(0x3):
                m.d.comb += self.segments_out.eq(0b1001111)

            with m.Case(0x4):
                m.d.comb += self.segments_out.eq(0b1100110)

            with m.Case(0x5):
                m.d.comb += self.segments_out.eq(0b1101101)

            with m.Case(0x6):
                m.d.comb += self.segments_out.eq(0b1111101)

            with m.Case(0x7):
                m.d.comb += self.segments_out.eq(0b0000111)

            with m.Case(0x8):
                m.d.comb += self.segments_out.eq(0b1111111)

            with m.Case(0x9):
                m.d.comb += self.segments_out.eq(0b1101111)

            with m.Case(0xA):
                m.d.comb += self.segments_out.eq(0b1110111)

            with m.Case(0xB):
                m.d.comb += self.segments_out.eq(0b1111100)

            with m.Case(0xC):
                m.d.comb += self.segments_out.eq(0b0111001)

            with m.Case(0xD):
                m.d.comb += self.segments_out.eq(0b1011110)

            with m.Case(0xE):
                m.d.comb += self.segments_out.eq(0b1111001)

            with m.Case(0xF):
                m.d.comb += self.segments_out.eq(0b1110001)

        return m

if __name__ == '__main__':
    digit_pattern = DigitPattern()

    # Main(digit_pattern).run()
    with Main(digit_pattern).sim as sim:
        @sim.sync_process
        def digits_proc():
            for i in range(0x10):
                yield digit_pattern.digit_in.eq(i)
                yield
