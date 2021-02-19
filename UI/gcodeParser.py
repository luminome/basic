#!/usr/bin/env python3
import re,os,sys,re
from subprocess import Popen, PIPE
import numpy as np


from basicGcodeCmds import probe_set_depth, probe_hold_depth

from plistLoader import PlistLoader, plistPath
LDLF = PlistLoader(plistPath())
LDLF.load_to_globals(globals(),('MACH','GRBL','MAIN'))

def parse_gcode_line_to_plot(line):
    state = {}
    cmdtxt = line.strip()
    if cmdtxt.find('(') < -1 or cmdtxt.find(')') > -1: 
        state['comment'] = cmdtxt
    else:
        cmds_list = re.findall('[A-Z][^A-Z]*',cmdtxt)
        if len(cmds_list) > 0 and cmds_list[0] != 'G0 0': 
            for cc in cmds_list: 
                k = str(cc)[0]
                v = cc[1:].strip()
                state[k] = int(v) if '.' not in v else float(v)
                    
    return state
    
    
def read_gcode(gcodefile, addprobe=None):
    lexical_output_file = []
    
    machine = {'G':0,'X':00.00,'Y':00.00,'Z':00.00,'F':0,'P':0.0,'comment':None}
    
    command_content = [] #whole file now
    with open(gcodefile, 'r') as filehandle:
        command_content = filehandle.readlines()
    
    if len(command_content) > 0:
        
        numeric_command = []
        strokes = 0
        distance_lock = False
        probed = False
        Z_STATE = False
        STROKE_START = False
        PROBED = False
        PAUSED = False
        FAR_LOCK = False
        GSTATE = None
        
        for c,cmd in enumerate(command_content):
            
            if cmd != '\n':
            
                #find new line here somehow.
                state = parse_gcode_line_to_plot(cmd)
                #save current state
                machine_A = machine.copy()
                a = np.array([machine_A['X'],machine_A['Y']])
                #save to new state
                machine.update(state)
                b = np.array([machine['X'],machine['Y']])
                # a -> b distance:
                spec = [machine[n] for n in machine]
                numeric_command.append(spec)
                dist = np.linalg.norm(b-a)
            
                
                #so machine_A[G] is always zero in this scenario
                    
                if addprobe:    
                    if dist > int(addprobe):
                        #print('have distance_lock')
                        distance_lock = True
                    
                    mix_in = [] 
                    #mix_in = None
                    # print('---am,m')
                    # print(machine_A)
                    # print(machine)
                    
                    if not GSTATE and machine['G'] == 0:
                        if dist > int(addprobe):
                            FAR_LOCK = True
                            
                    #FIRST G1
                    elif not GSTATE and machine['G'] == 1:
                        
                        if not STROKE_START:
                            strokes += 1
                            mix_in = ['(start stroke %i)' % strokes]
                            STROKE_START = True
                        
                        if FAR_LOCK:
                            mix_in += probe_set_depth(machine['X'],machine['Y'],PAUSE=PAUSE_TWO,pulses=1)
                            PROBED = True
                            FAR_LOCK = False
                    
                    #LAST G1
                    elif GSTATE and machine['G'] == 0:
                        if STROKE_START:
                            mix_in = ['(stop stroke %i)' % strokes]
                            PAUSED = False
                            PROBED = False
                            STROKE_START = False
                            
                    #SECOND G1
                    elif GSTATE and machine['G'] == 1:
                        #pass
                        if not PAUSED and not PROBED:
                            mix_in = probe_hold_depth(machine['X'],machine['Y'],PAUSE=PAUSE_ONE,pulses=1)
                            PAUSED = True
                    
                    
                    
                    if len(mix_in):
                        for i in mix_in:
                            print(i)
                            lexical_output_file += [i]
                            probe_line = parse_gcode_line_to_plot(i)
                            machine.update(probe_line)
                            spec = [machine[n] for n in machine]
                            numeric_command.append(spec)    
                    else:
                        pass#print(machine)
                        #lexical_file is...ok I guess?
                
                
                lexical_output_file += [str(cmd).strip()]
                #reset pause-state and g-state
                GSTATE = machine['G']

                machine['comment'] = None
        
        
        command_array = np.array(numeric_command)

        
    return command_array,lexical_output_file


def svg_to_gcode(svgfile, draw_args=None):
    os.chdir('svg2gcode_grbl-master')
    c = 'python3 convert.py %s %s' % (svgfile, svgfile+'.gcode')
    p = Popen([c], stdout=PIPE, shell=True)
    p.wait()
    kp = p.communicate()
    p.kill()

    p_output = kp[0].decode("utf-8")
    convert_proc = p_output.split('\n')
    for r in convert_proc: print(r) #lines

    gcode_source_file = svgfile+'.gcode'
    cmd,lexical_file = read_gcode(gcode_source_file, addprobe=draw_args.probe)
    
    with open(gcode_source_file,'w+') as file:
        for line in lexical_file:
            file.write(line+'\n')
            
    os.chdir(ROOT_ABS_PATH)
    return gcode_source_file
    
    

if __name__ == "__main__":
    import argparse
    
    draw_parser = argparse.ArgumentParser(description='draw-layout-from-gcode')
    draw_parser.add_argument('-file', help = 'gcode file read path')
    draw_parser.add_argument('-c','--convert', action='store_true', default=False, help='convert inbound svg to gcode')
    draw_parser.add_argument('-probe', help = 'distance between points to probe in units. (or None)')
    draw_args = draw_parser.parse_args()

    if draw_args.convert:
        svg_to_gcode(draw_args.file,draw_args)
    
    exit()