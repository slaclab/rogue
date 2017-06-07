#!/usr/bin/env python
#-----------------------------------------------------------------------------
# Title      : PyRogue epics support
#-----------------------------------------------------------------------------
# File       : pyrogue/epics.py
# Author     : Ryan Herbst, rherbst@slac.stanford.edu
# Created    : 2016-09-29
# Last update: 2016-09-29
#-----------------------------------------------------------------------------
# Description:
# Module containing epics support classes and routines
#-----------------------------------------------------------------------------
# This file is part of the rogue software platform. It is subject to 
# the license terms in the LICENSE.txt file found in the top-level directory 
# of this distribution and at: 
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html. 
# No part of the rogue software platform, including this file, may be 
# copied, modified, propagated, or distributed except according to the terms 
# contained in the LICENSE.txt file.
#-----------------------------------------------------------------------------
import threading
import pyrogue
import time
import pcaspy

try:
   import queue
except ImportError:
   import Queue as queue


class EpicsCaDriver(pcaspy.Driver):
    def __init__(self,queue):
        pcaspy.Driver.__init__(self)
        self._q = queue

    def write(self,reason,value):
        entry = {'value':value,'epath':reason}
        self._q.put(entry)
        self.setParam(reason,value)


class EpicsCaServer(object):
    """
    Class to contain an epics ca server
    """
    def __init__(self,base,root,pvMap=None):
        self._root    = root
        self._base    = base 
        self._runEn   = True
        self._server  = None
        self._driver  = None
        self._queue   = queue.Queue()
        self._wThread = None
        self._eThread = None
        self._pvDb    = {}
        self._log     = pyrogue.logInit(self)

        if pvMap is None:
            doAll = True
            self._pvMap = {}
        else:
            doAll = False
            self._pvMap = pvMap

        # Create PVs
        self._addDevice(self._root,doAll)

    def stop(self):
        self._runEn = False
        self._wThread.join()
        self._eThread.join()
        self._wThread = None
        self._eThread = None

    def start(self):
        self._runEn = True
        self._eThread = threading.Thread(target=self._epicsRun)
        self._wThread = threading.Thread(target=self._workRun)
        self._eThread.start()
        self._wThread.start()

    def _addPv(self,node,doAll):
        d = {}

        if doAll:
            d['name'] = node.path.replace('.',':')
        elif node.path in self._pvMap:
            d['name'] = self._pvMap[node.path]
        else:
            return

        self._pvMap[node.path] = d
        d['var'] = node

        if node.disp == 'enum':
            d['type']  = 'enum'
            d['enums'] = [val for key,val in node.enum.items()] 
            d['value'] = d['enums'].index(node.valueDisp())

        else:
            d['value'] = node.value()

            if node.minimum is not None:
                d['lolim'] = node.minimum
            if node.maximum is not None:
                d['hilim'] = node.maximum

            d['type'] = d['value'].__class__.__name__

            # Commands return None
            if d['type'] == 'NoneType':
                d['type'] = 'int'
            elif d['type'] == 'bool':
                d['type'] = 'int'
            
        node.addListener(self._variableUpdated)

        self._log.info("Adding {} type {} maped to {}".format(node.path,d['type'],d['name']))
        self._pvDb[d['name']] = d

    def _addDevice(self,node,doAll):

        # Get variables 
        for key,value in node.variables.items():
            self._addPv(value,doAll)

        # Get commands
        for key,value in node.commands.items():
            self._addPv(value,doAll)

        # Get devices
        for key,value in node.devices.items():
            self._addDevice(value,doAll)

    def _epicsRun(self):
        self._server = pcaspy.SimpleServer()

        # Create PVs
        self._server.createPV(self._base + ':',self._pvDb)
        self._driver = EpicsCaDriver(self._queue)

        while(self._runEn):
            self._server.process(0.5)

    def _workRun(self):
        while(self._runEn):
            try:
                e = self._queue.get(True,0.5)
                d = self._pvDb[e['epath']]
                value = e['value']

                if d['type'] == 'enum':
                    val = d['enums'][value]
                    d['var'].setDisp(val)
                else:
                    val = e['value']
                    d['var'].set(val)
            except:
                pass

    # Variable was updated
    def _variableUpdated(self,var,value,disp):
        if self._driver is None: return

        d = self._pvMap[var.path]

        if d['type'] == 'enum':
            val = d['enums'].index(disp)
        else:
            val = value

        self._driver.setParam(d['name'],val)
        self._driver.updatePVs()

