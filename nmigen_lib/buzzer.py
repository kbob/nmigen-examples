#!/usr/bin/env nmigen

import argparse

from nmigen import *
from nmigen_lib.util.main import Main

class Buzzer(Elaboratable):

    def __init__(self, frequency, sample_frequency):
        self.frequency = frequency
        self.sample_frequency = sample_frequency
        self.sample = Signal(signed(16))
        self.enable = Signal()
        self.stb = Signal()
        self.ack = Signal()
        self.ports = [self.enable, self.stb, self.ack, self.sample]

    def elaborate(self, platform):
        inc = round(2**16 * self.frequency / self.sample_frequency)
        # print(f'Buzzer: frequency = {self.frequency}')
        # print(f'Buzzer: sample_frequency = {self.sample_frequency}')
        # print(f'Buzzer: inc = {inc}')
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
    buzz_freq = 1_000
    samp_freq = 48_000
    clk_freq = 1_000_000
    sim_duration = 10 / buzz_freq
    design = Buzzer(buzz_freq, samp_freq)
    with Main(design).sim as sim:
        @sim.sync_process
        def ack_proc():
            strobed = False
            delay = round(clk_freq / samp_freq)
            yield design.ack.eq(True)
            yield design.enable.eq(True)
            acked = True
            yield
            for i in range(round(clk_freq * sim_duration)):
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
