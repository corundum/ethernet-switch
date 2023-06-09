# Copyright (c) 2023 Corundum organization
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

TOPLEVEL_LANG = verilog

SIM ?= icarus
WAVES ?= 0

COCOTB_HDL_TIMEUNIT = 1ns
COCOTB_HDL_TIMEPRECISION = 10fs

export RADIX ?= 4

DUT      = switch_oq
WRAPPER  = $(DUT)_wrap_$(RADIX)x$(RADIX)
TOPLEVEL = $(WRAPPER)
MODULE   = test_$(DUT)
VERILOG_SOURCES += $(WRAPPER).v ../../rtl/$(DUT).v ../../rtl/switch_crossbar_oq.v ../../lib/verilog-axis/rtl/axis_async_fifo.v ../../lib/verilog-axis/rtl/axis_fifo.v ../../lib/verilog-axis/rtl/axis_arb_mux.v ../../lib/verilog-axis/rtl/arbiter.v ../../lib/verilog-axis/rtl/priority_encoder.v

# module parameters
export PARAM_AXIS_DATA_WIDTH ?= 64
export PARAM_AXIS_KEEP_WIDTH ?= $(shell expr $(PARAM_AXIS_DATA_WIDTH) / 8)
export PARAM_AXIS_ID_ENABLE ?= 1
export PARAM_AXIS_ID_WIDTH ?= 64
export PARAM_AXIS_USER_ENABLE ?= 1
export PARAM_AXIS_USER_WIDTH ?= 17
export PARAM_RADIX ?= $(shell expr $(RADIX))
export PARAM_AXIS_DEST_ENABLE ?= 1
export PARAM_AXIS_DEST_WIDTH ?= $(shell expr $(PARAM_RADIX))

ifeq ($(SIM), icarus)
	PLUSARGS += -fst

	COMPILE_ARGS += $(foreach v,$(filter PARAM_%,$(.VARIABLES)),-P $(TOPLEVEL).$(subst PARAM_,,$(v))=$($(v)))

	ifeq ($(WAVES), 1)
		VERILOG_SOURCES += iverilog_dump.v
		COMPILE_ARGS += -s iverilog_dump
	endif
else ifeq ($(SIM), verilator)
	COMPILE_ARGS += -Wno-SELRANGE -Wno-WIDTH

	COMPILE_ARGS += $(foreach v,$(filter PARAM_%,$(.VARIABLES)),-G$(subst PARAM_,,$(v))=$($(v)))

	ifeq ($(WAVES), 1)
		COMPILE_ARGS += --trace-fst
	endif
endif

include $(shell cocotb-config --makefiles)/Makefile.sim

$(WRAPPER).v: ../../rtl/$(DUT)_wrap.py
	$< -p $(RADIX) $(RADIX)

iverilog_dump.v:
	echo 'module iverilog_dump();' > $@
	echo 'initial begin' >> $@
	echo '    $$dumpfile("$(TOPLEVEL).fst");' >> $@
	echo '    $$dumpvars(0, $(TOPLEVEL));' >> $@
	echo 'end' >> $@
	echo 'endmodule' >> $@

clean::
	@rm -rf iverilog_dump.v
	@rm -rf dump.fst $(TOPLEVEL).fst
	@rm -rf dump.fst *.fst
	@rm -rf *_wrap_*.v
	@rm -rf results.xml