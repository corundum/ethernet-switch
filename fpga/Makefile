# FPGA settings
FPGA_PART = xcku3p-ffvb676-2-e
FPGA_TOP = switch
FPGA_ARCH = kintexuplus

# Files for synthesis
SYN_FILES = rtl/switch.v
SYN_FILES += rtl/switch_crossbar.v
SYN_FILES += lib/verilog-axis/rtl/axis_fifo.v
SYN_FILES += lib/verilog-axis/rtl/axis_arb_mux.v
SYN_FILES += lib/verilog-axis/rtl/arbiter.v
SYN_FILES += lib/verilog-axis/rtl/priority_encoder.v

include vivado.mk
