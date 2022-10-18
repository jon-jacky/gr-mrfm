// -*- verilog -*-
//
//  USRP - Universal Software Radio Peripheral
//
//  Copyright (C) 2005,2006,2007,2008 Matt Ettus and Jonathan Jacky
//
//  This program is free software; you can redistribute it and/or modify
//  it under the terms of the GNU General Public License as published by
//  the Free Software Foundation; either version 2 of the License, or
//  (at your option) any later version.
//
//  This program is distributed in the hope that it will be useful,
//  but WITHOUT ANY WARRANTY; without even the implied warranty of
//  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
//  GNU General Public License for more details.
//
//  You should have received a copy of the GNU General Public License
//  along with this program; if not, write to the Free Software
//  Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
//

module shifter24(input wire [49:0] in, output wire [23:0] out, input wire [7:0] shift);
   // Wish we could do  assign out = in[15+shift:shift];

   reg [23:0] quotient, remainder;
   wire [23:0] out_unclipped;
   reg [26:0]  msbs;
   wire        in_range;
   
   always @*
     case(shift)
       0 : quotient = in[23:0];
       1 : quotient = in[24:1];
       2 : quotient = in[25:2];
       3 : quotient = in[26:3];
       4 : quotient = in[27:4];
       5 : quotient = in[28:5];
       6 : quotient = in[29:6];
       7 : quotient = in[30:7];
       8 : quotient = in[31:8];
       9 : quotient = in[32:9];
       10 : quotient = in[33:10];
       11 : quotient = in[34:11];
       12 : quotient = in[35:12];
       13 : quotient = in[36:13];
       14 : quotient = in[37:14];
       15 : quotient = in[38:15];
       16 : quotient = in[39:16];
       17 : quotient = in[40:17];
       18 : quotient = in[41:18];
       19 : quotient = in[42:19];
       20 : quotient = in[43:20];
       21 : quotient = in[44:21];
       22 : quotient = in[45:22];
       default : quotient = in[23:0];
     endcase // case(shift)

   always @*
     case(shift)
       0 : remainder = 24'b0;
       1 : remainder = {in[0],23'b0};
       2 : remainder = {in[1:0],22'b0};
       3 : remainder = {in[2:0],21'b0};
       4 : remainder = {in[3:0],20'b0};
       5 : remainder = {in[4:0],19'b0};
       6 : remainder = {in[5:0],18'b0};
       7 : remainder = {in[6:0],17'b0};
       8 : remainder = {in[7:0],16'b0};
       9 : remainder = {in[8:0],15'b0};
       10 : remainder = {in[9:0],14'b0};
       11 : remainder = {in[10:0],13'b0};
       12 : remainder = {in[11:0],12'b0};
       13 : remainder = {in[12:0],11'b0};
       14 : remainder = {in[13:0],10'b0};
       15 : remainder = {in[14:0],9'b0};
       16 : remainder = {in[15:0],8'b0};
       17 : remainder = {in[16:0],7'b0};
       18 : remainder = {in[17:0],6'b0};
       19 : remainder = {in[18:0],5'b0};
       20 : remainder = {in[19:0],4'b0};
       21 : remainder = {in[20:0],3'b0};
       22 : remainder = {in[21:0],2'b0};
       default : remainder = 24'b0;
     endcase // case(shift)

   always @*
     case(shift)
       0 : msbs = in[49:23];
       1 : msbs = {in[49],in[49:24]};
       2 : msbs = {{2{in[49]}},in[49:25]};
       3 : msbs = {{3{in[49]}},in[49:26]};
       4 : msbs = {{4{in[49]}},in[49:27]};
       5 : msbs = {{5{in[49]}},in[49:28]};
       6 : msbs = {{6{in[49]}},in[49:29]};
       7 : msbs = {{7{in[49]}},in[49:30]};
       8 : msbs = {{8{in[49]}},in[49:31]};
       9 : msbs = {{9{in[49]}},in[49:32]};
       10 : msbs = {{10{in[49]}},in[49:33]};
       11 : msbs = {{11{in[49]}},in[49:34]};
       12 : msbs = {{12{in[49]}},in[49:35]};
       13 : msbs = {{13{in[49]}},in[49:36]};
       14 : msbs = {{14{in[49]}},in[49:37]};
       15 : msbs = {{15{in[49]}},in[49:38]};
       16 : msbs = {{16{in[49]}},in[49:39]};
       17 : msbs = {{17{in[49]}},in[49:40]};
       18 : msbs = {{18{in[49]}},in[49:41]};
       19 : msbs = {{19{in[49]}},in[49:42]};
       20 : msbs = {{20{in[49]}},in[49:43]};
       21 : msbs = {{21{in[49]}},in[49:44]};
       22 : msbs = {{22{in[49]}},in[49:45]};
       default : msbs = in[49:23];
     endcase // case(shift)

   assign     in_range = &msbs | ~(|msbs);
   assign     out_unclipped = quotient + (in[49] & |remainder);
   assign     out = in_range ? out_unclipped : {in[49],{23{~in[49]}}};
   
endmodule // shifter
