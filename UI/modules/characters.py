#!/usr/bin/env python3
from plistLoader import PlistLoader, plistPath
LDLF = PlistLoader(plistPath())
LDLF.load_to_globals(globals(),('MACH','GRBL','MAIN'))

import numpy as np


#utility ƒ
def rotate(npx, npy, a):
    nx = npx*np.cos(a)-npy*np.sin(a)
    ny = npy*np.cos(a)+npx*np.sin(a)
    return nx,ny
    
    
"""C L A S S E S"""    
#_CLASS_ TEXT HANDLING
class SAC_TEXT:
    
    def __init__(self, string=None, scale=1.0, pos=[0.0,0.0], alignment='left', style='normal', angle=0, spacing=1.0):
        self.code = isinstance(string, int)
        self.string = string
        self.scale = scale
        self.position = pos
        self.angle = 0.0
        self.alignment = alignment
        self.styled = style
        self.gcode = []
        #self.bounds = []
        self.comments = []
        self.cursor = 0
        self.geometry = []
        self.charmap = {'normal':[],'bold':[]}
        self.charwidth = 10
        self.x_space = 2.5
        self.y_space = 2.5
        with open(CHARDATA_N,'r') as cfi: self.charmap['normal'] = [c.strip().split() for c in cfi.readlines()]
        with open(CHARDATA_B,'r') as cfi: self.charmap['bold'] = [c.strip().split() for c in cfi.readlines()]
        self.flat = []
        self.chardata_start_index = 0
        self.lines = []
        self.lines_total = 0
        self.lines_all = []
        
    def bounds(self):
        return np.array([np.amin(self.flat, axis=0),np.amax(self.flat, axis=0)]).flatten()
        
    def write(self, string=None, scale=1.0, pos=[0.0,0.0], alignment='left', style='normal', angle=0, spacing=1.0):
        if isinstance(string, str) or isinstance(string, int):
            self.lines = [string]
        else:
            self.lines = string
        
        if self.alignment == 'left': x_vary = 0.0
        if self.alignment == 'right': x_vary = -1.0
        if self.alignment == 'center': x_vary = -0.5
        points_one = []
        
        for j,line in enumerate(self.lines):
            if type(line) == int:
                points = [self.get_char_map(line, style)]
            else:
                points = [self.get_char_map(ord(char), style) for char in line]
            
            c = self.charwidth*scale
            xp = scale*self.x_space
            yp = scale*self.y_space
            line_width = (len(points)*(c+xp))-xp
            
            if self.lines_total == 0:
                self.cursor -= (c*0.5)
            else:
                self.cursor -= (c)
            
            for i,p in enumerate(points):
                m = np.array([i*(c+xp)+(line_width*x_vary), self.cursor])
                adj = [self.position+(np.array(q)*scale+m) for q in p]
                
                for v in adj:
                    v = [rotate(s[0],s[1],np.radians(self.angle)) for s in v]
                    for point in v:
                        self.flat += [point]
                    points_one.append(v)
            
            self.cursor -= (yp*spacing)
            self.lines_total += 1
                
        self.lines_all += points_one
        return points_one
        
    def get_char_map(self, char, style):
        #print(char)
        
        char_array = self.charmap['normal'][char] if style == 'normal' else self.charmap['bold'][char]
        chmap = [[char]]
        doc = ''

        for c in char_array:
            st_index = len(chmap)
            if c == '+':
                chmap.append([])
            elif c == '-':
                pass
            elif ',' in c:
                x,y = [float(x) for x in c.split(',')]
                chmap[st_index-1].append((x,y))
            else:
                chmap[st_index-1].append(c)
        
        g = chmap[1:]
        return g 


#_CLASS_ INDIVIDUAL CONTOUR HANDLING   
class SAC_SHAPE:
    def __init__(self, contour, index=0, valid=False, active=False, closed=False):
        self.id = index
        self.valid = valid
        self.active = active
        self.closed = closed
        self.polygon = None
        self.centroid = None
        self.bounds = None
        self.points = 0
        #print(type(contour))
        #contour is array or dict
        if contour is not None:
            if type(contour) == np.ndarray:
                e = np.flip(contour)
                self.contour = e #np.array(contour)
                self.validate()
            if type(contour) == dict:    
                self.load_from_dict(contour)
                self.validate()
        
    def coords(self):
        return np.array(self.polygon.exterior.coords).tolist()
        
    def load_from_dict(self, json_dict):
        def set(self,item,value):
            exec("self.{} = {}".format(item, value))
        blank = [set(self,k,json_dict[k]) for n,k in enumerate(json_dict)]
        #self.contour = np.array(self.polygon)
        
    def set_bounds(self):
        x1, y1, x2, y2 = self.polygon.bounds
        self.bounds = [(x1,y1),(x1,y2),(x2,y2),(x2,y1),(x1,y1)]
            
    def validate(self):
        self.contour = np.array(self.contour)
        self.closed = np.array_equal(self.contour[0],self.contour[-1])
        outline = LineString(self.contour)    
        outline = outline.simplify(0.88, preserve_topology=True)
        outline = chaikins_corner_cutting(outline.coords, 2, self.closed)
        self.points = len(outline)
        self.polygon = Polygon(outline)
        self.centroid = self.polygon.centroid.coords[0]
        
        x,y = self.centroid
        XY = Point(x,y)
        self.active = PARAMS_BOX.contains(XY)
        
        self.set_bounds()
        pass

    def __iter__(self):
        df = vars(self)
        for e in df:
            yield e, df[e] if type(df[e]) not in (Polygon, np.ndarray) else type(df[e]) # if len(df[e]) < 20 else len(df[e])
        
    def save_to_json(self):
        df = vars(self)
        tf = {}

        for e in df:
            if type(df[e]) == Polygon:
                tf[e] = np.array(df[e].exterior.coords).tolist()
            elif type(df[e]) == np.ndarray:
                tf[e] = df[e].tolist()
            else:    
                tf[e] = df[e]
                
        return tf
        