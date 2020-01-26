from warnings import warn_explicit
import sys

from nmigen import Record, unsigned

from .desc import SignalDesc, SignalDirection


# There is no need to warn about unconnected pipes if the program crashes.
_silence_warnings = False
_old_excepthook = sys.excepthook
def _new_excepthook(type, value, traceback):
    global _silence_warnings
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

    def leave_unconnected(self):
        assert not self._connected, (
            f'pipe endpoint {self} is already connected'
        )
        self._connected = True  # suppress warning

    @staticmethod
    def connect_ends(source, sink):
        assert isinstance(source, PipeInlet), (
            f'connection source must be PipeInlet, not {type(source)}'
        )
        assert isinstance(sink, PipeOutlet), (
            f'connection sink must be PipeOutlet, not {type(sink)}'
        )
        assert not source._connected, (
            f'connecting already-connected pipe inlet {source}'
        )
        assert not sink._connected, (
            f'connecting already-connected pipe outlet {sink}'
        )
        assert _PipeEnd._ends_are_compatible(source, sink), (
            f'connecting incompatible pipes {source._spec} and {sink._spec}'
        )
        source._connected = True
        sink._connected = True
        spec = source._spec
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

    @staticmethod
    def _ends_are_compatible(source, sink):
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

    def full(self):
        """True when receiver hasn't accepted last data."""
        return self.o_valid & ~self.i_ready

    def flow_to(self, outlet):
        return self.connect_ends(self, outlet)

    def leave_unconnected(self):
        super().leave_unconnected()
        self.i_ready.reset = 1      # Don't block senders

    prefices = {
        SignalDirection.UPSTREAM: 'i_',
        SignalDirection.DOWNSTREAM: 'o_',
    }


class PipeOutlet(_PipeEnd):

    def received(self):
        """true when data is received on current clock."""
        return self.o_ready & self.i_valid

    def flow_from(self, inlet):
        return self.connect_ends(inlet, self)

    prefices = {
        SignalDirection.UPSTREAM: 'o_',
        SignalDirection.DOWNSTREAM: 'i_',
    }


class UnconnectedPipeEnd(Warning):
    """A pipe end was instantiated but never connected."""
