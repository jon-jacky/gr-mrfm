

module acc24 (input clock, input reset, input clear, input enable_in, output reg enable_out,
	    input signed [46:0] addend, output reg signed [49:0] sum );

   always @(posedge clock)
     if(reset)
       sum <= #1 50'd0;
     //else if(clear & enable_in)
     //  sum <= #1 addend;
     //else if(clear)
     //  sum <= #1 34'd0;
     else if(clear)
       // sum <= #1 50'd0 + addend; -- add zero to force sign extension
       sum <= #1 addend; // DO NOT add zero to force sign extension
     else if(enable_in)
       sum <= #1 sum + addend;

   always @(posedge clock)
     enable_out <= #1 enable_in;
   
endmodule // acc

