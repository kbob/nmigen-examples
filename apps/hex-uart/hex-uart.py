#!/usr/bin/env nmigen

from nmigen import *
from nmigen.build import *
from nmigen_boards.icebreaker import ICEBreakerPlatform

from nmigen_lib import UARTRx, HexDisplay


class OneShot(Elaboratable):

    def __init__(self, duration):
        self.duration = duration
        self.trg = Signal()
        self.out = Signal()
        self.ports = (self.trg, self.out)

    def elaborate(self, platform):
        counter = Signal(range(-1, self.duration))
        m = Module()
        with m.If(self.trg):
            m.d.sync += [
                counter.eq(self.duration - 2),
                self.out.eq(True),
            ]
        with m.Elif(counter[-1]):
            m.d.sync += [
                self.out.eq(False),
            ]
        with m.Else():
            m.d.sync += [
                counter.eq(counter - 1),
            ]
        return m


class Top(Elaboratable):

    def elaborate(self, platform):
        clk_freq = platform.default_clk_frequency
        uart_baud = 9600
        uart_divisor = int(clk_freq // uart_baud)
        status_duration = int(0.1 * clk_freq)
        uart_pins = platform.request('uart')
        bad_led = platform.request('led_r', 0)
        good_led = platform.request('led_g', 0)
        seg7_pins = platform.request('seg7')


        m = Module()
        uart_rx = UARTRx(divisor=uart_divisor)
        recv_status = OneShot(duration=status_duration)
        err_status = OneShot(duration=status_duration)
        hex_display = HexDisplay(clk_freq, 100, 1)
        m.submodules += [uart_rx, recv_status, err_status]
        m.submodules.hex_display = hex_display
        m.d.comb += [
            uart_rx.rx_pin.eq(uart_pins.rx),
            recv_status.trg.eq(uart_rx.rx_rdy),
            good_led.eq(recv_status.out),
            err_status.trg.eq(uart_rx.rx_err),
            bad_led.eq(err_status.out),
            hex_display.i_data.eq(uart_rx.rx_data),
            seg7_pins.eq(hex_display.o_seg7),
        ]
        m.d.sync += [
            hex_display.i_pwm.eq(hex_display.i_pwm | uart_rx.rx_rdy),
        ]
        return m


if __name__ == '__main__':
    platform = ICEBreakerPlatform()
    conn = ('pmod', 1)
    platform.add_resources([
        Resource('seg7', 0,
            Subsignal('segs', Pins('1 2 3 4 7 8 9', conn=conn, dir='o')),
            Subsignal('digit', Pins('10', conn=conn, dir='o')),
        ),
    ])
    top = Top()
    platform.build(top, do_program=True)
