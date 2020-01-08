from typing import NamedTuple, Union

from nmigen import Elaboratable, Module, Record, Shape, Signal, Value
from nmigen import signed, unsigned
from nmigen.hdl.rec import Layout

from nmigen_lib.util import Main, delay

from .desc import SignalDesc, SignalDirection
from .endpoint import PipeInlet, PipeOutlet


DATA_SIZE = 1 << 8
START_STOP = 1 << 9


class PipeSpec(NamedTuple):
    flags: int
    dsol: Union[Shape, Layout]

    @classmethod
    def new(cls, dswol, *, flags=0):
        """
        Create a PipeSpec.

        The first arg is either the width of the data signal, the `Shape`
        of the data signal, a `Layout` describing the data signal, or
        a tuple of tuples that nMigen can coerce into a `Layout`.

        The flags arg may include DATA_SIZE or START_STOP flags.
        """
        # dsol: data shape or layout
        # dwsol: data width, shape, or layout
        if isinstance(dswol, (Shape, int)):
            dsol = Shape.cast(dswol)
        else:
            dsol = Layout.cast(dswol)
        return cls(flags, dsol)

    @classmethod
    def from_int(cls, n):
        """
        Create a PipeSpec from a 32 bit integer for SpokeFPGA compatibility.
        """
        data_width = n & 0xFF
        flags = n & 0x300
        if n != data_width | flags:
            raise ValueError(f'invalid PipeSpec {n:\#x}')
        return cls.new(data_width, flags=flags)

    @property
    def as_int(self):
        """Convert a PipeSpec to a SpokeFPGA-compatible 32 bit integer."""
        return self.data_width | self.flags

    @property
    def data_width(self):
        return Record((('d', self.dsol), )).shape()[0]

    @property
    def data_size(self):
        return bool(self.flags & DATA_SIZE)

    @property
    def start_stop(self):
        return bool(self.flags & START_STOP)

    def inlet(self, **kwargs):
        return PipeInlet(
            self,
            Layout(
                (PipeInlet.prefices[dir] + name, shape)
                for (name, shape, dir) in self._signals()
            ),
            src_loc_at=1,
            **kwargs,
        )

    def outlet(self, **kwargs):
        return PipeOutlet(
            self,
            Layout(
                (PipeOutlet.prefices[dir] + name, shape)
                for (name, shape, dir) in self._signals()
            ),
            src_loc_at=1,
            **kwargs,
        )

    def _signals(self):
        # N.B., these need to be in the same order as SpokeFPGA uses.
        sigs = (
            SignalDesc('data', self.dsol),
        )
        if self.flags & DATA_SIZE:
            size_bits = (self.data_width + 1).bit_length()
            sigs += (
                SignalDesc('data_size', size_bits),
            )
        if self.flags & START_STOP:
            sigs += (
                SignalDesc('stop', 1),
                SignalDesc('start', 1),
            )
        sigs += (
            SignalDesc('valid', 1),
            SignalDesc('ready', 1, SignalDirection.UPSTREAM),
        )
        return sigs

    @property
    def payload_signals(self):
        def is_payload(name, shape, dir):
            return name not in {'ready', 'valid'}
        return self._filter_signals(is_payload)

    @property
    def handshake_signals(self):
        def is_handshake(name, shape, dir):
            return name in {'ready', 'valid'}
        return self._filter_signals(is_handshake)

    @property
    def upstream_signals(self):
        def is_upstream(name, shape, dir):
            return dir == SignalDirection.UPSTREAM
        return self._filter_signals(is_upstream)

    @property
    def downstream_signals(self):
        def is_downstream(name, shape, dir):
            return dir == SignalDirection.DOWNSTREAM
        return self._filter_signals(is_downstream)

    def _filter_signals(self, predicate):
        return tuple(
            sig
            for sig in self._signals()
            if predicate(sig.name, sig.shape, sig.direction)
        )


# Override the NamedTuple constructor the hard way.
_PipeSpec = PipeSpec
del PipeSpec

def PipeSpec(data_width_shape_or_layout, *, flags=0):
    return _PipeSpec.new(data_width_shape_or_layout, flags=flags)
PipeSpec.__doc__ = _PipeSpec.new.__doc__
PipeSpec.from_int = _PipeSpec.from_int
