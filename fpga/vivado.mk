###################################################################
# 
# Xilinx Vivado FPGA Makefile
# 
# Copyright (c) 2016 Alex Forencich modified by Carlos Megías Núñez
# 
###################################################################
# 
# Parameters:
# FPGA_TOP - Top module name
# FPGA_FAMILY - FPGA family (e.g. VirtexUltrascale)
# FPGA_DEVICE - FPGA device (e.g. xcvu095-ffva2104-2-e)
# SYN_FILES - space-separated list of source files
# INC_FILES - space-separated list of include files
# XDC_FILES - space-separated list of timing constraint files
# XCI_FILES - space-separated list of IP XCI files
# 
# Example:
# 
# FPGA_TOP = switch
# FPGA_FAMILY = VirtexUltrascale
# FPGA_DEVICE = xcvu095-ffva2104-2-e
# SYN_FILES = rtl/tsn_vlan_core_tx.vhd
# XDC_FILES = fpga.xdc
# XCI_FILES = ip/pcspma.xci
# include ../common/vivado.mk
# 
###################################################################

# phony targets
.PHONY: fpga vivado tmpclean clean distclean

# prevent make from deleting intermediate files and reports
.PRECIOUS: %.xpr
.SECONDARY:

CONFIG ?= config.mk
-include ../$(CONFIG)

FPGA_TOP ?= tsn_vlan_core_tx
PROJECT ?= $(FPGA_TOP)

SYN_FILES_REL = $(patsubst %, ../%, $(filter-out /% ./%,$(SYN_FILES))) $(filter /% ./%,$(SYN_FILES))
SIM_FILES_REL = $(patsubst %, ../%, $(filter-out /% ./%,$(SIM_FILES))) $(filter /% ./%,$(SIM_FILES))
INC_FILES_REL = $(patsubst %, ../%, $(filter-out /% ./%,$(INC_FILES))) $(filter /% ./%,$(INC_FILES))
XCI_FILES_REL = $(patsubst %, ../%, $(filter-out /% ./%,$(XCI_FILES))) $(filter /% ./%,$(XCI_FILES))
IP_TCL_FILES_REL = $(patsubst %, ../%, $(filter-out /% ./%,$(IP_TCL_FILES))) $(filter /% ./%,$(IP_TCL_FILES))
CONFIG_TCL_FILES_REL = $(patsubst %, ../%, $(filter-out /% ./%,$(CONFIG_TCL_FILES))) $(filter /% ./%,$(CONFIG_TCL_FILES))

###################################################################
# Main Targets
#
# all: build everything
# clean: remove output files and project files
###################################################################

all: project

project: $(PROJECT).xpr

vivado: $(PROJECT).xpr
	vivado $(PROJECT).xpr

syn: $(PROJECT).runs/synth_1/$(PROJECT).dcp
	
tmpclean::
	-rm -rf *.log *.jou *.cache *.gen *.hbs *.hw *.ip_user_files *.runs *.xpr *.html *.xml *.sim *.srcs *.str .Xil defines.v
	-rm -rf create_project.tcl run_synth.tcl

clean:: tmpclean
	-rm -rf *_utilization.rpt *_utilization_hierarchical.rpt

distclean:: clean
	-rm -rf rev

###################################################################
# Target implementations
###################################################################

# Vivado project file
create_project.tcl: Makefile $(XCI_FILES_REL) $(IP_TCL_FILES_REL)
	rm -rf defines.v
	touch defines.v
	for x in $(DEFS); do echo '`define' $$x >> defines.v; done
	echo "create_project -force -part $(FPGA_PART) $(PROJECT)" > $@
	echo "add_files -fileset sources_1 defines.v $(SYN_FILES_REL)" >> $@
	echo "set_property top $(FPGA_TOP) [current_fileset]" >> $@
	echo "add_files -fileset sim_1 $(SIM_FILES_REL)" >> $@
	for x in $(XCI_FILES_REL); do echo "import_ip $$x" >> $@; done
	for x in $(IP_TCL_FILES_REL); do echo "source $$x" >> $@; done
	for x in $(CONFIG_TCL_FILES_REL); do echo "source $$x" >> $@; done

$(PROJECT).xpr: create_project.tcl
	vivado -nojournal -nolog -mode batch $(foreach x,$?,-source $x)

# synthesis run
$(PROJECT).runs/synth_1/$(PROJECT).dcp: $(PROJECT).xpr $(SYN_FILES_REL) $(INC_FILES_REL) $(XDC_FILES_REL)
	echo "open_project $(PROJECT).xpr" > run_synth.tcl
	echo "reset_run synth_1" >> run_synth.tcl
	echo "launch_runs -jobs 4 synth_1" >> run_synth.tcl
	echo "wait_on_run synth_1" >> run_synth.tcl
	vivado -nojournal -nolog -mode batch -source run_synth.tcl
