# Ethernet Switch Readme

## Introduction

Github repository: https://github.com/corundum/ethernet-switch

This repository contains code for the implementation of a FPGA-based Ethernet switch written in Verilog. 

The main idea is to collect different pieces of code to generate different switching architectures for the conmutation of Ethernet frames. These architectures follow this diagram from the input ports to the output ports:

![Switch block diagram](docs/switch_block.svg)

It is currently in the prototyping phase and includes code for the following architectures:

* Input Queued (IQ): all files related to it end with *_iq (e.g. switch_iq.v or switch_crossbar_iq.v)

The most advanced design for the switch does not use suffixes for its files and folders (e.g. switch.v or switch_crossbar.v)

## Tests
Tests associated to each implementation can be run by setting up a virtual environment using **poetry** and the given poetry.lock and pyproject.toml files in the corresponding directory.

Just run `poetry shell` and then `poetry install`.

## Modules

### `switch`

Wrapper of the switch. Includes the switch_crossbar logic and other logic.

### `switch_crossbar`

Main logic of the implementation connecting all the different modules.

### `switch_iq`

Wrapper of the IQ switch. Includes the switch_crossbar logic and input FIFOs.

### `switch_crossbar_iq`

Main logic of the IQ switch implementation connecting the input and output ports. One arbiter is instantiated for each output port to handle the input-output wiring.
