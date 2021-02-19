#INIT UTILITY VARIABLE FILES
def init():
    f = open(CHARMAP_FILE,'r')
    global CHARMAP
    for line in f:
        l = line.split()
        CHARMAP.append(l)
    f.close()
    
    f = open(CHARMAP_BOLD_FILE,'r')
    global CHARMAP_BOLD
    for line in f:
        l = line.split()
        CHARMAP_BOLD.append(l)
    f.close()
    
    f = open(WORDS_FILE,'r')
    global WORDS
    for line in f:
        WORDS.append(line.rstrip())
    f.close()
    random.shuffle(WORDS)
    logger.info(['ƒ',__name__,inspect.stack()[0][3]])
    
    #logger.info(WORDS)
    
"""C L A S S E S"""    
#_CLASS_ TEXT HANDLING
class SAC_TEXT:
    
    def __init__(self, string, scale=[1.0,1.0], position=[0.0,0.0], alignment='center', style='plain', angle=0):
        self.code = isinstance(string, int)
        self.string = string
        self.scale = scale
        self.position = position
        self.angle = angle
        self.alignment = alignment
        self.styled = style
        
        self.gcode = []
        
        self.bounds = []
        self.comments = []
        self.geometry = []
        
        self.build_string()
        self.set_position(position)
            
    def get_bounds_list(self):
        n = np.array(self.bounds.exterior.coords)
        return n.tolist()
                
    def get_lines_list(self):
        e = [np.array(e.coords).tolist() for e in self.geometry]
        return e   
                
    def set_position(self,position=[0.0,0.0]):
        self.bounds = affinity.translate(self.bounds, xoff=position[0], yoff=position[1])
        self.geometry = affinity.translate(self.geometry, xoff=position[0], yoff=position[1])
        
    def move(self,position=[0.0,0.0]):
        pos_delta = np.array(position)-np.array(self.position)
        self.bounds = affinity.translate(self.bounds, xoff=pos_delta[0], yoff=pos_delta[1])
        self.geometry = affinity.translate(self.geometry, xoff=pos_delta[0], yoff=pos_delta[1])
        self.position = position    
        
    def build_string(self):
        off = 10.0-CHARWIDTH
        x_spacing = 0
        chset = []
        c = []
        comments = []
        lines_all = []
        
        if self.code == True: 
            comment,lines = self.get_char_map(int(self.string),self.styled)
            x_spacing += 1
            c += [lines]
            comments.append(comment)
        else:
            for char in self.string:
                chrcode = ord(char)-CHARMAP_START_INDEX
                comment,lines = self.get_char_map(chrcode, self.styled)
                lines = affinity.translate(lines, xoff=x_spacing*CHARWIDTH, yoff=0.0)
                x_spacing += 1
                c += [lines]
                comments.append(comment)
        
        for st in c:
            if st.geom_type == 'MultiLineString':
                for line in st:
                    lines_all += [LineString(line)]
            elif st.geom_type == 'LineString':
                lines_all += [st]
        
        m = MultiLineString(lines_all)
        minx, miny, maxx, maxy = m.bounds
        bounds_box = box(0.0, 0.0, (x_spacing*CHARWIDTH)+off, 10.0, ccw=False)
        
        self.comments = comments
        self.bounds = affinity.scale(bounds_box, xfact=self.scale[0], yfact=self.scale[1], origin=(0,0))
        self.geometry = affinity.scale(m, xfact=self.scale[0], yfact=self.scale[1], origin=(0,0))
        
        minx, miny, maxx, maxy = self.bounds.bounds
        y_vary = maxy/-2.0
        
        if self.alignment == 'right': x_vary = 0.0
        if self.alignment == 'left': x_vary = maxx*-1.0
        if self.alignment == 'center': x_vary = maxx/-2.0
    
        self.bounds = affinity.translate(self.bounds, xoff=x_vary, yoff=y_vary)
        self.geometry = affinity.translate(self.geometry, xoff=x_vary, yoff=y_vary)
        
        self.bounds = affinity.rotate(self.bounds, self.angle, origin=(0,0))
        self.geometry = affinity.rotate(self.geometry, self.angle, origin=(0,0))
        
        e_pad = (self.scale[0]+self.scale[1])/2
        
        self.bounds = self.bounds.buffer((e_pad*CHARWIDTH)*0.25, cap_style=3, join_style=2)
        
    def get_char_map(self, char, style):
        char_array = CHARMAP[char] if style == 'plain' else CHARMAP_BOLD[char]
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
        #logger.error(g)
        
        if len(g) == 1:
            f = LineString(g[0])
        else: 
            f = MultiLineString(g)
                
        return chmap[0],f 

    def get_gcode(self):
        grblcmd = []
        
        for line in self.geometry:
            x,y = line.coords[0]
            grblcmd += ["G0 X%.3f Y%.3f F%i" % (x,y,SEEK_RATE)]
            grblcmd += ["G0 Z%i" % Z_DEPTH]
            #grblcmd += ["G1 Z%i F%i" % (Z_DEPTH,FEED_RATE)]
            grblcmd += ["G4 P%1.1f" % PAUSE_ONE]
            
            for c in line.coords:
                xx,yy = c
                grblcmd += ["G1 X%.3f Y%.3f F%i" % (xx,yy,FEED_RATE)]
            
            grblcmd += ["G0 Z0"]
            
        return grblcmd

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
        