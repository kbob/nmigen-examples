from nmigen import Elaboratable, Module, Signal
from nmigen.back.pysim import Passive

from nmigen_lib.uart import UARTTx, UARTRx
from . import *
from nmigen_lib.util import Main, delay


class P_UART(Elaboratable):

    def __init__(self, divisor, data_bits=8):
        self.divisor = divisor
        self.data_bits = data_bits

        data_spec = PipeSpec(data_bits)

        self.tx_outlet = data_spec.outlet()
        self.rx_inlet = data_spec.inlet()

        self.tx_pin = Signal()
        self.rx_pin = Signal()
        self.rx_err = Signal()

    def elaborate(self, platform):
        m = Module()
        tx = P_UARTTx(self.divisor, self.data_bits, self.tx_outlet)
        rx = P_UARTRx(self.divisor, self.data_bits, self.rx_inlet)
        m.submodules.tx = tx
        m.submodules.rx = rx
        m.d.comb += [
            self.tx_pin.eq(tx.tx_pin),
            rx.rx_pin.eq(self.rx_pin),
        ]
        return m


class P_UARTTx(Elaboratable):

    def __init__(self, divisor, data_bits, outlet=None):
        if outlet is None:
            outlet = PipeSpec(data_bits).outlet()
        self.divisor = divisor
        self.data_bits = data_bits

        self.tx_pin = Signal()
        self.outlet = outlet

    def elaborate(self, platform):
        m = Module()
        tx = UARTTx(self.divisor, self.data_bits)
        m.submodules.tx = tx
        m.d.comb += [
            self.tx_pin.eq(tx.tx_pin),
            self.outlet.o_ready.eq(tx.tx_rdy),
            tx.tx_trg.eq(self.outlet.i_valid & self.outlet.o_ready),
            tx.tx_data.eq(self.outlet.i_data),
        ]
        return m


class P_UARTRx(Elaboratable):

    def __init__(self, divisor, data_bits=8, inlet=None):
        if inlet is None:
            inlet = PipeSpec(data_bits).inlet()
        self.divisor = divisor
        self.data_bits = data_bits

        self.rx_pin = Signal()
        self.inlet = inlet

    def elaborate(self, platform):
        m = Module()
        rx = UARTRx(self.divisor, self.data_bits)
        m.submodules.rx = rx
        m.d.comb += [
            rx.rx_pin.eq(self.rx_pin),
        ]
        with m.If(rx.rx_rdy):
            m.d.sync += [
                self.inlet.o_valid.eq(True),
                self.inlet.o_data.eq(rx.rx_data),
            ]
        with m.If(self.inlet.sent()):
            m.d.sync += self.inlet.o_valid.eq(False)
        return m


if __name__ == '__main__':
    divisor = 8
    design = P_UART(divisor=divisor)

    # Workaround nmigen issue #280
    m = Module()
    m.submodules.design = design
    i_ready = Signal()
    i_valid = Signal()
    i_data = Signal(8)
    m.d.comb += design.rx_inlet.i_ready.eq(i_ready)
    m.d.comb += design.tx_outlet.i_valid.eq(i_valid)
    m.d.comb += design.tx_outlet.i_data.eq(i_data)

    #280 with Main(design).sim as sim:
    with Main(m).sim as sim:

        @sim.sync_process
        def recv_char():
            char = 'Q'
            char = chr(0x95) # Test high bit
            yield design.rx_pin.eq(1)
            yield from delay(3)
            for i in range(3):
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
                char = chr(ord(char) + 1)

        @sim.sync_process
        def read_char():
            count = 0
            yield Passive()
            while True:
                valid = yield (design.rx_inlet.o_valid)
                if valid:
                    if not count:
                        count = 10
                if count:
                    count -= 1
                    if count == 1:
                        #280 yield design.rx_inlet.i_ready.eq(True)
                        yield i_ready.eq(True)
                else:
                    #280 yield design.rx_inlet.i_ready.eq(False)
                    yield i_ready.eq(False)
                yield

        @sim.sync_process
        def send_char():
            yield from delay(2)
            yield Passive()
            for char in 'QRS':
                #280 yield design.tx_outlet.i_data.eq(ord(char))
                #280 yield design.tx_outlet.i_valid.eq(True)
                yield i_data.eq(ord(char))
                yield i_valid.eq(True)
                yield
                while not (yield design.tx_outlet.o_ready):
                    yield
            #280 yield design.tx_outlet.i_valid.eq(False)
            yield i_valid.eq(False)
