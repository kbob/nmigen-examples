import sys

from nmigen import *
from nmigen.hdl.rec import *
from nmigen.back import pysim
from nmigen_boards.icebreaker import ICEBreakerPlatform



# LED and Parity are platform independent and simulatable.
# Top is platform-specific and not simulatable.

class LED(Elaboratable):
    def __init__(self):
        self.pin = Record([
            ('pin', 1, DIR_FANIN),
            ])
        self.enable = Signal()

    def elaborate(self, platform):
        m = Module()
        m.d.sync += self.pin.pin.eq(self.enable)
        return m


class Parity(Elaboratable):

    """Light an LED whenever parity is odd."""

    def __init__(self):
        self.inputs = Signal(2)
        self.led_pin = Record([
            ('pin', 1, DIR_FANIN),
        ])

    def elaborate(self, platform):
        parity = Signal()
        m = Module()
        led = LED()
        m.submodules += [led]
        self.led_pin.connect(led.pin)
        m.d.comb += [
            parity.eq(self.inputs[0] ^ self.inputs[1]),
            led.enable.eq(parity),
            # self.led_pin.eq(led.pin),
        ]
        return m


class Top(Elaboratable):

    """connect an LED to two buttons."""

    def elaborate(self, platform):
        import pprint
        pprint.pprint(platform.resources)
        exit()
        spi = platform.request('spi_flash_1x', 0)
        print(spi)
        exit()
        led_pin = platform.request('led')
        print(f'platform led = {led_pin}')
        btn0 = platform.request('button', 0)
        btn1 = platform.request('button', 1)
        m = Module()
        par = Parity()
        m.submodules += [par]
        m.d.comb += [
            par.inputs.eq(Cat((btn0, btn1))),
            led_pin.eq(par.led_pin)
        ]
        return m


def simulate():
    design = Parity()
    with pysim.Simulator(design,
                         vcd_file=open('foo.vcd', 'w'),
                         gtkw_file=open('foo.gtkw', 'w'),
                         traces=(design.inputs, )) as sim:
        @sim.add_sync_process
        def inputs_proc():
            yield; yield
            for i in range(4):
                print(i)
                yield design.inputs.eq(i)
                yield; yield
        sim.add_clock(1e-6)
        sim.run()

def build():
    design = Top()
    platform = ICEBreakerPlatform()
    platform.add_resources(platform.break_off_pmod)
    platform.build(design, do_program=False)

def main():
    if sys.argv[-1] == 'simulate':
        simulate()
    else:
        build()

main()
