#!/usr/bin/env python3
import numpy as np
import basicGcodeCmds as bgc
from modules import circles, textures, characters

from plistLoader import PlistLoader, plistPath
LDLF = PlistLoader(plistPath())
LDLF.load_to_globals(globals(),('MACH','GRBL','MAIN'))








#utility ƒ
def rotate(npx, npy, a):
    nx = npx*np.cos(a)-npy*np.sin(a)
    ny = npy*np.cos(a)+npx*np.sin(a)
    return nx,ny





def derive(pos=[0.0,0.0], radius=1.0, sides=3, scale=1.0, d=1.0, delta=None, angle=0.0):
    
    n = [radius,0.0]
    i = np.pi/sides
    rtd = []
    
    #these r polygons and require closing point
    
    for p in range(0,sides+1):
        o = p*i
        p = rotate(n[0],n[1],o)
        rtd.append(p)
    #p = pos+
    
    print(rtd)
    pass

if __name__ == '__main__':
    
    pass
    #def poly(pos=[0,0],radius=1.0,sides=3,angle=0.0,)
    
    