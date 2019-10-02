#!/usr/bin/env nmigen

import argparse

from nmigen import *
from nmigen.back import verilog, pysim

class Buzzer(Elaboratable):

    def __init__(self, frequency, sample_frequency):
        self.frequency = frequency
        self.sample_frequency = sample_frequency
        self.sample = Signal((16, True))
        self.enable = Signal()
        self.stb = Signal()
        self.ack = Signal()
        self.ports = [self.enable, self.stb, self.ack, self.sample]

    def elaborate(self, platform):
        inc = round(2**16 * self.frequency / self.sample_frequency)
        print(f'Buzzer: frequency = {self.frequency}')
        print(f'Buzzer: sample_frequency = {self.sample_frequency}')
        print(f'Buzzer: inc = {inc}')
        m = Module()
        with m.If(self.ack):
            with m.If(self.enable):
                m.d.sync += [
                    self.sample.eq(self.sample + inc),
                ]
            with m.Else():
                m.d.sync += [
                    self.sample.eq(0),
                ]
            m.d.sync += [
                self.stb.eq(False),
            ]
        with m.Else():
            m.d.sync += [
                self.stb.eq(True),
            ]
        return m


if __name__ == '__main__':
    def cheap_parser():
        parser = argparse.ArgumentParser()
        p_action = parser.add_subparsers(dest='action')
        p_generate = p_action.add_parser('generate', help='generate Verilog')
        p_simulate = p_action.add_parser('simulate', help='simulate the design')
        return parser
    parser = cheap_parser()
    args = parser.parse_args()

    if args.action == 'generate':

        design = Buzzer(1_000, 48_000)
        fragment = Fragment.get(design, platform=None)
        print(verilog.convert(fragment, name='buzzer', ports=design.ports))

    elif args.action == 'simulate':

        clk_freq = 24_000_000
        samp_freq = 46_875
        buzz_freq = 261
        sim_clks = 50_000
        sim_duration = 10 / buzz_freq
        print('sim: clk_freq =', clk_freq)
        print('sim: sim_duration =', sim_duration)
        design = Buzzer(buzz_freq, samp_freq)
        with pysim.Simulator(design,
                vcd_file=open('buzzer.vcd', 'w'),
                gtkw_file=open('buzzer.gtkw', 'w'),
                traces=design.ports) as sim:

            @sim.add_sync_process
            def ack_proc():
                strobed = False
                delay = round(clk_freq / samp_freq)
                yield design.ack.eq(True)
                yield design.enable.eq(True)
                acked = True
                yield
                for i in range(round(clk_freq / sim_duration)):
                    if (yield design.stb):
                        strobed = True
                    if strobed and delay == 0:
                        yield design.ack.eq(True)
                        delay = round(clk_freq / samp_freq)
                        strobed = False
                        acked = True
                    elif acked:
                        yield design.ack.eq(False)
                        acked = False
                    if delay:
                        delay -= 1
                    yield

            sim.add_clock(1 / clk_freq)
            sim.run_until(sim_duration, run_passive=True)
