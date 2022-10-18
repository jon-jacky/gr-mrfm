module mult24 (input clock, input signed [23:0] x, input signed [23:0] y, output reg signed [46:0] product, input enable_in, output reg enable_out );

   always @(posedge clock)
     if(enable_in)
       product <= #1 x*y;
     else
       product <= #1 47'd0;
   
   always @(posedge clock)
     enable_out <= #1 enable_in;
   
endmodule // mult

