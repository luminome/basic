#!/usr/bin/env python3
import os
import json
import inspect

def plistPath():
    return 'UI/basic-plist.json'

class PlistLoader(object):
    def __init__(self, path, parent=None):
        self.VARS = {}
        self.RAW = {}
        self.CWD = os.getcwd()
        self.load_plist(path)
        
    def load_plist(self, path):
        with open(path, 'r') as fi:
            json_plist = json.load(fi)
        self.VARS = json_plist

    def print_digest(self):
        for section,content in self.RAW.items():
            print("%s (%i)"%(section, len(content)))

    def load_to_globals(self,scope,partial=None):
        print('VARS','def ƒ',__name__,inspect.stack()[0][3])
        if partial:
            self.RAW = {}
            for section_name in partial:
                print('section_name',section_name)
                if section_name in self.VARS.keys():
                    self.RAW[section_name] = self.VARS[section_name].copy()
        else:
            self.RAW = self.VARS.copy()
            
        #print(self.RAW)
        
        for section, content in self.RAW.items():
            
            if type(content) is dict:
                for (var,val) in content.items():
                    #self.RAW[var] = val    
                    scope[var] = val                
                    #locals().update(scope)
    
        globals().update(scope)
        pass


if __name__ == "__main__":
    path = 'UI/basic-plist.json'
    GDL = PlistLoader(path)

    GDL.load_to_globals(globals(),('MACH','GRBL',))
    GDL.print_digest()
    
    keys = globals().copy()
    for k,v in keys.items():
        print(k,v)