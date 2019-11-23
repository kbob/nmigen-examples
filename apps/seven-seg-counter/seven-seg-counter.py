#!/usr/bin/env nmigen

from nmigen import *
from nmigen.build import *
from nmigen_boards.icebreaker import ICEBreakerPlatform

from nmigen_lib import Counter, Timer, DigitPattern, SevenSegDriver


class Top(Elaboratable):

    def elaborate(self, platform):
        seg7_pins = platform.request('seg7', 0)

        clk_freq = platform.default_clk_frequency
        min_refresh_freq = 100
        count_freq = 4

        m = Module()
        ticker = Timer(period=int(clk_freq // count_freq))
        counter = Counter(period=16 * 16)
        ones_segs = DigitPattern()
        tens_segs = DigitPattern()
        driver = SevenSegDriver(clk_freq, min_refresh_freq)
        m.submodules += [ticker, counter, ones_segs, tens_segs, driver]

        m.d.comb += [
            counter.trg.eq(ticker.stb),
            ones_segs.digit_in.eq(counter.counter[:4]),
            tens_segs.digit_in.eq(counter.counter[4:]),
            driver.pwm.eq(~0),
            driver.segment_patterns[0].eq(ones_segs.segments_out),
            driver.segment_patterns[1].eq(tens_segs.segments_out),
            seg7_pins.eq(driver.seg7),
        ]
        return m


if __name__ == '__main__':
    platform = ICEBreakerPlatform()
    conn = ('pmod', 1)
    platform.add_resources([
        Resource('seg7', 0,
            Subsignal('segs', Pins('1 2 3 4 7 8 9', conn=conn, dir='o')),
            Subsignal('digit', Pins('10', conn=conn, dir='o')),
        ),
    ])
    platform.build(Top(), do_program=True)
