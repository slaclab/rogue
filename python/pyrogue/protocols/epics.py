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
import pyrogue
import time
import rogue.protocols.epicsV3

class EpicsCaServer(object):
    """
    Class to contain an epics ca server
    """
    def __init__(self,*,base,root,minVisibility=0,pvMap=None, syncRead=True, threadCount=0):
        self._root      = root
        self._base      = base 
        self._log       = pyrogue.logInit(cls=self)
        self._syncRead  = syncRead
        self._srv       = rogue.protocols.epicsV3.Server(threadCount)

        if not root.running:
            raise Exception("Epics can not be setup on a tree which is not started")

        if pvMap is None:
            doAll = True
            self._pvMap = {}
        else:
            doAll = False
            self._pvMap = pvMap

        # Create PVs
        for v in self._root.variableList:
            self._addPv(v,doAll,minVisibility)

    def createSlave(self, name, maxSize, type):
        slave = rogue.protocols.epicsV3.Slave(self._base + ':' + name,maxSize,type)
        self._srv.addValue(slave)
        return slave

    def createMaster(self, name, maxSize, type):
        mast = rogue.protocols.epicsV3.Master(self._base + ':' + name,maxSize,type)
        self._srv.addValue(mast)
        return mast

    def stop(self):
        self._srv.stop()

    def start(self):
        self._srv.start()

    def list(self):
        return self._pvMap

    def dump(self):
        for k,v in self._pvMap.items():
            print("{} -> {}".format(v,k))

    def _addPv(self,node,doAll,minVisibility):
        eName = self._base + ':'

        if doAll:
            if node.visibility >= minVisibility:
                eName += node.path.replace('.',':')
                self._pvMap[node.path] = eName
        elif node.path in self._pvMap:
            eName = self._pvMap[node.path]
        else:
            return

        if isinstance(node, pyrogue.BaseCommand):
            self._srv.addValue(rogue.protocols.epicsV3.Command(eName,node))
            self._log.info("Adding command {} mapped to {}".format(node.path,eName))
        else:

            # Add standard variable
            evar = rogue.protocols.epicsV3.Variable(eName,node,self._syncRead)
            node.addListener(evar.varUpdated)
            self._srv.addValue(evar)
            self._log.info("Adding variable {} mapped to {}".format(node.path,eName))

