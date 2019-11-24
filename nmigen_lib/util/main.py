import argparse
from collections import namedtuple
from contextlib import contextmanager
import inspect
import os.path
import warnings

from nmigen import *
from nmigen.hdl.ir import Fragment
from nmigen.back import rtlil, verilog, pysim

"""
An enhanced main patterned after nmigen.cli.main.

Has two actions: generate and simulate.

`generate` generates a Verilog or RTLIL source file from the given
module.  It has

  * By default, <design>.ports is used as the list of ports.

`simulate` runs pysim, but with differences:

  * By default, <design>.ports is used as the list of ports.

  * The `.vcd` and `.gtkw` files have the same basename
    as the module's source file by default.

  * The simulator can easily be extended by adding synchronous
    and asynchronous processes.

  * The simulator will run for either the number of clocks specified
    by the `--clocks=N` argument or until all defined processes
    have finished.

If you want the default simulator, instantiate like this.  In this
case, you must specify the `--clocks=N` argument to simulate.

    from nmigen_lib.util.main import main

    if __name__ == '__main__':
        design = MyModule(<args>)
        main(design)

If you want to add processes to the simulator, instantiate lik this.

    from nmigen_lib.util.main import Main

    if __name__ == '__main__':
        design - MyModule(<args>)
        with Main(design).sim as sim:
            @sim.add_sync_process
            def my_proc():
                ... # your logic here
"""

# default vcd and gtk files
# default run sim until procs exit
# default ports = module.ports
# way to add sim processes


class SimClock(namedtuple('SimClock', 'period phase domain if_exists')):
    pass

class SimSyncProc(namedtuple('SimSyncProc', 'process domain')):
    pass

class SimBuilder:

    def __init__(self, design, parse_args):
        self.design = design
        self.args = parse_args
        self.clocks = []
        self.procs = []
        self.sync_procs = []

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        return False

    def has_procs(self):
        return bool(self.procs or self.sync_procs)

    def has_clocks(self):
        return bool(self.clocks)

    def build(self, sim):
        for clock in self.clocks:
            sim.add_clock(**clock._asdict())
        for proc in self.procs:
            sim.add_process(proc)
        for sync_proc in self.sync_procs:
            sim.add_sync_process(*sync_proc)

    def add_clock(self, period, *,
                  phase=None, domain='sync', if_exists=False):
        self.clocks.append(SimClock(period, phase, domain, if_exists))

    # Use as decorator.
    def process(self, proc):
        self.procs.append(proc)
        return proc

    # Use as decorator.
    def sync_process(self, proc, domain='sync'):
        if proc is None:
            return lambda proc: self.sync_process(proc, domain)
        self.sync_procs.append(SimSyncProc(proc, domain))
        return proc


class Main:

    def __init__(self, design, platform=None, name='top', ports=()):
        self.design = design
        self.platform = platform
        self.name = name
        self.ports = ports
        self.args = self._arg_parser().parse_args()
        self._sim = SimBuilder(design, self.args)

    def run(self):
        if self.args.action == 'generate':
            self._generate()
        elif self.args.action == 'simulate':
            self._simulate()
        else:
            Elaboratable._Elaboratable__silence = True
            exit('main: must specify either `generate` or `simulate` action')

    @property
    @contextmanager
    def sim(self):
        ok = True
        try:
            yield self._sim
        except:
            ok = False
            raise
        finally:
            if ok:
                self.run()

    def _generate(self):
        args = self.args
        fragment = Fragment.get(self.design, self.platform)
        generate_type = args.generate_type
        if generate_type is None and args.generate_file:
            if args.generate_file.name.endswith(".v"):
                generate_type = "v"
            if args.generate_file.name.endswith(".il"):
                generate_type = "il"
        if generate_type is None:
            parser.error("specify file type explicitly with -t")
        if generate_type == "il":
            output = rtlil.convert(fragment,
                                   name=self.name, ports=self.ports)
        if generate_type == "v":
            output = verilog.convert(fragment,
                                     name=self.name, ports=self.ports)
        if args.generate_file:
            args.generate_file.write(output)
        else:
            print(output)

    def _simulate(self):
        args = self.args
        design_file = inspect.getsourcefile(self.design.__class__)
        prefix = os.path.splitext(design_file)[0]
        vcd_file = args.vcd_file or prefix + '.vcd'
        gtkw_file = args.gtkw_file = prefix + '.gtkw'
        with pysim.Simulator(self.design,
                vcd_file=open(vcd_file, 'w'),
                gtkw_file=open(gtkw_file, 'w'),
                traces=self.design.ports) as sim:
            self._sim.build(sim)
            if not self._sim.has_clocks():
                sim.add_clock(args.sync_period)
            if args.sync_clocks:
                sim.run_until(args.sync_period * args.sync_clocks,
                              run_passive=True)
            else:
                assert self._sim.has_procs(), (
                    "must provide either a sim process or --clocks"
                )
                sim.run()

    def _arg_parser(self, parser=None):
        if parser is None:
            parser = argparse.ArgumentParser()

        p_action = parser.add_subparsers(dest="action")

        p_generate = p_action.add_parser("generate",
            help="generate RTLIL or Verilog from the design")
        p_generate.add_argument("-t", "--type", dest="generate_type",
            metavar="LANGUAGE", choices=["il", "v"],
            default="v",
            help="generate LANGUAGE (il for RTLIL, v for Verilog; "
                 "default: %(default)s)")
        p_generate.add_argument("generate_file",
            metavar="FILE", type=argparse.FileType("w"), nargs="?",
            help="write generated code to FILE")

        p_simulate = p_action.add_parser(
            "simulate", help="simulate the design")
        p_simulate.add_argument("-v", "--vcd-file",
            metavar="VCD-FILE", type=argparse.FileType("w"),
            help="write execution trace to VCD-FILE")
        p_simulate.add_argument("-w", "--gtkw-file",
            metavar="GTKW-FILE", type=argparse.FileType("w"),
            help="write GTKWave configuration to GTKW-FILE")
        p_simulate.add_argument("-p", "--period", dest="sync_period",
            metavar="TIME", type=float, default=1e-6,
            help="set 'sync' clock domain period to TIME "
                 "(default: %(default)s)")
        p_simulate.add_argument("-c", "--clocks", dest="sync_clocks",
            metavar="COUNT", type=int,
            help="simulate for COUNT 'sync' clock periods")

        return parser

def main(design, platform=None, name='top', ports=()):
    Main(design, platform, name, ports).run()
