// adc_switch.v for mrfm.v, analogous to adc_interface.v used by usrp_std.v
// This is the super-simple version without serial bus or adc0,1 regs

`include "mrfm.vh" // defines FR_MRFM_SCALE_K0, K1

module adc_switch(input clock, input reset,
    input [6:0] serial_addr, input [31:0] serial_data, input serial_strobe, 
    input signed [11:0] in0, input signed [11:0] in1, // 12 bits
    output signed [15:0] sum); 

   wire [31:0] k0, k1; // for now, any nonzero value means 1x (switch closed)
   wire [16:0] sum_extend; // extra bit to check for overflow
   wire        in_range;

   setting_reg #(`FR_MRFM_SCALE_K0) sr_k0(.clock(clock),.reset(reset),
					  .strobe(serial_strobe),.addr(serial_addr),.in(serial_data),
					  .out(k0),.changed());
   
   setting_reg #(`FR_MRFM_SCALE_K1) sr_k1(.clock(clock),.reset(reset),
					  .strobe(serial_strobe),.addr(serial_addr),.in(serial_data),
					  .out(k1),.changed());
    
   assign sum_extend = (k0 == 32'd0 ? 17'd0 : {in0[11],in0,4'b0}) 
                 + (k1 == 32'd0 ? 17'd0 : {in1[11],in1,4'b0});

   assign in_range = &sum_extend[16:15] | ~(|sum_extend[16:15]);

   assign sum = in_range ? sum_extend[15:0] 
                         : {sum_extend[16],{15{~sum_extend[16]}}};
     
endmodule // adc_switch
