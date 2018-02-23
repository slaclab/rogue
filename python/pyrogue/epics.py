#!/usr/bin/env python
#-----------------------------------------------------------------------------
# Title      : PyRogue epics support
#-----------------------------------------------------------------------------
# File       : pyrogue/protocols/epics.py
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
import ctypes

try:
   import queue
except ImportError:
   import Queue as queue


class EpicsCaDriver(pcaspy.Driver):
    def __init__(self,queue, reg_map=None):
        pcaspy.Driver.__init__(self)
        self._q = queue
        self._reg_map = reg_map

    def write(self,reason,value):
        entry = {'value':value,'epath':reason}
        self._q.put(entry)
        self.setParam(reason,value)

# This class redefine the read method to do synchronous read
# using get() method for each caget call
class EpicsCaDriverSync(EpicsCaDriver):

    def read(self,reason):
        # Call register's get() method to update value
        if reason in self._reg_map:
            self._reg_map[reason].get()
        
        return self.getParam(reason)

class EpicsCaServer(object):
    """
    Class to contain an epics ca server
    """
    def __init__(self,*,base,root,pvMap=None, sync_read=True):
        self._root      = root
        self._base      = base 
        self._runEn     = True
        self._server    = None
        self._driver    = None
        self._queue     = queue.Queue()
        self._wThread   = None
        self._eThread   = None
        self._pvDb      = {}
        self._log       = pyrogue.logInit(self)
        self._sync_read = sync_read

        if not root.running:
            raise Exception("Epics can be setup on a tree which is not started")

        if pvMap is None:
            doAll = True
            self._pvMap = {}
        else:
            doAll = False
            self._pvMap = pvMap

        # Create PVs
        for v in self._root.variableList:
            self._addPv(v,doAll)

    def stop(self):
        self._runEn = False
        if self._wThread is not None:
            self._wThread.join()
        if self._eThread is not None:
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

            # EPICS uses 32-bit signed integers, 
            # So, check if the register value is unsigned, and cast the value if so.
            # Check if it is a RemoteVariable as LocalVariables don't have base property.
            if isinstance(node, pyrogue.RemoteVariable):
                if node.base is pyrogue.UInt:
                    d['value'] = ctypes.c_int(node.value()).value
            
            # All devices should return a not NULL value
            if d['value'] is None:
                self._log.warning("Device {} has a null value".format(d['name']))

            if node.minimum is not None:
                d['lolim'] = node.minimum
            if node.maximum is not None:
                d['hilim'] = node.maximum

            # Get device type
            d['type'] = d['value'].__class__.__name__

            # All devices should return a type different from NoneType
            if d['type'] == 'NoneType':
                self._log.warning("Device {} returned NoneType".format(d['name']))
                return 

            # Adjust some types
            if d['type'] == 'string' or d['type'] == 'str':
                # If this command has arguments, use char
                # String type will accept upto 40 chars only so
                # let's use char with count > 40 instead to accept longer inputs 
                # We can do "caput -s PV "long string argument"" to call the command
                d['type']  = 'char'
                d['count'] =  300
            elif d['type'] == 'bool':
                # Bool is not supported, so let's use int instead
                d['type'] = 'int'

            # Handle lists
            elif d['type'] == 'list':
                d['type'] = d['value'][0].__class__.__name__
                d['count'] = len(d['value'])

            # These are the only type supported by pcaspy
            supportedType = {"enum", "string", "char", "float", "int"}

            # Check if type is supported
            if d['type'] not in supportedType:
                self._log.warning("Device {} has type {} which is not supported by pcaspy".format(d['name'], d['type'] ))
                return
            
        node.addListener(self._variableUpdated)

        self._log.info("Adding {} type {} maped to {}".format(node.path,d['type'],d['name']))
        self._pvDb[d['name']] = d

    def _epicsRun(self):
        self._server = pcaspy.SimpleServer()

        # Create PVs
        self._server.createPV(self._base + ':',self._pvDb)

        # Create CA driver
        if self._sync_read:
            # Create PV name, register dictionary
            reg_map = {value['name']:value['var'] for key,value in self._pvMap.items()}
            self._driver = EpicsCaDriverSync(self._queue, reg_map)
        else:
            self._driver = EpicsCaDriver(self._queue)

        while(self._runEn):
            self._server.process(0.5)

    def _workRun(self):
        while(self._runEn):
            try:
                e = self._queue.get(True,0.5)
                d = self._pvDb[e['epath']]
                v = d['var']

                # Enum must be converted for both commands and variables
                if d['type'] == 'enum':
                    value = d['enums'][e['value']]
                else:
                    value = e['value']

                    # EPICS uses 32-bit signed integers
                    # So, check if the register value is unsigned, and cast the value if so.
                    # Check if it is a RemoteVariable as LocalVariables don't have base property. 
                    if isinstance(v, pyrogue.RemoteVariable):
                        if v.base is pyrogue.UInt:
                            value = ctypes.c_uint(e['value']).value

                if self._isCommand(v):
                    # Process command requests
                    v.call(value)
             
                else:
                    # Process normal register write requests
                    v.setDisp(value)

            except:
                pass

    # Variable was updated
    def _variableUpdated(self,path,value,disp):
        if self._driver is None: return

        d = self._pvMap[path]

        if d['type'] == 'enum':
            val = d['enums'].index(disp)
        else:
            val = value

            # EPICS uses 32-bit signed integers, 
            # So, check if the register value is unsigned, and cast the value if so.
            # Check if it is a RemoteVariable as LocalVariables don't have base property.
            if isinstance(d['var'], pyrogue.RemoteVariable):
                if d['var'].base is pyrogue.UInt:
                    val = ctypes.c_int(value).value

        self._driver.setParam(d['name'],val)
        self._driver.updatePVs()

    # Is this variable a command?
    def _isCommand(self, var):
        # Command are instances of pyrogue.BaseCommand
        return isinstance(var, pyrogue.BaseCommand)

