#!/usr/bin/env nmigen

import os

from nmigen import *
from nmigen.cli import main
from nmigen_boards.icebreaker import ICEBreakerPlatform

class Mul(Elaboratable):

    def __init__(self):
        self.a = Signal(signed(16))
        self.b = Signal(signed(16))
        self.c = Signal(signed(32))

    def elaborate(self, platform):

        m = Module()
        m.d.sync += [
            self.c.eq(self.a * self.b)
        ]
        return m


class Top(Elaboratable):

    def elaborate(self, platform):
        cnt = Signal(5)
        btn0 = platform.request('user_btn', 0)
        btn1 = platform.request('user_btn', 1)
        led = platform.request('user_led')
        mul = Mul()

        m = Module()
        m.submodules += mul
        m.d.sync += [
            cnt.eq(cnt + 1),
            mul.a.eq(mul.a << 1 | btn0),
            mul.b.eq(mul.b << 1 | btn1),
            led.eq(mul.c.bit_select(cnt, 1)),
        ]
        return m


if __name__ == '__main__':

    # Force Yosys to use DSP slices.
    os.environ['NMIGEN_synth_opts'] = '-dsp'

    platform = ICEBreakerPlatform()
    platform.add_resources(platform.break_off_pmod)
    platform.build(Top(), do_program=True)
