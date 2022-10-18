# cserver.py, begun from mrfm_fft.py in GNU Radio
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

from gnuradio import gr, gru
from gnuradio import usrp
from gnuradio import eng_notation
from gnuradio.eng_option import eng_option
from optparse import OptionParser
import sys
import mrfm
import socket
import threading
import os
import signal
from time import strftime
from params import params2sos # params imports tf transfer function utilities
from tf import scale

# wx imports only if -S, -W , or -T option

default_port = 8000
default_wc = 8e3
# coeff_frac_bits = 14 # now this is a command option -q --coeff_frac_bits
#                         different from options.frac_bits, 22 for 24bit data

# filter coeffs used by both app_flow_graph and input_watcher, below
# just translate from array elements to discrete variables from Matt's code
# Note order of returned coeffs, must match in caller
# Uses coeff_frac_bits (not frac_bits) to scale default b01 and b00
def assign_ba(ba, coeff_frac_bits):
    b01 = 2 ** coeff_frac_bits # defaults, recall ** is exp, ^ is bitwise XOR
    b00 = -b01 # to get non-inverting overall
    b10 = b20 = a10 = a20 = b11 = b21 = a11 = a21 = 0 # defaults
    if len(ba) >= 6:
        b00 = -ba[0]; b10 = -ba[1]; b20 = -ba[2]; a10 = ba[4]; a20 = ba[5]
    if len(ba) >= 12:
        b01 = ba[6]; b11 = ba[7]; b21 = ba[8]; a11 = ba[10]; a21=ba[11]
    return b00, b10, b20, a10, a20, b01, b11, b21, a11, a21

# ditto for compensator coeffs, note cscale is cs[4]
def assign_cs(cs):
    c11 = c22 = 1
    c12 = c21 = cscale = 0
    if len(cs) >= 5:
        c11 = cs[0]; c12 = cs[1]; c21 = cs[2]; c22 = cs[3]; cscale = cs[4]
    return c11, c12, c21, c22, cscale

# structure based in input_watcher in scopesink, used by app_flow_graph, below
class socket_watcher (threading.Thread):
    def __init__ (self, flowgraph, options, **kwds):
        threading.Thread.__init__ (self, **kwds)
        self.fg = flowgraph
        self.options = options
        self.count = 0 # count all messages from program startup
        self.start()

    def run(self):
        # This all needs its own thread, see input_watcher in scopesink.py
        if self.options.debug:
            # fragile but informative: traceback and exit if not one of these
            receivedExceptions =  (ValueError, IOError, IndexError)
        else:
            # robust but uninformative: handle all standard exceptions
            # at http://docs.python.org/api/standardExceptions.html
            # except base classes and KeyboardInterrupt and WindowsError
            # (not exactly the same list as in Python Nut. p. 110-111
            receivedExceptions = (AssertionError,AttributeError,EOFError,FloatingPointError,IOError,ImportError,IndexError,KeyError,MemoryError,NameError,NotImplementedError,OSError,OverflowError,ReferenceError,RuntimeError,SyntaxError,SystemError,SystemExit,TypeError,ValueError,ZeroDivisionError)
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.bind(('',self.options.port))  # '' means accept any host
        print "Listening on port", self.options.port, "..."
        self.sock.listen(1) 

        # why are count, sock both self. here?  Aren't they local to run?

        try: # accept socket connection, finally ... not except ...
            while True:
                newSocket, (address, port) = self.sock.accept() # BLOCKING
                print "Connected from", address, strftime(' %m/%d/%y %I:%M:%S %p')
                keep_reading = True;
                while keep_reading:
                    self.count = self.count + 1  # print to show message rcvd
                    try: # receive from socket
                        receivedData = newSocket.recv(1024)  # bufsize
                        if not receivedData:
                            # if partner closed connection, exit loop and close
                            keep_reading = False
                            raise IOError, "Partner closed connection"
                        # print ':', self.count, ':', len(receivedData), ':', receivedData
                        print 'Received message %d, %d characters, %s ...' \
                                 % (self.count, len(receivedData), receivedData[0:7])             
			if self.options.verbose:
            		    print receivedData

                            # try: # parsing message, loading USRP
                            if receivedData.startswith('Gains:'):
                                    # print "scales message detected"  # placeholder
                                    print receivedData[6:]
                                    ks = [ scale(float(f), self.options.frac_bits) \
                                           for f in receivedData[6:].split(', ') ]
                                    print "Scales: k1=%d k2=%d" % (ks[0],ks[1])
                                    if self.options.bitstream:
                                        self.fg.u.set_scales(ks[0], ks[1])
                            else: # params message, throw exception if other format
                                    ba, cs, wc, heterodyne = params2sos(receivedData, \
                                                                self.options.coeff_frac_bits)
                                    # if heterodyne: print '> heterodyne'
                                    # else: print '> flat'

                                    b00, b10, b20, a10, a20, b01, b11, b21, \
                                         a11, a21 = assign_ba(ba, self.options.coeff_frac_bits)
                                    # print b00, b10, b20, a10, a20, b01, b11, b21, \
                                    #      a11, a21, ':', self.options.coeff_frac_bits # debug
                                    print "Biquad 0 : b2=%d b1=%d b0=%d a2=%d a1=%d" % (b20,b10,b00,a20,a10)
                                    print "Biquad 1 : b2=%d b1=%d b0=%d a2=%d a1=%d" % (b21,b11,b01,a21,a11)
                                    if self.options.bitstream:
                                        # frac_bits not coeff_frac_bits for shifter in FPGA
                                        self.fg.u.set_coeffs(self.options.frac_bits,b20,b10,b00,
                                                             a20,a10,b21,b11,b01,a21,a11)
                                        if heterodyne:
                                            c11, c12, c21, c22, cscale = assign_cs(cs)
                                            # print c11, c12, c21, c22, cscale # debug
                                            if self.options.bitstream:
                                                self.fg.u.set_compensator(c11,c12,c21,c22,cscale)
                                                self.fg.u.set_center_freq(wc)
                                # reply to client expected, see LabVIEW CClient,Cserver
                                # send "Q" only AFTER successfully loading USRP
                            newSocket.sendall("Q") #reverse engineered from Cserver
                            # except receivedExceptions: # try parsing, loading
                               # newSocket.sendall("0") # error reply
                               #  print "Exception parsing message", self.count, "or loading USRP"
                    # except receivedExceptions: # try: receive from socket
                    except:
                        # if process message failed, just wait to read again
                        print "Exception receiving  message", self.count
                newSocket.close()
                print "Disconnected from", address, strftime(' %m/%d/%y %I:%M:%S %p')
        finally: # try: accept socket connection 
            print "Socket watcher thread exiting", strftime(' %m/%d/%y %I:%M:%S %p')
            self.sock.close()

def pick_subdevice(u):
    """
    The user didn't specify a subdevice on the command line.
    If there's a daughterboard on A, select A.
    If there's a daughterboard on B, select B.
    Otherwise, select A.
    """
    if u.db[0][0].dbid() >= 0:       # dbid is < 0 if there's no d'board or a problem
        return (0, 0)
    if u.db[1][0].dbid() >= 0:
        return (1, 0)
    return (0, 0)

def read_ints(filename):
    try:
        f = open(filename)
        ints = [ int(i) for i in f.read().split() ]
        f.close()
        return ints
    except:
        print "Couldn't read", filename
        return []

class nogui_flow_graph(gr.top_block):
    def __init__(self):
        gr.top_block.__init__(self)

        # No GUI calls here, all deferred to app_flow_graph, below
        
        parser = OptionParser(option_class=eng_option)
        parser.add_option("-v", "--verbose", action="store_true", default=False,
                          help="Verbose output")
        parser.add_option("-D", "--debug", action="store_true", default=False,
                          help="Debug mode, some exceptions cause traceback and exit")
        parser.add_option("-p", "--port", type="int",
                          default=default_port,
                          help="port number [default=%s]" % default_port)
        parser.add_option("-R", "--rx-subdev-spec", type="subdev", default=None,
                          help="select USRP Rx side A or B (default=first one with a daughterboard)")
        parser.add_option("-d", "--decim", type="int", default=16,
                          help="set fgpa decimation rate to DECIM [default=%default]")
        parser.add_option("-f", "--freq", type="eng_float", default=default_wc,
                          help="set frequency to FREQ", metavar="FREQ")
        parser.add_option("-g", "--gain", type="eng_float", default=None,
                          help="set RxPGA gain in dB, 0..20 dB (default is midpoint)")
        parser.add_option("-G", "--txgain", type="int", default=255,
                          help="set TxPGA gain, 0..255 is -20..0 dB [default=%default]")
        parser.add_option("-8", "--width-8", action="store_true", default=False,
                          help="Enable 8-bit samples across USB")
        parser.add_option("-S", "--oscilloscope", action="store_true", default=False,
                          help="Enable oscilloscope display")
        parser.add_option("-T", "--fft", action="store_true", default=False,
                          help="Enable FFT display")
        parser.add_option("-W", "--waterfall", action="store_true", default=False,
                          help="Enable waterfall display")
        parser.add_option("-F", "--filename", default=None,
                          help="Name of file with filter coeffs, sos format")
        parser.add_option("-P", "--pfilename", default=None,
                          help="Name of file with filter coeffs, params.h format")
        # -Q --frac_bits for data path is different from -q --coeff_frac_bits
        # frac_bits is only used by set_coeffs in mrfm.py to configure shifter
        # A given FPGA program (.rbf file) requires particular -Q and -q 
        # Most .rbf after Dec 2007 require -Q 22 and -q 22 (before, was -q 14)
        parser.add_option("-Q", "--frac_bits", type="int", default=22,
                          help="fraction bits in data path [default=22]")
        parser.add_option("-q", "--coeff_frac_bits", type="int", default=22,
                          help="fraction bits in filter coeffs [default=22]")
        parser.add_option("-C", "--cfilename", default=None,
                          help="Name of file with compensator coefficients")
        parser.add_option("-B", "--bitstream", default=None,
                          help="Name of FPGA Bitstream file (.rbf)")
        parser.add_option("-n", "--frame-decim", type="int", default=20,
                          help="set oscope frame decimation factor to n [default=20]")
        
        (options, args) = parser.parse_args()
        if len(args) != 0:
            parser.print_help()
            sys.exit(1)

        self.options = options # so app_flow_graph can get at it

        # defaults in case no files provided or readable
        ba, cs, wc, heterodyne = ([], [], default_wc, False)

        if options.filename:
            # print "-F ", options.filename
            ba = read_ints(options.filename)

        if options.cfilename:
            # print "-C ", options.cfilename
            cs = read_ints(options.cfilename)

        wc = options.freq 
        if options.pfilename:
           #  print "-P ", options.pfilename
            try: 
                f = open(options.pfilename)
                ba, cs, wc, heterodyne = params2sos(f.read(), options.coeff_frac_bits)
                f.close()
            except:
                pass # defaults already assigned above

        # print "ba ", ba
        b00, b10, b20, a10, a20, b01, b11, b21, a11, a21 = \
             assign_ba(ba, options.coeff_frac_bits)
        # print b00, b10, b20, a10, a20, b01, b11, b21, a11, a21, ':', options.coeff_frac_bits

        c11, c12, c21, c22, cscale = assign_cs(cs)
        # print c11, c12, c21, c22, cscale

        # Set up socket, start thread to listen for connections and read
        self.socket_watcher = socket_watcher(self, options)

        if options.bitstream:

            # build the graph
            self.u = mrfm.source_c(options.bitstream)

            self.u.set_decim_rate(options.decim)
            self.u.set_center_freq(wc)

            # Initially both switches open, gain = 0
            # Must send message to close one or both switches
            k0 = scale(0.0, options.frac_bits)
            k1 = scale(0.0, options.frac_bits)
            self.u.set_scales(k0, k1)
                              
            # options.frac_bits = 14 # now set by -Q option
            # NOT coeff_frac_bits, this is frac_bits passed to shifter in FPGA
            self.u.set_coeffs(options.frac_bits,b20,b10,b00,a20,a10,b21,b11,b01,a21,a11)
            self.u.set_compensator(c11,c12,c21,c22,cscale)

            if options.rx_subdev_spec is None:
                options.rx_subdev_spec = pick_subdevice(self.u)
            self.u.set_mux(usrp.determine_rx_mux_value(self.u, options.rx_subdev_spec))

            if options.width_8:
                width = 8
                shift = 8
                format = self.u.make_format(width, shift)
                print "format =", hex(format)
                r = self.u.set_format(format)
                print "set_format =", r

            # determine the daughterboard subdevice we're using
            self.subdev = usrp.selected_subdev(self.u, options.rx_subdev_spec)

            #input_rate = self.u.adc_freq() / self.u.decim_rate()
            input_rate = self.u.adc_freq() / options.decim
            self.input_rate = input_rate   # So app_flow_graph below can use it
            
            # fft_rate = 15
            fft_rate = 5
            self.fft_rate = fft_rate   # So app_flow_graph below can use it
            
            # if options.no_gui:
            self.sink = gr.null_sink(gr.sizeof_gr_complex) # throttled by USRP
            self.connect(self.u, self.sink)

            # set initial values
            if options.gain is None:
                # if no gain was specified, use the mid-point in dB
                g = self.subdev.gain_range()
                options.gain = float(g[0]+g[1])/2

            #if options.no_gui:
            self.subdev.set_gain(options.gain)
            # print "options.gain ", options.gain, " RxPGA gain", self.u.pga(0)

            # Can't use subdev.set_gain for other subdev, u.set_pga instead
            self.u.set_pga(1, options.gain) # first arg is other subdev
            
            self.u._write_9862(0,16,options.txgain) # from mrfm_gui.py
            # print "options.txgain ", options.txgain, " TxPGA gain", self.u._read_9862(0,16)

            if wc is None:
                # if no freq was specified, use the mid-point
                r = self.subdev.freq_range()
                wc = float(r[0]+r[1])/2
            self.wc = wc # So app_flow_graph below can use it
            
            r = self.u.tune(0, self.subdev, wc)
            if not r:
                print "Failed to set initial frequency"
            self.r = r   # So app_flow_graph below can use it
            
class app_flow_graph(nogui_flow_graph):
    def __init__(self, frame, panel, vbox, argv):
        nogui_flow_graph.__init__(self)

        # graphics ONLY follows, what we could NOT do in nogui_flow_graph 
        self.frame = frame
        self.panel = panel

        if self.options.waterfall and self.options.bitstream:
            self.scope1=waterfallsink2.waterfall_sink_c (panel, fft_size=1024, sample_rate=self.input_rate,
                                                        fft_rate=self.fft_rate)
            self.scope2=waterfallsink2.waterfall_sink_c (panel, fft_size=1024, sample_rate=self.input_rate,
                                                        fft_rate=self.fft_rate)

        elif self.options.oscilloscope and self.options.bitstream:
            self.scope1 = scopesink2.scope_sink_c(panel, sample_rate=self.input_rate,frame_decim=self.options.frame_decim) # added option JPJ 4/21/2006
            self.scope2 = scopesink2.scope_sink_c(panel, sample_rate=self.input_rate,frame_decim=self.options.frame_decim) 

        elif self.options.fft and self.options.bitstream:
            self.scope1 = fftsink2.fft_sink_c (panel, fft_size=1024, sample_rate=self.input_rate,
                                             fft_rate=self.fft_rate)
            self.scope2 = fftsink2.fft_sink_c (panel, fft_size=1024, sample_rate=self.input_rate,
                                             fft_rate=self.fft_rate)
        else:
            # create minimal panel, must be an easier way, just imitate for now
            messages = form.form()
            vbox.Add((0,10),0)
            hbox = wx.BoxSizer(wx.HORIZONTAL)
            messages['no_USRP'] = form.static_text_field(parent=panel,sizer=hbox)
            messages['no_USRP'].set_value("          USRP not connected           ")
            vbox.Add(hbox, 0, wx.EXPAND)
            vbox.Add((0,10), 0)
            return # but socket_watcher thread keeps running

        self.show_debug_info = True  # turns on some display features, below

        self.deint = gr.deinterleave(gr.sizeof_gr_complex)
        self.connect(self.u,self.deint)

        # to show I, I' on top scope panel, Q, Q' on bottom
        # use code omitted here, find in earlier versions
        self.connect ((self.deint,0),self.scope1)
        self.connect ((self.deint,1),self.scope2)

        self._build_gui(vbox)  

        # update displayed values only, nogui_flow_graph  already set USRP
        self.myform['gain'].set_value(self.options.gain)

        if self.r:  # assigned by ngui_flow_graph above when it set USRP
            self.myform['freq'].set_value(self.wc) # update displayed value
            if self.show_debug_info:
                self.myform['baseband'].set_value(self.r.baseband_freq)
                self.myform['ddc'].set_value(self.r.dxc_freq)
        else:
            self._set_status_msg("Failed to set initial frequency")

        if self.show_debug_info:
            self.myform['decim'].set_value(self.u.decim_rate())
            self.myform['fs@usb'].set_value(self.u.adc_freq() / self.u.decim_rate())
            self.myform['dbname'].set_value(self.subdev.name())

    def _set_status_msg(self, msg):
        self.frame.GetStatusBar().SetStatusText(msg, 0)

    def _build_gui(self, vbox):

        def _form_set_freq(kv):
            return self.set_freq(kv['freq'])
            
        vbox.Add(self.scope1.win, 10, wx.EXPAND)
        vbox.Add(self.scope2.win, 10, wx.EXPAND)
        
        # add control area at the bottom
        self.myform = myform = form.form()
        hbox = wx.BoxSizer(wx.HORIZONTAL)
        hbox.Add((5,0), 0, 0)
        myform['freq'] = form.float_field(
            parent=self.panel, sizer=hbox, label="Center freq", weight=1,
            callback=myform.check_input_and_call(_form_set_freq, self._set_status_msg))

        hbox.Add((5,0), 0, 0)
        g = self.subdev.gain_range()
        myform['gain'] = form.slider_field(parent=self.panel, sizer=hbox, label="Gain",
                                           weight=3,
                                           min=int(g[0]), max=int(g[1]),
                                           callback=self.set_gain)

        hbox.Add((5,0), 0, 0)
        vbox.Add(hbox, 0, wx.EXPAND)

        self._build_subpanel(vbox)

    def _build_subpanel(self, vbox_arg):
        # build a secondary information panel (sometimes hidden)

        # FIXME figure out how to have this be a subpanel that is always
        # created, but has its visibility controlled by foo.Show(True/False)
        
        if not(self.show_debug_info):
            return

        panel = self.panel
        vbox = vbox_arg
        myform = self.myform

        #panel = wx.Panel(self.panel, -1)
        #vbox = wx.BoxSizer(wx.VERTICAL)

        hbox = wx.BoxSizer(wx.HORIZONTAL)
        hbox.Add((5,0), 0)
        myform['decim'] = form.static_float_field(
            parent=panel, sizer=hbox, label="Decim")

        hbox.Add((5,0), 1)
        myform['fs@usb'] = form.static_float_field(
            parent=panel, sizer=hbox, label="Fs@USB")

        hbox.Add((5,0), 1)
        myform['dbname'] = form.static_text_field(
            parent=panel, sizer=hbox)

        hbox.Add((5,0), 1)
        myform['baseband'] = form.static_float_field(
            parent=panel, sizer=hbox, label="Analog BB")

        hbox.Add((5,0), 1)
        myform['ddc'] = form.static_float_field(
            parent=panel, sizer=hbox, label="DDC")

        hbox.Add((5,0), 0)
        vbox.Add(hbox, 0, wx.EXPAND)

        
    def set_freq(self, target_freq):
        """
        Set the center frequency we're interested in.

        @param target_freq: frequency in Hz
        @rypte: bool

        Tuning is a two step process.  First we ask the front-end to
        tune as close to the desired frequency as it can.  Then we use
        the result of that operation and our target_frequency to
        determine the value for the digital down converter.
        """
        r = self.u.tune(0, self.subdev, target_freq)
        
        if r:
            self.myform['freq'].set_value(target_freq)     # update displayed value
            if self.show_debug_info:
                self.myform['baseband'].set_value(r.baseband_freq)
                self.myform['ddc'].set_value(r.dxc_freq)
            return True

        return False

    def set_gain(self, gain):
        self.myform['gain'].set_value(gain)     # update displayed value
        self.subdev.set_gain(gain)

def main ():
    # module names declared global for conditional imports in 'else', below
    global wx, stdgui2, fftsink2, waterfallsink2, scopesink2, form, slider
    if '-S' in sys.argv or '-T' in sys.argv or '-W' in sys.argv:
        print "Starting GUI, close panel to exit"
        import wx
        from gnuradio.wxgui import stdgui2, fftsink2, waterfallsink2, scopesink2, form, slider
        app = stdgui2.stdapp(app_flow_graph, "USRP OSCILLOSCOPE", nstatus=1)
        app.MainLoop()
        # after exit from GUI, kill thread,closes socket, sys.exit doesn't work
        os.kill(os.getpid(), signal.SIGINT) # No msg, SIGKILL prints "Killed" 
    else:
        print "Starting without GUI, close terminal window to exit"
        global fg # so we can access fg.u registers from shell after main exits
        fg = nogui_flow_graph()
        fg.start()
        # When main exits, thread keeps running
        # Start program python -i cserver.py ... to get python shell 
        # Must close terminal window to stop, ^C does not stop running thread

if __name__ == '__main__':
    main ()
