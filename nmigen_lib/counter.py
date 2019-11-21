#!/usr/bin/env nmigen

import argparse

from nmigen import *
from nmigen_lib.util.main import Main

class Counter(Elaboratable):

    """Count a fixed number of events.  Assert .stb every `period` events."""

    def __init__(self, period):
        assert isinstance(period, int)
        self.period = period
        self.trg = Signal()
        self.counter = Signal((period - 1).bit_length())
        self.stb = Signal()
        self.ports = [self.counter, self.trg, self.stb]

    def elaborate(self, platform):
        m = Module()
        with m.If(self.trg & (self.counter == self.period - 1)):
            m.d.sync += [
                self.stb.eq(True),
                self.counter.eq(0),
            ]
        with m.Else():
            m.d.sync += [
                self.stb.eq(False),
            ]
            with m.If(self.trg):
                m.d.sync += [
                    self.counter.eq(self.counter + 1),
                ]
        return m


if __name__ == '__main__':
    design = Counter(5)
    with Main(design).sim as sim:
        @sim.sync_process
        def sample_gen_proc():
            def is_prime(n):
                return n >= 2 and all(n % k for k in range(2, n))
            for i in range(40):
                yield design.trg.eq(not is_prime(i))
                yield


if __name__ == 'XXX__main__':
    def cheap_parser():
        parser = argparse.ArgumentParser()
        p_action = parser.add_subparsers(dest='action')
        p_generate = p_action.add_parser('generate', help='generate Verilog')
        p_simulate = p_action.add_parser('simulate', help='simulate the design')
        return parser
    parser = cheap_parser()
    args = parser.parse_args()

    if args.action == 'generate':

        design = Counter(5)
        fragment = Fragment.get(design, platform=None)
        print(verilog.convert(fragment, name='counter', ports=design.ports))

    elif args.action == 'simulate':

        design = Counter(5)
        with pysim.Simulator(design,
                vcd_file=open('counter.vcd', 'w'),
                gtkw_file=open('counter.gtkw', 'w'),
                traces=design.ports) as sim:

            @sim.add_sync_process
            def sample_gen_proc():
                def is_prime(n):
                    return n >= 2 and all(n % k for k in range(2, n))
                for i in range(40):
                    yield design.trg.eq(not is_prime(i))
                    yield

            sim.add_clock(1e-6)
            sim.run()
            # sim.add_clock(1 / design.clk_freq)
            # sim.run_until(0.0005, run_passive=True)
