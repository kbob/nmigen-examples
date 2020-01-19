#!/usr/bin/env nmigen

from nmigen import *
from nmigen.build import *
from nmigen_boards.icebreaker import ICEBreakerPlatform

from nmigen_lib import UARTRx, OneShot


class Top(Elaboratable):

    def elaborate(self, platform):
        clk_freq = platform.default_clk_frequency
        uart_baud = 9600
        uart_divisor = int(clk_freq // uart_baud)
        status_duration = int(0.1 * clk_freq)
        uart_pins = platform.request('uart')
        bad_led = platform.request('led', 0)
        good_led = platform.request('led', 1)
        digit_leds = [platform.request('led', i + 2)
                      for i in range(5)]

        m = Module()
        uart_rx = UARTRx(divisor=uart_divisor)
        recv_status = OneShot(duration=status_duration)
        err_status = OneShot(duration=status_duration)
        m.submodules += [uart_rx, recv_status, err_status]
        m.d.comb += [
            uart_rx.rx_pin.eq(uart_pins.rx),
            recv_status.i_trg.eq(uart_rx.rx_rdy),
            good_led.eq(recv_status.o_pulse),
            err_status.i_trg.eq(uart_rx.rx_err),
            bad_led.eq(err_status.o_pulse),
        ]
        with m.If(uart_rx.rx_rdy):
            m.d.sync += [
                digit_leds[i].eq(uart_rx.rx_data == ord('1') + i)
                for i in range(5)
            ]
        return m


if __name__ == '__main__':
    platform = ICEBreakerPlatform()
    platform.add_resources(platform.break_off_pmod)
    top = Top()
    platform.build(top, do_program=True)
