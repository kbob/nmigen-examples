from nmigen import *

from lib.util import delay
from lib.util.main import Main


### Currently, only receive is implemented.
class UART(Elaboratable):

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
                    with m.If(rx_bits[-1]):
                        m.d.sync += [
                            rx_counter.eq(self.divisor - 2),
                        ]
                        m.next = 'STOP'
                    with m.Else():
                        new_bit = Signal(self.data_bits)
                        m.d.comb += new_bit[6].eq(self.rx_pin)
                        m.d.sync += [
                            # rx_data.eq(rx_data << 1 | self.rx_pin),
                            rx_data.eq(new_bit | rx_data >> 1),
                            rx_bits.eq(rx_bits - 1),
                            rx_counter.eq(self.divisor - 2),
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
        sim.add_clock(1 / 12e6)
        @sim.sync_process
        def recv_char():
            char = 'Q'
            yield design.rx_pin.eq(1)
            yield from delay(2)
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
