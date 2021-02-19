#!/usr/bin/env python3
import re,os,sys,re
from subprocess import Popen, PIPE
import numpy as np


from basicGcodeCmds import probe_set_depth, probe_hold_depth

# sys.path.insert(1, '/Users/sac/Sites/afsolo/')
# os.chdir('/Users/sac/Sites/afsolo/')
#
# import variables
# variables.load(globals())
# import utility


from plistLoader import PlistLoader, plistPath
LDLF = PlistLoader(plistPath())
LDLF.load_to_globals(globals(),('MACH','GRBL','MAIN'))

#
# from parse import parse,compile
# gcodefmt = compile('F{}G{}X{}Y{}Z{}P{}')
#
# samp = gcodefmt.parse('F1000G0X10Z4')
# print(samp)
# exit()


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
                # machine['G'] = 0
#                 machine['P'] = 0.0
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
    
    pass
    
    
    
    
    
    
    
# #plot main content here! ƒ-based
# if draw_args.file:
#     #if it's adding probe data, run the thing once to get indices, then again to get plottable. no. not necessary(days later)
#
#     
#
#     #for l in lexical_file: print(l.strip())
#
#     for c in range(1,numeric_command_array.shape[0]): print(numeric_command_array[c-1])
#
##########################################################################################################
"""
exit();

if __name__ == "__main__":
    
    gcode_source_file = draw_args.file
    lexical_output_file = []

    if draw_args.convert:
        os.chdir('svg2gcode_grbl-master')
        c = 'python3 convert.py %s %s' % (draw_args.file, draw_args.file+'.gcode')
        p = Popen([c], stdout=PIPE, shell=True)
        p.wait()
        kp = p.communicate()
        p.kill()
    
        p_output = kp[0].decode("utf-8")
        convert_proc = p_output.split('\n')
        for r in convert_proc: print(r) #lines
    
        gcode_source_file = draw_args.file+'.gcode'
        cmd,lexical_file = read_gcode(gcode_source_file, addprobe=draw_args.probe)
        
        with open(gcode_source_file,'w+') as file:
            for line in lexical_file:
                file.write(line+'\n')
        
        
        
    
    numeric_command_array,lexical_file = read_gcode(gcode_source_file, addprobe=draw_args.probe)
    
    
    
    
    
    
    #for l in lexical_file: print(l.strip())
    for c in range(1,numeric_command_array.shape[0]): print(numeric_command_array[c-1])
"""    
   
   
   
    
    
##########################################################################################################
"""
#!/usr/bin/python3
import re

from matplotlib import pyplot as plt
import numpy as np
import argparse
import json

import variables
variables.load(globals())

import utility



draw_parser = argparse.ArgumentParser(description='draw-layout-from-gcode')
draw_parser.add_argument('-file', help = 'gcode file read path')  
draw_parser.add_argument('-probe', help = 'distance between points to probe. (or None)')  
draw_args = draw_parser.parse_args()




def parse_gcode_line_to_plot(line):
    state = {}
    cmdtxt = line.strip()
    if cmdtxt.find('(') < -1 or cmdtxt.find(')') > -1: 
        #state['comment'] = cmdtxt
        pass
    else:
        cmds_list = re.findall('[A-Z][^A-Z]*',cmdtxt)
        if len(cmds_list) > 0 and cmds_list[0] != 'G0 0': 
            for cc in cmds_list: 
                k = str(cc)[0]
                v = cc[1:].strip()
                state[k] = int(v) if '.' not in v else float(v)
                    
    return state
    
    

def read_gcode(gcodefile):
    #return a set of lines.
    #lines are np arrays.
    command_content = []
    with open(gcodefile, 'r') as filehandle:
        command_content = filehandle.readlines()
    
    #cursor = {}
    G,X,Y,Z,F,P = 0,0.0,0.0,0.0,0,0
    current = [G,X,Y,Z,F,P]
    previous = []
    
    machine = {}
    
    if len(command_content) > 0:
        
        saved = []
        
        for c,cmd in enumerate(command_content):
            #find new line here somehow.
            state = parse_gcode_line_to_plot(cmd)

            #TODO:
            #in case of adding probe-cycle automatically:...
            #find delta in position first, if greater than threshold, inject probe¬
            #based upon current X and Y (G0)
            #if 'G' in state and state['G'] == 0 and 'X' in state: print(state)
    
            # if 'X' in state and 'Y' in state: X,Y = state['X'], state['Y']
            # if 'Z' in state: Z = state['Z']
            # if 'F' in state: F = state['F']
            # if 'P' in state: P = state['P']
            # if 'G' in state: G = state['G']
            
            machine.update(state)
            
            spec = [machine[n] for n in iter(machine)]
            
            print(spec)
            
            saved.append(spec)
            
            machine['P'] = 0
            
            # if len(state)>0:
 #
 #
 #                if current != previous:
 #                    #∆ in point(s)
 #                    if previous:
 #                        a = np.array(previous[1:3])
 #                        b = np.array(current[1:3])
 #                        dist = np.linalg.norm(b-a)
 #                        if draw_args.probe and dist > int(draw_args.probe):
 #
 #                            print(dist)
 #
 #                    previous = current
 #                    saved.append(current)
 #
 #            current = [G,X,Y,Z,F,P]
 #            P = 0
        
        # if draw_args.probe:
        #     get probe subroutine
        #     def gcode_get_depth_probe(xf,yf,PAUSE_timer=PROBE_PAUSE,pulses=1):
        #         returns
        
        
        command_array = np.array(saved)
        print(command_array.shape)
        
    return command_array
    pass




#setup
plt.axis('equal')
plt.axis([0, X_SIZE, 0, Y_SIZE])
plt.grid(color='blue', linewidth=0.7, alpha=0.15)
c = 100
plt.xticks(np.arange(0, X_SIZE+c, step=c),fontsize=6, alpha=0.5)
plt.yticks(np.arange(0, Y_SIZE+c, step=c),fontsize=6, alpha=0.5)

#plot 0,0 and limits
ple = np.array([(0,0),(X_SIZE,Y_SIZE)])
plt.plot(ple[:, 0], ple[:, 1], linewidth=0, marker='o', markersize=1, color='k')




#plot main content here! ƒ-based
if draw_args.file:
    #if it's adding probe data, run the thing once to get indices, then again to get plottable.
    
    ple = read_gcode(draw_args.file)
    
    for c in range(1,ple.shape[0]):
        a = ple[c-1]
        b = ple[c]
        dyn = np.array([a,b])
        G,X,Y,Z,F,P = b
        
        p_color = 'k'
        p_mark_size = (F/10000)*2
        p_line_width = (Z+0.4)*0.4
        p_alp = 1.0
        
        if P > 0:
            p_mark_size = P*10
            p_color = 'b'
            p_alp = 0.2
        
        if Z == 0:
            plt.annotate("", xy=(X,Y), xytext=(a[1],a[2]), arrowprops=dict(arrowstyle="->",color='r',linewidth=0.5,linestyle='--'))

        
        plt.plot(dyn[:, 1], dyn[:, 2], linewidth=p_line_width, marker='o', markersize=p_mark_size, color=p_color, alpha=p_alp)
    
    #print(s)




#plot markers
buf = (DATA_BUF_HR*15.0)
ost = (DATA_OFFSET_HR*15.0)
wid = (DATA_MAP_HRS*15)

ple = np.array([(buf+ost,-15),(buf+ost,DATA_Y_SIZE+15)])*NAT_SCALE
plt.plot(ple[:, 0], ple[:, 1], linewidth=1, marker='o', markersize=2, color='g')
ple = np.array([buf+ost,DATA_Y_SIZE+15])*NAT_SCALE
plt.annotate(str(ost)+'º', ple, va="bottom", ha="center", size=8, color='g', zorder=4)    
    
buffer_lines = [buf,buf+wid]
for ct,p in enumerate(buffer_lines):
    ple = np.array([(p,0),(p,DATA_Y_SIZE)])*NAT_SCALE
    plt.plot(ple[:, 0], ple[:, 1], linestyle='--', linewidth=0.5, marker='o', markersize=2, color='r')

plt.tight_layout()
plt.show()
#wait.
plt.close()

exit()

"""