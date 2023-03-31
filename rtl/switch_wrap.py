#!/usr/bin/env python
"""
Generates an AXI Stream switch wrapper with the specified number of ports
"""

import argparse
from jinja2 import Template


def main():
    parser = argparse.ArgumentParser(description=__doc__.strip())
    parser.add_argument('-p', '--ports',  type=int, default=[4], nargs='+', help="number of ports")
    parser.add_argument('-n', '--name',   type=str, help="module name")
    parser.add_argument('-o', '--output', type=str, help="output file name")

    args = parser.parse_args()

    try:
        generate(**args.__dict__)
    except IOError as ex:
        print(ex)
        exit(1)


def generate(ports=4, name=None, output=None):
    if type(ports) is int:
        m = n = ports
    elif len(ports) == 1:
        m = n = ports[0]
    else:
        m, n = ports

    if name is None:
        name = "switch_wrap_{0}x{1}".format(m, n)

    if output is None:
        output = name + ".v"

    print("Generating {0}x{1} port AXI stream switch wrapper {2}...".format(m, n, name))

    cm = (m-1).bit_length()
    cn = (n-1).bit_length()

    t = Template(u"""/*

Copyright (c) Corundum organization

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

// Language: Verilog 2001

`resetall
`timescale 1ns / 1ps
`default_nettype none

/*
 * AXI4-Stream {{m}}x{{n}} switch (wrapper)
 */
module {{name}} #
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
    input  wire                  clk,
    input  wire                  rst,

    /*
     * AXI Stream inputs
     */
{%- for p in range(m) %}
    input  wire [AXIS_DATA_WIDTH-1:0]  s{{'%02d'%p}}_axis_tdata,
    input  wire [AXIS_KEEP_WIDTH-1:0]  s{{'%02d'%p}}_axis_tkeep,
    input  wire                        s{{'%02d'%p}}_axis_tvalid,
    output wire                        s{{'%02d'%p}}_axis_tready,
    input  wire                        s{{'%02d'%p}}_axis_tlast,
    input  wire [AXIS_ID_WIDTH-1:0]    s{{'%02d'%p}}_axis_tid,
    input  wire [AXIS_DEST_WIDTH-1:0]  s{{'%02d'%p}}_axis_tdest,
    input  wire [AXIS_USER_WIDTH-1:0]  s{{'%02d'%p}}_axis_tuser,
{% endfor %}
    /*
     * AXI Stream outputs
     */
{%- for p in range(n) %}
    output wire [AXIS_DATA_WIDTH-1:0]  m{{'%02d'%p}}_axis_tdata,
    output wire [AXIS_KEEP_WIDTH-1:0]  m{{'%02d'%p}}_axis_tkeep,
    output wire                        m{{'%02d'%p}}_axis_tvalid,
    input  wire                        m{{'%02d'%p}}_axis_tready,
    output wire                        m{{'%02d'%p}}_axis_tlast,
    output wire [AXIS_ID_WIDTH-1:0]    m{{'%02d'%p}}_axis_tid,
    output wire [AXIS_DEST_WIDTH-1:0]  m{{'%02d'%p}}_axis_tdest,
    output wire [AXIS_USER_WIDTH-1:0]  m{{'%02d'%p}}_axis_tuser{% if not loop.last %},{% endif %}
{% endfor -%}
);

// parameter sizing helpers
function [AXIS_DEST_WIDTH-1:0] w_dw(input [AXIS_DEST_WIDTH-1:0] val);
    w_dw = val;
endfunction

function [{{m-1}}:0] w_s(input [{{m-1}}:0] val);
    w_s = val;
endfunction

switch #(
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
switch_inst (
    .clk(clk),
    .rst(rst),
    // AXI inputs
    .s_axis_tdata({ {% for p in range(m-1,-1,-1) %}s{{'%02d'%p}}_axis_tdata{% if not loop.last %}, {% endif %}{% endfor %} }),
    .s_axis_tkeep({ {% for p in range(m-1,-1,-1) %}s{{'%02d'%p}}_axis_tkeep{% if not loop.last %}, {% endif %}{% endfor %} }),
    .s_axis_tvalid({ {% for p in range(m-1,-1,-1) %}s{{'%02d'%p}}_axis_tvalid{% if not loop.last %}, {% endif %}{% endfor %} }),
    .s_axis_tready({ {% for p in range(m-1,-1,-1) %}s{{'%02d'%p}}_axis_tready{% if not loop.last %}, {% endif %}{% endfor %} }),
    .s_axis_tlast({ {% for p in range(m-1,-1,-1) %}s{{'%02d'%p}}_axis_tlast{% if not loop.last %}, {% endif %}{% endfor %} }),
    .s_axis_tid({ {% for p in range(m-1,-1,-1) %}s{{'%02d'%p}}_axis_tid{% if not loop.last %}, {% endif %}{% endfor %} }),
    .s_axis_tdest({ {% for p in range(m-1,-1,-1) %}s{{'%02d'%p}}_axis_tdest{% if not loop.last %}, {% endif %}{% endfor %} }),
    .s_axis_tuser({ {% for p in range(m-1,-1,-1) %}s{{'%02d'%p}}_axis_tuser{% if not loop.last %}, {% endif %}{% endfor %} }),
    // AXI outputs
    .m_axis_tdata({ {% for p in range(n-1,-1,-1) %}m{{'%02d'%p}}_axis_tdata{% if not loop.last %}, {% endif %}{% endfor %} }),
    .m_axis_tkeep({ {% for p in range(n-1,-1,-1) %}m{{'%02d'%p}}_axis_tkeep{% if not loop.last %}, {% endif %}{% endfor %} }),
    .m_axis_tvalid({ {% for p in range(n-1,-1,-1) %}m{{'%02d'%p}}_axis_tvalid{% if not loop.last %}, {% endif %}{% endfor %} }),
    .m_axis_tready({ {% for p in range(n-1,-1,-1) %}m{{'%02d'%p}}_axis_tready{% if not loop.last %}, {% endif %}{% endfor %} }),
    .m_axis_tlast({ {% for p in range(n-1,-1,-1) %}m{{'%02d'%p}}_axis_tlast{% if not loop.last %}, {% endif %}{% endfor %} }),
    .m_axis_tid({ {% for p in range(n-1,-1,-1) %}m{{'%02d'%p}}_axis_tid{% if not loop.last %}, {% endif %}{% endfor %} }),
    .m_axis_tdest({ {% for p in range(n-1,-1,-1) %}m{{'%02d'%p}}_axis_tdest{% if not loop.last %}, {% endif %}{% endfor %} }),
    .m_axis_tuser({ {% for p in range(n-1,-1,-1) %}m{{'%02d'%p}}_axis_tuser{% if not loop.last %}, {% endif %}{% endfor %} })
);

endmodule

`resetall

""")

    print(f"Writing file '{output}'...")

    with open(output, 'w') as f:
        f.write(t.render(
            m=m,
            n=n,
            cm=cm,
            cn=cn,
            name=name
        ))
        f.flush()

    print("Done")


if __name__ == "__main__":
    main()
