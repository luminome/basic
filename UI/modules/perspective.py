#!/usr/bin/env python3
from shapely.geometry import box, LineString
from scipy import spatial
import numpy as np
import basicGcodeCmds as bgc
from modules import circles, textures, characters

from plistLoader import PlistLoader, plistPath



LDLF = PlistLoader(plistPath())
LDLF.load_to_globals(globals(), ('MACH', 'GRBL', 'MAIN'))

MOUSE_GRID_SNAP = True

#
# In [1]: from scipy import spatial
#
# In [2]: import numpy as np
#
# In [3]: A = np.random.random((10,2))*100
#
# In [4]: A
# Out[4]:
# array([[ 68.83402637,  38.07632221],
#        [ 76.84704074,  24.9395109 ],
#        [ 16.26715795,  98.52763827],
#        [ 70.99411985,  67.31740151],
#        [ 71.72452181,  24.13516764],
#        [ 17.22707611,  20.65425362],
#        [ 43.85122458,  21.50624882],
#        [ 76.71987125,  44.95031274],
#        [ 63.77341073,  78.87417774],
#        [  8.45828909,  30.18426696]])
#
# In [5]: pt = [6, 30]  # <-- the point to find
#
# In [6]: AC[spatial.KDTree(AC).query(pt)[1]] # <-- the nearest point
# Out[6]: array([  8.45828909,  30.18426696])
#
# #how it works!
# In [7]: distance, index = spatial.KDTree(AC).query(pt)
#
# In [8]: distance # <-- The distances to the nearest neighbors
# Out[8]: 2.4651855048258393
#
# In [9]: index # <-- The locations of the neighbors
# Out[9]: 9
#
# #then
# In [10]: A[index]
# Out[10]: array([  8.45828909,  30.18426696])
#

bounds = box(-10, -10, X_PAGE + 10, Y_PAGE + 10)


#TODO: now scatter
#np.linalg.norm(from_array[:,:,None]-to_array[:,None,:], axis=0)

def perspective_point(r_loc, pn=0):
    GCODE = []
    pw = X_PAGE * 0.5
    v_offset = Y_PAGE * 0.5

    PL = [-pw, v_offset]
    PR = [pw + X_PAGE, v_offset]
    PZ = [X_PAGE / 2.0, Y_PAGE * 3.0]

    z_mint = 2 + np.random.random_sample() * 20

    # apt = np.array([X_PAGE,Y_PAGE])
    # r_loc = np.random.random_sample(2)*apt
    #r_len = 100*z_mint #(20+np.random.random_sample(3)*100.0)*z_mint

    r_len = np.empty(3)
    r_len.fill(10 * z_mint)

    pto = [PL, PR, PZ]
    lpt = []
    GCODE += bgc.probe_set_depth(r_loc[0], r_loc[1], 1.0)

    for n, t in enumerate(pto):
        tg = np.array(t)
        d = tg - r_loc
        c = np.linalg.norm(d)
        d_unit = (d / c)
        pts = np.array([r_len[n] * d_unit * -1, r_len[n] * d_unit]) + r_loc

        sh_graph_line = LineString(pts)
        gne = bounds.intersection(sh_graph_line)
        pts = np.array(gne.coords)

        cpp = r_loc - pts[0]
        cpc = np.linalg.norm(cpp)
        #if cpc:
        c_unit = (cpp / cpc)

        lpt.append([cpc, c_unit])
        GCODE += bgc.line([pts.tolist()], n)

    txpos = -1.0 * ((lpt[2][0] + 5.0) * lpt[2][1]) + r_loc

    # txpos = r_loc+(lpt[2][0]*1.1)
    f = characters.SAC_TEXT(pos=[txpos[0], txpos[1]], alignment='center')
    f.write((f'{pn:02}',), 0.3, 'normal')
    GCODE += bgc.line(f.lines_all, n)

    return GCODE


def get_scatter(ARRC):
    apt = np.array([X_PAGE, Y_PAGE])
    r_loc = np.random.random_sample(2) * apt

    if MOUSE_GRID_SNAP:
        r_loc = np.round(r_loc / GRID_SPACING) * GRID_SPACING
    #y = np.round(y/GRID_SPACING)*GRID_SPACING

    distance, index = spatial.KDTree(ARRC).query(r_loc)

    print(ARRC.shape[0], r_loc)
    print(distance, index)

    if distance < 200:
        get_scatter(ARRC)
    else:
        ARRC = np.vstack((ARRC, r_loc))

    return ARRC





def run_perspective():
    GCO = []
    centers = np.zeros([1, 2])

    for n in range(0, 40):
        centers = get_scatter(centers)

    for n in range(0, len(centers)):
        GCO += perspective_point(centers[n], n)

    return GCO



if __name__ == '__main__':
    pass



    #main()
    #point_loc = (_lim) * np.random.random_sample((1,2)) -(_lim/2)
    #left,right,top
