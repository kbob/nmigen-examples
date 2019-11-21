#!/usr/bin/env nmigen

from nmigen import *
from nmigen.build import *
from nmigen_boards.icebreaker import ICEBreakerPlatform

from nmigen_lib.buzzer import Buzzer
from nmigen_lib.i2s import I2SOut
from nmigen_lib.pll import PLL


class Top(Elaboratable):

    def elaborate(self, platform):
        i2s_pins = platform.request('i2s', 0)
        clk_pin = platform.request(platform.default_clk, dir='-')

        freq_in = platform.default_clk_frequency
        pll_freq = 24_000_000
        freq_in_mhz = freq_in / 1_000_000
        pll_freq_mhz = pll_freq / 1_000_000
        buzz_freq = 440 * 2**(-9/12)    # Middle C

        m = Module()
        pll = PLL(freq_in_mhz=freq_in_mhz, freq_out_mhz=pll_freq_mhz)
        i2s = I2SOut(pll_freq)
        buzzer = Buzzer(buzz_freq, i2s.sample_frequency)
        m.domains += pll.domain     # override the default 'sync' domain
        m.submodules += [pll, buzzer, i2s]
        m.d.comb += [
            pll.clk_pin.eq(clk_pin),
            buzzer.enable.eq(True),
            buzzer.ack.eq(i2s.ack),
            i2s.samples[0].eq(buzzer.sample),
            i2s.samples[1].eq(buzzer.sample),
            i2s.stb.eq(buzzer.stb),
            i2s_pins.eq(i2s.i2s),
        ]
        return m


if __name__ == '__main__':
    platform = ICEBreakerPlatform()
    platform.add_resources([
        Resource('i2s', 0,
            Subsignal('mclk', Pins('1', conn=('pmod', 0), dir='o')),
            Subsignal('lrck', Pins('2', conn=('pmod', 0), dir='o')),
            Subsignal('sck',  Pins('3', conn=('pmod', 0), dir='o')),
            Subsignal('sd',   Pins('4', conn=('pmod', 0), dir='o')),
        ),
    ])
    platform.build(Top(), do_program=True)
