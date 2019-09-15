#!/bin/sh

for i
do
    {
        echo 'read_ilang <<XXX'
        cat "$i"
        echo 'XXX'
        echo proc_init
        echo proc_arst
        echo proc_dff
        echo proc_clean
        echo memory_collect
        echo write_verilog -norename
    } | yosys -q -
done
