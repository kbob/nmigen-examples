# nmigen-examples

I want to learn [n]Migen.

Verilog is awful, as you know.  There are a few newer HDLs to explore.
myHDL, Migen and nMigen, and SpinalHDL/Chisel.

Since I already know Python, it seems like nMigen is a good place to
start. nMigen (new Migen) is a reimplementation of Migen, and I guess
Migen is on its way to deprecation.  OTOH, nMigen is far from mature.

I want to understand whether and how nMigen makes it possible to create
abstractions that Verilog can't.


# Extremely basic nMigen

nMigen is a Python library that implements a hardware description
language (HDL). You describe hardware using nMigen's Python extensions,
then nMigen can simulate your design, emit your design as Verilog, or
synthesize it for an FPGA and optionally load it onto an FPGA dev board.

More complex arrangements are possible -- nMigen is a Python library, so
it can be embedded into an arbitrary runtime.  Check out [the Glasgow
project](https://github.com/GlasgowEmbedded/glasgow) for an example that
uses nMigen to automatically generate and load FPGA functions on the
fly.


## nMigen program structure

An nMigen design is organized as a tree of modules, just like Verilog.
Each module has:

 * one or more clock domains
 * the `comb` pseudo-domain for combinatorial logic
 * zero or more submodules.

Modules are defined in classes derived from `Elaboratable`. Each
`Elaboratable` has a method called `elaborate`, which constructs and
initializes a `Module`.  (I don't understand why they're called
"elaboratable".  The word does not connote anything useful to me.)

Within the `elaborate` method, you create the `Module`, attach any clock
domains and submodules, and then add logic statements to the domains,
including the combinatoric pseudo-domain, `comb`.  By convention, the
default clock domain is called `sync`.  AFAIK there is nothing magical
about `sync` -- you could use any identifier.

Each domain has a clock signal, an optional reset signal, and a set of
logic statements.  The logic statements are implicitly bound to the
clock edge (rising edge by default); Instead of littering your code with
Verilog's `always @(posedge clk) ...`, you litter your code with
`m.d.sync += ...`. nMigen automatically generates code to initialize
signals on reset, and automatically gives signals a default reset value
of zero.

So that's a higher level than Verilog.  Clock and reset are implicit,
and clock domains are explicit.

TBD: The `Instantiate` class.

## nMigen's HDL

TBD: Start with the `Value` hierarchy, then explain operators,
assignment, and control flow.

Explain that you need to understand Python operator overloading and
context managers.


## nMigen Simulation

Building in minimal simulation is trivial.  Just drop this at the end of
a source file.

```python
from nmigen.cli import main
if __name__ == '__main__':
    x = MyModule()
    main(x, ports=x.ports)
```

Then you simulate that module like this.

```sh
$ nmigen mymodule.py simulate -v mymodule.vcd -w mymodule.gtkw -c 1000
```

You can also do more complex stuff building in a test bench that sets up
specific conditions and looks for specific outputs.  There is also a
unit testing framework that I don't know much about.  I think it lets
you run a bunch of simulation runs on the same module.

nMigen also has `Assert`, `Assume`, and `Cover` keywords.  They don't
appear to be fully implemented yet.

## nMigen and platforms

TBD.


# Repository Organization

There are two main subdirectories.  `lib` contains reusable modules.
They do not have any platform dependencies. `apps` contains top-level
modules that connect modules from `lib` together and bind them to the
pins of a specific package.

All of the apps here target the iCEBreaker platform with various PMOD
cards attached.


# How to Use

For reusable modules in the `lib` directory, you can simulate a module
or generate Verilog from it. See the README in that directory.

The `apps` directory has a subdirectory for each app.  Each app creates
a complete FPGA bitstream for one platform and downloads (uploads?) it.
(All my apps are for the iCEBreaker FPGA at present.)  There's only one
way to use it -- run `./build.sh`.  See `apps/README.md`.


## What's this nmigen command in the READMEs and build scripts?

That's a shell script I have in my path.  It invokes python in the
virtualenv where nmigen is installed.  My implementation is complicated
&mdash; you don't want to know.  It's more or less equivalent to this,
though.

```sh
#!/bin/sh
export VIRTUAL_ENV=/path/to/nmigen/virtualenv
export PATH="$VIRTUAL_ENV/bin:$PATH"
unset PYTHONHOME
python ${1+"$@"}
```

I recommend putting a script like that in your path.

# Misc.

## Enabling iCE40 DSP inference

By default, yosys does not infer DSP slices for multiplication.
(*i.e.*, it does not use DSPs to implement multiply ops.)

You can enable DSP inference by setting the `NMIGEN_synth_opts`
environment variable to `-dsp`.

```sh
$ NMIGEN_synth_opts=-dsp nmigen my-app.py
```
