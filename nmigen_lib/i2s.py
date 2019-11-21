#!/usr/bin/env nmigen

import argparse

from nmigen import *

from nmigen_lib.util.main import Main

class I2SOut(Elaboratable):

    """
    Inter-IC Sound (I2S) output.  Drives a Cirrus CS4344 converter.

    This module is hardcoded to two channels, 16 bit samples, 256X
    master clock.  The master clock runs at half the speed of the
    module's clock.  So the module should be clocked at a speed in
    the 16-64 MHz range.

        clock freq     sample freq
        ===========    ===========
        16.3840 MHz       32   KHz
        22.5792 MHz       44.1 KHz
        24.5760 MHz       48   KHz
        45.1584 MHz       88.2 KHz
        49.1520 MHz       96   KHz
        65.5360 MHz       128  KHz

    Intermediate frequencies are possible and are probably necessary
    when the hardware doesn't have a clock chosen specifically for I2S.

    Samples are flow controlled by two signals, `stb` and `ack`.  The
    source should assert `stb` when a stereo sample is available, and
    this module asserts `ack` when the sample has been consumed.

    sample[0] is left channel, and sample[1] is right channel.
    """

    def __init__(self, clk_freq):
        self.clk_freq = clk_freq
        self.i2s = Record([
            ('mclk', 1),
            ('lrck', 1),
            ('sck', 1),
            ('sd', 1),
        ])
        self.samples = Array((Signal(signed(16)), Signal(signed(16))))
        self.stb = Signal()
        self.ack = Signal()
        self.ports = [self.i2s.mclk, self.i2s.lrck, self.i2s.sck, self.i2s.sd]
        self.ports += [self.samples[0], self.samples[1], self.stb, self.ack]

    @property
    def sample_frequency(self):
        return self.clk_freq / 2 / 256

    def elaborate(self, platform):
        bitstream = Signal(32)
        mcnt = Signal(9)
        mclk = Signal()
        sck = Signal()
        sd = Signal()
        lrck = Signal()
        m = Module()
        m.d.sync += [
            mcnt.eq(mcnt + 1),
        ]
        with m.If((mcnt == 0x00F) & (self.stb == True)):
            m.d.sync += [
                # I2S bitstream is MSB first, so reverse bits here.
                bitstream.eq(Cat(self.samples[0][::-1], self.samples[1][::-1])),
                self.ack.eq(True),
            ]
        with m.Elif(mcnt == 0x00F):
            m.d.sync += [
                bitstream.eq(0),
                self.ack.eq(False),
            ]
        with m.Else():
            m.d.sync += [
                self.ack.eq(False),
            ]
        m.d.sync += [
            mclk.eq(mcnt[0]),
            sck.eq(mcnt[3]),
            sd.eq(bitstream.bit_select(mcnt[4:4+5] - 1, 1)),
            lrck.eq(mcnt[4 + 4]),
        ]
        m.d.comb += [
            self.i2s.mclk.eq(mclk),
            self.i2s.sck.eq(sck),
            self.i2s.sd.eq(sd),
            self.i2s.lrck.eq(lrck),
        ]
        return m


if __name__ == '__main__':
    design = I2SOut(24_000_000)
    with Main(design).sim as sim:
        @sim.sync_process
        def sample_gen_proc():
            left = 0; right = 100;
            for i in range(24):
                yield design.samples[0].eq(left)
                yield design.samples[1].eq(right)
                yield design.stb.eq(True)
                left += 3; right += 5
                while (yield design.ack) == False:
                    yield
                yield design.stb.eq(False)
                yield
