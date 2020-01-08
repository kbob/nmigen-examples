from nmigen import Elaboratable, Module, Record, Signal, Value
from nmigen import Shape, signed, unsigned
from nmigen.hdl.rec import Layout

from nmigen_lib.pipe import *
from nmigen_lib.pipe.endpoint import PipeInlet, PipeOutlet
from nmigen_lib.util import Main, delay

if __name__ == '__main__':

    def selftest():
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
        c0 = pi0.flow_to(ps0.outlet())
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
        c1 = ps1.outlet().flow_from(pi1)
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
        c2 = pi2.flow_to(po2)
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
        c3 = pi3.flow_to(po3)
        c3a = outlet_3.flow_from(inlet_3)
        assert len(c3) == 6
        assert len(c3a) == 6

    selftest()

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
            m.d.comb += src.data_out.flow_to(snk.data_in)
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
