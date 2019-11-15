#!/bin/sh

NMIGEN_synth_opts=-dsp \
PYTHONPATH=../.. \
    nmigen seven_seg_fade.py
