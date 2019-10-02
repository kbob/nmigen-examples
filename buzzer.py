#!/usr/bin/env nmigen

from pprint import pprint

from nmigen import *
from nmigen.build.dsl import *
from nmigen.lib.cdc import ResetSynchronizer
from nmigen_boards.icebreaker import ICEBreakerPlatform

SAMPLE_RATE = 12_000_000 / 256
MIDDLE_C_Hz = 440 * 2**(-9 / 12)
INCR = round(2**16 * MIDDLE_C_Hz / SAMPLE_RATE)
# print('Fs', SAMPLE_RATE)
# print('Middle C', MIDDLE_C_Hz)
# print('INCR', INCR)


class PLL(Elaboratable):

    def __init__(self, domain_name='pll'):
        self.domain_name = domain_name
        self.domain = ClockDomain(self.domain_name)

    def elaborate(self, platform):

        clk_pin = platform.request('clk12', dir='-')
        pll_lock = Signal()
        pll = Instance("SB_PLL40_PAD",
            p_FEEDBACK_PATH='SIMPLE',
            p_DIVR=0,
            p_DIVF=63,
            p_DIVQ=5,
            p_FILTER_RANGE=0b001,

            i_PACKAGEPIN=clk_pin,
            i_RESETB=Const(1),
            i_BYPASS=Const(0),

            o_PLLOUTGLOBAL=ClockSignal(self.domain_name),
            o_LOCK=pll_lock)

        m = Module()
        m.submodules += pll
        m.submodules += ResetSynchronizer(~pll_lock, self.domain_name)
        return m


class Buzzer(Elaboratable):

    def __init__(self, i2s):
        self.i2s = i2s

    def elaborate(self, platform):
        mcnt = Signal(8)
        sample = Signal(16)

        m = Module()
        m.d.sync += [
            mcnt.eq(mcnt + 1),
        ]
        with m.If(mcnt == (1 << mcnt.nbits) - 1):
            m.d.sync += [
                sample.eq(sample + INCR),
            ]
        m.d.comb += [
            self.i2s.mclk.eq(mcnt[0]),
            self.i2s.sck.eq(mcnt[3]),
            self.i2s.lrck.eq(mcnt[3 + 4]),
            self.i2s.sdin.eq(sample.bit_select(15 - mcnt[3:3+4], 1)),
        ]
        return m


class Blinker(Elaboratable):

    def __init__(self, period):
        assert period % 2 == 0
        self.led = Signal()
        self.period = period

    @property
    def ports(self):
        return [self.led]

    def elaborate(self, platform):
        counter = Signal(self.period.bit_length())
        m = Module()
        with m.If(counter[-1]):
            m.d.sync += [
                counter.eq(self.period // 2 - 1),
                self.led.eq(~self.led),
            ]
        with m.Else():
            m.d.sync += [
                counter.eq(counter - 1),
            ]
        return m


class Top(Elaboratable):

    def elaborate(self, platform):
        led = platform.request('user_led')
        i2s = platform.request('i2s')

        m = Module()
        pll = PLL('sync')
        m.domains += pll
        m.submodules += pll
        m.submodules += Buzzer()
        m.submodules += Blinker(period=24_000_000)
        return m


class Unused:
    def elaborate(self, platform):
        ledg = platform.request('user_ledg')
        ledr = platform.request('user_ledr')
        i2s = platform.request('i2s', 0)
        mcnt = Signal(8)
        sample = Signal(16)

        m = Module()
        # pll = PLL()
        # sync_dest = m.d.pll
        pll = PLL('sync')
        sync_dest = m.d.sync
        m.submodules += pll
        m.domains += pll.domain
        sync_dest += [
            mcnt.eq(mcnt + 1),
        ]
        m.d.comb += [
            i2s.mclk.eq(mcnt[0]),
            i2s.sck.eq(mcnt[3]),
            i2s.lrck.eq(mcnt[3 + 4]),
            i2s.sdin.eq(sample.bit_select(15 - mcnt[3:3+4], 1)),
            ledg.eq(ClockSignal(pll.domain_name)),
        ]
        with m.If(mcnt == (1 << mcnt.nbits) - 1):
            sync_dest += [
                sample.eq(sample + INCR),
            ]

        count_max = 24_000_000
        counter = Signal(count_max.bit_length() + 1)
        with m.If(counter[-1]):
            sync_dest += counter.eq(count_max)
        with m.Else():
            sync_dest += counter.eq(counter - 1)
        m.d.comb += ledr.eq(counter[-2])

        return m


def assemble_platform():
    plat = ICEBreakerPlatform()
    plat.add_resources(plat.break_off_pmod)
    plat.add_resources([
        Resource('i2s', 0,
            Subsignal('mclk', Pins('1', conn=('pmod', 0), dir='o')),
            Subsignal('lrck', Pins('2', conn=('pmod', 0), dir='o')),
            Subsignal('sck',  Pins('3', conn=('pmod', 0), dir='o')),
            Subsignal('sdin', Pins('4', conn=('pmod', 0), dir='o')),
        ),
    ])
    return plat


# if __name__ == '__main__':
#     blink = Buzzer()
#     # main(blink, ports=[blink.led])
#     plat = assemble_platform()
#     # plat.build(blink)
#     plat.build(blink, do_program=True)

top = Top()
plat = assemble_platform()
plat.build(top, do_program=True)
