#!/usr/bin/env nmigen

"""
Pipe -- unidirectional data transfer with handshaking.

Pipes are a set of classes and conventions that allow modules to be
pass data between them.  Using pipes, two modules can be connected and
synchronized without knowing much about each other.

The simplest pipe is a BasicPipe.  It only transfers a handshake.
Two modules can use a BasicPipe to run in lockstep.

Next is the DataPipe.  DataPipe transfers a block of data all at once.
DataPipe is parameterized by the data type.  It can either be a
single word (or bit) or an nMigen Record.

A PacketPipe extends DataPipe by adding packet start and stop signals.
Transfers between a start and a stop are understood to be in the
same packet.  Transfers not bracketed by start and stop are
still permitted

A SizedPipe extends DataPipe by add

The Handshake

The two handshake signals are `ready` and `valid`.  When the source is
making data available, it sets `valid`.  When the sink can accept new
data, it sets `ready`.  Whenever the endpoints sees that both `valid`
and `ready` were active at the same time, they know that a transfer
is complete.  The sink must make a copy of the data, as the source
may overwrite it on the next clock.






Pipes are based on David Williams' SpokeFPGA pipes.  In principle,
they should be binary compatible with a shim to pack and unpack the
signals.

"""

# Pipe based on @davidthings' SpokeFPGA pipes

# Basic Pipe: VALID, READY signals.
#    VALID is controlled by the source.
#    READY is controlled by the sink (flows upstream)
#
# Either may be asserted at any time; a transfer happens
# during any clock where both are asserted.
#
# Properties overridden by subclasses:
#   .downstream_signals
#   .upstream_signals
#   .handshake_signals
#   .payload_signals
#
# Methods:
#   .connect(self, other)    # overrides Record
#   @staticmethod layout(...)

# Data Pipe: Adds DATA[] signal.
#    DATA[] is arbitrary data, may be a Record.

# PacketPipe: Adds beginning and end of packet flags.
#    START - this is the first word of a packet.
#    STOP  - this is the last word of a packet.
#
# It should be illegal to have two STARTs without an intervening STOP
# or a STOP that doesn't follow a START (possibly on the same clock).
#
# A data pipe can simulate a PacketPipe by always asserting START and STOP
# -- each word is its own packet.

# SizedPipe: Adds valid bit count to each word.

# What does the API look like?

# Create a pipe like this.
# >>> my_pipe = DataPipe(signed(16))
# or
# >>> my_pipe = DataPipe(Layout(('numerator', 8), ('denominator', 8)))
#
# Access endpoints.
# >>> my_output = my_pipe.source_end
# >>> my_input = my_pipe.sink_end
#
# Connect endpoints.
# >>> m.d.comb += my_pipe.connection()
#
# Source: send data
# >>> with m.If(my_output.sent()):
# ...     # send completes on this clock.
# ...     # otherwise, repease.
#
# Sink: receive data
# >>> with m.If(my_input.received()):
# ...     #
#
# Sink: receive data.
# >>> with m.If(my_input.receive()):
# ...     m.d.sync += my_data.eq(my_input.i_data)


from enum import Enum, auto
import sys
from typing import NamedTuple, Union
from warnings import warn_explicit

from nmigen import *
from nmigen import tracer
from nmigen.hdl.rec import *

from nmigen_lib.util import delay, Main


DATA_SIZE = 1 << 8
START_STOP = 1 << 9
REVERSE = 1 << 10

class UnconnectedPipe(Warning):
    pass


class SignalDirection(Enum):
    UPSTREAM = auto()
    DOWNSTREAM = auto()


class SignalDesc(NamedTuple):
    name: str
    shape: Union[Layout, Shape]
    direction: SignalDirection = SignalDirection.DOWNSTREAM


class PipeSourceEnd(Record):

    def __init__(self, layout, **kwargs):
        super().__init__(layout, **kwargs)

    def sent(self):
        """True when data is sent on the current clock."""
        return self.i_ready & self.o_valid

    def get_signal(self, desc):
        prefix = self.prefices[desc.direction]
        sig_name = prefix + desc.name
        return getattr(self, sig_name, None)

    prefices = {
        SignalDirection.UPSTREAM: 'i_',
        SignalDirection.DOWNSTREAM: 'o_',
    }


class PipeSinkEnd(Record):

    def __init__(self, layout, **kwargs):
        super().__init__(layout, **kwargs)

    def received(self):
        """true when data is received on current clock."""
        return self.o_ready & self.i_valid

    def get_signal(self, desc):
        prefix = self.prefices[desc.direction]
        sig_name = prefix + desc.name
        return getattr(self, sig_name, None)

    prefices = {
        SignalDirection.UPSTREAM: 'o_',
        SignalDirection.DOWNSTREAM: 'i_',
    }


class Pipe:

    def __init__(self,
        shape_or_layout,
        *,
        name=None,
        flags=0,
        result_size=0,
        command_size=0,
        request_size=0,
        src_loc_at=0,
    ):
        if flags & REVERSE:
            raise NotImplementedError('reverse pipe not implemented')
        if request_size:
            raise NotImplementedError('pipe request not implemented')
        if result_size:
            raise NotImplementedError('pipe result not implemented')
        if command_size:
            raise NotImplementedError('pipe command not implemented')
        if name is None:
            name = tracer.get_var_name(depth=2 + src_loc_at, default='$pipe')
        self._data_layout = shape_or_layout
        self._name = name
        self._flags = flags
        self._result_size = result_size
        self._command_size = command_size
        self._request_size = request_size
        self._src_loc_at = src_loc_at
        self._connected = False
        frame = sys._getframe(1 + src_loc_at)
        self._creation_context = {
            'filename': frame.f_code.co_filename,
            'lineno': frame.f_lineno,
            'source': self
        }
        self._src_end = PipeSourceEnd(
            Layout(
                (PipeSourceEnd.prefices[dir] + name, shape)
                for (name, shape, dir) in self._signals()
            ),
            name='o_' + self._name,
        )
        self._snk_end = PipeSinkEnd(
            Layout(
                (PipeSinkEnd.prefices[dir] + name, shape)
                for (name, shape, dir) in self._signals()
            ),
            name='i_' + self._name,
        )

    def __del__(self):
        if not self._connected:
            warn_explicit(
                f'{self!r} was never connected',
                UnconnectedPipe,
                **self._creation_context,
            )

    def __repr__(self):
        return f'<{self.__class__.__name__} {self._name}>'

    @property
    def source_end(self):
        return self._src_end

    @property
    def sink_end(self):
        return self._snk_end

    def connection(self):
        self._connected = True
        source, sink = self.source_end, self.sink_end
        return [
            dst.eq(src)
            for (src, dst) in [
                (source.get_signal(desc), sink.get_signal(desc))
                for desc in self.downstream_signals
            ] + [
                (sink.get_signal(desc), source.get_signal(desc))
                for desc in self.upstream_signals
            ]
        ]

    def _signals(self):
        sigs = (
            SignalDesc('ready', 1, SignalDirection.UPSTREAM),
            SignalDesc('valid', 1),
            SignalDesc('data', self._data_layout),
        )
        if self._flags & DATA_SIZE:
            tmp = Record(self._data_layout)
            size_bits = (tmp.shape()[0] + 1).bit_length()
            sigs += (
                SignalDesc('data_size', size_bits),
            )
        if self._flags & START_STOP:
            sigs += (
                SignalDesc('start', 1),
                SignalDesc('stop', 1),
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


# class DataPipe(BasicPipe):
#
#     def _signals(self):
#         sigs = super()._signals()
#         sigs += (
#             SignalDesc('data', self._data_layout, SignalDirection.DOWNSTREAM),
#         )
#         return sigs
#
#     def __init__(self, layout, name=None, src_loc_at=0):
#         self._data_layout = layout
#         super().__init__(
#             name=name,
#             src_loc_at=src_loc_at + 1
#         )


if __name__ == '__main__':

    class TestSource(Elaboratable):

        def __init__(self, pipe):
            self.trigger = Signal()
            self.data_out = pipe.source_end

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

        def __init__(self, pipe):
            self.data = Signal.like(pipe.sink_end.i_data)
            self.data_in = pipe.sink_end

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
            my_pipe = Pipe(unsigned(8))
            m = Module()
            src = TestSource(my_pipe)
            snk = TestSink(my_pipe)
            m.submodules.source = src
            m.submodules.sink = self.sink = snk
            m.d.comb += my_pipe.connection()
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
