#!/usr/bin/python3
import numpy as np
from shapely.geometry import box, Point, Polygon, LineString, MultiLineString
from shapely import affinity

def polygon_max(poly):
    distances = []
    hull = poly.convex_hull    
    c = hull.centroid.coords[0]
    points = hull.exterior.coords
    
    for i in range(0,len(points)):
        a = np.array(points[i])
        for j in range(0,len(points)):
            if j!=i:
                b = np.array(points[j])
                d = np.linalg.norm(b-a)        
                distances.append([d,[a,b]])
        
    distances.sort(key=lambda x: x[0])
    distances.reverse()
    ray = np.array(distances[0][1])
    dist = distances[0][0]
    
    #print('max',dist,'points:',len(points),'comparisons:',len(distances))
    return dist,ray,hull

def make_cell(texture,mm_size,pos,d,angle=0.0,ost=0.0):

    n_offset = 0.0
    mod = (d/2 % mm_size)/mm_size
    if mod > 0.6 or mod < 0.1: n_offset = mm_size/2.0
    
    if texture == 'dust':
        pass
        
    if texture == 'lines':
        npoints = []
        n = np.arange(0,d+(mm_size*2),mm_size)
        no = (np.floor(len(n)/2)*mm_size)-n_offset
        o = np.array([d/2,no])
        
        for y in range(0,len(n)):
            a = (0,n[y])
            b = (d,n[y])
            l = np.array([a,b])+(pos-o)
            npoints.append(l)
        
    if texture == 'circles':
        n = np.arange(0,d,mm_size)
        d_offset = (((len(n)-1)+ost)*mm_size)+n_offset
        npoints = []
        px,py = pos
        pos_center = [(px+(d_offset))+ost,py]
        
        n = np.arange(0,d*2,mm_size)
        for x in range(1,len(n)-1):
            p = Point(pos_center).buffer(n[x],resolution=2+int(x*1.0))
            cc = LineString(p.exterior.coords)
            npoints.append(np.array(cc.coords))
            
    lines = MultiLineString(npoints)
    lines = affinity.rotate(lines, angle, origin=(pos[0],pos[1]), use_radians=False)

    return lines

def textured_poly(N_POLY,point_loc,texture='lines',mm_size=1.0,angle=0.0,ost=0.0):
    #print(angle)
    _d,ray,poly_hull = polygon_max(N_POLY)    
    test_center = poly_hull.centroid.coords[0]
    rx,ry = test_center

    cell = box(_d/-2,_d/-2,_d/2,_d/2)
    cell = affinity.translate(cell,rx,ry)
    cell = affinity.rotate(cell, angle, origin=(rx,ry), use_radians=False)

    while cell.contains(poly_hull) == False:
        cell = affinity.scale(cell,1.01,1.01)
        _d *= 1.01

    #MultiLineString here
    lines = make_cell(texture, mm_size, pos=np.array(test_center), d=_d, angle=angle, ost=ost)
    
    output_shapes = []
    for ct,line in enumerate(lines):
        i = poly_hull.intersection(line)
        if i:
            try:
                npl = np.array(i.coords)
                if ct % 2 == 0: npl = np.flipud(npl)
                output_shapes.append(npl)
            except (NotImplementedError,IndexError):
                pass

    return output_shapes

def texture(type="circles",angle=0.0):
    
    _lim = 40
    _width = 200
    _angle = 0.0 #90.0 # np.degrees(np.pi/12)

    #point_loc = (_lim) * np.random.random_sample((1,2)) -(_lim/2)
    point_width = (_width/2)+(_width * np.random.random_sample())

    point_loc = [900,500]

    r = 8+int(point_width/3)

    N_POLY = Point(point_loc).buffer(point_width,resolution=r)

    #array of LineStrings as np
    return textured_poly(N_POLY,point_loc,texture='circles',mm_size=10,angle=angle,ost=-4)
    





