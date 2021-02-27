#!/usr/bin/env python3
import numpy as np
import sys
from shapely.geometry import box, LineString, MultiLineString, Polygon, LinearRing
from shapely.ops import linemerge

sys.path.insert(1, '/Users/sac/Sites/basic/UI')

from plistLoader import PlistLoader, plistPath

LDLF = PlistLoader(plistPath())
#LDLF = PlistLoader('../basic-plist.json')

LDLF.load_to_globals(globals(), ('MACH', 'GRBL', 'MAIN'))

bounds = box(-10, -10, X_PAGE+10, Y_PAGE+10)
bounds = Polygon(bounds)


def rotate(npx, npy, a):
    """#utility ƒ"""
    nx = npx*np.cos(a)-npy*np.sin(a)
    ny = npy*np.cos(a)+npx*np.sin(a)
    return nx, ny


def derive(pos=None, delta=None, radius=1.0, sides=3, rmin=None, angle=0.0):
    
    if delta is None:
        delta = [0.0, 0.0]
    if pos is None:
        pos = [0.0, 0.0]
    if rmin:
        radius *= rmin+(np.random.random_sample()*(1-rmin))

    n = [radius, 0.0]
    i = (2*np.pi)/sides
    rtd = []
    
    b = np.array(delta)
    a = np.array(pos)
    d = a-b
    #//% measure angle
    ang = np.arctan2(d[1], d[0])
    #print(np.degrees(a))

    #//these r polygons and require closing point
    for p in range(0, sides):
        o = p*i
        x, y = rotate(n[0], n[1], o+ang+angle)
        rtd.append([x+pos[0], y+pos[1]])

    ring = LinearRing(rtd)
    gne = ring.intersection(bounds)
    pts = []

    if type(gne) == MultiLineString:
        pm = linemerge(gne)
        #for pt in gne:
        pts.append(np.array(pm.coords).tolist())

    else:
        pts.append(np.array(gne.coords).tolist())

    return pts
    pass


if __name__ == '__main__':
    MOD_POLY['pos'] = [100, 100]
    MOD_POLY['delta'] = [0, 0]
    MOD_POLY['radius'] = 200
    rpt = derive(**MOD_POLY)
    print(rpt)

    pass


"""
        # # Put the sub-line coordinates into a list of sublists
        # outcoords = [list(i.coords) for i in gne]
        # 
        # # Flatten the list of sublists and use it to make a new line
        # outline = LineString([i for sublist in outcoords for i in sublist])

        #pts = np.array([np.array(x.coords) for x in pert])  # np.array([dx.coords for dx in pert[1:]])
        #pts = np.array(pld) #+np.array(gne[1].coords)
        #pert = sorted(gne, key=lambda sx: (len(sx.coords)))
        # #gne.sort(key=len)
        # pert = list(gne)
        # pert.sort(key=len(coords))pert
        # print(pert)
        #an = np.empty([0, 2])  #np.array([0,0])
        # for lr in gne:
        #     print(type(lr), len(lr.coords))
        #     pn = np.array(lr.coords)
        #     an = np.vstack((an, pn))
        # 
        # lp = LineString(an[:-1])
        # pts.append(np.array(lp.coords).tolist())
"""