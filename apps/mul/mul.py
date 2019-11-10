#!/usr/bin/env nmigen

from nmigen import *
from nmigen.cli import main
from nmigen_boards.icebreaker import ICEBreakerPlatform

class Mul(Elaboratable):

    def __init__(self):
        self.a = Signal((16, True))
        self.b = Signal((16, True))
        self.c = Signal((32, True))

    def elaborate(self, platform):

        m = Module()
        m.d.sync += [
            self.c.eq(self.a * self.b)
        ]
        return m


# if __name__ == '__main__':
#     mul = Mul()
#     main(mul, ports=[mul.a, mul.b, mul.c])
#     exit()

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

    platform = ICEBreakerPlatform()
    platform.add_resources(platform.break_off_pmod)
    platform.build(Top(), do_program=True)
