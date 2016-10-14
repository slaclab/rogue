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
import yaml
import threading
import pyrogue
import time
import pcaspy


class EpicsCaDriver(pcaspy.Driver):
    def __init__(self,root):
        pcaspy.Driver.__init__(self)
        self._root = root

    def write(self,reason,value):
        print("epics: write %s = %s" % (reason,value))


class EpicsCaServer(threading.Thread):
    """
    Class to contain an epics ca server
    """
    def __init__(self,base,root):
        threading.Thread.__init__(self)
        self._root    = root
        self._base    = base 
        self._runEn   = True
        self._server  = None

        if self._root:
            self._root.addVarListener(self._variableStatus)

        self.start()

    def _addDevice(self,node,pvdb):

        # Get variables
        for key,value in node.getNodes(pyrogue.Variable).iteritems():
            if value.hidden == False:
                d = {}
                if value.base == 'enum': 
                    d['type'] = 'enum'
                    d['enums'] = [value for value in value.enums]
                elif value.base == 'uint' or value.base == 'hex':
                    d['type'] = 'int'
                else:
                    d['type'] = 'string'

                name = value.path.replace('.',':')
                print("Adding: %s" % (name))
                pvdb[name] = d

        # Get devices
        for key,value in node.getNodes(pyrogue.Device).iteritems():
            if value.hidden == False:
                self._addDevice(value,pvdb)

    def run(self):
        server = pcaspy.SimpleServer()

        # Create PVs
        pvdb = {}
        self._addDevice(self._root,pvdb)

        server.createPV(self._base + ':',pvdb)
        driver = EpicsCaDriver(self._root)

        while(self._runEn):
            server.process(0.1)

    # Variable field updated on server
    def _variableStatus(self,yml,d):
        self._walkDict("",d)
        self._driver.setPVs()

    def _walkDict(self,currPath,d):
        for key,value in d.iteritems():
            locPath = currPath + ':' + key
            if isinstance(value,dict):
                self._walkDict(locPath,value)
            else:
                print("epics: updating %s = %s" % (locPath,value))
                self._driver.setParam(locPath,value)

