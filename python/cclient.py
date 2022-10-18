# This is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3, or (at your option)
# any later version.
# 
# This software is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

import sys
import socket
from params import tf2params
from tf import lowpass2, lowpass1

def print_commands():
    print "At the prompt, type one-character command followed by data" 
    print " h (or unrecognized cmd): help, print commands, data ignored"
    print " ?: send uninterpreted data (string) to server"
    print " !: send string, then close connection without reading server response"
    print " z: zero output always (open loop), data ignored"
    print " k: output is scaled input, data is gain"
    print " f: first order low-pass filter, data is corner frequency"
    print " s: second order low-pass filter, data is resonant frequency"
    print " t: transfer function, data is b coeffs, comma, then a coeffs"
    print " m: scale factors, data are k0 k1, usually 0 or 1"
    print " p: read from file in params.h format, data is filename"
    print " x (or RETURN, empty line): exit, data ignored"

def print_help():
    print "cclient: send controller transfer functions to cserver (cantilever server)"
    print " optional first argument: cserver port, default 8000"
    print " optional second argument: cserver host, default localhost"
    print_commands()

port = 8000
host = "localhost"

try:
    if len(sys.argv) > 1:
        port = int(sys.argv[1])
    if len(sys.argv) > 2:
        host = sys.argv[2]
except:
    print_help()
    sys.exit()

read_reply = True

nconnects = 0
ok = True
prompting = True
while ok and prompting:
    try:
        s = None
        cmd = raw_input("Type command + data, h for help, RETURN to exit: ")
        if cmd == '' or cmd == 'x':
            prompting = False
        elif cmd[0] == '?':  # ?: just pass command through uninterpreted
            s = cmd[2:]      # except skip first two char: '? '
        elif cmd[0] == '!':  # ?: just pass command through uninterpreted
            s = cmd[2:]      # except skip first two char: '? '
            read_reply = False;
        elif cmd[0] == 'z': # s: second order filter, open loop
            w = float(cmd[1:])
            b,a = lowpass2(w,k=0)
            s = tf2params(b,a)
        elif cmd[0] == 'k': # output is scaled input, data is gain
            k = float(cmd[1:])
            b = [ k ]
            a = [ 1 ]
            s = tf2params(b,a)
        elif cmd[0] == 'f': # f: first order filter, cmd is corner freq
            w = float(cmd[1:])
            b,a = lowpass1(w)
            s = tf2params(b,a)
        elif cmd[0] == 's': # second order filter, cmd is resonant freq
            w = float(cmd[1:])
            b,a = lowpass2(w)
            s = tf2params(b,a)
        elif cmd[0] == 't': # transfer function, b coeffs, comma, a coeffs
            print "Not yet implemented"
        elif cmd[0] == 'm': # scale factors, data are k0 k1, usually 0 or 1
            ks = [ float(x) for x in cmd[1:].split() ]
            s = "Gains: %.4E, %.4E" % (ks[0], ks[1])
        elif cmd[0] == 'p': # read, parse, send params.h file
            try:
                fname = cmd[1:].lstrip()
                f = open(fname) # filename, remove leading blanks
                s = f.read()
                f.close()
            except:
                print "Couldn't read", fname
        else:
            print_commands()
        if s:
            # similar to Python in a Nutshell (Mar 2003), Example 19-2 p.435
            # but cycle sending repeatedly, also try... except...
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect((host,port))  # note tuple arg
            nconnects = nconnects + 1
            print "Connection %d to %s, port %d" % (nconnects,host,port)
            sock.sendall(s)
            if read_reply:
                r = sock.recv(1024) # "Q" success, "0" error
                print "Server replied", r
            else:
                print "Close connection without reading server response"
                read_reply = True
            sock.close()
    except:
        # sock.close()  # shouldn't we test if it exists first?
        ok = False
if not prompting:
    print "Finished, cclient exiting"
if not ok:
    print "Socket operation failed, cclient exiting"
