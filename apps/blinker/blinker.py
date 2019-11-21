#!/usr/bin/env nmigen

from nmigen import *
from nmigen_boards.icebreaker import ICEBreakerPlatform

from nmigen_lib.blinker import Blinker


class Top(Elaboratable):

    def elaborate(self, platform):
        led = platform.request('user_led')
        m = Module()
        bink = Blinker(period=int(platform.default_clk_frequency))
        m.submodules += bink
        m.d.comb += led.eq(bink.led)
        return m


if __name__ == '__main__':
    platform = ICEBreakerPlatform()
    platform.build(Top(), do_program=True)
