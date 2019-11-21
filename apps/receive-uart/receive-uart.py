#!/usr/bin/env nmigen

from nmigen import *
from nmigen.build import *
from nmigen_boards.icebreaker import ICEBreakerPlatform

from nmigen_lib.uart import UARTRx


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
        bad_led = platform.request('user_led', 0)
        good_led = platform.request('user_led', 1)
        digit_leds = [platform.request('user_led', i + 2)
                      for i in range(5)]

        m = Module()
        uart_rx = UARTRx(divisor=uart_divisor)
        recv_status = OneShot(duration=status_duration)
        err_status = OneShot(duration=status_duration)
        m.submodules += [uart_rx, recv_status, err_status]
        m.d.comb += [
            uart_rx.rx_pin.eq(uart_pins.rx),
            recv_status.trg.eq(uart_rx.rx_rdy),
            good_led.eq(recv_status.out),
            err_status.trg.eq(uart_rx.rx_err),
            bad_led.eq(err_status.out),
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
