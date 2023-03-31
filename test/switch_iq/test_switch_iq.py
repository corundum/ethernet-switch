#!/usr/bin/env python
"""

Copyright (c) 2023 Corundum organization

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

from scapy.layers.l2 import Ether, Dot1Q, DestMACField
from scapy.packet import Packet

import pytest
import cocotb_test.simulator

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge
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

async def run_test(dut, payload_lengths=None, payload_data=None, idle_inserter=None, backpressure_inserter=None, input=0, output=1):

    tb = TB(dut)

    await tb.reset()

    tb.set_idle_generator(idle_inserter)
    tb.set_backpressure_generator(backpressure_inserter)

    USER_ENABLE= int(os.getenv("PARAM_AXIS_USER_ENABLE"))
    USER_WIDTH = int(os.getenv("PARAM_AXIS_USER_WIDTH")) 
    ID_ENABLE= int(os.getenv("PARAM_AXIS_ID_ENABLE"))
    ID_WIDTH = int(os.getenv("PARAM_AXIS_ID_WIDTH")) 
    DEST_ENABLE= int(os.getenv("PARAM_AXIS_DEST_ENABLE"))
    DEST_WIDTH = int(os.getenv("PARAM_AXIS_DEST_WIDTH")) 

    test_frames = []
    payload_lengths_lite = [28]

    # frames loop
    for payload in [payload_data(x) for x in payload_lengths()]:
        test_frame = AxiStreamFrame(payload)

        tdest = [0 if (i!=output) else 1 for i in range(tb.radix)][::-1]
        tdest_int = int(''.join(map(str, tdest)), 2)
        test_frame.tdest = tdest_int

        test_frame.tuser = len(payload)%(2**USER_WIDTH)
        test_frame.tid = len(payload)%(2**ID_WIDTH)

        test_frames.append(test_frame)

    # Send frames
    for test_frame in test_frames:
        await tb.source[input].send(test_frame)

    for test_frame in test_frames:
        rx_frame = await tb.sink[output].recv()
        tb.log.info("RX packet: %s", repr(rx_frame))
        
        # Assertions
        assert len(bytes(rx_frame)) == len(bytes(test_frame))
        assert bytes(test_frame) == bytes(rx_frame)

        if(USER_ENABLE):
            assert rx_frame.tuser == test_frame.tuser
        if(ID_ENABLE):
            assert rx_frame.tid == test_frame.tid
        if(DEST_ENABLE):
            assert rx_frame.tdest == test_frame.tdest

        assert rx_frame.tdata == test_frame.tdata

    assert all(sink.empty() for sink in tb.sink)

    for i in range(14):
        await RisingEdge(dut.clk)

async def run_stress_test(dut, payload_lengths=None, payload_data=None, idle_inserter=None, backpressure_inserter=None):

    tb = TB(dut)

    await tb.reset()

    tb.set_idle_generator(idle_inserter)
    tb.set_backpressure_generator(backpressure_inserter)

    USER_ENABLE= int(os.getenv("PARAM_AXIS_USER_ENABLE"))
    USER_WIDTH = int(os.getenv("PARAM_AXIS_USER_WIDTH")) 
    ID_ENABLE= int(os.getenv("PARAM_AXIS_ID_ENABLE"))
    ID_WIDTH = int(os.getenv("PARAM_AXIS_ID_WIDTH")) 
    DEST_ENABLE= int(os.getenv("PARAM_AXIS_DEST_ENABLE"))
    DEST_WIDTH = int(os.getenv("PARAM_AXIS_DEST_WIDTH")) 

    # matrix of lists [rows, columns] -> [input, output]
    test_frames = [[list() for y in tb.radix] for x in tb.radix]

    # input port loop
    for input in range(tb.radix):
        # frames loop
        for k in range(128):
            length = random.randint(1, 128)
            test_data = bytearray(itertools.islice(itertools.cycle(range(256)), length))
            test_frame = AxiStreamFrame(test_data)

            output = random.randrange(len(tb.sink))
            tdest = [0 if (i!=output) else 1 for i in range(tb.radix)][::-1]
            tdest_int = int(''.join(map(str, tdest)), 2)
            test_frame.tdest = tdest_int

            test_frame.tuser = length%USER_WIDTH
            test_frame.tid = length%ID_WIDTH

            test_frames[input][output].append(test_frame)

    # Send frames
    # input port loop
    for input in range(tb.radix):
        # output port loop
        for output in range(tb.radix):
        # frames loop
            for test_frame in test_frames[input][output]:
                await tb.source[input].send(test_frame)

    for lst in test_frames:
        while any(lst):
            rx_frame = await tb.sink[[x for x in lst if x][0][0].tdest].recv()
            tb.log.info("RX packet: %s", repr(rx_frame))

            # input port loop
            for input in range(tb.radix):
                # output port loop
                for output in range(tb.radix):
                    if (bytes(rx_frame) == bytes(test_frames[input][output])):
                        test_frame = test_frames[input][output]
            
                        # Assertions
                        assert test_frame is not None

                        assert len(bytes(rx_frame)) == len(bytes(test_frame))
                        assert bytes(test_frame) == bytes(rx_frame)

                        if(USER_ENABLE):
                            assert rx_frame.tuser == test_frame.tuser
                        if(ID_ENABLE):
                            assert rx_frame.tid == test_frame.tid
                        if(DEST_ENABLE):
                            assert rx_frame.tdest == test_frame.tdest

                        assert rx_frame.tdata == test_frame.tdata

    assert all(sink.empty() for sink in tb.sink)

    for i in range(14):
        await RisingEdge(dut.clk)

def cycle_pause():
    return itertools.cycle([1, 0, 1, 1, 0])

def cycle_pause_one():
    return itertools.cycle([1, 1, 1, 1, 0])

def cycle_pause_two():
    return itertools.cycle([1, 0, 1, 1, 1])

def cycle_pause_three():
    return itertools.cycle([0, 0, 0, 1, 1])
    
def size_list():
    return list(range(1, 128)) + [512, 1514, 9214] + [60]*10

def incrementing_payload(length):
    return bytes(itertools.islice(itertools.cycle(range(256)), length))

# things to do within each run
if cocotb.SIM_NAME:

    RADIX = int(os.getenv("PARAM_RADIX"))

    factory = TestFactory(run_test)
    factory.add_option("payload_lengths", [size_list])
    factory.add_option("payload_data", [incrementing_payload])
    factory.add_option("idle_inserter", [None, cycle_pause, cycle_pause_one, cycle_pause_two, cycle_pause_three])
    factory.add_option("backpressure_inserter", [None, cycle_pause, cycle_pause_one, cycle_pause_two, cycle_pause_three])
    # factory.add_option("idle_inserter", [None, cycle_pause])
    # factory.add_option("backpressure_inserter", [None, cycle_pause])
    factory.add_option("input", range(RADIX))
    factory.add_option("output", range(RADIX))

    factory.generate_tests()

# cocotb-test

tests_dir = os.path.abspath(os.path.dirname(__file__))
rtl_dir = os.path.abspath(os.path.join(tests_dir, '..', '..', 'rtl'))
lib_dir = os.path.abspath(os.path.join(rtl_dir, '..', '..', 'lib'))
axis_rtl_dir = os.path.abspath(os.path.join(lib_dir, 'verilog-axis', 'rtl'))

# each run
@pytest.mark.parametrize("data_width", [8, 16, 32, 64, 128, 256, 512])
@pytest.mark.parametrize("radix", [4])
def test_switch_iq_wrap(request, data_width, radix):
    dut = "switch_iq"
    wrapper = f"{dut}_wrap_{radix}x{radix}"    
    module = os.path.splitext(os.path.basename(__file__))[0]
    toplevel = wrapper

    # generate wrapper
    wrapper_file = os.path.join(tests_dir, f"{wrapper}.v")
    if not os.path.exists(wrapper_file):
        subprocess.Popen(
            [os.path.join(rtl_dir, f"{dut}_wrap.py"), "-p", f"{radix}", f"{radix}"],
            cwd=tests_dir
        ).wait()

    verilog_sources = [
        os.path.join(rtl_dir, f"{dut}.v"),
        os.path.join(rtl_dir, f"switch_crossbar.v"),
        os.path.join(axis_rtl_dir, f"axis_fifo.v"),
        os.path.join(axis_rtl_dir, f"axis_arb_mux.v"),
        os.path.join(axis_rtl_dir, f"arbiter.v"),
        os.path.join(axis_rtl_dir, f"priority_encoder.v"),
    ]

    parameters = {}

    parameters['AXIS_DATA_WIDTH'] = data_width
    parameters['AXIS_KEEP_WIDTH'] = parameters['AXIS_DATA_WIDTH'] // 8
    parameters['AXIS_ID_ENABLE'] = 1
    parameters['AXIS_ID_WIDTH'] = 8
    parameters['AXIS_USER_ENABLE'] = 1
    parameters['AXIS_USER_WIDTH'] = 17    
    parameters['RADIX'] = radix
    parameters['AXIS_DEST_ENABLE'] = 1
    parameters['AXIS_DEST_WIDTH'] = parameters['RADIX']

    extra_env = {f'PARAM_{k}': str(v) for k, v in parameters.items()}

    sim_build = os.path.join(tests_dir, "sim_build",
        request.node.name.replace('[', '-').replace(']', ''))

    cocotb_test.simulator.run(
        python_search=[tests_dir],
        verilog_sources=verilog_sources,
        toplevel=toplevel,
        module=module,
        parameters=parameters,
        sim_build=sim_build,
        extra_env=extra_env,
    )