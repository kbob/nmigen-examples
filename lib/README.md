# Library Modules

So far, we have one.. blinker.  Blinks an LED (or other signal)
with a specified period.  Pretty simple.

## How to Use

```sh
$ # Generate Verilog source.
$ nmigen blinker.py generate > blinker.v
$
$ # Simulate and create .VCD trace.  (100 clock periods)
$ nmigen blinker.py simulate -v blinker.vcd -c 100
$ open blinker.vcd
```
