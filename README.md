# nmigen-examples

I want to learn [n]Migen.

Verilog is awful, as you know.  There are a few newer HDLs to explore.
myHDL, Migen and nMigen, and SpinalHDL/Chisel.

Since I already know Python, it seems like nMigen is a good place to start.
nMigen is a reimplementation of Migen, and I guess Migen is on its way
to deprecation.  OTOH, nMigen is far from mature.

I want to understand whether and how nMigen makes it possible to
create abstractions that Verilog can't.

The Migen (not nMigen) manual has a nice section about dataflow programming
and "actors" -- it's not clear where that source actually lives, but it looks promising.


# Elaboratables and Modules and Domains

nMigen uses classes derived from `Elaboratable` to structure code.
I'm not sure about the Elaboratable name.  An Elaboratable has a
method, `elaborate`, which creates a `Module`.  The basic structure
of most `Elaboratable` classes is to declare the ports as data members
in `__init__`, then create everything else in `elaborate`.

A `Module` is the basic unit of a design.  A `Module`
maps to a Verilog module if you choose to generate Verilog.
A `Module` has:

 * one or more clock domains
 * the `comb` pseudo-domain for combinatorial logic
 * zero or more submodules.

Each submodule is not a `Module`; it is an `Elaboratable`.  So modules
and elaboratables are closely related.  (I really wish I understood
why the name is "elaboratable".)

Each domain has a clock signal, an optional reset signal, and a set
of logic statements.  The logic statements are implicitly executed
on each clock edge (rising edge by default).  Domains have global
scope by default.  By convention, the default clock domain is called
`sync`.  The reset signal is auto-generated.  It is present and
synchronous by default; either can be overriden in the `ClockDomain`
constructor.

So far, so good.  nMigen makes the clock and reset implicit, makes
multiple clock domains explicit.  That's a small improvement on Verilog.


# Project Organization

I think I need two sets of source files. One for modules that are not
tied to any specific platform, and one for systems(?) that tie
a platform to a set of top-level modules.

The non-platform bits should all be simulatable (and should have sim
built in), and the platform bit will not.  Therefore the platform bits
should be really small.


## Simulation

Building in minimal simulation is trivial:

```python
from nmigen.cli import main
if __name__ == '__main__':
    x = MyModule()
    main(x, ports.x.ports())
```

Then you simulate that module like this.

```sh
$ nmigen mymodule.py simulate -v mymodule.vcd -w mymodule.gtkw -c 1000
```

You can also do more complex stuff building in a test bench that sets up
specific conditions and looks for specific outputs.  There is also a unit
testing framework that I don't know much about.  I think it lets you run
a bunch of simulation runs on the same module.

nMigen also has `Assert`, `Assume`, and `Cover` keywords.  They
don't appear to be fully implemented yet.


## Directory organization

I dunno.  Presumably there will be several top level things and several
callable/includable modules, with some overlap.  I don't want the paths
to get weird, though.

    /
    /apps
    /apps/tricorder.py
    /apps/sonic_screwdriver.py
    /parts
    /parts/uart.py
    /parts/cordic.py

The problem is that tricorder needs to import ../uart.

Maybe

    /
    /tricorder.py
    /sonic_screwdriver.py
    /lib
    /lib/uart.py
    /lib/cordic.py

would be better.  Top level directory is a bunch of unrelated apps.

Or else I use a makefile/build script to put the parts into the path.

```Makefile
PYTHONPATH := ../lib

prog:
    nmigen tricorder.py program

.PHONY: prog
```

## How is Misoc organized?

I looked at [misoc](https://github.com/m-labs/misoc).  Misoc is
written in Migen, not nMigen, but it's still a useful example.

Misoc has a top level build script.  It sits in the root directory
and pulls other files in from subdirectories.

It also invokes `make` in a subshell to build from C and ASM.  But
the migen build appears to all take place in the make.py process.

I could create a script like that.  Invoke it like this, maybe.

```sh
$ nmigen make.py prog tricorder
```

I kind of like that.  It's a lot of work, though.


## How does Boneless do it?

Boneless is a tiny 16 bit CPU written in nMigen.  It is organized
as a Python module, and it has one example which instantiates it for
a specific iCE40 board.  It's very much the standard mechanism.

```Python
if __name__ == "__main__":
    design = BonelessDemo(firmware=Instr.assemble(firmware()))
    ICE40HX1KBlinkEVNPlatform().build(design, do_program=True)
```


## How does Glasgow do it?

Glasgow is a hardware Swiss army chainsaw tool.  It uses nMigen
implicitly -- when needed, it builds and installs an FPGA bitstream
as a side effect of whatever it's trying to do.
The build process is much more complicated than anything I want
to write.


## How am I going to do it?

The file layout will look like this, I think.

    /
    /README.md (this file)
    /apps
    /apps/tricorder
    /apps/tricorder/tricorder.py
    /apps/tricover/build.sh
    /apps/sonic-screwdriver
    /apps/sonic-screwdriver/sonic-screwdriver.py
    /apps/sonic-screwdriver/build.sh
    /lib
    /lib/uart.py
    /lib/cordic.py

The bulk of the code will be in /lib.  Each file will
have the usual CLI interface for generation and simulation.
Some will have more extensive simulation.

The apps in /apps will tie a program to a platform and bind
the ports to pins.  Each directory will have a build script;
its exact function is TBD.

That will get me started, I think.

# How to Use

There are two directories (as discussed ad nauseum above).  `lib` and `apps`.

In the `lib` directory, you can simulate a module or generate Verilog from it.
See the README in that directory.

The `apps` directory has a subdirectory for each app.  Each app
creates a complete FPGA bitstream for one platform and installs it.
(All my apps are for the iCEBreaker FPGA at present.)  There's only
one way to use it -- run `./build.sh`.  See the README.


## What's this nmigen command in the READMEs and build scripts?

That's a shell script I have in my path.  It invokes python in the
virtualenv where nmigen is installed.  My implementation is complicated &mdash;
you don't want to know.  It's more or less equivalent to this, though.

```sh
#!/bin/sh
export VIRTUAL_ENV=/path/to/nmigen/virtualenv
export PATH="$VIRTUAL_ENV/bin:$PATH"
unset PYTHONHOME
python ${1+"$@"}
```

I recommend putting a script like that in your path.
