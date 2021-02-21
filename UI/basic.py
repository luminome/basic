#!/usr/bin/env python3
import sys
import time
from time import localtime,strftime
import locale
import inspect
import os
import re

from scipy.spatial.distance import cdist

from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5 import uic

# TODO YES
import numpy as np
import pyqtgraph as pg 

import asyncio
from qasync import QEventLoop

import argparse
from types import MethodType

import gcodeParser

from basicVarsWidget import VarsWidget

from serialAsyncGrbl import ser_async_grbl

from plistLoader import PlistLoader, plistPath

#from modules import characters

import basicGcodeCmds as bgc

from modules import circles, textures, characters


LDLF = PlistLoader(plistPath())
LDLF.load_to_globals(globals(),('MACH','GRBL','MAIN'))

_parser = argparse.ArgumentParser(description='draw-layout-from-gcode')
_parser.add_argument('-file', help = 'gcode file read path')
_parser.add_argument('-probe', help = 'distance between points to probe in units. (or None)')  
_parser.add_argument('-s','--session', action='store_true', default=False, help='space plot session')
_args = _parser.parse_args()

        
FONT = QFont('Monaco', 10)

on_color = pg.mkColor(0,0,0,200)
off_color = pg.mkColor(255,0,0,150)
off_color_lt = pg.mkColor(255,0,0,90)
off_brush = pg.mkBrush(color=off_color_lt)

pause_color = pg.mkColor(0,255,0,100)
pause_brush = pg.mkBrush(color=pause_color)

on_pen = pg.mkPen(cosmetic=False, width=0.6, color=on_color)
off_pen = pg.mkPen(cosmetic=False, width=1.0, color=off_color, style=Qt.DotLine)

trace_color = pg.mkColor(0,120,200,125)
trace_brush = pg.mkBrush(color=trace_color)

"""ROOT CLASSES [ƒ]"""
class MainPlotWindowHandler():
    def __init__(self, parent = None):
        #print(args)
        self.batch = []
        self.s_pos = []
        self.file_raw = []
        self.plot = None #pg.PlotWidget
        self.adj = []
        self.source_path = ''
        self.point_index = 0
        self.bounds_points_index = 0
        self.subplots = []
        self.subplots_rst = 0
        self.subplot_index = 1
        self.bounds_pos = np.array([])
        self.bounds_adj = np.array([])
        self.off_pos = np.array([])
        self.off_state = np.array([])
        self.points_count = 0
        self.parent = None
        self.marks = True
        self.clickpos = []

    def re_slate(self):
        for cplot in self.plot.allChildItems(): self.plot.removeItem(cplot)
        self.subplots = []
        #self.points_count = 0
        self.subplot_index = 0
        self.bounds_points_index = 0
        self.g_base = pg.GraphItem()
        self.plot.addItem(self.g_base)
        
        
        
        # self.g_off_base = pg.GraphItem()
        # self.plot.addItem(self.g_off_base)
        # self.g_trace_base = pg.GraphItem()
        # self.plot.addItem(self.g_trace_base)
        
        # x,y = np_ppos[i-1]-np_ppos[i]
        # arrow_angle = np.arctan2(y,x) * 180 / np.pi
        arrow_dims = 10.0
        arrow = pg.ArrowItem(angle=90.0, pen=None)
        arrow.setPos(0,0)
        arrow.setStyle(headWidth=(arrow_dims*0.75), headLen=(arrow_dims*2), tailLen=arrow_dims, tailWidth=(arrow_dims*0.5), brush='r')
        arrow.setParentItem(self.g_base)
        #self.plot.addItem(self.arrow)
        self.arrow = arrow
        
        if self.points_count:
            subplots = int(np.ceil(self.points_count/GRAPH_SUBPLOT_LEN))+1
            self.subplots_rst = subplots-1
            for d in range(subplots): self.add_subplot()
        
        if not self.marks: self.g_base.hide()
        
        
    def attach_plot(self,plot):
        self.plot = plot
        
    def show_mach_location(self):
        npos = np.array([[-1,0],[1,0],[0,-1],[0,1]],dtype=float)
        nadj = np.array([[0,1],[2,3]],dtype=int)
        x,y,z = MACH.get_pos_tuple()
        pos = np.array([x,y],dtype=float)
        pos_r = pos+(npos*100)
        s = int(float(z))
        
        self.location.setData(pos=pos_r, adj=nadj, pen=off_pen, size=1+s, pxMode=False)

    def movecallback(self,event):
        position = event[0]
        b = self.plot.getViewBox()
        x = int(b.mapSceneToView(position).x())
        y = int(b.mapSceneToView(position).y())
        follow = None
        if len(self.clickpos):
            follow = str(self.clickpos)
        self.parent.user_location.setText(f'({x},{y}) {follow}')
    
    def clickcallback(self,event):
        position = event[0].pos()
        b = self.plot.getViewBox()
        x = b.mapSceneToView(position).x()
        y = b.mapSceneToView(position).y()
        self.clickpos = (x,y)
        self.parent.plotClicked(event,x,y)
        self.parent.user_location.setText(f'CLK({x},{y})')

            
    
    def init_plot(self, init_args):
        self.plot.setMouseEnabled()
        self.plot.setAspectLocked()
        self.plot.hideAxis('left')
        self.plot.setXRange(1800,00)
        self.plot.setYRange(0,1000)
        
        self.source_path = prepare_source(init_args)
        self.parent.log(init_args)
        self.parent.log('SRC', self.source_path)
        
        self.moveproxy = pg.SignalProxy(self.plot.scene().sigMouseMoved, rateLimit=60, slot=self.movecallback)
        self.clickproxy = pg.SignalProxy(self.plot.scene().sigMouseClicked, rateLimit=60, slot=self.clickcallback)
        
        if len(self.source_path):
            self.batch, self.file_raw  = gcodeParser.read_gcode(self.source_path[0])
            self.batch = np.array(self.batch)
            self.adj = np.array([[c,c+1] for c in range(0,len(self.batch)-1)])
            self.points_count = self.batch.shape[0]
            self.off_state = np.zeros([self.points_count,2], dtype=int)
            self.off_pos = np.zeros([self.points_count,2])
            self.bounds_pos = np.zeros([self.points_count,2])
            self.bounds_adj = np.zeros([self.points_count,2], dtype=int)
            self.s_pos = np.array(self.batch[:,[1,2]], dtype=float)
        
        self.re_slate()
        self.parent.log('SRC LEN',len(self.file_raw))
        
    def show_subplot_bounds(self,subplot_index):
        g = self.subplots[subplot_index]
        _b = 5.0 #_buffer
        # (N,2) array of the positions of each node in the graph.
        x = g.pos[:, 0].ravel()
        y = g.pos[:, 1].ravel()
        x0,y0,x1,y1 = min(x)-_b,min(y)-_b,max(x)+_b,max(y)+_b
        
        np_ppos = np.array([[x0,y0],[x0,y1],[x1,y1],[x1,y0],[x0,y0]])
        np_adjs = np.array([[0,1],[1,2],[2,3],[3,4],[4,0]], dtype=int)+self.bounds_points_index
        
        cap_points = np.array([g.pos[0],g.pos[-1]])
        i_b = self.bounds_points_index
        
        def dset(npa,tgt):
            for i,np in enumerate(npa):
                tgt[i_b+i] = np
            return tgt
        
        self.bounds_pos = dset(np_ppos,self.bounds_pos)
        self.bounds_adj = dset(np_adjs,self.bounds_adj)
        self.bounds_points_index += np_ppos.shape[0]

        i_b = self.bounds_points_index
        pos_r = self.bounds_pos[0:i_b]
        adj_r = self.bounds_adj[0:i_b]
        
        label = pg.LabelItem('%i' % subplot_index, color=off_color_lt, size='9pt', bold=True)
        label.setOpacity(0.25)
        label.setPos(np_ppos[1][0],np_ppos[1][1])
        label.scale(1, -1)
        label.setParentItem(self.g_base)
        # print(label.boundingRect())
        # l = label.__class__
        # for n in dir(l): print(n)
        
        self.g_base.setData(pos=pos_r, adj=adj_r, pen=off_pen, size=1, symbol='+', pxMode=False)
        
        caps = pg.GraphItem()
        caps.setData(pos=cap_points, pen=off_pen, brush=off_brush, symbolPen=None, size=[5,10], symbol=['+','x'], pxMode=False)
        caps.setParentItem(self.g_base) #subplots[subplot_index])
        
    def add_subplot(self):
        
        #g = pg.GraphicsItem()
        
        gA = pg.GraphItem()
        gB = pg.GraphItem()
        
        #
        # gA.setParentItem(g)
        # gB.setParentItem(g)
        #g.addItem(gA)
        
        self.plot.addItem(gA)
        self.plot.addItem(gB)
        #self.subplots.append(g)
        
        ee = self.plot.allChildItems()
        self.subplots = [sp for sp in ee if 'GraphItem.GraphItem' in str(sp.__class__)][2:]
        #self.subplot_index += 1
        #return self.subplots[-1]
        #def get_current_subplot

class GraphUtil(object):
    def __init__(self, parent=None):
        self._subplot_pts = int(GRAPH_SUBPLOT_LEN)
        self.index = 0
        self.s_index = 0
        self._on_ind = 0
        self._on_adj = 0
        #self._off_ind = 0
        self.tape = None
        self.off_tape = None
        #self.segments = 0
        self.is_on = False
        #self.segment_lock = False
        #self.segment = 0
        self.d_lines = 0
        #self.mod = 0
        self.parent = parent
        self.trace_points = []
        
        self.trace_rad = 0
        
    def set_tape(self):
        self.off_tape = np.zeros([MMM.points_count,2],dtype=int)
        self.off_points = np.zeros([MMM.points_count,2],dtype=int)
        self.trace_points = []
        self.index = 0
        self.s_index = 0
        
    def prepare(self):
        #print('prepare graphe here.')
        self.tape_adj = np.zeros([self._subplot_pts+2,2], dtype=int)
        self.tape = np.zeros([self._subplot_pts+2,2], dtype=float)
        self._on_ind = 0
        self._on_adj = 0
        self.d_lines = 0 
        #MMM.g_trace_base = pg.GraphItem()
        #TODO
        self.trace_points = [] #np.zeros([self._subplot_pts*2,2], dtype=int)
        
        
        
    def log(self,logdata):
        window.testTextBrowser.append(str(logdata))
        self.parent.do_log(logdata)
        #do_log
    
    def closest_node(self, node, nodes):
        return nodes[cdist([node], nodes).argmin()]
        
    def machine_trace(self):
        """THIS ƒ is called BY SER_ASYNC_GRBL"""
        
        x,y,z = MACH.get_pos_tuple()
        MMM.arrow.setPos(float(x),float(y))
        MMM.arrow.setStyle(brush='r' if float(z) == 0 else 'k')

        try:
            #TODO print(len(MMM.subplots), MMM.subplots_rst, MMM.subplot_index)
            target_subplot = MMM.subplots[(MMM.subplots_rst+MMM.subplot_index)]
        except Exception as exc:
            pass
            
        self.trace_points += [[float(x),float(y)]]
        pos = np.array(self.trace_points)
        
        #
        # closest to what?
        #
        
        # poses = MMM.s_pos[0:self.index]#self.tape[0:self._on_ind]
        #
        # if len(poses):
        #
        #     try:
        #         d = np.array([float(x),float(y)])
        #         cd = self.closest_node(d, poses)
        #         i = np.where((poses == (cd[0], cd[1])).all(axis=1))
        #         #print(np.amax(i))
        #         self.trace_rad = np.amax(i)
        #     except Exception as exc:
        #         print(exc)
        #         #return


            

        
        
        target_subplot.setData(pos=pos, pen=None, symbol='o', symbolPen=None, symbolBrush=trace_brush, size=3.0, pxMode=False)
 
        #return
        
    def iterate(self, spec=None):
        #global AUTORUN

        #if self.index < self.trace_rad: return
        
        if self.index > MMM.points_count-1: 
            self.parent.log('finished iterating')
            self.parent.AUTORUN = False
            return
                
        sta = int((self._subplot_pts-1)*(MMM.subplot_index-1))
        
        try:
            target_subplot = MMM.subplots[MMM.subplot_index] #drawing to this one
            #target_subplot = subplot.allChildItems()[0]
            
        except Exception as exc:
            self.parent.log(exc)
            self.parent.AUTORUN = False
            return
        
        ind = self.index
        sid = self.s_index
        
        pt0 = MMM.batch[ind]
        pt1 = MMM.batch[ind-1]
        
        #if spec and ind > spec: return()
        
        
        
        if self.s_index == 0:
            self.parent.log('starting subplot', MMM.subplot_index, sta)
        
        if pt0[6]: 
            self.parent.messenger.setText(pt0[6])
            #self.parent.tableWidget.resizeColumnToContents(7)
        # print('---',self._on_ind)
        # #print('B',pt1)
        # print('A',pt0)
        
        # A [0 789.588 528.638 0.0 8000 2.4 '(start stroke 2)']
        # effectively skipping lines w/comments
        c = pt0[0] == 1 and not pt0[6]
        
        if c:
            if pt1[0] == 0:# previous point has G0
                x,y = MMM.s_pos[ind]
                label = pg.LabelItem(('%i' % self._on_ind), color=on_color)
                label.setPos(x,y)
                label.scale(0.25, -0.25)
                label.setParentItem(MMM.g_base)#target_subplot)
            
            self.tape[self._on_ind] = MMM.s_pos[ind]
            if pt1[0] != 0: # either G1 or G4 w/out comment.
                b = np.array([self._on_ind-1,self._on_ind])
                self.tape_adj[self._on_ind] = b
                
            self._on_ind += 1
            
        pos = self.tape[0:self._on_ind]
        adj = self.tape_adj[1:self._on_ind]
        adj = adj[~np.all(adj == 0, axis=1)] #void any zeros
        
        try:
            target_subplot.setData(pos=pos, adj=adj, pen=on_pen, symbol='x', size=0.5, pxMode=False)
        except Exception as exc:
            self.parent.log(("GRAPH ERROR",exc))

        
        if self.s_index == self._subplot_pts-1: 
            if self.s_index: 
                MMM.show_subplot_bounds(MMM.subplot_index)
                MMM.subplot_index += 1
                self.prepare()
                
            self.s_index = 0
            self.index -= 1 #TODO RECENT ADDITION bc line getting lost scross subplot switch
            
        else:
            self.s_index += 1
            self.index += 1
        
        return
        
        
        
        
class selecta(QComboBox):
    def __init__(self, parent = None):
        super(selecta, self).__init__(parent)
        self.index = None
        self.parent = parent
      
        self.currentIndexChanged.connect(self.selectionchange)
	
      # layout.addWidget(self.cb)
      # self.setLayout(layout)
      # self.setWindowTitle("combo box demo")

    def selectionchange(self,i):
        self.index = i
                #
        # for count in range(self.count()):
        #     print( self.itemText(count))
        # print( "Current index",i,"selection changed ",self.currentText())
	
        self.parent.moduleChange(i,self.currentText())
    
    # def showPopup(self):
    #     super().showPopup()
    #     # find the widget that contains the list; note that this is *not* the view
    #     # that QComboBox.view() returns, but what is used to show it.
    #     popup = self.view().window()
    #     rect = popup.geometry()
    #     print(rect.topLeft())
    #     popup.move(rect.topLeft())
        # QComboBox::showPopup();
#         QPoint pos = mapToGlobal(QPoint(0, height()));
#         view()->parentWidget()->move(pos);

         
        
class NewLabel(QLabel):
    def __init__(self, label_text, label_action=None):
        QLabel.__init__(self)
        self.setText(label_text)
        label_action.triggered.connect(self.refresh)
        self.addAction(label_action)
        self.baseText = label_text
        self.refresh()
        
    def is_selcted(self):
        return self.actions()[0].isChecked()
        
    def refresh(self):
        if self.is_selcted():
            pchr = '√'
        else:
            pchr = ' '
        #isck = self.actions()[0].isChecked()
        self.setProperty("mandatoryField", self.is_selcted())
        self.setStyle(self.style())
        self.setText(self.baseText[:-1]+pchr)
       
        #print('triggered',w)
        
    def enterEvent(self, event):
        pass
        #print(self.text(),'entered')

    def leaveEvent(self, event):
        pass
        #print(self.text(),'left')

    def mousePressEvent(self, event):
        chk = self.actions()[0].isChecked()
        self.actions()[0].setChecked(not chk)
        self.refresh()
        
        window.menu_action_click(self.actions()[0])
        return super().mousePressEvent(event)

class FancyOverlay(QTableWidget): 
    def __init__(self, parent=None):
        QTableWidget.__init__(self, parent)
        self.setColumnCount(2)    
        self.setColumnWidth(1,48)
        self.setColumnWidth(2,48)
        self.horizontalHeader().hide()
        self.verticalHeader().hide()
        self.setAutoScroll(True)
        self.setAutoFillBackground(True)
        self.horizontalHeader().setStretchLastSection(True)
        self.setSelectionMode(QAbstractItemView.NoSelection) # .NoSelection .MultiSelection)
        self.setMouseTracking(True)
        #self.setProperty("mandatoryField", True)
        # self.verticalScrollBar().setDisabled(True);
        # self.horizontalScrollBar().setDisabled(True);
        #self.FONT = QFont('Monaco', 10)
        self.AUTO_scroll = True
        self.compressed_state = False
        self.currentheight = 0
        self.rowheight = 20 #int(self.FONT.pointSize()+(self.FONT.pointSize()*0.2))
        self.setObjectName('logWidget')
        self.verticalHeader().setDefaultSectionSize(10);
        
        #self.setShowGrid(False)
        
    def enterEvent(self, event):
        self.AUTO_scroll = False
        self.setStyle(self.style())
        pass
        #print(self.text(),'entered')

    def leaveEvent(self, event):
        self.AUTO_scroll = True
        pass
        #print(self.text(),'left')
    
    def mousePressEvent(self, event):
        self.toggle()
        
        # window.menu_action_click(self.actions()[0])
        # chk = self.actions()[0].isChecked()
        # self.actions()[0].setChecked(not chk)
        # self.refresh(not chk)
        # return super().mousePressEvent(event)
    
    def toggle(self):
        self.compressed_state = not self.compressed_state
        
        if self.compressed_state:
            h = self.rowheight
        else:
            h = self.currentheight
    
        s = self.size()
        self.setGeometry(0,0,s.width(),h)
        self.resizeColumnToContents(0)
        self.scrollToBottom()
    
    def log(self, *args):
        FMT = '%H:%M:%S'
        now = time.localtime(time.time())
        init_time_fmt = strftime(FMT, now)
        
        for n,l in enumerate(args):
            rowPosition = self.rowCount()
            self.insertRow(rowPosition)
            if n == 0: self.setItem(rowPosition , 0, QTableWidgetItem(init_time_fmt))
    
            rc = QTableWidgetItem(str(l))
            #rc.setContentsMargins(0, 0, 0, 0)
            #print(l)
            self.setItem(rowPosition , 1, rc)
            #c = self.FONT.pointSize()
            self.setRowHeight(rowPosition, self.rowheight)
        
        if self.AUTO_scroll: self.scrollToBottom()
    
class MainWindow(QMainWindow): 
    
    def __init__(self):
        super(MainWindow, self).__init__()
        
        self.mrun = 'Idle'
        self.mpos = (0.0,0.0,0.0)
        self.wpos = (0.0,0.0,0.0)
        
        #call these metas before loading UI with graphicsView.
        pg.setConfigOptions(antialias=True)
        pg.setConfigOption('background', 'w')
        pg.setConfigOption('foreground', 'k')
        
        #now load the UI
        uic.loadUi('UI/basicui.ui', self)
        
        qss = "UI/catnip.qss"
        with open(qss,"r") as fh:
          ft = fh.read()
          self.spec_style_sheet = ft
        #
        self.setStyleSheet(self.spec_style_sheet)
        # self.setAutoFillBackground(True)

        self.plot_click_interactions_count = 0
        
        self.log_table = FancyOverlay(self) 
        self.log_table.setContentsMargins(0, 0, 0, 0)
        
        self.vars_tree = VarsWidget(self)
        self.vars_tree.hide()
        #self.LDL = PopListMainWindow(parent=self)
        
        self.setContentsMargins(0, 0, 0, 0)
        self.statusBar().showMessage('Message in statusbar.')
        self.COMD = 'sent automatically' #'basic program loaded'
        self.AUTORUN = False
        self.tsec = 0
        self.frame = 0
        

        MACH.parent = self
        
        MMM.attach_plot(self.graphicsView)
        MMM.parent = self
        MMM.init_plot(_args)
        MMM.marks = True

        GRA.prepare()
        GRA.set_tape()
        GRA.parent = self
        
        
        self.progressBar.setValue(0)
        self.progressBar.setStyleSheet(self.spec_style_sheet)
        
        self.ControlWidget.resizeEvent = self.controlWidgetResizeEvent        
        
        self.lineEdit.returnPressed.connect(self.mach_cmd)
        self.lineEdit.setStyleSheet(self.spec_style_sheet)
        
        self.testSplitter.setOpaqueResize(True)
        
        self.setAutoFillBackground(True)
        
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_frame)
        self.timer.start(0)
        
        
        rowCount = 6
        columnCount = 6
        for c in range(0,columnCount):
            self.tableWidget.insertColumn(c);
        
        for c in range(0,rowCount):
            self.tableWidget.insertRow(c);
        
        # labels = ["∆","String"]
        self.tableWidget.setColumnCount(columnCount)
        self.tableWidget.setContentsMargins(0, 0, 0, 0)
        self.tableWidget.horizontalHeader().hide()
        self.tableWidget.verticalHeader().hide()
        self.tableWidget.setSelectionMode(QAbstractItemView.NoSelection) # .NoSelection .MultiSelection)
        self.tableWidget.setMouseTracking(True)
        self.tableWidget.setRowCount(5)        
        self.tableWidget.setColumnCount(9)
  
        self.tableWidget.setStyleSheet(self.spec_style_sheet)
        self.tableWidget.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.tableWidget.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.tableWidget.verticalScrollBar().setDisabled(True);
        self.tableWidget.horizontalScrollBar().setDisabled(True);
        self.tableWidget.horizontalHeader().setStretchLastSection(True)



        self.checkStatsMenu.triggered.connect(self.log)        
        self.UiComponents()
        self.setObjectName('basic')
        self.show()
  
    def basic_reset(self):
        
        MMM.re_slate()
        
        GRA.prepare()
        
        GRA.set_tape()
        
        MACH.reset_delivery()
        
        self.log('wiped/reset',MMM,GRA,MACH)
        
        pass

    def log(self, *args):     
        self.log_table.log(*args)
        #print(args)

    # method for menu and table control components 
    def UiComponents(self): 
        ##Derive a custom class from QLabel implementing handlers for mouse events.
        
        self.actions = {
            'machine':{
                'main':{
                    'connect':{'f':'connect','k':'C'},
                    'start':{'f':'start'},
                    'stop':{'f':'stop'},
                    'load':{'f':'load'},
                },
                'menu':True,
                'column':0,
                
            },
            'wind':{
                'main':{
                    'vars':{'f':'toggle vars list view.','k':'D','c':False},
                    'log status':{'f':'show grbl status in log','c':False},
                    'log grbl':{'f':'show grbl messages in log','c':True},
                    'check':{'f':'show machine information'},
                },
                'menu':True,
                'column':1,
            },
            'kpad_1':{
                'main':{
                    '1':{'f':'keypad1','ke':'1'},
                    '4':{'f':'keypad4','ke':'2'},
                    '7':{'f':'keypad7','k':'3'},
                    '-':{'f':'keypadNeg','k':'4'},
                },
                'menu':False,
                'column':2,
            },
            'kpad_2':{
                'main':{
                    '2':{'f':'keypad2','k':'1'},
                    '5':{'f':'keypad5','k':'2'},
                    '8':{'f':'keypad8','k':'3'},
                    '0':{'f':'keypad0','k':'4'},
                },
                'menu':False,
                'column':3,
            },
            'kpad_3':{
                'main':{
                    '3':{'f':'keypad3','k':'1'},
                    '6':{'f':'keypad6','k':'2'},
                    '9':{'f':'keypad9','k':'3'},
                    '+':{'f':'keypadPos','k':'4'},
                },
                'menu':False,
                'column':4,
            },
            'commands':{
                'main':{
                    'goto zero':{'f':'go to zero','k':'X'},
                    'set zero':{'f':'set zero position','k':'Z'},
                    'init':{'f':'init machine','k':'I'},
                },
                'menu':True,
                'column':6,
            },
            'basic':{
                'main':{
                    'auto':{'f':'auto run graphui','k':'A'},
                    'wipe':{'f':'clear it all out','k':'W'},
                    'marks':{'f':'toggle subplot bounds and numbers','k':'W','c':True},
                },
                'menu':True,
                'column':7,
            }
        }
        
        
        
        
        bar = self.menuBar()
        
        
        
        
        
        for c,n in enumerate(self.actions):
            c_col = self.actions[n]['column']
            group = self.actions[n]
            if group['menu']:
                
                top = bar.addMenu(n)
                top.setToolTipsVisible(True)
                top.hovered[QAction].connect(self.menu_action_hover)
                top.triggered[QAction].connect(self.menu_action_click)
            
            row = 0
            for k,v in self.actions[n]['main'].items():
                
                item_action = QAction(k,self)
                if 'k' in v: item_action.setShortcut("Ctrl+%s"%v['k'])
                if 'c' in v: 
                    item_action.setCheckable(True)
                    item_action.setChecked(v['c'])
                    
                item_action.setToolTip(v['f'])
                
                if group['menu']: top.addAction(item_action)

                control_label = NewLabel(' '+k+' ',item_action,)
                control_label.setAlignment(Qt.AlignCenter)
                control_label.setStatusTip(v['f'])
                self.tableWidget.setCellWidget(row , c_col, control_label)
        
                row += 1
        
        sFONT = QFont("minim", 18, QFont.Bold) #minim"PF Tempesta Seven"
        sFONT.setFixedPitch(True)
        sFONT.setStyleHint(QFont.Monospace)
        sFONT.setLetterSpacing(QFont.AbsoluteSpacing,2)
        for c in range(0,3):
            self.tableWidget.setRowHeight(c,32)
            rc = QTableWidgetItem(str('0000.000'))
            rc.setTextAlignment(Qt.AlignRight)
            rc.setTextAlignment(Qt.AlignVCenter)
            rc.setFont(sFONT)
            self.tableWidget.setItem(c , 5, rc)
            
        rc = QTableWidgetItem('State')
        rc.setTextAlignment(Qt.AlignCenter)
        self.tableWidget.setItem(3 , 5, rc)
        
        
        flit = QLabel('(comment)')
        flit.setObjectName('messenger')
        flit.setAlignment(Qt.AlignLeft)
        flit.setAlignment(Qt.AlignVCenter)
        self.tableWidget.setCellWidget(0 , 8, flit)
        self.messenger = flit
        
        flit = QLabel('(comment)')
        flit.setObjectName('user_location')
        flit.setAlignment(Qt.AlignLeft)
        flit.setAlignment(Qt.AlignVCenter)
        self.tableWidget.setCellWidget(1 , 8, flit)
        self.user_location = flit
        
        flit = selecta(self)
        flit.setObjectName('module_selecta')
        flit.addItems(["module", "numbers", "G0 (move to)", "circles", "texture", "text"])
        self.tableWidget.setCellWidget(2 , 8, flit)
        self.module_selecta = flit
        
        #self.module_selecta.parent = self 
        
        for c in range(0,self.tableWidget.columnCount()):
            self.tableWidget.resizeColumnToContents(c)


    

    def auto_run(self):
        global AUTORUN
        AUTORUN = not AUTORUN
        self.AUTO = AUTORUN
        self.COMD = 'init'
        log('Test Button Clicked.', 'AUTORUN:%s'%AUTORUN)
    
    def open_vars_tree(self):
        
        iv = self.vars_tree.isVisible()
        self.vars_tree.setVisible(not iv)
        #self.log_table.lower()
        #self.vars_tree.raise()
                        
    def controlWidgetResizeEvent(self,event):
        s = self.size()
        t = self.testSplitter.sizes()[0]
        self.log_table.setGeometry(0,0,s.width(),t-32)
        self.log_table.currentheight = t-32
        self.vars_tree.setGeometry(0,0,s.width(),t)
        
    def resizeEvent(self, event):
        s = self.size()
        #pass
        #p =  self.geometry().bottomLeft() - self.testFrame.geometry().bottomLeft() - QPoint(0,52)
        # self.ControlWidget.setGeometry(0,0,s.width(),int(s.height()/2))
        self.tableWidget.setGeometry(0,24,s.width(),int(s.height()/2))
        self.testSplitter.setGeometry(0,0,s.width(),s.height()-18)
        
        self.testSplitter.setSizes([2,1])
        t = self.testSplitter.sizes()[0]
        #self.ControlWidget.setFixedHeight(180)
        #self.testSplitter.setSizes([400,100])
        
        self.log_table.setGeometry(0,0,s.width(),t-32)
        self.log_table.currentheight = t-32
        
        self.vars_tree.setGeometry(0,0,s.width(),t)
        #self.log_table.currentheight = t-32
        
        #self.log_table.lower()
        # self.testFrame.setFixedWidth(s.width())
        # #self.testFrame.setGeometry(100,100,200,200)
        # self.graphicsView.setGeometry(0,0,s.width(),200)
        # self.testSplitter.setFixedWidth(s.width())
        # #self.testSplitter.setGeometry(0,0,s.width(),s.height())
        # #self.testLineEdit.setFixedWidth(s.width())
        self.progressBar.setGeometry(0,0,s.width(),24)
        self.progressBar.lower()        
        self.lineEdit.setGeometry(0,0,s.width(),24)

    def eventFilter(self, obj, event):
        if (event.type() == QEvent.KeyPress):
            key = event.key()
            if key == Qt.Key_Escape:
                print("Escape key")
        return super(MainWindow, self).eventFilter(obj, event)
    
    def iterate(self,spec=None):
        #TODO YOU DID IT!
        #if self.AUTORUN:
        if MACH.delivering: GRA.iterate(spec)
        #return

    def machine_trace(self):
        #if self.AUTORUN:
        GRA.machine_trace()
        #return
        
    def update_frame(self):
        try:
            
            self.frame += 1
            t = int(time.time() % 60)
            if t != self.tsec:
                self.statusBar().showMessage('%02i | %ifps' % (t,self.frame))
                self.tsec = t
                self.frame = 0
            
            if MACH.connected and MACH.status:
                for n,v in enumerate(MACH.status[1].split(',')):
                    tgt = self.tableWidget.item(n,5).setText(str("%8.3f" % float(v)))
                tgt = self.tableWidget.item(3,5).setText(str(MACH.status[0]))
                if MACH.lc: self.progressBar.setValue(int(100*(MACH.gc/MACH.gcl)))                
                #MMM.show_mach_location()
                
            if self.AUTORUN:
                GRA.iterate()
                
        except KeyboardInterrupt:
            print('KeyboardInterrupt W T F, use QUIT')
        
    def toggle_text_browser(self, event=None):
        print('clicked and released, yay',event)
        
    def input_trigger(self, event):
        print('test')
        pass
        
    def closeEvent(self, event):
        loop = asyncio.get_event_loop()
        loop.stop()
        self.log("asyncio loop.stop.")



    def plotClicked(self, evt, x, y):
        
        #self.parent.user_location.setText(f'Clicked ({x},{y})')
        print(evt, x, y)
        
        if self.module_selecta.index == 1: #for "numbers"
            f = characters.SAC_TEXT(position=[x,y], alignment='center')
            f.write((f'{self.plot_click_interactions_count}',),2.0,'bold')
            rew = bgc.line(f.lines_all,0)
            MACH.reset_delivery()
            MACH.load_gcode(rew)
            MACH.delivering = True
            self.lineEdit.setText(f'delivering module. ({self.plot_click_interactions_count})')
            
        elif self.module_selecta.index == 2: #for "G0 %s"          
            cmd = 'G0 X%4.3f Y%4.3f Z0 F%i' % (x,y,SEEK_RATE)
            self.lineEdit.setText(cmd)
            self.mach_cmd()
        
        self.plot_click_interactions_count += 1
        

    def moduleChange(self,index,name):
        #self.module_selecta
        print(index,name)
    
    def menu_action_hover(self,q):
          self.statusBar().showMessage(q.toolTip())
    
    def menu_action_click(self,q):
        #self.log('ACTION: %s %s' % (q.text(), q.isChecked()) )
        if q.text() == 'connect':
            q.setEnabled(False)
            self.mach_connect()
        elif q.text() == 'start':
            self.mach_start()
        elif q.text() == 'stop':
            self.mach_stop()
        elif q.text() == 'load':
            self.mach_load()
        elif q.text() == 'log grbl':
            MACH.log_grbl = q.isChecked()
        elif q.text() == 'log status':
            MACH.log_status = q.isChecked()
        elif q.text() == 'vars':
            self.open_vars_tree()
        elif q.text() == 'set zero':
            MACH.cmd = SET_ZERO
        elif q.text() == 'goto zero':
            MACH.cmd = GOTO_ZERO
        elif q.text() == 'init':
            MACH.cmd = INIT_DEPTH
        elif q.text() == 'check':
            self.mach_check()
        elif q.text() == 'auto':
            self.AUTORUN = not self.AUTORUN
        elif q.text() == 'wipe':
            self.basic_reset()
        elif q.text() == 'marks':
            MMM.marks = not MMM.marks
            if MMM.marks:
                MMM.g_base.show()
            else:
                MMM.g_base.hide()
                
        elif 'keypad' in q.toolTip():
            key = str(q.text())[-1]
            x,y = [[0,0],[-1,1],[0,1],[1,1],[-1,0],[0,0],[1,0],[-1,-1],[0,-1],[1,-1]][int(key)]
            
            mx,my,mz = [float(a) for a in MACH.status[2].split(',')] #s,m,w,b,r
            
            MACH.delivering = False
            cmd = f'G0 X{mx+x*10} Y{my+y*10} Z0 F{SEEK_RATE}'
            self.lineEdit.setText(cmd)
            self.mach_cmd()
            
    #THIS
    def mach_connect(self):
        self.log('MACH','def ƒ',__name__,inspect.stack()[0][3])
        loop = asyncio.get_event_loop()
        task = loop.create_task(MACH.run(loop))
        MACH.delivering = False
        
    #THIS
    def mach_start(self):
        #MACH.run_state('UNLOCK')
        self.log('MACH','def ƒ',__name__,inspect.stack()[0][3])
        MACH.delivering = True
        MACH.cmd = '~'
    
    #THIS
    def mach_stop(self):
        #MACH.run_state('LOCK')
        self.log('MACH','def ƒ',__name__,inspect.stack()[0][3])
        MACH.delivering = False
        MACH.cmd = '!'
    
    #THIS
    def mach_load(self):
        self.log('MACH','def ƒ',__name__,inspect.stack()[0][3])
        MACH.load_gcode(MMM.file_raw)
        MACH.delivering = False
        
    #THIS
    def mach_check(self):
        self.log('MACH CHECK')
        MACH.delivering = False
        MACH.test()
    
    #THIS
    def mach_cmd(self):
        cmd_txt = self.lineEdit.text()
        MACH.cmd = str(cmd_txt).strip()
        
        

    
"""ROOT FUNCTIONS [ƒ]"""
#prepare file sources from _args return file(s)_to_print[] autonome ƒ
def prepare_source(_args):
    print(sys.path[0],__file__,__name__)
    file_sources = []
    files_to_print = []
    extension = 'gcode'
    skip_exts = ["session", ".ai", ".png", ".jpg"]

    if _args.file: 
        PATH = _args.file
        
        if os.path.exists(PATH):
            if os.path.isfile(PATH):
                file_sources += [PATH]
            else:
                file_sources += [file for file in os.listdir(PATH) if not any(x in file for x in skip_exts)]
                #os.path.join(PATH,file)
                file_ordered = sorted(file_sources,key=lambda x: int(os.path.splitext(x)[0]))
                file_sources = [os.path.join(PATH,file) for file in file_ordered]
        else:
            print('path no found:',PATH)
            exit()

        
        for f_PATH in file_sources:
            CONVERT_SVG = False if '.gcode' in f_PATH or '.txt' in f_PATH else True
            f_PATH_abs = os.path.join(os.getcwd(),f_PATH)
            
            files_to_print += [gcodeParser.svg_to_gcode(f_PATH_abs, _args) if CONVERT_SVG else f_PATH_abs]
            print('file:', f_PATH, f_PATH_abs, CONVERT_SVG)
            
        if _args.session:
            #//assumes sources in same directory
            session_file_path = os.path.join(os.getcwd(),PATH,'session.gcode')
            with open(session_file_path,'w+') as file:
                file.truncate(0)
                for f in files_to_print:
                    with open(f) as cmd_block:
                        file.write(cmd_block.read()+'\n\n')
            
            files_to_print = [session_file_path]
            print('session:', session_file_path)
            
    else:    
        print('no path provided. opening module.')
        #exit()
        
    
    return files_to_print

   
    

"""ROOT INSTANCES [ƒ]"""
MMM = MainPlotWindowHandler()
GRA = GraphUtil()
MACH = ser_async_grbl() 

    

"""MEATS,+WINES,+CHEESES"""    
if __name__ == '__main__':

    app = QApplication(sys.argv)
    app.setFont(FONT)
    app.setApplicationName("basic")
    window = MainWindow()
    
    window.log('Initialized')
    
    loop = QEventLoop(app)
    asyncio.set_event_loop(loop)
    
    with loop:
        sys.exit(loop.run_forever())
    #OR app.exec_()