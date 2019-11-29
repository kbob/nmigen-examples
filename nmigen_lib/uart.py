#!/usr/bin/env nmigen

from nmigen import *

from nmigen_lib.util import delay
from nmigen_lib.util.main import Main


class UART(Elaboratable):

    def __init__(self, divisor, data_bits=8):
        self.divisor = divisor
        self.data_bits = data_bits

        self.tx_data = Signal(data_bits)
        self.tx_pin = Signal()
        self.tx_trg = Signal()
        self.tx_rdy = Signal()

        self.rx_pin = Signal(reset=1)
        self.rx_rdy = Signal()
        self.rx_err = Signal()
        # self.rx_ovf = Signal()  # XXX not used yet
        self.rx_data = Signal(data_bits)

        self.ports = (
                      self.tx_data,
                      self.tx_trg,
                      self.tx_rdy,
                      self.tx_pin,

                      self.rx_pin,
                      self.rx_rdy,
                      self.rx_err,
                      # self.rx_ovf,
                      self.rx_data,
                     )

    def elaborate(self, platform):
        m = Module()
        tx = UARTTx(divisor=self.divisor, data_bits=self.data_bits)
        rx = UARTRx(divisor=self.divisor, data_bits=self.data_bits)
        m.submodules += [tx, rx]
        m.d.comb += [
            tx.tx_data.eq(self.tx_data),
            tx.tx_trg.eq(self.tx_trg),
            self.tx_rdy.eq(tx.tx_rdy),
            self.tx_pin.eq(tx.tx_pin),

            rx.rx_pin.eq(self.rx_pin),
            self.rx_rdy.eq(rx.rx_rdy),
            self.rx_err.eq(rx.rx_err),
            # self.rx_ovf.eq(rx.rx_ovf),
            self.rx_data.eq(rx.rx_data),
        ]
        return m


### Currently, only receive is implemented.
class UARTTx(Elaboratable):

    def __init__(self, divisor, data_bits=8):
        self.divisor = divisor
        self.data_bits = data_bits
        self.tx_data = Signal(data_bits)
        self.tx_trg = Signal()
        self.tx_rdy = Signal()
        self.tx_pin = Signal(reset=1)
        self.ports = (
                      self.tx_data,
                      self.tx_trg,
                      self.tx_pin,
                      self.tx_rdy,
        )

    def elaborate(self, platform):
        tx_data = Signal(self.data_bits)
        tx_fast_count = Signal(range(-1, self.divisor - 1), reset=-1)
        tx_bit_count = Signal(range(-1, self.data_bits))

        m = Module()
        with m.If(tx_fast_count[-1]):
            with m.FSM():
                with m.State('IDLE'):
                    with m.If(self.tx_trg):
                        m.d.sync += [
                            tx_data.eq(self.tx_data),
                            self.tx_rdy.eq(False),
                            self.tx_pin.eq(0),  # start bit
                            tx_bit_count.eq(self.data_bits - 1),
                            tx_fast_count.eq(self.divisor - 2),
                        ]
                        m.next = 'DATA'
                    with m.Else():
                        m.d.sync += [
                            self.tx_rdy.eq(True),
                        ]
                with m.State('DATA'):
                    with m.If(tx_bit_count[-1]):
                        m.d.sync += [
                            self.tx_pin.eq(1),  # stop bit
                            tx_fast_count.eq(self.divisor - 2),
                        ]
                        m.next = 'STOP'
                    with m.Else():
                        m.d.sync += [
                            self.tx_pin.eq(tx_data[0]),
                            tx_data.eq(tx_data[1:]),
                            tx_bit_count.eq(tx_bit_count - 1),
                            tx_fast_count.eq(self.divisor - 2),
                        ]
                        m.next = 'DATA'
                with m.State('STOP'):
                    m.d.sync += [
                        # self.tx_pin.eq(1),
                        self.tx_rdy.eq(True),
                        tx_fast_count.eq(self.divisor - 2),
                    ]
                    m.next = 'IDLE'

        with m.Else():
            m.d.sync += [
                tx_fast_count.eq(tx_fast_count - 1),
            ]
        return m


class UARTRx(Elaboratable):

    def __init__(self, divisor, data_bits=8):
        """Assume no parity, 1 stop bit"""
        self.divisor = divisor
        self.data_bits = data_bits
        self.rx_pin = Signal(reset=1)
        self.rx_rdy = Signal()
        self.rx_err = Signal()
        # self.rx_ovf = Signal()  # XXX not used yet
        self.rx_data = Signal(data_bits)
        self.ports = (self.rx_pin,
                      self.rx_rdy,
                      self.rx_err,
                      # self.rx_ovf,
                      self.rx_data,
                     )

    def elaborate(self, platform):
        # N.B. both counters (rx_counter, rx_bits) count from n-2 to -1.
        rx_max = self.divisor - 2
        rx_counter = Signal(range(2 * (rx_max + 1)), reset=~0)
        rx_data = Signal(self.data_bits)
        rx_bits = Signal(range(2 * (self.data_bits - 1)))

        m = Module()
        with m.If(rx_counter[-1]):
            with m.FSM():
                with m.State('IDLE'):
                    with m.If(~self.rx_pin):
                        m.d.sync += [
                            rx_data.eq(0),
                            self.rx_rdy.eq(False),
                            self.rx_err.eq(False),
                            rx_counter.eq(self.divisor // 2 - 2),
                        ]
                        m.next = 'START'
                    with m.Else():
                        m.d.sync += [
                            self.rx_rdy.eq(False),
                            self.rx_err.eq(False),
                        ]
                        m.next = 'IDLE'
                with m.State('START'):
                    with m.If(self.rx_pin):
                        m.d.sync += [
                            self.rx_err.eq(True),
                            rx_counter.eq(self.divisor - 2),
                        ]
                        m.next = 'IDLE'
                    with m.Else():
                        m.d.sync += [
                            rx_bits.eq(self.data_bits - 2),
                            rx_counter.eq(self.divisor - 2),
                        ]
                        m.next = 'DATA'
                with m.State('DATA'):
                    new_bit = Signal(self.data_bits)
                    m.d.comb += new_bit[7].eq(self.rx_pin)
                    m.d.sync += [
                        # rx_data.eq(rx_data << 1 | self.rx_pin),
                        rx_data.eq(new_bit | rx_data >> 1),
                        rx_counter.eq(self.divisor - 2),
                    ]
                    with m.If(rx_bits[-1]):
                        m.next = 'STOP'
                    with m.Else():
                        m.d.sync += [
                            rx_bits.eq(rx_bits - 1),
                        ]
                        m.next = 'DATA'
                with m.State('STOP'):
                    with m.If(~self.rx_pin):
                        m.d.sync += [
                            self.rx_err.eq(True),
                            rx_counter.eq(self.divisor - 2),
                        ]
                        m.next = 'IDLE'
                    with m.Else():
                        m.d.sync += [
                            self.rx_data.eq(rx_data),
                            self.rx_rdy.eq(True),
                        ]
                        m.next = 'IDLE'
        with m.Else():
            m.d.sync += [
                rx_counter.eq(rx_counter - 1),
                self.rx_rdy.eq(False),
                self.rx_err.eq(False),
            ]
        return m


if __name__ == '__main__':
    divisor = 3
    design = UART(divisor=divisor)
    with Main(design).sim as sim:

        @sim.sync_process
        def send_char():
            char = 'Q'
            yield from delay(2)
            yield design.tx_data.eq(ord(char))
            yield design.tx_trg.eq(True)
            yield
            yield design.tx_trg.eq(False)
            yield from delay(10 * divisor + 2)

        @sim.sync_process
        def recv_char():
            char = 'Q'
            char = chr(0x95) # Test high bit
            yield design.rx_pin.eq(1)
            yield from delay(3)
            # Start bit
            yield design.rx_pin.eq(0)
            yield from delay(divisor)
            # Data bits
            for i in range(8):
                yield design.rx_pin.eq(ord(char) >> i & 1)
                yield from delay(divisor)
            # Stop bit
            yield design.rx_pin.eq(1)
            yield from delay(divisor)
            yield from delay(2)
