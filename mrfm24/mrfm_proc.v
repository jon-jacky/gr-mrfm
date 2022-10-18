
`include "mrfm.vh"
`include "../../../firmware/include/fpga_regs_common.v"
`include "../../../firmware/include/fpga_regs_standard.v"

module mrfm_proc (input clock, input reset, input enable,
		  input [6:0] serial_addr, input [31:0] serial_data, input serial_strobe,
		  input [15:0] signal_in, output wire [15:0] signal_out, output wire sync_out,
		  output wire [15:0] i, output wire [15:0] q, 
		  output wire [15:0] ip, output wire [15:0] qp,
		  output wire strobe_out, output wire [63:0] debugbus);

   // Strobes
   wire                       sample_strobe, strobe_0, strobe_1;
   assign                     sample_strobe = 1'b1;
   wire [7:0]                 rate_0, rate_1, rate_2;

   setting_reg #(`FR_MRFM_DECIM) sr_decim(.clock(clock),.reset(reset),.strobe(serial_strobe),.addr(serial_addr),.in(serial_data),.out({rate_2,rate_1,rate_0}));
   
   strobe_gen strobe_gen_0
     ( .clock(clock),.reset(reset),.enable(enable),
       .rate(rate_0),.strobe_in(sample_strobe),.strobe(strobe_0) );
   strobe_gen strobe_gen_1
     ( .clock(clock),.reset(reset),.enable(enable),
       .rate(rate_1),.strobe_in(strobe_0),.strobe(strobe_1) );
   
   assign      sync_out = 1'd0;  // no longer needed, was phase[31];

   assign      i=signal_in;    // connect signal input to USB output
   assign      ip=signal_out;  // connect signal output to another USB output

   assign      q=16'd0;  // quadrature signal removed
   assign      qp=16'd0; 
   
   assign      strobe_out = strobe_1;

   biquad_2stage iir_i (.clock(clock),.reset(reset),.strobe_in(strobe_1),
			.serial_strobe(serial_strobe),.serial_addr(serial_addr),.serial_data(serial_data),
			.sample_in(signal_in),.sample_out(signal_out),.debugbus(debugbus));
   
endmodule // mrfm_proc
