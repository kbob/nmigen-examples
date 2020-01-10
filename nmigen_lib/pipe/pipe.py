#!/usr/bin/env nmigen

"""

# **This module is obsolete.  It hasn't been removed because**
# **the doc hasn't been moved to the new API.**

Pipe -- unidirectional data transfer with handshaking.

Pipes provide a framework and set of conventions that allows modules
to pass data between them.  Using pipes, two modules can be connected
and synchronized without knowing much about each other.

Pipes are modeled on David Williams' [SpokeFPGA
pipes](https://davidthings.github.io/spokefpga/pipelines).  In
principle, they should be binary compatible with a shim to pack and
unpack the signals, though the API is different.

# The Data

A pipe transfers one record of data at a time in parallel.  The
data format is described by an nMigen `Record` and may contain
several pieces.

# The Handshake

The handshake protocol uses two signals,`ready` and `valid`.  When the
source is making data available, it stores it in the pipe's `data`
signal and sets `valid`.  When the sink can accept new data, it sets
`ready`.  Whenever the endpoints see that both `valid` and `ready`
were active at the same time, they know that a transfer is complete.
The sink must either use the data immediately or make a copy of it, as
the source may overwrite it on the next clock.

# Packets

A pipe may optionally group data into packets (aka messages or
frames).  When a pipe is created with the START_STOP flag, two signals
are created called `start` and `stop`.  The pipe implementation itself
does nothing with these signals; it is up to the source and sink to
interpret them as the first and last records in a packet.  See the
[the SpokeFPGA
documentation](https://davidthings.github.io/spokefpga/pipelines#start--stop)
for more info.

# Data Size

A pipe may optionally pass a `size` signal that describes how many
bits of the `data` field are valid.  Again, see [the SpokeFPGA
documentation](https://davidthings.github.io/spokefpga/pipelines#data-size).

# API

## Creating a pipe

The pipe constructor takes an nMigen Layout, Shape, or integer that
describes the data signal's layout.  A Shape or integer is coerced
to a Layout using nMigen's rules.

The constructor takes an optional `flags` argument.  When flags'
`DATA_SIZE` bit is set, the pipe has a `data_size` signal.  When the
`START_STOP` bit is set, the pipe has `start` and `stop` signals.

Here are examples.

    >>> a_layout = Layout(        # define a layout with two fields
    ...     ('command', 4),
    ...     ('operand', 8),
    ...     )
    >>> my_pipe = Pipe(a_layout)    # the payload is two fields.
    >>> my_pipe2 = Pipe(signed(16)) # payload is a signed int.
    >>> my_pipe3 = Pipe(16)         # payload is an unsigned int.
    >>> my_pipe4 = Pipe(7, flags=START_STOP | DATA_SIZE)
    >>>                             # enable both options

# Endpoints

A pipe has two endpoints, accessible through its `source_end` and
`sink_end` properties.  Each endpoint is an nMigen Record subtype,
and the signals can be accessed directly.  For clarity, the
signals are prefixed with `i_` for inputs and `o_` for outputs.
Signals that transmit data downstream use the `o_` prefix on
the source end and `i_` on the sink end.  Upstream signals
use the opposite convention.

Currently, the only upstream signal is `ready`.  The source
endpoint's signal is called `i_ready`, and the sink endpoint's
signal is called `o_ready`.

The source endpoint's `sent` method tests whether a transfer has
occurred.

    >>> my_src = my_pipe.source_endpoint
    >>> with m.If(my_src.sent()):
    ...     # transfer happened.  `o_data` may be loaded with next data.

Similarly, the sink endpoint has a `received` method.

    >>> my_sink = my_pipe.sink_endpoint
    >>> with m.If(my_sink.received()):
    ...     # transfer happened.  Use or copy `i_data` now.

# Making the Connection

A pipe's endpoints must be connected before it works.  This is done in
the combinatoric domain.  Somewhere, probably close to the pipe's
constructor, connect the pipe with this code.

    >>> m.d.comb += my_pipe.connection()

If a pipe is not connected, an `UnconnectedPipe` warning is raised
when the pipe is destroyed.

# TBD

Create a PipeSpec class analogous to SpokeFPGA's PipeSpec; convert
between PipeSpec and int, and create Pipe from PipeSpec (or int).
Mostly for SpokeFPGA compatibility.

SpokeFPGA pipes have a bunch of optional features that we don't --
bidirectional data; command, request, and response fields; and
maybe more.
"""


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
