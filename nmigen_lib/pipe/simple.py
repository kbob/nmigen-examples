#!/usr/bin/env nmigen

from nmigen import Elaboratable, Module

from nmigen_lib.pipe import PipeSpec, START_STOP

# This code is an idea.  It does not run in current form.
# But boy would it make pipelining easy...
#
# A `SimpleStage` is a pipeline stage that can always compute one
# result from one input in a single clock.  It has no state
# or external timing dependencies.
#
# Example:
#   into_a = PipeSpec(...)
#   a_to_b = PipeSpec(...)
#   b_to_c = PipeSpec(...)
#   out_of_c = PipeSpec(...)
#
#   class A(SimpleStage):
#
#       # set output `o` based on input `i`.  Handshake
#       # and flow control are provided.
#       def logic(self, m, i, o):
#           m.d.sync += o.eq(...)
#           m.d.comb += ...
#
#   class B(SimpleStage):
#
#       # control both logic and optional handshake signals
#       def logic_and_handshake(self, m, i, o):
#           m.d.sync += [
#               o.data.eq(...),
#               o.o_start.eq(...), # or whatever
#           ]
#
#   m.submodules.a = a = SimpleStage(into_a, a_to_b)
#   m.submodules.b = b = SimpleStage(a_to_b, b_to_c)
#   m.submodules.c = SimpleStage.sync_expr([o.eq(...), ...])
#
# And that's it.  The last one doesn't work, because the input and
# output pipespecs are not passed in, and because `o` is not bound
# in the expression.

# Here's another idea.
#
#   m.pipeline = pipeline = SimplePipeline.assemble(
#       PipeSpec(16),              # pipe takes unsigned(16) words
#       LogicStage(
#           lambda i, o: o.eq(some_function(i))
#       ),
#       PipeSpec(unsigned(12)),     # 1st stage passes unsigned(16) to 2nd
#       LogicAndHandshakeStage(
#           lambda i, o:
#               [
#                   o.o_data_size.eq(whatever),
#                   o.o_data.flag.eq(some_condition),
#                   o.o_data.word.eq(other_function(i)),
#               ]
#       ),
#       PipeSpec((('flag': 1), ('word', signed(8)), flags=DATA_SIZE)
#                               # pipe emits flag + 8-bit word + data_size.
#   )

class Decimator(Elaboratable):

    def __init__(self, cfg):
        ...
        self.samples_in = mono_sample_spec(cfg.osc_depth).outlet()
        self.samples_out = mono_sample_spec(cfg.osc_depth).inlet()

    def elaborate(self, platform):
        m = Module()
        N = self.M + 2
        assert _is_power_of_2(N)
        # kernel_RAM = Memory(width=COEFF_WIDTH, depth=N, init=kernel)
        m.submodules.kr_port = kr_port = kernel_RAM.read_port()
        sample_RAM = Memory(width=self.sample_depth, depth=N, init=[0] * N)
        m.submodules.sw_port = sw_port = sample_RAM.write_port()
        m.submodules.sr_port = sr_port = sample_RAM.read_port()

        roto_sample_spec = PipeSpec(
            (
                ('coeff', COEFF_SHAPE),
                ('sample', signed(sample_depth)),
            ),
            flags=START_STOP,
        )

        class RotorFIFO(Elaboratable):
            def elaborate(self):
                m = Module()
                # when samples_in and fifo not full: insert sample.
                # when samples_readable and out pipe not full:
                #     out pipe send {}
                #         o_data.coeff = kernel[c_index],
                #         o_data.sample = sample[...],
                #         o_start=c_index == 1,
                #         o_stop=c_index == ~0,
                #     }
                # when c_index == ~0:
                #     c_index = 1
                #     sr_index = start_index + R
                #     start_index += R
                # else:
                #     c_index += 1
                #     sr_index += 1
                return m


        m.submodules.rfifo = RotorFifo()
        m.submodules.pipe = SimplePipeline.assemble(
            roto_sample_spec,
            LogicModule(lambda m, i, o: o.eq(i.coeff * i.sample)),
            PipeSpec(signed(COEFF_WIDTH + sample_depth)),
            LogicAndHandshakeModule(
                lambda m, i, o: {
                    'sync': acc.eq(Mux(i_start, i_data, acc + i_data)),
                    'comb': o.o_data.eq(acc[shift:]),
                }
            ),
            PipeSpec(signed(sample_depth)),
            flags=START_STOP,
        )
        return m



class SimplePipeline(Elaboratable):

    @classmethod
    def assemble(cls, *args):
        assert len(args) % 2 == 1
        assert all(callable(a) for a in args[1::2])
        assert all(isinstance(s, PipeSpec) for s in args[::2])
        pline = cls()
        pline.inlet = args[0]
        pline.outlet = args[1]
        stages = args[1:-1:2]
        sources = args[:-2:2]
        sinks = args[2::2]
        for (src, stg, snk) in zip(sources, stages, sinks):
            # get name for stage
            # LogicStg()
            ...
        return pline

    def __init__(self):
        self.stages = []
        self.connector_specs = []

    # @property.setter
    # def inlet(self, spec):
    #     self.inlet_spec = spec
    #     self.data_in = spec.outlet()
    #     return self
    #
    # @property.setter
    # def outlet(self, spec):
    #     self.outlet_spec = spec
    #     self.data_out = spec.inlet()
    #     return self

    def data(self, data):
        self.elements.append(data)
        return self

    def logic_stage(self, logic):
        """logic may be:
              a callable
              an assignment (e.g. a.eq(b0))
              a list of assignments
              a dict that maps domain names to (list of) assignments
        """
        self.stages.append(logic)
        return self

    def logic_and_handshake_stage(self, logic):
        """logic may be a callable or a dict"""
        self.elements.append(logic)
        return self

    def elaborate(self, platform):
        ...


class SimpleStage(Elaboratable):

    def __init__(self, in_spec, out_spec):
        self.in_data = in_spec.outlet()
        self.out_data = out_spec.inlet()

    def elaborate(self, platform):
        m = Module()
        m.d.comb += self.in_data.o_ready.eq(~self.out_data.full())
        with m.If(self.in_data.received()):
            self.logic_and_handshake(m, self.in_data, self.out_data)
            m.d.sync += self.out_data.o_valid.eq(True)
        with m.Else():
            m.d.sync += self.out_data.o_valid.eq(False)
        return

    def logic_and_handshake(self, m, i, o):
        """default implementation.  Override to access handshake signals."""
        ...
        return self.logic(m, i.i_data, o.o_data)

    def logic(self, m, i, o):
        """Override with code that unconditionally computes o from i."""
        raise NotImplementedError()

    def elaborate(self, platform):
        m = Module()
        logic = self.logic_and_handshake(m, self.in_data, self.out_data)
        if isinstance(logic, dict):
            ...
        elif isinstance(logic, AST):
            ...
        return m

    # @classmethod
    # def sync_expr(cls, m, sync_exprs):
    #     """create a pipeline stage around one or more nMigen AST expressions"""
    #     class Anonymous(cls):
    #         def logic(self, m, i, o):
    #             m.d.sync += sync_exprs
    #     return Anonymous()


def LogicAndHandshakeStage(SimpleStage):

    def __init__(self, logic):
        super().__init__(None, None)
        self._logic = logic

    def logic_and_handshake(self, m, i, o):
        frag = self._logic
        if callable(frag):
            frag = frag(m, i, o)
        if isinstance(frag, (list, Assign)):
            m.d.sync += frag
        elif isinstance(frag, dict):
            for domain, frags in frag:
                m.d[domain] += frag
        else:
            raise TypeError('unknown logic_and_handshake {frag!r}')


if __name__ == '__main__':
    spec = PipeSpec(1)  # one bit of data
    # design = SimpleStage.sync_expr(o.eq(~i))
