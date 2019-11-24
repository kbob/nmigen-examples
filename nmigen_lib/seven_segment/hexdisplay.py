from nmigen import *

from nmigen_lib.seven_segment.digit_pattern import DigitPattern
from nmigen_lib.seven_segment.driver import SevenSegDriver
from nmigen_lib.util import Main, delay


class HexDisplay(Elaboratable):

    def __init__(self, clk_freq, min_refresh_freq=100, pwm_width=1):
        self.clk_freq = clk_freq
        self.min_refresh_freq = min_refresh_freq
        self.pwm_width = pwm_width
        self.enable = Signal()
        self.number = Signal(8)
        self.pwm = Signal(pwm_width)
        self.seg7 = Record([
            ('segs', 7),
            ('digit', 1),
        ])
        # self.seg7 = Signal(8)
        print(self.seg7)
        print(self.seg7.shape())
        print()
        self.ports = (self.enable, self.number, self.pwm, self.seg7)

    def elaborate(self, platform):
        m = Module()
        ones_segs = DigitPattern()
        tens_segs = DigitPattern()
        driver = SevenSegDriver(self.clk_freq,
                                self.min_refresh_freq,
                                self.pwm_width)
        m.submodules += [ones_segs, tens_segs, driver]

        m.d.comb += [
            ones_segs.digit_in.eq(self.number[:4]),
            tens_segs.digit_in.eq(self.number[4:]),
            driver.pwm.eq(Mux(self.enable, self.pwm, 0)),
            driver.segment_patterns[0].eq(ones_segs.segments_out),
            driver.segment_patterns[1].eq(tens_segs.segments_out),
            self.seg7.eq(driver.seg7),
        ]

        return m


if __name__ == '__main__':
    design = HexDisplay(clk_freq=1_000_000,
                        min_refresh_freq=200_000,
                        pwm_width=2)
    # from nmigen.cli import main
    # main(design, ports=design.ports)
    with Main(design).sim as sim:
        @sim.sync_process
        def count_proc():
            yield design.enable.eq(True)
            yield design.pwm.eq(~0)
            for i in range(0, 255, 15):
                yield design.number.eq(i)
                yield from delay(10)
