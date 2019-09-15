# Applications

These are trivial but complete applications ready to be loaded onto an
iCEBreaker FPGA.

 * **blinker** - blink one LED at one Hertz.<br>
   Demonstrates the Blinker module.

 * **pll-blinker** - drive two LEDs from a phase-locked loop.<br>
   Demonstrates the PLL and Blinker modules.
   One LED blinks at 1 Hz, and the other blinks at 5 Hz.

# How to Use

```sh
$ cd $app
$ ./build.sh
$ # app is built and FPGA is flashed.
```
