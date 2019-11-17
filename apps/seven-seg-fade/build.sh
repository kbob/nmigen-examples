#!/bin/sh

NMIGEN_synth_opts=-dsp \
PYTHONPATH=../.. \
    nmigen seven-seg-fade.py
