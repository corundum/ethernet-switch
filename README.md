# Ethernet Switch Readme

## Introduction

Github repository: https://github.com/corundum/ethernet-switch

This repository contains code for the implementation of a FPGA-based Ethernet switch written in Verilog. 

The main idea is to collect different pieces of code to generate different switching architectures for the conmutation of Ethernet frames. These architectures follow this diagram from the input ports to the output ports:

![Switch block diagram](docs/switch_block.svg)

It is currently in the prototyping phase and includes code for the following architectures:

* Input Queued (IQ): all files related to it end with *_iq (e.g. switch_iq.v or switch_crossbar_iq.v)
* Input Queued with Virtual Output Queueing (IQ with VOQ): all files related to it end with *_iq_voq (e.g. switch_iq_voq.v or switch_crossbar_iq_voq.v)

The most advanced design for the switch does not use suffixes for its files and folders (e.g. switch.v or switch_crossbar.v): currently corresponds to IQ with VOQ

None of the current switch designs support broadcasting.

## Tests
Tests associated to each implementation can be run by setting up a virtual environment using **poetry** and the given poetry.lock and pyproject.toml files in the corresponding directory.

Just run `poetry shell` and then `poetry install`.

## Benchmark
A command line interface (CLI) written in Python is provided to launch benchmark tests for the different switch architectures. The tool provides a command to generate **traffic** patterns which are based on individual frames defined by: input (arrival) port, output (destination) port and size in bytes. Currently, the size of the frame can be the same for each one or taken from a 
uniform distribution within a specified range. The traffic patern obtained is stored in a .txt (.csv). The **latency** command launches the benchmark for the selected switch architecture and traffic pattern. Options such as the radix of the switch or the width of the data bus can be configured. The results of the benchmark are stores in another file for further processing.

The main purpose of this benchmark is to test the performance for the different switch architectures implemented and compare them against each other.

## Modules

### `switch`

Wrapper of the switch. Includes the switch_crossbar logic and other logic. The tdest signal of AXI-Stream interface is currently used to handle the destination port of an incoming frame.

### `switch_crossbar`

Main logic of the implementation connecting all the different modules.

### `switch_iq`

Wrapper of the IQ switch. Includes the switch_crossbar logic and input FIFOs. The tdest signal of AXI-Stream interface is currently used to handle the destination port of an incoming frame.

### `switch_crossbar_iq`

Main logic of the IQ switch implementation connecting the input and output ports. One arbiter is instantiated for each output port to handle the input-output wiring.

### `switch_iq_voq`

Wrapper of the IQ with VOQ switch. Includes the switch_crossbar logic and VOQ FIFOs. The tdest signal of AXI-Stream interface is currently used to handle the destination port of an incoming frame.

### `switch_crossbar_iq_voq`

Main logic of the IQ with VOQ switch implementation connecting the VOQ FIFOs and output ports. One arbiter is instantiated for each output port to handle the input-output wiring.
