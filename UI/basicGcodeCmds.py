#!/usr/bin/env python3

from plistLoader import PlistLoader, plistPath
LDLF = PlistLoader(plistPath())
LDLF.load_to_globals(globals(),('MACH','GRBL',))

def probe_set_depth(xf,yf,PAUSE=PAUSE_TWO,pulses=1):
    _cmd = []
    for p in range(0,pulses):
        _cmd += ["(probe_depth_adapt)"]
        _cmd += ["G0 X%.3f Y%.3f Z0 F%i" %(xf,yf,SEEK_RATE)]
        _cmd += ["G1 Z%i F%i" % (Z_DEPTH, FEED_RATE)]
        _cmd += ["G4 P%1.1f" % PAUSE]
        _cmd += ["G0 Z0 F%i" % SEEK_RATE]
        _cmd += ["(end_probe)"]
    return _cmd
    
def probe_hold_depth(xf,yf,PAUSE=PAUSE_ONE,pulses=1):
    _cmd = []
    for p in range(0,pulses):
        _cmd += ['(pause)']
        _cmd += ['G4 P%1.1f' % PAUSE]
        _cmd += ["(end_pause)"]
    return _cmd