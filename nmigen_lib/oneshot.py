#!/usr/bin/env nmigen

from nmigen import Elaboratable, Module, Signal
from nmigen_lib.util import Main

class OneShot(Elaboratable):

    def __init__(self, duration):
        self.duration = duration
        self.i_trg = Signal()
        self.o_pulse = Signal()

    def elaborate(self, platform):
        counter = Signal(range(-1, self.duration - 1))
        m = Module()
        with m.If(self.i_trg):
            m.d.sync += [
                counter.eq(self.duration - 2),
                self.o_pulse.eq(True),
            ]
        with m.Elif(counter[-1]):
            m.d.sync += [
                self.o_pulse.eq(False),
            ]
        with m.Else():
            m.d.sync += [
                counter.eq(counter - 1),
            ]
        return m

if __name__ == '__main__':
    duration = 3
    design = OneShot(duration)

    # work aroun nMigen bug #280
    m = Module()
    m.submodules.design = design
    i_trg = Signal.like(design.i_trg)
    m.d.comb += [
        design.i_trg.eq(i_trg),
    ]
    #280 with Main(design).sim as sim:
    with Main(m).sim as sim:
        @sim.sync_process
        def test_proc():

            def set(value):
                #280 yield design.i_trg.eq(value)
                yield i_trg.eq(value)

            def chk(expected):
                actual = yield design.o_pulse
                assert actual == expected, f'wanted {expected}, got {actual}'

            def chk_n(expected, n):
                for _ in range(n):
                    yield from chk(expected)
                    yield

            try:
                # single pulse
                yield from chk_n(False, 1)
                yield from set(True)
                yield from chk_n(False, 1)
                yield from set(False)
                yield from chk_n(False, 1)
                yield from chk_n(True, duration)
                yield from chk_n(False, 1)

                # two overlapping pulses
                yield from set(True)
                yield from chk_n(False, 1)
                yield from set(False)
                yield from chk_n(False, 1)
                yield from chk_n(True, 1)
                yield from set(True)
                yield from chk_n(True, 1)
                yield from set(False)
                yield from chk_n(True, duration + 1)
                yield from chk_n(False, 1)

            except AssertionError:
                import traceback
                traceback.print_exc()
