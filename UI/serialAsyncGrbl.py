#!/usr/bin/env python3

#CREDIT https://tinkering.xyz/async-serial/
import asyncio
import serial_asyncio
from parse import parse,compile
import re
import time
from plistLoader import PlistLoader, plistPath

LDLF = PlistLoader(plistPath())
LDLF.load_to_globals(globals(),('MACH','GRBL',))

class ser_async_grbl(object):
    """# SAC use asyncioserial to talk to grbl."""
    #calls parent.GRA.iterate, parent.GRA.machine_trace(), and parent.log
    def __init__(self, parent = None): #parent = None):
        #super(ser_async_grbl, self).__init__()
        self.coms = True
        self.parent = parent
        self.grblstatusfmt = compile('<{},MPos:{},WPos:{},Buf:{},RX:{}>')
        self.lc = 0
        self.bc = []
        self.gc = 0
        self.RX = None #reader
        self.TX = None #writer
        self.statusPos = STATUS_POS
        self.status = None
        self.state = 'init'
        self.gcode = ['(welcome init in list)']
        self.gcl = 0
        self.clock = 0
        self.shell = False
        self._event = asyncio.Event()
        self.is_reading = False
        self.cmd = None
        self.log_status = False
        self.log_grbl = True
        self.poo_lock = True
        self.cond = asyncio.Condition()
        self.delivering = False
        self.connected = False
        self.cmd_actual = 0
        
    
    def reset_delivery(self):
        self.lc = 0
        self.bc = []
        self.gc = 0
        self.gcl = 0
        self.clock = 0
        self.cmd = None
        self.gcode = []
        
    #PRINT/STDOUT HANDLER
    def log(self,*args):
        if self.parent:
            self.parent.log(args)
        else:
            print(args)
    #LOAD COMMANDS [LIST]
    def load_gcode(self,code_list):
        #self.gcode = ['G0 X0 Y0 Z0']#['G21 G90','G10 L20 X0 Y0 Z0']
        self.gcode += code_list
        self.gcl = len(self.gcode)
        self.state = 'ser_async_grbl loaded %i lines' % self.gcl
        self.log(self.state)
        
    #VARS DUMP
    def test(self):
        self.state = 'test'
        for k,v in self.__dict__.items():
            val = '%s (%s)' % (type(v),len(str(v))) if len(str(v)) > RX_BUFFER_SIZE-1 else v
            self.log(k,val)
    #WHAT
    def get_pos_tuple(self):
        if self.status:
            s,m,w,b,r = self.status
            if STATUS_POS == 'M': return m.split(',')
            if STATUS_POS == 'W': return w.split(',')
            
        return (0.0,0.0,0.0)
    #WAITER:
    def run_state(self, val=None):
        if val == 'LOCK':
            self._event.clear()
            self.poo_lock = False
        if val == 'UNLOCK':
            self._event.set()
            self.poo_lock = True

        return 'LOCKED' if not self._event.is_set() else 'UNLOCKED'
    
    #EVENT TO TOGGLE
    async def is_done(self):
        return await self._event.wait()
    #PO-LOCK
    async def po_lock(self):
        return self.poo_lock
    #MAIN_RUN        
    async def run(self, loop):
        self.RX, self.TX = await serial_asyncio.open_serial_connection(url=SERIAL_PORT, baudrate=MAX_BAUD_RATE)
        await asyncio.sleep(3.0)
        self.log('serial opened.')
        self.state = 'run'
        self.connected = True
        grbl_send_idle = self.grbl_write_idle()
        grbl_send = self.grbl_write_gcode()
        grbl_received = self.grbl_read()
        await asyncio.wait([grbl_received, grbl_send, grbl_send_idle])

    
    #WRITE IDLE(?)
    async def grbl_write_idle(self):
        
        while True:
            
            # with self.cond: await self.cond.wait()
            # print(self._event.is_set())
            # await self.is_done()
            
            self.TX.write(b'?')
            self.clock += 1
            #await self.TX.drain()
            # if self.state == 'sent-batch':
            #     if self.status:
            #         s,m,w,b,r = self.status
            #         if s == 'Idle' and b == '0' and r == '0':
            #             self.state = 'completed'
            #             self.TX.write(b'?') #last one to flush read.
            #             #break
                    
            if self.coms: self.parent.machine_trace()
            
            await asyncio.sleep(STATUS_DELAY)
            #await asyncio.sleep(1.0)
                    
        self.log('grbl_write_idle',self.state)
            
    #READ MACHINE PROGRESS
    async def grbl_read(self):
        while True:
            try:
                msg = await self.RX.readline()#until(b'\r\n')
                self.is_reading = True
                msg_str = msg.rstrip().decode()
                if msg_str.find('ok') < 0 and msg_str.find('error') < 0:
                    if set(['<','>']) & set(msg_str):
                        self.status = self.grblstatusfmt.parse(msg_str)
                        if self.log_status: self.log(msg_str)
                    else:
                        self.log(msg_str)
                else:
                    
                    if self.log_grbl and self.poo_lock: self.log(msg_str)
                    
                    if msg_str.find('error') != -1:
                        self.log(self.gc,'grbl error encountered',msg_str,self.run_state())
                        self.cmd = '!' #run_state('LOCK')
                    else:
                        #OK\n
                        # if self.status:
                        #     s,m,w,b,r = self.status
                        #     self.cmd_actual = self.gc-int(b)
                        #     print('cmd_actual',self.cmd_actual)
                        #
                        # if self.coms: self.parent.iterate(self.cmd_actual)
                        if self.coms: self.parent.iterate()
                        
                        self.gc += 1
                        del self.bc[0]
                
                #if self.state == 'completed': break
                
                await asyncio.sleep(BUFFER_DELAY)
                
            except Exception as err:
                self.log('grbl_read',err)#,str(err[0]))
        
        self.log('grbl_read',self.state,'everything. exit.')
    
    #WRITE CODES
    async def grbl_write_gcode(self,dat=None):
        
        while True:
            try:
                # await self.is_done()
                # Clochard. ¬ if there's anything in this array (at index), do that.
                # this function will now block here though.
                if self.cmd:
                    if set(['~','unlock']) & set(self.cmd):
                        #self.log('c',self.run_state('UNLOCK'))
                        self.poo_lock = False
                        self.cmd = '~'
                    elif set(['!','lock']) & set(self.cmd):
                        #self.log('c',self.run_state('LOCK'))
                        self.poo_lock = True
                        self.cmd = '!'
                        
                        
                    # try:
                    #     ds = eval(self.cmd)
                    # except (NameError,Exception):
                    #ds = str('nope')
                        
                        
                    if type(self.cmd) == list:
                        for line in self.cmd:
                            block = re.sub('\s|\(.*?\)','',line).upper()
                            self.log(block)
                            self.bc += [len(block)+1]# really important.
                            self.TX.write((block+'\n').encode('utf-8'))
                    else:                    
                        self.bc += [len(self.cmd)+1]# really important.
                        self.TX.write((self.cmd+'\n').encode('utf-8'))
                        
                    await self.TX.drain()                        
                    self.cmd = None
                else:
                    
                    if len(self.gcode) > self.lc and self.delivering:
                        line = self.gcode[self.lc]
                        block = re.sub('\s|\(.*?\)','',line).upper()
                        
                        if sum(self.bc)+(len(block)+1) < RX_BUFFER_SIZE-1:
                            
                            # if self.status:
                            #     s,m,w,b,r = self.status
                            #     self.cmd_actual = self.gc-int(b)
                            #     #print('cmd_actual',self.cmd_actual)
                            
                            
                            
                            
                            self.bc.append(len(block)+1)
                            self.TX.write((block+'\n').encode('utf-8'))
                            
                            #await self.TX.drain()
                            if self.log_grbl: self.log("tx: ( %03i / %i ) g%03i \'%s\'" % (self.lc,self.gcl,self.gc,block))
                            self.lc += 1
                            
                    if self.lc and len(self.gcode) == self.lc:
                        self.state = 'sent-batch'
                        #break
                
                await asyncio.sleep(BUFFER_DELAY)
                
            except Exception as err:
                self.log('grbl_write_gcode',err)

                
        self.log('grbl_write_gcode',self.state)













if __name__ == '__main__':
    #
    # def log(*args):
    #     print(args)
    #
        
    s = ser_async_grbl()
    s.shell = False
    s.coms = False
    s.run_state('UNLOCK')
    
    with open ('command-logs/4.txt','r') as fi:
        batch = fi.readlines()
    s.load_gcode(batch)
    
    s.test()
    #time.sleep(1)
    #s.gcode = ['?','?','?']
    
    task_main = None
    
    try:
        loop = asyncio.get_event_loop()
        loop.create_task(loop.run_until_complete(s.run(loop)))
        loop.run_until_complete(s.cleanup(loop))
        print('graceful quit program')
    except (KeyboardInterrupt,Exception) as err:
        pass #3print(err)
    finally:
        loop = asyncio.get_event_loop()
        loop.run_until_complete(s.cleanup(loop))
        pending = asyncio.all_tasks(loop)
        if pending: print('left pending (%i)' % len(pending))
        print('sloppy quit program')
        
    print('closed everything')    
    loop.close()
    
    
    exit()










