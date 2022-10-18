# utilities for working with transfer functions in various representations
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

from math import pi, sin, cos
from numpy import array, sign, around, hstack
from scipy.signal.filter_design import tf2zpk, zpk2tf, bilinear

# also coded inline in biquad, below
def scale(f, frac_bits=22):
    return int(round((2**frac_bits)*f))  # f is usually float

# phase compensator + gain matrix 
def compen(theta, gain=1.0, shift=14):
    scale = 2**shift
    theta_r = pi*theta/180.0
    pmat = [ cos(theta_r), sin(theta_r), -sin(theta_r), cos(theta_r) ]
    a = [ int(round(gain*scale*e)) for e in pmat ]
    return [ a[0], a[2], a[1], a[3], shift ]  # same order as compenwrite.m

# helper for tf2sos
def sort_match(z,p):
    # pis is indices of poles sorted in increasing distance from unit circle
    pis = (1 - abs(p)).argsort()  # scipy array operations similar to matlab
    # match each zero to nearest pole
    # zis is indices of zeroes in z that match indices of poles in pis
    zis = []
    for i in pis:
        # izlist is indices of z sorted by increasing distance from p[i]
        izlist = (abs(p[i] - z)).argsort()
        for iz in izlist: 
            if iz not in zis: # each iz must appear in zis only once
                zis.append(iz)
                break
        # print 'i', i, 'p[i]', p[i], 'izlist', izlist
        # print 'zis', zis
    # TODO: what about any leftover poles or zeroes?  What can we assume?
    return z.take(zis), p.take(pis)

# like matlab tf2sos, less general, order and scale baked in for now
def tf2sos(b,a):
    (z,p,k) = tf2zpk(b,a)  # from scipy
    # print 'k', k
    # print 'z', z
    # print 'p', p
    if k == 0:       # zero output, special case to avoid exception below
        sos = [[0,0,0,1,0,0]] # b all zeroes, open loop controller requested
        return sos, k
    if len(z) == 0 and len(p) == 0: # scaled output, special case to avoid ex.
        sos = [[1,0,0,1,0,0]]
        return sos, k
    (zs,ps) = sort_match(z,p)
    # print 'zs', zs
    # print 'ps', ps
    np = len(ps)
    sos = []
    h = 0
    for i in xrange(np//2): # first make second-order sections
        j = 2*i
        h = j+2 # k is gain (above)
        (b,a) = zpk2tf(zs[j:h],ps[j:h],1)
        # insert at head to write out sections in reverse order
        sos.insert(0,hstack((b,a)).tolist()) # return list not numpy array
    if np%2: # maybe one first-order section left over at the end
        (b,a) = zpk2tf(zs[h],ps[h],1) # b,a have 2 not 3 elements
        # like matlab put first-order section in first row of sosmatrix
        sos.insert(0,hstack((b,0,a,0)).tolist())
        istart = 1
    return sos, k # gain k factored out, return in same order as matlab tf2sos

"""
 Like our matlab biquad.m but more general, handles any n of stages
 Inputs: transfer function b, a coefficients, also coeff_frac_bits and gain
 Outputs: scaled integer coeffs for FPGA second order sections
 For 16-bit coeffs (as in Matt's FPGA code,flat-16 branches) coeff_frac_bits=14
 For 24-bit coeffs (as in recent flat-24 branches), coeff_frac_bits = 22
 gain parameter here multiplies gain implicit in b, a coeffs
"""
def biquad(bd, ad, coeff_frac_bits=22, gain=1.0):
    sos, g = tf2sos(bd,ad)
    sosm = array(sos)  # so we can use numpy, scipy
    nstages = len(sosm)
    g = g*gain    # combine gains: g from bd,ad; gain from parameter
    sgn = sign(g)
    gnn = sgn*g   # always non-negative
    gr = gnn**(1.0/nstages) # root, to spread gain evenly across all stages
    scale = 2**coeff_frac_bits
    sosm = scale*sosm             # scale all coeffs
    sosm[:,0:3] = gr*sosm[:,0:3]  # gain on b coeffs only
    sosm[0,0:3] = sgn*sosm[0,0:3] # sign on first stage b coeffs only
    sosm = around(sosm).astype(int) 
    sosm[:,4:6] = -sosm[:,4:6]    # Matt's sign convention for FPGA coeffs
    return sosm.tolist()          # works fine on 2d array

"""
compute discrete transfer function of a 2nd order lowpass system with
DC gain k, resonant frequency w, bandwidth B (where B = w/Q).
Continuous transfer function is

              k w^2
  H(s) = ----------------
          s^2 + Bs + w^2
"""
def lowpass2(wf=8e3, Bf=200, k=1, fs=5e5):  # wf, Bf, fs in Hz
    w = 2*pi*wf   # rad/sec           
    B = 2*pi*Bf
    b = [ k*(w**2) ]
    a = [ 1, B, w**2 ]
    (ba, aa) = bilinear(b,a,fs) # c2d, returns pair of numpy array
    b = ba.tolist()            
    a = aa.tolist()
    return b, a

def lowpass1(wf=8e3, k=1, fs=5e5):  # wf, fs in Hz
    w = 2*pi*wf   # rad/sec           
    b = [ k ]
    a = [ 1/w, 1 ]
    (ba, aa) = bilinear(b,a,fs) # c2d, returns pair of numpy array
    b = ba.tolist()            
    a = aa.tolist()
    return b, a

def main ():
    # flat controller from JG email 12 Jul 2006, see fpga-test.txt
    # Compare to output from biquad.m. This is for ~8 kHz at decim 128 (500kHz)
    bf = [-1.922105E-3, -2.584190E-3, 1.697985E-3, 2.360070E-3]
    af = [1.000000E+0, -2.805051E+0, 2.622746E+0, -8.157756E-1]

    # flat controller from Nov/Dec 2007 transfer function measurements
    # stored in params_11_21_07.h
    b_tf = [7.026189E-5, 1.027999E-4, -5.927540E-5, -9.181339E-5];
    a_tf = [1.000000E+0, -2.848528E+0, 2.708790E+0, -8.588522E-1];

    # heterodyne controller
    # bh, ah are intermediate results of foq14(0.004,0.008,8000,2,128)
    # as used in filter-acceptance.txt, 6 Jun 2006
    bh = [ 6.030039E-4,  6.030039E-4 ]
    ah = [ 1.0,         -9.999397E-1 ]

    print "compen"
    # compare to ct*s14.txt in ~/filter, by compen.m and compenwrite.m
    print 15, compen(15.0)
    print 30, compen(30.0)
    print 60, compen(60.0)
    print 90, compen(90.0)
    print 120, compen(120.0)
    print 180, compen(180.0)
    print -180, compen(-180.0)
    print -60, compen(-60.0)
    print -90, compen(-90.0)

    print
    print "tf2sos, flat controller"
    sosf, kf = tf2sos(bf,af)
    print 'kf:', kf
    print 'f: ', sosf[0]
    print '   ', sosf[1]

    print    
    print "tf2sos, heterodyne controller"
    sosh, kh = tf2sos(bh,ah)
    print 'kh:', kh
    print 'h: ', sosh[0]
    # print '   ', sosh[1] # There is no sosh[1], controller is simple

    print
    print "biquad, flat controller, 16 bits Q14"
    sosmf = biquad(bf,af)
    print 'f: ', sosmf[0]
    print '   ', sosmf[1]
    
    print
    print "biquad, flat controller, 24 bits Q22"
    sosmf22 = biquad(bf,af,22)
    print 'f: ', sosmf22[0]
    print '   ', sosmf22[1]

    print
    print "biquad, flat controller from params_11_21_07.h, 16 bits Q14"
    sosm_tf = biquad(b_tf,a_tf)
    print 'f: ', sosm_tf[0]
    print '   ', sosm_tf[1]
    
    print
    print "biquad, flat controller from params_11_21_07.h, 20 bits Q18"
    sosm_tf18 = biquad(b_tf,a_tf,18)
    print 'f: ', sosm_tf18[0]
    print '   ', sosm_tf18[1]
    
    print
    print "biquad, flat controller from params_11_21_07.h, 24 bits Q22"
    sosm_tf22 = biquad(b_tf,a_tf,22)
    print 'f: ', sosm_tf22[0]
    print '   ', sosm_tf22[1]

    print
    print "biquad, heterodyne controller"
    sosmh = biquad(bh,ah)
    print 'h: ', sosmh[0]
    # print '   ', sosmh[1] # no sosmh[1]
    
    print
    print "lowpass2"
    b,a = lowpass2()
    print "b: ", b
    print "a: ", a

    print
    print "lowpass1, w = 8e3, k=1, fs=5e5"
    b,a = lowpass1()
    print "b: ", b
    print "a: ", a

    print
    print "lowpass1, as in foq14.m, tau=0.0033 -> w=48 k=2, d = 4096 -> fs=15625"
    b,a = lowpass1(wf=48,k=2,fs=15625)
    print "b: ", b
    print "a: ", a

    print
    print "lowpass1, as in 6 Jun 2006 het, tau=0.0033 -> w=48 k=2, d = 128 -> fs= 5e5"
    b,a = lowpass1(wf=48,k=2,fs=5e5)
    print "b: ", b
    print "a: ", a

    print
    print "lowpass2 as above but with gain 0, open loop controller"
    b,a = lowpass2(k=0)
    print "b: ", b
    print "a: ", a
    
if __name__ == '__main__':
    main ()
