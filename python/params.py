# utils for params.h format files and msgs created/used by MRFM software
#
# This is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3, or (at your option)
# any later version.
# 
# This software is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

from time import strftime
from tf import compen, biquad, lowpass2

def check_prefix(s, prefix):
    if not s.startswith(prefix):
        raise ValueError, "Couldn't find %s, got %s" % (prefix,s[0:len(prefix)])

def parse_array(s, prefix):
    check_prefix(s, prefix)
    a = [ float(f) for f in s[4:-2].split(', ') ]
    return a  

def parse_coeffs(msg, clock=64E6):  # FPGA clock is 64 MHZ
    ls = [ l for l in msg.splitlines() ]
    check_prefix(ls[6], "Ts=")
    decim = int(clock*float(ls[6][3:-1]))
    b = parse_array(ls[7], "bd=")
    a = parse_array(ls[8], "ad=")
    return decim, b, a

def parse_het(msg):
    ls = [ l for l in msg.splitlines() ]
    check_prefix(ls[9], "wc=")
    wc = float(ls[9][3:-1])
    check_prefix(ls[10], "phase=")
    phase = float(ls[10][6:-1])
    return wc, phase

# Here used ONLY for tests in main(), different from parameter with that name
coeff_frac_bits = 14  # different from options.frac_bits, 22 for 24bit data

# Use coeff_frac_bits (not just frac_bits) to scale filter coefficients
def params2sos(msg, coeff_frac_bits):
    decim, b, a = parse_coeffs(msg)
    # print '>', decim, len(b), len(a), b, a
    try:
        wc, phase = parse_het(msg)
        cs = compen(phase)
        heterodyne = True
    except:
        wc, phase, cs = (8e3, 0, [])
        heterodyne = False
    g = 1.0 # gain, in the future maybe get this from msg
    sosm = biquad(b,a,coeff_frac_bits,g)
    # FPGA can only handle 1 or 2 sections of ba
    if len(sosm) == 1:
        ba = sosm[0]
    elif len(sosm) > 1:
        ba = sosm[0] + sosm[1] # flatten sosm to ba
    else:
        raise ValueError, "Could not extract coeffs from message"
    return ba, cs, wc, heterodyne

"""
 Write transfer function coefficients in a params.h-format string
 Can't use Python 2.4 string templates and substitution because Mac uses 2.3
 Does not *exactly* copy params.h format, compare main output with msg below
"""
def tf2params(b, a, fs=5e5, wc=None, phase=None):

    msg1 = """#define sample_period     79
#define size_a %d 
#define size_b %d
#define a_coef_def .var a_coefs[size_a] = %s;
#define b_coef_def .var b_coefs[size_b] = %s;
/*
Ts=%E;
bd=%s;
ad=%s;
""" \
 % (len(a), len(b), a[::-1], b[::-1], 1/fs, b, a) # nondestructive reverse

    date = strftime('%m/%d/%y')
    time = strftime('%I:%M %p')
    msg3 = """Date: %s
Time: %s
*/""" % (date, time)

    if wc != None and phase != None:
        msg2 = """wc=%f;
phase=%f;
""" % (wc, phase)
        return msg1 + msg2 + msg3
    else:
        return msg1 + msg3

msg = """#define sample_period     79
#define size_a 3 
#define size_b 4 
#define a_coef_def .var a_coefs[size_a] = 8.157756E-1, -2.622746E+0, 2.805051E+0;
#define b_coef_def .var b_coefs[size_b] = 2.360070E-3, 1.697985E-3, -2.584190E-3, -1.922105E-3;
/*
Ts=2.000000E-6;
bd=[-1.922105E-3, -2.584190E-3, 1.697985E-3, 2.360070E-3];
ad=[1.000000E+0, -2.805051E+0, 2.622746E+0, -8.157756E-1];
wc=8000.1;
phase=30.0;
Date: 4/27/07
Time: 11:52 AM
*/"""

msg_bad = "extra line\n" + msg

# flat controller
bf = [-1.922105E-3, -2.584190E-3, 1.697985E-3, 2.360070E-3]
af = [1.000000E+0, -2.805051E+0, 2.622746E+0, -8.157756E-1]

# heterodyne controller
bh = [ 6.030039E-4,  6.030039E-4 ]
ah = [ 1.0,         -9.993970E-1 ]

# open loop controller, b's all zero
bo = [0.000000E+0, 0.000000E+0, -0.000000E+0, -0.000000E+0]
ao = [1.000000E+0, -2.831318E+0, 2.673088E+0, -8.403509E-1]

# uses global variable coeff_frac_bits = 14 hard coded above,
# just for these tests, other values are used in production
def main():
    try:
        parse_coeffs(msg_bad)
    except ValueError:
        print "parse_coeffs couldn't parse msg_bad, raised ValueError"
    decim, b, a = parse_coeffs(msg)
    print decim
    print len(b), b
    print len(a), a
    wc, phase = parse_het(msg)
    print wc, phase
    ba, cs, wc, heterodyne = params2sos(msg, coeff_frac_bits)
    print wc, heterodyne
    print "ba ", ba
    print "cs ", cs
    print

    print
    print "Second-order lowpass filter with resonant peak"
    print 
    b,a = lowpass2()    
    msg_lp2 = tf2params(b,a)
    print msg_lp2
    ba, cs, wc, heterodyne = params2sos(msg_lp2, coeff_frac_bits)
    print 
    print "ba ", ba
    
    print
    print "Heterodyne controller, first order lowpass filter"
    print
    msg_het = tf2params(bh,ah, wc=8000.2  , phase=30.1 )
    print msg_het
    ba, cs, wc, heterodyne = params2sos(msg_het, coeff_frac_bits)
    print 
    print "ba ", ba
    
    print
    print "Open loop controller"
    print
    msg_ol = tf2params(bo,ao)
    print msg_ol
    ba, cs, wc, heterodyne = params2sos(msg_ol, coeff_frac_bits)
    print 
    print "ba ", ba
    
if __name__ == '__main__':
        main ()
