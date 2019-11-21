#!/usr/bin/env nmigen

from nmigen import *
from nmigen.build import *
from nmigen_boards.icebreaker import ICEBreakerPlatform

from nmigen_lib.uart import UART


class CaseBender(Elaboratable):

    """Translate lowercase to uppercase, uppercase to lower."""

    def __init__(self):
        self.char_in = Signal(8)
        self.char_out = Signal(8)
        self.ports = (self.char_in, self.char_out)

    def elaborate(self, platform):

        m = Module()
        is_alpha = (self.char_in & 0xC0) == 0x40
        is_alpha &= (self.char_in & 0x1F) >= 1
        is_alpha &= (self.char_in & 0x1F) <= 26
        with m.If(is_alpha):
            m.d.comb += [
                self.char_out.eq(self.char_in ^ 0x20),
            ]
        with m.Else():
            m.d.comb += [
                self.char_out.eq(self.char_in)
            ]
        return m


class Top(Elaboratable):

    def elaborate(self, platform):
        clk_freq = platform.default_clk_frequency
        uart_baud = 9600
        uart_divisor = int(clk_freq // uart_baud)
        status_duration = int(0.1 * clk_freq)
        uart_pins = platform.request('uart')

        m = Module()
        uart = UART(divisor=uart_divisor)
        bender = CaseBender()
        m.submodules += [uart, bender]
        m.d.comb += [
            uart_pins.tx.eq(uart.tx_pin),
            bender.char_in.eq(uart.rx_data),
            uart.tx_data.eq(bender.char_out),
            uart.tx_trg.eq(uart.rx_rdy),
            uart.rx_pin.eq(uart_pins.rx),
        ]
        return m


if __name__ == '__main__':
    platform = ICEBreakerPlatform()
    platform.add_resources(platform.break_off_pmod)
    top = Top()
    platform.build(top, do_program=True)
