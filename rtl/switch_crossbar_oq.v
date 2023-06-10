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

module switch_crossbar_oq #
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
    // Enable user signal propagation
    parameter AXIS_USER_ENABLE = 1,
    // Width of user signal in bits
    parameter AXIS_USER_WIDTH = 17,
    
    // Architectural parameters
    // Number of ports (radix of the switch)
    parameter RADIX = 4,
    // Enable dest signal propagation
    parameter AXIS_DEST_ENABLE = 1,
    // Width of dest signal in bits
    parameter AXIS_DEST_WIDTH = RADIX
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

// auxiliar registers and wires
wire [RADIX*RADIX-1:0]  s_arbiter_axis_tvalid;
wire [RADIX*RADIX-1:0]  s_axis_tready_aux;
wire [RADIX-1:0]  s_axis_tready_int;
wire [RADIX*RADIX-1:0] s_axis_tready_reg;

assign s_axis_tready = s_axis_tready_int;

// output wires
wire [RADIX*AXIS_DATA_WIDTH-1:0]             m_axis_tdata_reg;
wire [RADIX*AXIS_KEEP_WIDTH-1:0]             m_axis_tkeep_reg;
wire [RADIX-1:0]                             m_axis_tvalid_reg;
wire [RADIX-1:0]                             m_axis_tready_reg;
wire [RADIX-1:0]                             m_axis_tlast_reg;
wire [RADIX*AXIS_ID_WIDTH-1:0]               m_axis_tid_reg;
wire [RADIX*AXIS_DEST_WIDTH-1:0]             m_axis_tdest_reg;
wire [RADIX*AXIS_USER_WIDTH-1:0]             m_axis_tuser_reg;

// Instantiation of one arbiter per output port
generate
    genvar n, k;
    for (n = 0; n < RADIX; n = n + 1) begin : arbiters
        for (k = 0; k < RADIX; k = k + 1) begin
            // which connections are valid
            assign s_arbiter_axis_tvalid[n*RADIX+k] = s_axis_tvalid[k] && s_axis_tdest[n+k*RADIX];
            assign s_axis_tready_aux[n*RADIX+k] = s_axis_tready_reg[n+k*RADIX] && s_arbiter_axis_tvalid[n+k*RADIX];
        end

        assign s_axis_tready_int[n] = |s_axis_tready_aux[n*RADIX +: RADIX];

        axis_arb_mux #(
            .S_COUNT(RADIX),
            .DATA_WIDTH(AXIS_DATA_WIDTH),
            .KEEP_ENABLE(1),
            .KEEP_WIDTH(AXIS_KEEP_WIDTH),
            .ID_ENABLE(AXIS_ID_ENABLE),                                                                 
            .S_ID_WIDTH(AXIS_ID_WIDTH),                                                            
            .M_ID_WIDTH(AXIS_ID_WIDTH),                                                            
            .DEST_ENABLE(1),                                                               
            .DEST_WIDTH(AXIS_DEST_WIDTH),                                                           
            .USER_ENABLE(AXIS_USER_ENABLE),                                                            
            .USER_WIDTH(AXIS_USER_WIDTH),      
            .LAST_ENABLE(1),
            .UPDATE_TID(0),       
            .ARB_TYPE_ROUND_ROBIN(1),                                                                    
            .ARB_LSB_HIGH_PRIORITY(1)        
        )
        axis_arb_mux_inst (
            .clk(clk),
            .rst(rst),

            /*
            * AXI-Stream input
            */
            .s_axis_tdata(s_axis_tdata),
            .s_axis_tkeep(s_axis_tkeep),
            .s_axis_tvalid(s_arbiter_axis_tvalid[n*RADIX +: RADIX]),
            .s_axis_tready(s_axis_tready_reg[n*RADIX +: RADIX]),
            .s_axis_tlast(s_axis_tlast),
            .s_axis_tid(s_axis_tid),
            .s_axis_tdest(s_axis_tdest),
            .s_axis_tuser(s_axis_tuser),

            /*
            * AXI-Stream output
            */
            .m_axis_tdata(m_axis_tdata_reg[n*AXIS_DATA_WIDTH +: AXIS_DATA_WIDTH]),
            .m_axis_tkeep(m_axis_tkeep_reg[n*AXIS_KEEP_WIDTH +: AXIS_KEEP_WIDTH]),
            .m_axis_tvalid(m_axis_tvalid_reg[n]),
            .m_axis_tready(m_axis_tready_reg[n]),
            .m_axis_tlast(m_axis_tlast_reg[n]),
            .m_axis_tid(m_axis_tid_reg[n*AXIS_ID_WIDTH +: AXIS_ID_WIDTH]),
            .m_axis_tdest(m_axis_tdest_reg[n*AXIS_DEST_WIDTH +: AXIS_DEST_WIDTH]),
            .m_axis_tuser(m_axis_tuser_reg[n*AXIS_USER_WIDTH +: AXIS_USER_WIDTH])
        );
    end
endgenerate

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