from warnings import warn_explicit
import sys

from nmigen import Record, unsigned

from .desc import SignalDesc, SignalDirection


# There is no need to warn about unconnected pipes if the program crashes.
_silence_warnings = True
_old_excepthook = sys.excepthook
def _new_excepthook(type, value, traceback):
    _silence_warnings = True
    return _old_excepthook(type, value, traceback)
sys.excepthook = _new_excepthook


class _PipeEnd(Record):

    def __init__(self, spec, layout, src_loc_at=0, **kwargs):
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
        if not self._connected and not _silence_warnings:
            warn_explicit(
                f'{self.__class__.__name__} {self!r} was never connected',
                UnconnectedPipeEnd,
                **self._creation_context,
            )

    def connect_ends(self, source, sink):
        assert isinstance(source, PipeInlet), (
            f'connection source must be PipeInlet, not {type(source)}'
        )
        assert isinstance(sink, PipeOutlet), (
            f'connection sink must be PipeOutlet, not {type(sink)}'
        )
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
                (source._get_signal(desc), sink._get_signal(desc))
                for desc in spec.downstream_signals
            ] + [
                (sink._get_signal(desc), source._get_signal(desc))
                for desc in spec.upstream_signals
            ]
        ]

    def _ends_are_compatible(self, source, sink):
        # Take the easy way out for now.
        return source._spec == sink._spec

    def _get_signal(self, desc):
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

    class MockSpec:
        downstream_signals = [SignalDesc('a', unsigned(1))]
        upstream_signals = []

    spec = MockSpec()
    layout = (('a', 1), )
    i = PipeInlet(spec, (('o_a', 1), ))
    o = PipeOutlet(spec, (('i_a', 1), ))
    c = i.connect_to(o)
    assert repr(c) == '[(eq (sig i_a) (sig o_a))]'
