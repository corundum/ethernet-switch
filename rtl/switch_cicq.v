/*

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

*/

`resetall
`timescale 1ns / 1ps
`default_nettype none

module switch_cicq #
(
    // AXI streaming interface parameters
    // Width of data bus in bits
    parameter AXIS_DATA_WIDTH = 64,
    // Width of keep signal in bits
    parameter AXIS_KEEP_WIDTH = AXIS_DATA_WIDTH/8,
    // Enable id signal propagation
    parameter AXIS_ID_ENABLE = 1,
    // Width of id signal in bits
    parameter AXIS_ID_WIDTH = 8,
    
    // Architectural parameters
    // Number of ports (radix of the switch)
    parameter RADIX = 4,
    // Enable dest signal propagation
    parameter AXIS_DEST_ENABLE = 1,
    // Width of dest signal in bits
    parameter AXIS_DEST_WIDTH = RADIX,
    // Number of virtual channels (VCs) per input
    parameter VC_COUNT = 8,
    // Enable user signal propagation
    parameter AXIS_USER_ENABLE = 1,
    // Width of user signal in bits
    parameter AXIS_USER_WIDTH = $clog2(VC_COUNT)
)
(
    input  wire                                   clk,
    input  wire                                   rst,
    
    /*
     * AXI-Stream input
     */
    input  wire [RADIX*AXIS_DATA_WIDTH-1:0]       s_axis_tdata,
    input  wire [RADIX*AXIS_DATA_WIDTH/8-1:0]     s_axis_tkeep,
    input  wire [RADIX-1:0]                       s_axis_tvalid,
    output wire [RADIX-1:0]                       s_axis_tready,
    input  wire [RADIX-1:0]                       s_axis_tlast,
    input  wire [RADIX*AXIS_ID_WIDTH-1:0]         s_axis_tid,
    input  wire [RADIX*AXIS_DEST_WIDTH-1:0]       s_axis_tdest,
    input  wire [RADIX*AXIS_USER_WIDTH-1:0]       s_axis_tuser,

    /*
     * AXI-Stream output
     */
    output wire [RADIX*AXIS_DATA_WIDTH-1:0]       m_axis_tdata,
    output wire [RADIX*AXIS_DATA_WIDTH/8-1:0]     m_axis_tkeep,
    output wire [RADIX-1:0]                       m_axis_tvalid,
    input  wire [RADIX-1:0]                       m_axis_tready,
    output wire [RADIX-1:0]                       m_axis_tlast,
    output wire [RADIX*AXIS_ID_WIDTH-1:0]         m_axis_tid,
    output wire [RADIX*AXIS_DEST_WIDTH-1:0]       m_axis_tdest,
    output wire [RADIX*AXIS_USER_WIDTH-1:0]       m_axis_tuser
);

// architectural parameters
localparam FIFO_DEPTH_CYCLES = 100;
localparam VC_WIDTH = AXIS_USER_WIDTH;

// mapping wires (FIFOs to switch crossbar)
wire [RADIX*AXIS_DATA_WIDTH*VC_COUNT-1:0]          m_axis_tdata_fifo;
wire [RADIX*AXIS_KEEP_WIDTH*VC_COUNT-1:0]          m_axis_tkeep_fifo;
wire [RADIX*VC_COUNT-1:0]                          m_axis_tvalid_fifo;
wire [RADIX*VC_COUNT-1:0]                          m_axis_tready_fifo;
wire [RADIX*VC_COUNT-1:0]                          m_axis_tlast_fifo;
wire [RADIX*AXIS_ID_WIDTH*VC_COUNT-1:0]            m_axis_tid_fifo;
wire [RADIX*AXIS_DEST_WIDTH*VC_COUNT-1:0]          m_axis_tdest_fifo;
wire [RADIX*AXIS_USER_WIDTH*VC_COUNT-1:0]          m_axis_tuser_fifo;

// selected VC wires
wire [RADIX*AXIS_DATA_WIDTH-1:0]                   s_axis_tdata_vc;
wire [RADIX*AXIS_KEEP_WIDTH-1:0]                   s_axis_tkeep_vc;
wire [RADIX-1:0]                                   s_axis_tvalid_vc;
wire [RADIX-1:0]                                   s_axis_tready_vc;
wire [RADIX-1:0]                                   s_axis_tlast_vc;
wire [RADIX*AXIS_ID_WIDTH-1:0]                     s_axis_tid_vc;
wire [RADIX*AXIS_DEST_WIDTH-1:0]                   s_axis_tdest_vc;
wire [RADIX*AXIS_USER_WIDTH-1:0]                   s_axis_tuser_vc;

// auxiliar registers and wires
wire [RADIX*VC_COUNT-1:0] s_axis_tvalid_fifos;
wire [RADIX-1:0] s_axis_tready_fifos;
wire [RADIX*VC_COUNT-1:0] s_axis_tready_reg;

assign s_axis_tready = s_axis_tready_fifos;

// Instantiation of RADIX FIFOs per input port
generate
    genvar n, m;
    for (n = 0; n < RADIX; n = n + 1) begin : input_ports
        // map selected VC to input port: for input n look if the tready signal of the selected VC is high (and valid)
        assign s_axis_tready_fifos[n] = |(s_axis_tvalid_fifos[n*VC_COUNT +: VC_COUNT] & s_axis_tready_reg[n*VC_COUNT +: VC_COUNT]);
        // map valid and tuser to write in VC FIFO
        assign s_axis_tvalid_fifos[n*VC_COUNT +: VC_COUNT] = {VC_COUNT{s_axis_tvalid[n]}} & (1 << s_axis_tuser[n*VC_WIDTH +: VC_WIDTH]);

        for (m = 0; m < VC_COUNT; m = m + 1) begin : virtual_channels
            // instantiate VC m for input n
            axis_fifo #(
                .DEPTH(FIFO_DEPTH_CYCLES * AXIS_DATA_WIDTH/8),
                .DATA_WIDTH(AXIS_DATA_WIDTH),
                .KEEP_ENABLE(1),
                .KEEP_WIDTH(AXIS_KEEP_WIDTH),
                .LAST_ENABLE(1),
                .ID_ENABLE(AXIS_ID_ENABLE),                                                                 
                .ID_WIDTH(AXIS_ID_WIDTH),                                                            
                .DEST_ENABLE(AXIS_DEST_ENABLE),                                                               
                .DEST_WIDTH(AXIS_DEST_WIDTH),                                                           
                .USER_ENABLE(AXIS_USER_ENABLE),                                                            
                .USER_WIDTH(AXIS_USER_WIDTH),                                                            
                .RAM_PIPELINE(1),       
                .OUTPUT_FIFO_ENABLE(0),                                                                    
                .FRAME_FIFO(0),                                                               
                .USER_BAD_FRAME_VALUE(1'b1),                                                               
                .USER_BAD_FRAME_MASK(1'b1),                                                                 
                .DROP_OVERSIZE_FRAME(0),                                                                          
                .DROP_BAD_FRAME(0),                                                               
                .DROP_WHEN_FULL(0)           
            )
            axis_fifo_inst (
                .clk(clk),
                .rst(rst),

                /*
                * AXI-Stream input
                */
                .s_axis_tdata(s_axis_tdata[n*AXIS_DATA_WIDTH +: AXIS_DATA_WIDTH]),
                .s_axis_tkeep(s_axis_tkeep[n*AXIS_KEEP_WIDTH +: AXIS_KEEP_WIDTH]),
                .s_axis_tvalid(s_axis_tvalid_fifos[n*VC_COUNT + m]),
                .s_axis_tready(s_axis_tready_reg[n*VC_COUNT + m]),
                .s_axis_tlast(s_axis_tlast[n]),
                .s_axis_tid(s_axis_tid[n*AXIS_ID_WIDTH +: AXIS_ID_WIDTH]),
                .s_axis_tdest(s_axis_tdest[n*AXIS_DEST_WIDTH +: AXIS_DEST_WIDTH]),
                .s_axis_tuser(s_axis_tuser[n*AXIS_USER_WIDTH +: AXIS_USER_WIDTH]),

                /*
                * AXI-Stream output
                */
                .m_axis_tdata(m_axis_tdata_fifo[(n*VC_COUNT + m)*AXIS_DATA_WIDTH +: AXIS_DATA_WIDTH]),
                .m_axis_tkeep(m_axis_tkeep_fifo[(n*VC_COUNT + m)*AXIS_KEEP_WIDTH +: AXIS_KEEP_WIDTH]),
                .m_axis_tvalid(m_axis_tvalid_fifo[n*VC_COUNT + m]),
                .m_axis_tready(m_axis_tready_fifo[n*VC_COUNT + m]),
                .m_axis_tlast(m_axis_tlast_fifo[n*VC_COUNT + m]),
                .m_axis_tid(m_axis_tid_fifo[(n*VC_COUNT + m)*AXIS_ID_WIDTH +: AXIS_ID_WIDTH]),
                .m_axis_tdest(m_axis_tdest_fifo[(n*VC_COUNT + m)*AXIS_DEST_WIDTH +: AXIS_DEST_WIDTH]),
                .m_axis_tuser(m_axis_tuser_fifo[(n*VC_COUNT + m)*AXIS_USER_WIDTH +: AXIS_USER_WIDTH]),

                /*
                * Additional output
                */
                .status_overflow(),
                .status_bad_frame(),
                .status_good_frame()
            );
        end

        // select VC to transmit from input n
        axis_arb_mux #(
            .S_COUNT(VC_COUNT),
            .DATA_WIDTH(AXIS_DATA_WIDTH),
            .KEEP_ENABLE(1),
            .KEEP_WIDTH(AXIS_KEEP_WIDTH),
            .ID_ENABLE(AXIS_ID_ENABLE),                                                                 
            .S_ID_WIDTH(AXIS_ID_WIDTH),                                                            
            .M_ID_WIDTH(AXIS_ID_WIDTH),                                                            
            .DEST_ENABLE(AXIS_DEST_ENABLE),                                                               
            .DEST_WIDTH(AXIS_DEST_WIDTH),                                                           
            .USER_ENABLE(AXIS_USER_ENABLE),                                                            
            .USER_WIDTH(AXIS_USER_WIDTH),      
            .LAST_ENABLE(1),
            .UPDATE_TID(0),       
            .ARB_TYPE_ROUND_ROBIN(1),                                                                    
            .ARB_LSB_HIGH_PRIORITY(1)        
        )
        axis_arb_mux_vc_inst (
            .clk(clk),
            .rst(rst),

            /*
            * AXI-Stream input
            */
            .s_axis_tdata(m_axis_tdata_fifo[n*VC_COUNT*AXIS_DATA_WIDTH +: VC_COUNT*AXIS_DATA_WIDTH]),
            .s_axis_tkeep(m_axis_tkeep_fifo[n*VC_COUNT*AXIS_KEEP_WIDTH +: VC_COUNT*AXIS_KEEP_WIDTH]),
            .s_axis_tvalid(m_axis_tvalid_fifo[n*VC_COUNT +: VC_COUNT]),
            .s_axis_tready(m_axis_tready_fifo[n*VC_COUNT +: VC_COUNT]),
            .s_axis_tlast(m_axis_tlast_fifo[n*VC_COUNT +: VC_COUNT]),
            .s_axis_tid(m_axis_tid_fifo[n*VC_COUNT*AXIS_ID_WIDTH +: VC_COUNT*AXIS_ID_WIDTH]),
            .s_axis_tdest(m_axis_tdest_fifo[n*VC_COUNT*AXIS_DEST_WIDTH +: VC_COUNT*AXIS_DEST_WIDTH]),
            .s_axis_tuser(m_axis_tuser_fifo[n*VC_COUNT*AXIS_USER_WIDTH +: VC_COUNT*AXIS_USER_WIDTH]),

            /*
            * AXI-Stream output
            */
            .m_axis_tdata(s_axis_tdata_vc[n*AXIS_DATA_WIDTH +: AXIS_DATA_WIDTH]),
            .m_axis_tkeep(s_axis_tkeep_vc[n*AXIS_KEEP_WIDTH +: AXIS_KEEP_WIDTH]),
            .m_axis_tvalid(s_axis_tvalid_vc[n]),
            .m_axis_tready(s_axis_tready_vc[n]),
            .m_axis_tlast(s_axis_tlast_vc[n]),
            .m_axis_tid(s_axis_tid_vc[n*AXIS_ID_WIDTH +: AXIS_ID_WIDTH]),
            .m_axis_tdest(s_axis_tdest_vc[n*AXIS_DEST_WIDTH +: AXIS_DEST_WIDTH]),
            .m_axis_tuser(s_axis_tuser_vc[n*AXIS_USER_WIDTH +: AXIS_USER_WIDTH])
        );
    end
endgenerate

// output wires
wire [RADIX*AXIS_DATA_WIDTH-1:0]             m_axis_tdata_reg;
wire [RADIX*AXIS_KEEP_WIDTH-1:0]             m_axis_tkeep_reg;
wire [RADIX-1:0]                             m_axis_tvalid_reg;
wire [RADIX-1:0]                             m_axis_tready_reg;
wire [RADIX-1:0]                             m_axis_tlast_reg;
wire [RADIX*AXIS_ID_WIDTH-1:0]               m_axis_tid_reg;
wire [RADIX*AXIS_DEST_WIDTH-1:0]             m_axis_tdest_reg;
wire [RADIX*AXIS_USER_WIDTH-1:0]             m_axis_tuser_reg;

// Instantiation of switch crossbar logic
switch_crossbar_cicq #(
    .AXIS_DATA_WIDTH(AXIS_DATA_WIDTH),
    .AXIS_KEEP_WIDTH(AXIS_KEEP_WIDTH),
    .AXIS_ID_ENABLE(AXIS_ID_ENABLE),
    .AXIS_ID_WIDTH(AXIS_ID_WIDTH),
    .AXIS_DEST_ENABLE(AXIS_DEST_ENABLE),
    .AXIS_DEST_WIDTH(AXIS_DEST_WIDTH),
    .AXIS_USER_ENABLE(AXIS_USER_ENABLE),
    .AXIS_USER_WIDTH(AXIS_USER_WIDTH),
    .RADIX(RADIX)
)
switch_crossbar_inst (
    .clk(clk),
    .rst(rst),

    /*
    * AXI-Stream input
    */
    .s_axis_tdata(s_axis_tdata_vc),
    .s_axis_tkeep(s_axis_tkeep_vc),
    .s_axis_tvalid(s_axis_tvalid_vc),
    .s_axis_tready(s_axis_tready_vc),
    .s_axis_tlast(s_axis_tlast_vc),
    .s_axis_tid(s_axis_tid_vc),
    .s_axis_tdest(s_axis_tdest_vc),
    .s_axis_tuser(s_axis_tuser_vc),

    /*
    * AXI-Stream output
    */
    .m_axis_tdata(m_axis_tdata_reg),
    .m_axis_tkeep(m_axis_tkeep_reg),
    .m_axis_tvalid(m_axis_tvalid_reg),
    .m_axis_tready(m_axis_tready_reg),
    .m_axis_tlast(m_axis_tlast_reg),
    .m_axis_tid(m_axis_tid_reg),
    .m_axis_tdest(m_axis_tdest_reg),
    .m_axis_tuser(m_axis_tuser_reg)
);

// output mapping
assign m_axis_tdata = m_axis_tdata_reg;
assign m_axis_tkeep = m_axis_tkeep_reg;
assign m_axis_tvalid = m_axis_tvalid_reg;
assign m_axis_tready_reg = m_axis_tready;
assign m_axis_tlast = m_axis_tlast_reg;
assign m_axis_tid = m_axis_tid_reg;
assign m_axis_tdest = m_axis_tdest_reg;
assign m_axis_tuser = m_axis_tuser_reg;

endmodule
