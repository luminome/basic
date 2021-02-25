#!/usr/bin/env python3
import numpy as np

from plistLoader import PlistLoader, plistPath
LDLF = PlistLoader(plistPath())

LDLF.load_to_globals(globals(), ('MACH', 'GRBL', 'MAIN'))




def rotate(npx, npy, a):
    """#utility ƒ"""
    nx = npx*np.cos(a)-npy*np.sin(a)
    ny = npy*np.cos(a)+npx*np.sin(a)
    return nx, ny





def derive(pos=None, delta=None, radius=1.0, sides=3, d=1.0, angle=0.0):
    
    if delta is None:
        delta = [0.0, 0.0]
    if pos is None:
        pos = [0.0, 0.0]

    n = [radius, 0.0]
    i = (2*np.pi)/sides
    rtd = []
    
    b = np.array(delta)
    a = np.array(pos)
    d = a-b
    #% measure angle
    
    ang = np.arctan2(d[1], d[0])
    #print(np.degrees(a))
    
    #TODO these r polygons and require closing point
    
    for p in range(0,sides+1):
        o = p*i
        x, y = rotate(n[0], n[1], o+ang)
        rtd.append([x+pos[0], y+pos[1]])

    return rtd
    pass


if __name__ == '__main__':
    pass
