#!/usr/bin/python3

# # https://en.wikipedia.org/wiki/Circular_segment
# h the sagitta (height) of the segment,
# c the chord length,
# R the radius of the circle,
# RTTL the central angle in radians,

import numpy as np

_resolution = 10

#utility ƒ
def rotate(npx, npy, a):
    nx = npx*np.cos(a)-npy*np.sin(a)
    ny = npy*np.cos(a)+npx*np.sin(a)
    return nx,ny

def circle_arc(ray,h,res=_resolution):
    a,b = ray
    d = b-a
    c = np.linalg.norm(d)

    d_u = (d / c)

    n_unit = np.empty_like(d_u)
    n_unit[0] = -d_u[1]
    n_unit[1] = d_u[0]

    s = ((b-a)/2)
    s += a

    h_pos = s+(n_unit*h)

    R = (h/2) + ((c*c)/(h*8))
    
    #angle
    RTTL = (2*(np.arcsin(c/(2*R))))

    #arc-length
    hd = h+((c*c)/(4*h))
    RAL = np.arcsin(c/hd)*hd
    
    if np.absolute(h) > np.absolute(R):
        sig = np.sign(RTTL)
        o = np.pi-(sig*RTTL)
        RTTL = (np.pi+o)*sig
        
    l = int(res*RAL)    
        
    RC = h_pos-(R*n_unit)
    OREL = b-RC
    RINT = RTTL/(l)

    print(R,RAL,np.degrees(RTTL))
        
    points = np.zeros([l+1,2])
    for i in range(0,l+1):
        points[i] = np.array([rotate(OREL[0],OREL[1],(i*RINT))])

    points += RC

    return points
    

def test():
    print('ok')

