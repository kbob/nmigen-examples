# Applications

These are trivial but complete applications ready to be loaded onto an
iCEBreaker FPGA.

 * **blinker** - blink one LED at one Hertz.<br>
   Library modules: `Blinker`

 * **pll-blinker** - drive two LEDs from a phase-locked loop.<br>
   Library modules: `PLL`, `Blinker`

   One LED blinks at 1 Hz, and the other blinks at 5 Hz.  Shows
   how to use the iCE40's PLL to create two clock domains.

 * **off** - turn the freq'ing LEDs off.

   They are distracting!

 * **buzzer** - make buzzing sound an I2S interface.<br>
   Library modules: `PLL`, `I2SOut`, `Buzzer`

   Makes a simple, continuous buzzer that sounds at 261 Hz (Middle C).

   This demo requires an I2S interface on PMOD 1A.  A Digilent [I2S
   (retired)](https://store.digilentinc.com/pmod-i2s-stereo-audio-output-retired/)
   or
   [I2S2](https://store.digilentinc.com/pmod-i2s2-stereo-audio-input-and-output/)
   PMOD works.  See Digilent's documentation for
   [pinout](https://reference.digilentinc.com/reference/pmod/pmodi2s/start).

 * **seven-seg-counter** - count on a seven segment display.<br>
   Library modules: `Timer`, `Counter`, `seven_segment.DigitPattern`,
   `seven_segment.Driver`

   Display a continuously running two digit counter
   on a seven segment display.

   This demo requires a seven segment display in PMOD 1B.
   A [1BitSquared PMOD 7 Segment
   Display](https://1bitsquared.com/collections/fpga/products/pmod-7-segment-display)
   works.

 * **seven-seg-fade** - fade a seven segment display with pwm.<br>
   Library modules: `Timer`, `Counter`, `seven_segment.DigitPattern`,
   `seven_segment.Driver`, `Mul`

   Display a continuously running counter whose brightness is
   proportional to the number displayed.

   As a cheap approximation to perceptual brightness, the PWM
   amount is proportional to the square of the counter value.

   This is also the first app that uses a DSP block.  The
   DSP computes the square of the counter (a simple multiply).
   Note that `build.sh` has an environment variable to enable
   DSP synthesis.

 * **receive-uart** - receive characters from UART.<br>
   Library modules: `UART`

   Receive characters from the FTDI UART.  Flashes the green and
   red LEDs to indicate good/bad reception.  When a digit 1-5
   is received, lights the corresponding LED on the breakaway PMOD.

   Connect to FTDI UART 1 at 9600 baud, 8 data bits, no parity,
   one stop bit.  To test the error code (red LED), use a faster
   baud rate.

   This demo requires the iCEBreaker break-off PMOD on connector
   PMOD 2.  The iCEBreaker ships with that PMOD attached.

 * **othercase-uart** - echo characters from UART.<br>
   Library modules: `UART`

   Receive characters from the FTDI UART and echo them.  Uppercase
   letters (US ASCII only) are echoed in lowercase, and lowercase
   letters are echoed in uppercase.

   The serial setup is the same as `receive_uart` above.


# How to Use

```sh
$ cd $app
$ ./build.sh
$ # app is built and FPGA is flashed.
```
