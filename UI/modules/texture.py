#!/usr/bin/python3
import numpy as np
from shapely.geometry import box, Point, Polygon, LineString, MultiLineString
from shapely import affinity

def line_gcode(line_string_list):
    x,y = line_string_list[0]
    GRBLCMD = []
    GRBLCMD += ["G0 X%4.3f Y%4.3f Z0 F%i" % (x, y, SEEK_RATE)]
    GRBLCMD += ["G1 Z%i F%i" % (Z_DEPTH,FEED_RATE)]
    GRBLCMD += ["G4 P%1.1f" % PAUSE_ONE]
    for vertex in line_string_list: GRBLCMD += ["G1 X%4.3f Y%4.3f F%i" % (vertex[0], vertex[1], FEED_RATE)]
    GRBLCMD += ["G0 Z0"]
    return GRBLCMD
    
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





if __name__ == '__main__':
    import sys,os
    sys.path.insert(1, '/Users/sac/Sites/afsolo/')
    os.chdir('/Users/sac/Sites/afsolo/')
    
    import matplotlib.pyplot as plt
    from matplotlib.animation import FuncAnimation

    import variables
    variables.load(globals())

    fig, ax = plt.subplots()
    
    group = []
    
    def init():
        return group
    
    def update(iteration):
        global _angle
        _interval = (np.pi/8)
        _angle = 90.0 #_interval*iteration #np.ceil(_interval)

        ax.clear()
        _lim = 40
        _width = 20
        _angle = 0.0 #90.0 # np.degrees(np.pi/12)

        ax.set_xlim(-_lim, _lim)
        ax.set_ylim(-_lim, _lim)
        ax.set_aspect('equal', adjustable='box')

        point_loc = (_lim) * np.random.random_sample((1,2)) -(_lim/2)
        point_width = (_width/2)+(_width * np.random.random_sample())

        point_loc = [0,0]

        r = 8+int(point_width/3)
    
        N_POLY = Point(point_loc).buffer(point_width,resolution=r)
    
        #array of LineStrings as np
        lines = textured_poly(N_POLY,point_loc,texture='circles',mm_size=2,angle=_angle,ost=-4)
    
        #ax.plot(ray[:,0],ray[:,1], '-ro', markersize=1.5, linewidth=3.0)
        
        rx,ry = point_loc
        ax.plot(rx,ry,'-ro', markersize=4.5, alpha=1.0)
    

        GCO = []
        for line in lines:
            ax.plot(line[:,0],line[:,1], '-r', linewidth = 0.8)
            code = line_gcode(line)
            GCO += [code]
            #print(code)

        hull_geom = np.array(N_POLY.exterior.coords)
        ax.plot(hull_geom[:,0],hull_geom[:,1], '-ko', markersize=1.5, linewidth=0.5, alpha=0.25)


    animation = FuncAnimation(fig, update, init_func=init, interval=2000)#, blit=True)
    
    plt.show()   
    #print(hull)
    exit()
###################################################################################################




















"""














plt.show()   
#print(hull)
exit()
###################################################################################################



def init():
    return group
    
def update(iteration):
    global _angle
    _interval = (np.pi/8)
    _angle = _interval*iteration #np.ceil(_interval)
    
    point_loc = (_lim*2) * np.random.random_sample((1,2)) -_lim #PLACEMENT
    point_width = _width * np.random.random_sample() #9.45# _width+((_width * np.random.random_sample() -_width/2))

    r = 2+int(point_width/4)
    N_POLY = Point(point_loc[0]).buffer(point_width,resolution=r)
    
    #points_g = _lim * np.random.random_sample((15,2)) -_lim/2
    #N_POLY = Polygon(points_g+point_loc)
    
    lines = make_filled_shape(N_POLY,point_loc,point_width)
    
    for line in lines:
        ax.plot(line[:,0],line[:,1], '-r', linewidth = 0.8)
    
    hull_geom = np.array(N_POLY.exterior.coords)
    ax.plot(hull_geom[:,0],hull_geom[:,1], '-ko', markersize=1.5, linewidth=0.5, alpha=0.25)
    
animation = FuncAnimation(fig, update, init_func=init, interval=1)#, blit=True)



# for line in lines:
#     lp = np.array(line.coords)
#     ax.plot(lp[:,0],lp[:,1], '-ko', markersize=0.5, linewidth=0.5, alpha=0.5)


# gspacing 1 is every millimeter














#ax.plot(ray[:,0],ray[:,1], '-ro', markersize=1.5, linewidth=3.0)
# ax.plot(rx,ry,'-ro', markersize=4.5, alpha=0.25)
#
# cell_gm = np.array(cell.exterior.coords)
# ax.plot(cell_gm[:,0],cell_gm[:,1], '-bo', markersize=2.0, linestyle='--', linewidth=1.0, alpha=0.25)
#
# hull_geom = np.array(poly_hull.exterior.coords)
# ax.plot(hull_geom[:,0],hull_geom[:,1], '-ko', markersize=1.5, linewidth=0.5, alpha=0.25)
#










#TODO qualify if polygon
if style == 'buffer':
    point = _width * np.random.random_sample((1,2)) -_width/2
    _d = _width+((_width * np.random.random_sample() -_width/2)/2)
    x,y = point[0]
    ray = np.array([(x-_d,y),(x+_d,y)])
    poly_hull = Point(point[0]).buffer(_d)
    _d = np.ceil(_d*2)
else:
    points_g = _width * np.random.random_sample((12,2)) -_width/2
    test_poly = Polygon(points_g)
    _d,ray,poly_hull = polygon_max_dimension_g(test_poly)

test_center = poly_hull.centroid.coords[0]

































#
# _angle = np.pi/6
# cell_gm = np.array([spin(np[0], np[1], _angle) for np in cell_gm])
#




while p_box.contains(hull) == False:
    
    #cell_gm *= 0.01
    p_box = affinity.scale(p_box,1.01,1.01)
    cell_gm = np.array(p_box.exterior.coords)
    ax.plot(cell_gm[:,0],cell_gm[:,1], '-ro', markersize=2.0, linewidth=1.0, alpha=1.0)











def polygon_max_dimension(poly):
    distances = []
    hull = poly.convex_hull
    
    xc,yc = hull.centroid.coords[0]
    ray = LineString([(xc-_width,yc),(xc+_width,yc)])
    
    for r in range(0,180):
        i = hull.intersection(ray)
        if i:
            try:
                a = i.coords[0]
                b = i.coords[1]
                npl = np.array([a,b])
                c = np.linalg.norm(npl[1]-npl[0])
                distances.append([c,[a,b]])
            except IndexError:
                pass

        ray = affinity.rotate(ray, 1.0, origin=(xc,yc), use_radians=False)

    distances.sort(key=lambda x: x[0])
    distances.reverse()
    longest = distances[0]
    ray = np.array(longest[1])
    dist = longest[0]
    
    return dist,ray,hull 


def polygon_max_dimension_c(poly):
    distances = []
    hull = poly.convex_hull
    
    c = hull.centroid.coords[0]
    #xc,yc = c 
    #ray = LineString([(xc-_width,yc),(xc+_width,yc)])
    points = hull.exterior.coords
    for i in range(0,len(points)):
        p = np.array(points[i])
        d = np.linalg.norm(c-p)        
        distances.append([d,p])
        print(i)
        
    distances.sort(key=lambda x: x[0])
    distances.reverse()

    ray = np.array([distances[0][1],distances[1][1]])
    dist = np.linalg.norm(ray[1]-ray[0])
    
    return dist,ray,hull
    #print(distances)
    
        #
    #
    #
    #
    #
    # for r in range(0,180):
    #     i = hull.intersection(ray)
    #     if i:
    #         try:
    #             a = i.coords[0]
    #             b = i.coords[1]
    #             npl = np.array([a,b])
    #             c = np.linalg.norm(npl[1]-npl[0])
    #             distances.append([c,[a,b]])
    #         except IndexError:
    #             pass
    #
    #     ray = affinity.rotate(ray, 1.0, origin=(xc,yc), use_radians=False)
    #
    # distances.sort(key=lambda x: x[0])
    # distances.reverse()
    # longest = distances[0]
    # ray = np.array(longest[1])
    # dist = longest[0]
    #
    # return dist,ray,hull
    
    
def polygon_max_dimension_g(poly):
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
    
    print('max',dist,'points:',len(points),'comparisons:',len(distances))
    
    return dist,ray,hull



points_g = _width * np.random.random_sample((5,2)) -_width/2
test_poly = Polygon(points_g)

d,ray,hull = polygon_max_dimension_g(test_poly)










hull_geom = np.array(hull.exterior.coords)
ax.plot(hull_geom[:,0],hull_geom[:,1], '-ko', markersize=1.5, linewidth=0.5)
centr = hull.centroid.coords[0]
cx,cy = centr
ax.plot(cx,cy, '-ko', markersize=3.0, linewidth=0.5)

ax.plot(ray[:,0],ray[:,1], '-ro', markersize=1.5, linewidth=3.0)

cell = box(-d/2,-d/2,d/2,d/2)
cell_gm = np.array(cell.exterior.coords)

angle = np.pi/6
cell_gm = np.array([spin(np[0], np[1], angle) for np in cell_gm])






ax.plot(cell_gm[:,0],cell_gm[:,1], '-bo', markersize=2.0, linewidth=1.0, alpha=0.3)

#m = ray/2
#
# a,b = ray
# center = a+((b-a)/2)
# x,y = center
#
# ax.plot(x,y,'-ko', markersize=4.5, linewidth=1.0)

cell_gm += centr




p_box = Polygon(cell_gm)


while p_box.contains(hull) == False:
    
    #cell_gm *= 0.01
    p_box = affinity.scale(p_box,1.01,1.01)
    cell_gm = np.array(p_box.exterior.coords)
    ax.plot(cell_gm[:,0],cell_gm[:,1], '-ro', markersize=2.0, linewidth=1.0, alpha=1.0)



ax.plot(cell_gm[:,0],cell_gm[:,1], '-bo', markersize=2.0, linewidth=3.0, alpha=1.0)

plt.show()   
#print(hull)
exit()






#get shape
#get texture based on bounds #(minx, miny, maxx, maxy)
#get merged

def texture_cell_MultiLineString(shape_bounds,density,angle=0,pos=[0,0]):
    minx, miny, maxx, maxy = shape_bounds
    lim = max(maxx-minx,maxy-miny)
    
    number_of_lines = int(np.ceil(lim/density))
    lines = [[[0,e*density],[lim,e*density]] for e in range(0,number_of_lines)]
    texture = MultiLineString(lines)
    
    pr = (number_of_lines-1)*density
    poffset = pr/-2.0
    
    
    
    
    #texture = affinity.translate(texture, xoff=pos[0], yoff=pos[1])
    
    #base translation pos for sum of width and zero.
    
    #texture = affinity.rotate(texture, angle, origin=pos, use_radians=False)
    #
    
    
    
    
    return texture



r = 20.0
    
p = Point(0,0).buffer(r)


t = [(-2,-1),(2,-1),(0,3),(-2,-1)]
p = Polygon(t)



#p_center = p.centroid.coords[0]


minx, miny, maxx, maxy = p.bounds
xw = maxx-minx
yw = maxy-miny


p_center = np.array([0,0]) #,[maxx, maxy]]) #,[xw/2,yw/2])
prv = np.array(p.exterior.coords)
ax.plot(prv[:,0],prv[:,1], '-bo', markersize=0.5, linewidth = 1.0)

#TODO: bounds not good enough, find longest ray in the shape, or better yet, furthest distance.
# [n for n]
# #print(p_center)

#trying to design design rules here

texture = texture_cell_MultiLineString(p.bounds,0.15,45.0,p_center)    
circ = plt.Circle([0,0], radius=r, alpha=0.3)
ax.add_patch(circ)



for line in texture:
    npl = np.array(line.coords)
    ax.plot(npl[:,0],npl[:,1], '-go', markersize=0.5, linewidth = 0.5)
    i = p.intersection(line)

    if i:
        try:
            a = i.coords[0]
            b = i.coords[1]
            npl = np.array([a,b])








            ax.plot(npl[:,0],npl[:,1], '-ro', markersize=1.5, linewidth = 0.5)
        except IndexError:
            pass
        #
    #

#print(texture)





plt.show()    
    
    
    """

"""    
    



def COMMAND_HATCH_CIRCLE(radius,density_mm,angle_deg,pos):
    batch = []

    ax,ay = pos[0],pos[1]
    AR = math.ceil((2.0*radius)/density_mm) #: 80,4(mm) -> 20 lines 

    CENTER = (0,0)
    HATCH_OFFSET = 0.0 
    
    p = Point(0,0)
    c = p.buffer(radius).boundary
    
    AR_int = int(AR)

    HATCH_OFFSET = (((radius*2.0)-(density_mm*AR_int))/2.0)

    if (AR_int % 2) == 0: HATCH_OFFSET+=(density_mm/2.0)

    for i in range(0,AR_int):

        pax,pay = radius*-1.0, (radius*-1.0) + (i*density_mm) + HATCH_OFFSET
        pbx,pby = radius, (radius*-1.0) + (i*density_mm) + HATCH_OFFSET

        l = LineString([(pax,pay), (pbx,pby)])
        rotated_l = affinity.rotate(l, angle_deg, CENTER)

        i = c.intersection(rotated_l)
        
        if i:
            a = i.geoms[0].coords[0]
            b = i.geoms[1].coords[0]

            batch += ["G0 X%4.3f Y%4.3f F%i" % (ax+a[0], ay+a[1], GRBL_SEEK_RATE)]
            batch += ["G0 Z%i" % GRBL_Z_DEPTH]
            batch += ["G4 P%i" % GRBL_PAUSE_ONE]
            batch += ["G1 X%4.3f Y%4.3f F%i" % (ax+b[0], ay+b[1], GRBL_FEED_RATE)]
            batch += ["G0 Z0"]
    
    return batch


"""