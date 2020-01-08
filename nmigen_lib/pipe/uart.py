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
        tx = P_UARTTx(divisor=self.divisor, data_bits=self.data_bits)
        rx = P_UARTRx(self.divisor, self.data_bits, self.rx_inlet)
        m.submodules.tx = tx
        m.submodules.rx = rx
        m.d.comb += [
            self.tx_pin.eq(tx.tx_pin),
            rx.rx_pin.eq(self.rx_pin),
        ]
        return m

class P_UARTTx(Elaboratable):

    def __init__(self, divisor, data_bits, inlet=None):
        self.tx_pin = Signal()
        ...

    def elaborate(self, platform):
        m = Module()
        ...
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
    m.d.comb += design.rx_inlet.i_ready.eq(i_ready)

    #280 with Main(design).sim as sim:
    with Main(m).sim as sim:

        @sim.sync_process
        def recv_char():
            char = 'Q'
            char = chr(0x95) # Test high bit
            yield design.rx_pin.eq(1)
            yield from delay(3)
            for i in range(2):
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
