#!/usr/bin/env python
"""

Copyright (c) 2023 Carlos Megías Núñez

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
THE SOFTWARE.

"""

import itertools
import logging
import os
import codecs
import subprocess
import random
from pathlib import Path

import pytest
import cocotb_test.simulator

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge, Event
from cocotb.regression import TestFactory

from cocotbext.axi import AxiStreamBus, AxiStreamSource, AxiStreamSink, AxiStreamFrame
from cocotbext.axi.stream import define_stream


EthHdrBus, EthHdrTransaction, EthHdrSource, EthHdrSink, EthHdrMonitor = define_stream("EthHdr",
    signals=["hdr_valid", "hdr_ready", "dest_mac", "src_mac", "type"]
)


class TB:
    def __init__(self, dut):
        self.dut = dut

        self.radix = int(os.getenv("PARAM_RADIX"))

        self.log = logging.getLogger("cocotb.tb")
        self.log.setLevel(logging.DEBUG)

        cocotb.start_soon(Clock(dut.clk, 1, units="ns").start())

        self.source = [AxiStreamSource(AxiStreamBus.from_prefix(dut, f"s{k:02d}_axis"), dut.clk, dut.rst) for k in range(self.radix)]
        self.sink = [AxiStreamSink(AxiStreamBus.from_prefix(dut, f"m{k:02d}_axis"), dut.clk, dut.rst) for k in range(self.radix)]

    def set_idle_generator(self, generator=None):
        if generator:
            for source in self.source:
                source.set_pause_generator(generator())

    def set_backpressure_generator(self, generator=None):
        if generator:
            for sink in self.sink:
                sink.set_pause_generator(generator())

    async def reset(self):
        self.dut.rst.setimmediatevalue(0)
        await RisingEdge(self.dut.clk)
        await RisingEdge(self.dut.clk)
        self.dut.rst.value = 1
        await RisingEdge(self.dut.clk)
        await RisingEdge(self.dut.clk)
        self.dut.rst.value = 0
        await RisingEdge(self.dut.clk)
        await RisingEdge(self.dut.clk)

async def latency_test(dut, idle_inserter=None, backpressure_inserter=None):

    tb = TB(dut)
    tb.set_idle_generator(idle_inserter)
    tb.set_backpressure_generator(backpressure_inserter)

    # retrieve environment simulation parameters
    RADIX = int(os.getenv("RADIX"))
    bench_file = str(os.getenv("BENCH_FILE"))
    architecture = str(os.getenv("ARCHITECTURE"))
    data_width = str(os.getenv("DATA_WIDTH"))

    # additional hardware parameters
    USER_ENABLE= int(os.getenv("PARAM_AXIS_USER_ENABLE"))
    USER_WIDTH = int(os.getenv("PARAM_AXIS_USER_WIDTH")) 
    ID_ENABLE= int(os.getenv("PARAM_AXIS_ID_ENABLE"))
    ID_WIDTH = int(os.getenv("PARAM_AXIS_ID_WIDTH")) 
    DEST_ENABLE= int(os.getenv("PARAM_AXIS_DEST_ENABLE"))
    DEST_WIDTH = int(os.getenv("PARAM_AXIS_DEST_WIDTH")) 

    # use tid to univocally identify frames in simulation
    id_count = 2**ID_WIDTH
    id_mask = id_count-1

    src_width = (len(tb.source)-1).bit_length()
    src_mask = 2**src_width-1 if src_width else 0
    src_shift = ID_WIDTH-src_width
    max_count = 2**src_shift
    count_mask = max_count-1

    cur_id = 1

    await tb.reset()

    # Prepare main folder for results
    dir_file = f'latency/results'
    Path(dir_file).mkdir(parents=True, exist_ok=True)

    # prepare final output file
    bench_file_name = bench_file.split('/')
    output_file = f'{dir_file}/{architecture}-{data_width}-{bench_file_name[len(bench_file_name)-1]}'

    # temporal files to store frame data at the input and output AXIS
    tmp_gen = f'{dir_file}/tmp_gen.txt'
    tmp_in = f'{dir_file}/tmp_in.txt'
    tmp_out = f'{dir_file}/tmp_out.txt'

    # Load frames
    test_frames = [[list() for y in range(tb.radix)] for x in range(tb.radix)]
    # Altenative with events
    # test_frames_timed = [list() for x in range(tb.radix)]

    f_gen = open(tmp_gen, "a")

    with open(bench_file) as f:
        line = f.readline().strip('\n')
        line = f.readline().strip('\n')
        line = f.readline().strip('\n')
        while line:
            # parse traffic file
            line_list = line.split(",")
            input = int(line_list[0])
            output = int(line_list[1])
            length = int(line_list[2])

            test_data = bytearray(itertools.islice(itertools.cycle(range(256)), length))

            test_frame = AxiStreamFrame(test_data, tx_complete=tx_complete_source)
            # Altenative with events
            # test_frame = AxiStreamFrame(test_data, tx_complete=Event())

            tdest = [0 if (i!=output) else 1 for i in range(tb.radix)][::-1]
            tdest_int = int(''.join(map(str, tdest)), 2)
            test_frame.tdest = tdest_int

            test_frame.tid = cur_id | (input << src_shift)
            test_frame.tuser = length%(2**USER_WIDTH)

            test_frames[input][output].append(test_frame)
            # Altenative with events
            # test_frames_timed[input].append(test_frame)

            f_gen.write(f'{input},{output},{test_frame.tid}\n')

            await tb.source[input].send(test_frame)

            cur_id = (cur_id + 1) % max_count

            line = f.readline().strip('\n')

    f_gen.close()

    # Benchmarking

    # check if configuration already available
    try:
        # create files
        Path(output_file).touch(exist_ok=False)

        Path(tmp_out).touch(exist_ok=True)
        f = open(tmp_out, "a")

        # input port loop
        for input in test_frames:
            # while there are test frames to be received for that input port
            while any(input):
                # advance for next output
                lst_clean = [x for x in input if x]

                # identify the output port
                output = bin(lst_clean[0][0].tdest)[2:][::-1].index('1')
                rx_frame = await tb.sink[output].recv()
                
                f.write(f'{output},{rx_frame.sim_time_start},{rx_frame.sim_time_end},{rx_frame.tid}\n')

                test_frame = None

                for input_a in test_frames:
                    for output_a in input_a:
                        if output_a and output_a[0].tid == (rx_frame.tid & id_mask):
                            test_frame = output_a.pop(0)
                            break
                
                # Assertions
                assert test_frame is not None

                assert len(bytes(rx_frame)) == len(bytes(test_frame))
                assert rx_frame.tdata == test_frame.tdata
                assert bytes(test_frame) == bytes(rx_frame)

                if(USER_ENABLE):
                    assert rx_frame.tuser == test_frame.tuser
                if(ID_ENABLE):
                    assert rx_frame.tid == test_frame.tid
                if(DEST_ENABLE):
                    assert rx_frame.tdest == test_frame.tdest
        f.close()
        
        assert all(sink.empty() for sink in tb.sink)

        # Altenative with events: read all send events
        # for input in test_frames_timed:
        #     for test_frame in input:
        #         await test_frame.tx_complete.wait()
        #         print(test_frame.tx_complete.data.sim_time_start)

        # Prepare results
        f = open(output_file, "a")
        f.write(f'Architecture,{architecture},TrafficProfile,{bench_file}\n')
        f.write(f'Input,Output,StartTime,EndTime,DiffTime,ID\n')

        tid_pos_or = 3
        with open(tmp_in) as f_in, open(tmp_out) as f_out, open(tmp_gen) as f_gen: 
            # read files
            tmp_in_data = f_in.readlines()
            tmp_out_data = f_out.readlines()
            tmp_gen_data = f_gen.readlines()
            # sort files by tid
            tmp_in_list = sorted([[int(y) for y in x.strip('\n').split(",")] for x in tmp_in_data], key=lambda x: x[3])
            tmp_out_list = sorted([[int(y) for y in x.strip('\n').split(",")] for x in tmp_out_data], key=lambda x: x[3])
            tmp_gen_list = sorted([[int(y) for y in x.strip('\n').split(",")] for x in tmp_gen_data], key=lambda x: x[2])

            # write output file and perform some checks
            for line_in, line_out, line_gen in zip (tmp_in_list, tmp_out_list, tmp_gen_list):
                # check tid and output
                if((line_in[3] == line_out[3] and line_in[3] == line_gen[2]) and (line_in[0] == line_out[0] and line_in[0] == line_gen[1])):
                    f.write(f'{line_gen[0]},{line_in[0]},{int(line_in[1]/1000)},{int(line_out[2]/1000)},{int((line_out[2]-line_in[1])/1000)},{line_in[3]}\n')
                else:
                    print("Something went wrong: input and output files do not match")
                    break

        # delete temporal files
        os.remove(tmp_in)
        os.remove(tmp_out)
        os.remove(tmp_gen)

        f.close()

    except FileExistsError:
        print(f'Results already exists for {architecture} switch architecture with {bench_file} traffic profile.')
        return

def tx_complete_source(frame):
    print("Test")
    print(frame.sim_time_start)
    print(frame.tid[0])
    print(frame.tdest)
    # prepare folder and file
    dir_file = f'latency/results'
    Path(dir_file).mkdir(parents=True, exist_ok=True)
    tmp_in = f'{dir_file}/tmp_in.txt'
    Path(tmp_in).touch(exist_ok=True)

    output = bin(frame.tdest[0])[2:][::-1].index('1')

    f = open(tmp_in, "a")
    f.write(f'{output},{frame.sim_time_start},{frame.sim_time_end},{frame.tid[0]}\n')
    f.close()

def cycle_pause():
    return itertools.cycle([1, 0, 1, 1, 0])

def cycle_pause_one():
    return itertools.cycle([1, 1, 1, 1, 0])

def cycle_pause_two():
    return itertools.cycle([1, 0, 1, 1, 1])

def cycle_pause_three():
    return itertools.cycle([0, 0, 0, 1, 1])

# things to do within each run
if cocotb.SIM_NAME:

    factory = TestFactory(latency_test)
    # factory.add_option("idle_inserter", [None, cycle_pause])
    # factory.add_option("backpressure_inserter", [None, cycle_pause])
    factory.generate_tests()