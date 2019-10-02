# Applications

These are trivial but complete applications ready to be loaded onto an
iCEBreaker FPGA.

 * **blinker** - blink one LED at one Hertz.<br>
   Demonstrates the Blinker module.

 * **pll-blinker** - drive two LEDs from a phase-locked loop.<br>
   Demonstrates the PLL and Blinker modules.
   One LED blinks at 1 Hz, and the other blinks at 5 Hz.

 * **off** - turn the freq'ing LEDs off.
   They are distracting!

 * **buzzer** - make buzzing sound an I2S interface.<br>
   Demonstrates the I2SOut and SimpleSaw modules.
   This demo requires an I2S interface on PMOD 1A.  A Digilent [I2S
   (retired)](https://store.digilentinc.com/pmod-i2s-stereo-audio-output-retired/)
   or
   [I2S2](https://store.digilentinc.com/pmod-i2s2-stereo-audio-input-and-output/)
   PMOD works.  See Digilent's documentation for
   [pinout](https://reference.digilentinc.com/reference/pmod/pmodi2s/start).

# How to Use

```sh
$ cd $app
$ ./build.sh
$ # app is built and FPGA is flashed.
```
