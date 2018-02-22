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
import pyrogue
import time
import rogue.protocols.epics

class EpicsCaServer(object):
    """
    Class to contain an epics ca server
    """
    def __init__(self,*,base,root,pvMap=None, sync_read=True):
        self._root      = root
        self._base      = base 
        self._log       = pyrogue.logInit(self)
        self._sync_read = sync_read
        self._srv       = rogue.protocols.epics.Server()

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

    def createSlave(self, name, maxSize, type):
        slave = rogue.protocols.epics.Slave(self._base + ':' + name,maxSize,type)
        self.addValue(slave)
        return slave

    def stop(self):
        self._srv.stop()

    def start(self):
        self._srv.start()

    def _addPv(self,node,doAll):
        name = self._base + ':'

        if doAll:
            eName += node.path.replace('.',':')
        elif node.path in self._pvMap:
            eName = self._pvMap[node.path]
        else:
            return

        if isinstance(node, pyrogue.BaseCommand):
            evar = rogue.protocols.epics.Command(eName,node)
        else:
            evar = rogue.protocols.epics.Variable(eName,node,self._sync_read)
            node.addListener(evar.varUpdated)
      
        svr.addValue(evar)
        self._log.info("Adding {} mapped to {}".format(node.path,eName))

