from nmigen import Elaboratable, Module

from .endpoint import PipeInlet, PipeOutlet

class Pipeline(Elaboratable):

    def __init__(self, seq):
        self.seq = seq

    def elaborate(self, platform):
        m = Module()
        sink = None
        for source in self.seq:
            if sink is not None:
                outlets = find_outlets(source)
                if not outlets:
                    raise ValueError(f'{source} has no PipeOutlet members')
                inlets = find_inlets(sink)
                if not inlets:
                    raise ValueError(f'{sink} has no PipeInlet members')
                try:
                    outlet, inlet = best_match(outlets, inlets)
                except TypeError:
                    raise ValueError(
                        f'{sink} and {source} have no matching pipe endpoints'
                    )
                m.d.comb += outlet.flow_from(inlet)
            sink = source
        return m


def find_outlets(obj):
    if isinstance(obj, PipeOutlet):
        return [obj]
    return [
        member
        for member in obj.__dict__.values()
        if isinstance(member, PipeOutlet)
    ]

def find_inlets(obj):
    if isinstance(obj, PipeInlet):
        return [obj]
    return [
        member
        for member in obj.__dict__.values()
        if isinstance(member, PipeInlet)
    ]

def best_match(outlets, inlets):
    for o in outlets:
        for i in inlets:
            if o._spec == i._spec:
                return o, i
