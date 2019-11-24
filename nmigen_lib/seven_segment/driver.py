#!/usr/bin/env nmigen

from nmigen import *
from nmigen_lib.util.main import Main


class SevenSegDriver(Elaboratable):

    def __init__(self, clk_freq, min_refresh_freq=100, pwm_width=8):
        self.clk_freq = clk_freq
        self.min_refresh_freq = min_refresh_freq
        self.pwm_width = pwm_width

        self.segment_patterns = Array((Signal(7), Signal(7)))
        self.pwm = Signal(pwm_width)
        self.digit_sel = Signal()
        self.seg7 = Record([
            ('segs', 7),
            ('digit', 1),
        ])

        self.ports = (self.pwm, self.digit_sel)
        self.ports += tuple(self.segment_patterns)
        self.ports += tuple(self.seg7._lhs_signals())

    def elaborate(self, platform):
            counter_max0 = int(self.clk_freq / self.min_refresh_freq)
            counter_max = (1 << counter_max0.bit_length()) - 1
            counter_width = counter_max.bit_length()
            assert counter_width > self.pwm_width

            counter = Signal(counter_width)
            digit = Signal()
            cmp = Signal(self.pwm_width)
            on = Signal()

            m = Module()
            m.d.sync += [
                counter.eq(counter + 1),
            ]
            m.d.comb += [
                digit.eq(counter[-1]),
                cmp.eq(counter[-1 - self.pwm_width:-1]),
                on.eq(cmp < self.pwm),
                self.digit_sel.eq(digit),
                self.seg7.digit.eq(~digit),
            ]
            with m.If(on):
                m.d.sync += [
                    self.seg7.segs.eq(~self.segment_patterns[digit]),
                ]
            with m.Else():
                m.d.sync += [
                    self.seg7.segs.eq(~0),
                ]
            return m


if __name__ == '__main__':
    design = SevenSegDriver(1_000_000, 60_000, pwm_width=2)
    with Main(design).sim as sim:
        @sim.sync_process
        def fade_proc():
            yield design.segment_patterns[0].eq(0x0A)
            yield design.segment_patterns[1].eq(0x05)
            for i in range(4):
                yield design.pwm.eq(i)
                yield from [None] * 32  # step 32 clocks
            yield
