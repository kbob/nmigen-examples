#!/usr/bin/env nmigen

from nmigen import *
from nmigen.build import *
from nmigen_boards.icebreaker import ICEBreakerPlatform

from nmigen_lib.pipe import PipeSpec, Pipeline
from nmigen_lib.pipe.uart import P_UART


class CaseBender(Elaboratable):

    """Translate lowercase to uppercase, uppercase to lower."""

    def __init__(self):
        spec = PipeSpec(8)
        self.char_outlet = spec.outlet()
        self.char_inlet = spec.inlet()

    def elaborate(self, platform):

        m = Module()
        def is_alpha(c):
            return ((c & 0xc0) == 0x40) & (1 <= (c & 0x1F)) & ((c & 0x1F) <= 26)
        def other_case(c):
            return Mux(is_alpha(c), c ^ 0x20, c)
        m.d.comb += [
            self.char_inlet.o_valid.eq(self.char_outlet.i_valid),
            self.char_inlet.o_data.eq(other_case(self.char_outlet.i_data)),
            self.char_outlet.o_ready.eq(self.char_inlet.i_ready),
        ]
        return m


class Top(Elaboratable):

    def elaborate(self, platform):
        clk_freq = platform.default_clk_frequency
        uart_baud = 9600
        uart_divisor = int(clk_freq // uart_baud)
        uart_pins = platform.request('uart')

        m = Module()
        uart = P_UART(divisor=uart_divisor)
        bender = CaseBender()
        m.submodules.uart = uart
        m.submodules.bender = bender
        m.submodules.pipeline = Pipeline([uart, bender, uart])
        m.d.comb += [
            uart_pins.tx.eq(uart.tx_pin),
            uart.rx_pin.eq(uart_pins.rx),
        ]
        return m


if __name__ == '__main__':
    platform = ICEBreakerPlatform()
    platform.add_resources(platform.break_off_pmod)
    top = Top()
    platform.build(top, do_program=True)
