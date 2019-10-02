#!/usr/bin/env nmigen

import itertools

from nmigen import *
from nmigen.build import ResourceError
from nmigen_boards.icebreaker import ICEBreakerPlatform


class Top(Elaboratable):

    def elaborate(self, platform):
        try:
            leds = []
            for i in itertools.count():
                leds.append(platform.request('user_led', i))

        except ResourceError:
            pass
        leds = Cat(led.o for led in leds)
        m = Module()
        m.d.comb += leds.eq(0)
        return m


if __name__ == '__main__':
    platform = ICEBreakerPlatform()
    platform.add_resources(platform.break_off_pmod)
    platform.build(Top(), do_program=True)
