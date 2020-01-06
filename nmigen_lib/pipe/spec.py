from enum import Enum, auto
from typing import NamedTuple, Union
from warnings import warn_explicit
import sys

from nmigen import *
from nmigen.hdl.rec import Layout

from nmigen_lib.util import Main, delay


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
            **kwargs,
        )

    def outlet(self, **kwargs):
        return PipeOutlet(
            self,
            Layout(
                (PipeOutlet.prefices[dir] + name, shape)
                for (name, shape, dir) in self._signals()
            ),
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


class SignalDirection(Enum):
    UPSTREAM = auto()
    DOWNSTREAM = auto()


class SignalDesc(NamedTuple):
    name: str
    shape: Union[Layout, Shape]
    direction: SignalDirection = SignalDirection.DOWNSTREAM


class _PipeEnd(Record):

    def __init__(self, spec, layout, src_loc_at=1, **kwargs):
        super().__init__(layout, src_loc_at=src_loc_at + 1, **kwargs)
        self._spec = spec
        self._connected = False
        frame = sys._getframe(1 + src_loc_at)
        self._creation_context = {
            'filename': frame.f_code.co_filename,
            'lineno': frame.f_lineno,
            'source': self
        }

    def __del__(self):
        if not self._connected:
            warn_explicit(
                f'{self.__class__.__name__} {self!r} was never connected',
                UnconnectedPipeEnd,
                **self._creation_context,
            )

    def connect_ends(self, source, sink):
        assert not source._connected, (
            f'connecting already-connected pipe end {source}'
        )
        assert not sink._connected, (
            f'connecting already-connected pipe end {sink}'
        )
        source._connected = True
        sink._connected = True
        spec = source._spec
        assert self._ends_are_compatible(source, sink), (
            f'connecting incompatible pipes {spec} and {sink._spec}'
        )
        return [
            dst.eq(src)
            for (src, dst) in [
                (source.get_signal(desc), sink.get_signal(desc))
                for desc in spec.downstream_signals
            ] + [
                (sink.get_signal(desc), source.get_signal(desc))
                for desc in spec.upstream_signals
            ]
        ]

    def _ends_are_compatible(self, source, sink):
        # Take the easy way out for now.
        return source._spec == sink._spec

    def get_signal(self, desc):
        prefix = self.prefices[desc.direction]
        sig_name = prefix + desc.name
        return getattr(self, sig_name, None)


class PipeInlet(_PipeEnd):

    def sent(self):
        """True when data is sent on the current clock."""
        return self.i_ready & self.o_valid

    def connect_to(self, outlet):
        return self.connect_ends(self, outlet)

    prefices = {
        SignalDirection.UPSTREAM: 'i_',
        SignalDirection.DOWNSTREAM: 'o_',
    }


class PipeOutlet(_PipeEnd):

    def received(self):
        """true when data is received on current clock."""
        return self.o_ready & self.i_valid

    def connect_to(self, inlet):
        return self.connect_ends(inlet, self)

    prefices = {
        SignalDirection.UPSTREAM: 'o_',
        SignalDirection.DOWNSTREAM: 'i_',
    }

class UnconnectedPipeEnd(Warning):
    """A pipe end was instantiated but never connected."""

if __name__ == '__main__':
    ps0 = PipeSpec(8)
    assert ps0.data_width == 8
    assert ps0.flags == 0
    assert type(ps0.dsol) is Shape
    assert ps0.dsol == unsigned(8)
    assert ps0.start_stop is False
    assert ps0.data_size is False
    assert ps0.as_int == 8
    pi0 = ps0.inlet()
    assert isinstance(pi0, PipeInlet)
    assert isinstance(pi0, Record)
    assert isinstance(pi0, Value)
    assert pi0.o_data.shape() == unsigned(8)
    c0 = pi0.connect_to(ps0.outlet())
    assert len(c0) == 3
    assert repr(c0[0]) == '(eq (sig i_data) (sig pi0__o_data))'
    assert repr(c0[1]) == '(eq (sig i_valid) (sig pi0__o_valid))'
    assert repr(c0[2]) == '(eq (sig pi0__i_ready) (sig o_ready))'

    ps1 = PipeSpec(signed(5), flags=DATA_SIZE)
    assert ps1.data_width == 5
    assert ps1.flags == DATA_SIZE
    assert type(ps1.dsol) is Shape
    assert ps1.dsol == signed(5)
    assert ps1.start_stop is False
    assert ps1.data_size is True
    assert ps1.as_int == 256 + 5
    pi1 = ps1.inlet()
    assert isinstance(pi1, PipeInlet)
    assert isinstance(pi1, Record)
    assert isinstance(pi1, Value)
    assert pi1.o_data.shape() == signed(5)
    c1 = ps1.outlet().connect_to(pi1)
    assert len(c1) == 4

    ps2 = PipeSpec((('a', signed(4)), ('b', unsigned(2))), flags=START_STOP)
    assert ps2.data_width == 6
    assert ps2.flags == START_STOP
    assert type(ps2.dsol) is Layout
    assert ps2.dsol == Layout((('a', signed(4)), ('b', unsigned(2))))
    assert ps2.start_stop is True
    assert ps2.data_size is False
    assert ps2.as_int == 512 + 6
    pi2 = ps2.inlet()
    assert isinstance(pi2, PipeInlet)
    assert isinstance(pi2, Record)
    assert isinstance(pi2, Value)
    assert pi2.o_data.shape() == unsigned(4 + 2)
    po2 = ps2.outlet()
    assert isinstance(po2, PipeOutlet)
    assert po2.i_data.shape() == unsigned(4 + 2)
    c2 = pi2.connect_to(po2)
    assert len(c2) == 5

    ps3 = PipeSpec.from_int(START_STOP | DATA_SIZE | 10)
    assert ps3.data_width == 10
    assert ps3.flags == START_STOP | DATA_SIZE
    assert type(ps3.dsol) is Shape
    assert ps3.dsol == unsigned(10)
    assert ps3.start_stop is True
    assert ps3.data_size is True
    assert ps3.as_int == 512 + 256 + 10
    pi3 = ps3.inlet(name='inlet_3')
    assert isinstance(pi3, PipeInlet)
    assert isinstance(pi3, Record)
    assert isinstance(pi3, Value)
    assert pi3.o_data.shape() == unsigned(10)
    inlet_3 = ps3.inlet()
    po3 = ps3.outlet(name='outlet_3')
    outlet_3 = ps3.outlet()
    assert repr(pi3) == repr(inlet_3)
    assert repr(po3) == repr(outlet_3)
    assert repr(pi3.fields) == repr(inlet_3.fields)
    assert repr(po3.fields) == repr(outlet_3.fields)
    c3 = pi3.connect_to(po3)
    c3a = outlet_3.connect_to(inlet_3)
    assert len(c3) == 6
    assert len(c3a) == 6

    my_spec = PipeSpec(8)

    class TestSource(Elaboratable):

        def __init__(self):
            self.trigger = Signal()
            self.data_out = my_spec.inlet()

        def elaborate(self, platform):
            counter = Signal.like(self.data_out.o_data, reset=0x10)
            m = Module()
            m.d.comb += [
                self.data_out.o_data.eq(counter),
            ]
            with m.If(self.trigger):
                m.d.sync += [
                    self.data_out.o_valid.eq(True),
                ]
            with m.Else():
                m.d.sync += [
                    self.data_out.o_valid.eq(False),
                ]
            with m.If(self.data_out.sent()):
                m.d.sync += [
                    counter.eq(counter + 1),
                ]
            return m


    class TestSink(Elaboratable):

        def __init__(self):
            self.data_in = my_spec.outlet()
            self.data = Signal.like(self.data_in.i_data)

        def elaborate(self, platform):
            m = Module()
            with m.If(self.data_in.received()):
                m.d.sync += [
                    self.data.eq(self.data_in.i_data),
                    self.data_in.o_ready.eq(self.data[1]),
                ]
            with m.Else():
                m.d.sync += [
                    self.data_in.o_ready.eq(True)
                ]
            return m


    class Top(Elaboratable):

        def __init__(self):
            self.trigger = Signal()

        def elaborate(self, platform):
            m = Module()
            src = TestSource()
            snk = TestSink()
            m.submodules.source = src
            m.submodules.sink = self.sink = snk
            m.d.comb += src.data_out.connect_to(snk.data_in)
            # m.d.comb += my_pipe.connection()
            m.d.comb += src.trigger.eq(self.trigger)
            return m


    top = Top()
    with Main(top).sim as sim:
        @sim.sync_process
        def trigger_proc():
            trg = top.trigger
            for i in range(10):
                yield trg.eq(True)
                yield
                if i % 3:
                    yield trg.eq(False)
                    yield from delay((i + 1) % 3)
            yield trg.eq(False)
            yield from delay(3)
        @sim.sync_process
        def result_proc():
            expected = (
                0, 0, 0,
                0x10, 0x10, 0x10, 0x10,
                0x11, 0x11,
                0x12, 0x12, 0x12,
                0x13,
                0x14,
                0x15, 0x15, 0x15,
                0x16, 0x16,
            )
            for (i, e) in enumerate(expected):
                a = (yield top.sink.data)
                assert (yield top.sink.data) == e, (
                    f'tick {i}: expected {e:#x}, actual {a:#x}'
                )
                yield
