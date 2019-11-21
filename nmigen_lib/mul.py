from nmigen import *
from nmigen.asserts import *

from nmigen_lib.util.main import Main

class Mul(Elaboratable):

    def __init__(self, signed=False):
        self.multiplicand = Signal(Shape(16, signed))
        self.multiplier = Signal(Shape(16, signed))
        self.product = Signal(Shape(32, signed))
        self.ports = (self.multiplicand, self.multiplier, self.product)

    def elaborate(self, platform):
        m = Module()
        m.d.sync += [
            self.product.eq(self.multiplicand * self.multiplier)
        ]
        return m

if __name__ == '__main__':
    design = Mul()
    with Main(design).sim as sim:
        @sim.sync_process
        def inputs_proc():
            a = b = 0
            for i in range(100):
                yield design.multiplier.eq(a)
                yield design.multiplicand.eq(b)
                yield
                a += 19
                b += 97
