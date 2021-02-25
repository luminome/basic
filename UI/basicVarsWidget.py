#!/usr/bin/env python3
import sys
import time
import locale
import os
import json
import time
import inspect

from time import strftime, gmtime

from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5 import uic


class VarsWidget(QTreeWidget):
    def __init__(self, parent=None):
        QTreeWidget.__init__(self, parent)
        
        self.bright = QColor(0, 255, 0)
        self.normal = QColor(0, 200, 0)
        self.special = QColor(0, 45, 0)
        
        self.setAlternatingRowColors(1);
        # p = QPalette() #palette();
        # p.setColor( QPalette.AlternateBase, QColor(226, 237, 253) );
        # self.setPalette(p);
        
        self.setObjectName("basicVarsWidget")
        self.setColumnCount(3)
        self.setColumnWidth(0,200)
        self.setColumnWidth(1,200)
        self.setHeaderLabels(("property","value","aux"))
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.setAutoFillBackground(True)
        self.customContextMenuRequested.connect(self.openMenu)
        
        self.icon = QIcon('UI/graphics/plus-icon.png')
        self.button_style = "QPushButton {color:rgba(%i,%i,%i,%i); border: 0; padding:0; max-width: 12; height: 12;}" % self.bright.getRgb()
        
        f = 'UI/basic-plist.json'
        l = os.path.join(os.getcwd(),f)
        
        self.PATH = l
        self.DATA = self.load_json_dict(l)
        self.FONT = QFont('Monaco', 12)
        
        root = self.invisibleRootItem()
        list(self.id_generator(root,self.DATA))
        
        self.item_edit_name = None
        
        self.setMouseTracking(True)
        self.itemClicked.connect(self.onItemClicked)
        self.itemEntered.connect(self.onItemEntered)
        self.itemChanged.connect(self.saveEdit)
        self.itemDoubleClicked.connect(self.checkEdit)
        self.resizeColumnToContents(0)
        self.resizeColumnToContents(1)
        
        
    def id_generator(self,root,dict_var,l=0,ni=0):
        for n,k in enumerate(dict_var):
            qw = QTreeWidgetItem(n)
            root.addChild(qw)
            
            if isinstance(dict_var, dict):
                v = dict_var[k]
                qw.setData(0, 2, str(k))
            else:
                v = k
            
            if l == 0:
                qw.setExpanded(True)
                
            can_edit = None
            
            if isinstance(v, dict) or isinstance(v, list):
                ct = 0
                for id_val in self.id_generator(qw,v,l+1,n):
                    ct += 1
                    yield (l,id_val)

                qw.setData(1, 2, '(%i)'%ct)
                can_edit = True
                    
            else:
                qw.setForeground( 1 , self.bright)
                qw.setData(1, 2, str(v))
                can_edit = True
                yield ('v',v)
    
            tmp = qw.flags()
            if can_edit:
                qw.setFlags(tmp | Qt.ItemIsEditable)
            elif tmp & Qt.ItemIsEditable:
                qw.setFlags(tmp ^ Qt.ItemIsEditable)
                
    def slog(self, *args):
        self.parent().log(args)
        
    def save_json_dict(self,new_dict,proc_path=None):
        with open(proc_path, 'w+') as fi:
            json.dump(new_dict, fi, indent = 4)
    
    def load_json_dict(self,proc_path=None):
        pr = None
        f = open(proc_path,'r')
        process = json.load(f)
        f.close()
        return process
        
    def save_data(self, klist, kva=None):
        #global DATA

        def hand(obj,klist,n=0):
            if isinstance(obj, dict) and n<len(klist)-1:
                d_obj = obj[klist[n]]
                #self.slog(d_obj)
                if isinstance(d_obj, dict):
                    return hand(d_obj,klist,n+1)
                elif isinstance(d_obj, list):
                    #if len(d_obj) > 1: 
                        
                    if len(str(kva)) > 0: 
                        i = klist[n+1]
                        if i > len(d_obj)-1:
                            d_obj.append(kva)
                        else:
                            d_obj[i] = kva
                    #else:
                    #    if kva: d_obj[0] = kva
                    #return d_obj
                else:
                    
                    if len(str(kva)) > 0: obj[klist[n]] = kva
                    #self.slog("HERE!",obj[klist[n]])
                    return obj
            
            return obj
        
        #self.slog([klist])
        data_object = hand(self.DATA,klist)
        return data_object

    def get_heirarchy(self,item):
        level_list = []
        current_item = item
        current_index = self.indexFromItem(current_item)

        if current_index.isValid():
            dat = current_item.data(0,2) 
            if dat: level_list.append(dat)
            rw = current_index.row()
        while current_index.isValid():
            current_item = self.itemFromIndex(current_index.parent())
            current_index = self.indexFromItem(current_item)
            if current_index.isValid():
                pt = current_item.data(0,2)
                level_list.append(pt)
        
        level_list = level_list[::-1]
        level_list.append(rw)
        
        return level_list
        
    def update_tree_item(self, item):
        n = item.childCount()
        if n:
            item.setData(1,2,'(%i)'%n)
        else:
            item.setData(1,2,0)
        item.setForeground( 2 , self.normal)
        pass
        
    #@pyqtSlot(QTreeWidgetItem, int)
    def saveEdit(self, item, col):
        #global DATA,PATH
        
        flags = item.flags()
        if flags & Qt.ItemIsEditable:
            
            if self.item_edit_name and self.item_edit_name != item.text(0):
                f = self.get_heirarchy(item)[:-2]
                f.append(self.item_edit_name)
                f.append(0)
                DF = self.save_data(f)
                DF[item.text(0)] = DF[self.item_edit_name]
                del(DF[self.item_edit_name])

            if item.childCount() == 0:
                if item.text(0) != item.text(col):
                    try:
                        v = float(item.text(col)) if '.' in item.text(col) else int(item.text(col))
                        
                    except ValueError as err:
                        v = str(item.text(col))
                        
                    f = self.get_heirarchy(item)
                    self.slog('edited',f, [item.text(0)], v)
                    DF = self.save_data(f, v)
            
            self.save_json_dict(self.DATA,self.PATH)
            
        self.item_edit_name = None
        
    #@pyqtSlot(QTreeWidgetItem, int)
    def checkEdit(self, item, col):
        self.item_edit_name = item.text(0)
        #self.slog(item.text(0))
        pass
    
    #@pyqtSlot(QTreeWidgetItem, int)
    def onItemClicked(self, item, col):
        f = self.get_heirarchy(item)
        DF = self.save_data(f)
        try:
            V = DF[item.text(0)]
        except KeyError:
            V = item.text(1)
            
        self.slog('F:QTreeWidgetItem.clicked',f,V)
        #if self.parent():self.parent().LOG.log(['F:QTreeWidgetItem.clicked',f,V])
        
        pass
        
    #@pyqtSlot(QTreeWidgetItem, int)
    def onItemEntered(self, item, col):
        pass
        # f = self.get_heirarchy(item)
        # r = self.indexFromItem(item).row()
        # status = '%i %s' % (r, f)
        # self.statusBar.showMessage(status)
    
    def add_node(self,item,it_type='list'):
        n = item.childCount()
        qc = QTreeWidgetItem(n+1)
        
        if it_type == 'list':
            qc.setData(1,2,'blank')
            qc.setForeground( 1 , self.bright)
        elif it_type == 'dict':
            qc.setData(0,2,'blank_%02i'%n)
            qc.setData(1,2,'blank')
            qc.setForeground( 1 , self.bright)
        else:
            qc.setData(0,2,'blank_%02i'%n)
            #qc.setForeground( 1 , self.normal)
            
        
        item.addChild(qc)
        
        self.update_tree_item(item)
        
        tmp = qc.flags()
        qc.setFlags(tmp | Qt.ItemIsEditable)
        return qc
        pass
    
    def openMenu(self, position):
        indexes = self.selectedIndexes()
        if not len(indexes): return
        rollo = None
        self.menu = QMenu()
        
        index = indexes[0]
        qw = self.itemFromIndex(index)
        
        data_on_first = qw.data(0,2)
        f = self.get_heirarchy(qw)
        DF = self.save_data(f)
        DFTYPE = str(type(DF)).split("'")[1]
              
        try:
            if qw.text(0):
                s = DF[qw.text(0)]
                if type(s) == list: DFTYPE = 'list'
            else:
                DFTYPE = 'list-item'
        except KeyError as err:
            pass
        
        add_list_item = None
        add_list = None
        add_value = None
        remove_list_item = None
        remove_item = None
        
        if DFTYPE == 'dict':
            add_list = self.menu.addAction(self.tr('add-list'))
            add_value = self.menu.addAction(self.tr('add-value'))
            remove_item = self.menu.addAction(self.tr('remove'))
        if DFTYPE == 'list' and data_on_first:
            add_list_item = self.menu.addAction(self.tr('add-item'))
            remove_item = self.menu.addAction(self.tr('remove'))
        if DFTYPE == 'list-item' and not data_on_first:
            remove_list_item = self.menu.addAction(self.tr('remove-item'))

        if DF: rollo = type(DF).__name__

        #pat = self.treeWidget.palette()
        action = self.menu.exec_(self.viewport().mapToGlobal(position))
        if not action: return
        
        if action == remove_item:
            # self.slog('remove_item subroutine here.')
            # self.slog(qw.text(0),f,DF)
            # print(DF)
            
            del(DF[qw.text(0)])
            
            p = qw.parent()
            
            if len(DF) == 0:
                par = p.text(0)
                f = self.get_heirarchy(p.parent())
                DZ = self.save_data(f)
                DZ[par] = 0
                
                #self.slog('DZ',DZ)
                # par = p.parent().text(0)
                # f = self.get_heirarchy(p)
                # DW = self.save_data(f)
                # DW[par] = 0
            
            p.removeChild(qw)
            self.update_tree_item(p)
            
        if action == remove_list_item:
            self.slog('remove_list_item subroutine here.')
            dli = qw.parent().text(0)
            b = DF[dli]
            del(b[f[-1]])
            p = qw.parent()
            p.removeChild(qw)
            self.update_tree_item(p)
            
        if action == add_list_item:
            self.slog('add_list_item subroutine here.')
            DA = self.save_data(f,'blank')
            self.add_node(qw,'list')
               
        if action == add_value:
            self.slog('add_value subroutine here.')
            n = qw.childCount()
            DA = self.save_data(f)
            #self.slog(DA[qw.text(0)])
            #rp = DA[qw.text(0)]
            #self.slog(DA)
            #subsequent additions handled differently.
            
            if n == 0:
                try:
                    DA[qw.text(0)] = {('blank_%02i'%n):'blank'}
                except KeyError as err:
                    pass #self.slog('KeyError',err)
            else:
                DA[('blank_%02i'%n)] = 'blank'
            #DA['blank_%02i'%n] = 'blank'
            self.add_node(qw,'dict')
            qw.setExpanded(True)
            #else:
                #self.slog('DA',DA)
                #DA[qw.text(0)]['blank_%02i'%n] = 'blank' #{('blank_%02i'%n):'blank'}
                
                
            #how ot get position here?
            #yeah ok.

        if action == add_list:
            self.slog('add_list subroutine here.')
            n = qw.childCount()
            DA = self.save_data(f)
            DA['blank_%02i'%n] = ['blank']
            
            qs = self.add_node(qw,'array')
            qs.setExpanded(True)
            
            self.add_node(qs,'list')
            #how ot get position here?
            #yeah ok.
    
    def resizeEvent(self, event):
        s = self.size()
        # self.centralWidget.setGeometry(0,0,s.width(),s.height())
        # self.LOGStab.setGeometry(0,0,s.width(),s.height())
        # self.LISTtab.setGeometry(0,0,s.width(),s.height())
        self.setGeometry(0,0,s.width(),s.height())
        
    def eventFilter(self, obj, event):
        if (event.type() == QEvent.KeyPress):
            key = event.key()
            if key == Qt.Key_Escape:
                self.slog("Escape key")
        return super(QTreeWidget, self).eventFilter(obj, event)

    def closeEvent(self, event):
        print("shut down pop-list.")

    
if __name__ == '__main__':
    
    app = QApplication(sys.argv)
    app.setApplicationName("basicVarsWidget")
    window = VarsWidget()
    app.setFont(window.FONT)
    
    window.WINDOW_OPEN = True
    window.show()
    #window.setContentsMargins(20, 20, 20, 20)

    app.exec_()