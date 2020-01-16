#!/usr/bin/env nmigen

from nmigen import Elaboratable, Module, Signal

from nmigen_lib.util import Main, delay

from .digit_pattern import DigitPattern
from .driver import SevenSegDriver, Seg7Record

class HexDisplay(Elaboratable):

    def __init__(self, clk_freq, min_refresh_freq=100, pwm_width=8):
        self.clk_freq = clk_freq
        self.min_refresh_freq = min_refresh_freq
        self.pwm_width = pwm_width

        self.i_data = Signal(8)
        self.i_pwm = Signal(pwm_width)
        self.o_seg7 = Seg7Record()
        self.o_seg7.segs.reset = ~0
        self.o_seg7.digit.reset = ~0

    def elaborate(self, platform):
        m = Module()
        ones = DigitPattern()
        tens = DigitPattern()
        drv = SevenSegDriver(
            clk_freq=self.clk_freq,
            min_refresh_freq=self.min_refresh_freq,
            pwm_width=self.pwm_width,
        )
        m.submodules.ones = ones
        m.submodules.tens = tens
        m.submodules.drv = drv
        m.d.comb += [
            ones.digit_in.eq(self.i_data[:4]),
            tens.digit_in.eq(self.i_data[4:]),

            drv.pwm.eq(self.i_pwm),
            drv.segment_patterns[0].eq(ones.segments_out),
            drv.segment_patterns[1].eq(tens.segments_out),

            self.o_seg7.eq(drv.seg7),
        ]
        oo_seg7 = Signal(8)
        m.d.comb += oo_seg7.eq(self.o_seg7)
        return m


if __name__ == '__main__':
    clk_freq = 1e6
    clk_per_digit = 4
    refresh_freq = clk_freq / clk_per_digit
    pwm_width = 2
    pwm_count = 2**pwm_width
    design = HexDisplay(
        clk_freq=clk_freq,
        min_refresh_freq=refresh_freq,
        pwm_width=pwm_width,
    )

    with Main(design).sim as sim:

        @sim.sync_process
        def seg_proc():
            dig_to_seg = {
                0x0: 0b0111111,
                0x1: 0b0000110,
                0x2: 0b1011011,
                0x3: 0b1001111,
                0x4: 0b1100110,
                0x5: 0b1101101,
                0x6: 0b1111101,
                0x7: 0b0000111,
                0x8: 0b1111111,
                0x9: 0b1101111,
                0xA: 0b1110111,
                0xB: 0b1111100,
                0xC: 0b0111001,
                0xD: 0b1011110,
                0xE: 0b1111001,
                0xF: 0b1110001,
            }
            expected_segs_z1 = 127
            pw_z1 = 0
            for i in range(256):
                pw = i % pwm_count
                pw = 3
                yield design.i_data.eq(i)
                yield design.i_pwm.eq(pw)
                for j in range(clk_per_digit * pwm_count):
                    seg7 = yield design.o_seg7
                    actual_digit = (seg7 >> 7) ^ 1
                    actual_segs = (seg7 & 0x7F) ^ 0x7F
                    on_off = j % pwm_count < pw_z1
                    expected_digit = j >> pwm_width & 1
                    if on_off:
                        sel = (j >> pwm_width) & 1
                        assert sel in {0, 1}
                        dig = [i % 0x10, i // 0x10][sel]
                        expected_segs = dig_to_seg[dig]
                    else:
                        expected_segs = 0
                    # print(f'i={i} j={j} seg7={seg7:08b}')
                    # print(f'    expected '
                    #       f'digit = {expected_digit} '
                    #       f'segs = {expected_segs:07b}'
                    #       f' (was {expected_segs_z1:07b})')
                    # print(f'    actual   '
                    #       f'digit = {actual_digit} '
                    #       f'segs = {actual_segs:07b}')
                    # print()
                    assert actual_digit == expected_digit
                    # XXX This is not right.
                    # assert actual_segs == expected_segs_z1
                    yield
                    pw_z1 = pw
                    expected_segs_z1 = expected_segs
