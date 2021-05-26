#-----------------------------------------------------------------------------
# Title      : PyRogue epics support
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
import rogue.protocols.epicsV3


class EpicsCaServer(object):
    """
    Class to contain an epics ca server
    """
    def __init__(self,*,base,root,incGroups=None,excGroups=None,pvMap=None, syncRead=True, threadCount=0):
        self._root      = root
        self._base      = base
        self._log       = pyrogue.logInit(cls=self)
        self._syncRead  = syncRead
        self._srv       = rogue.protocols.epicsV3.Server(threadCount)
        self._pvMap     = pvMap
        self._incGroups = incGroups
        self._excGroups = excGroups
        self._started   = False

    def createSlave(self, name, maxSize, type):
        slave = rogue.protocols.epicsV3.Slave(self._base + ':' + name,maxSize,type)
        self._srv._addValue(slave)
        return slave

    def createMaster(self, name, maxSize, type):
        mast = rogue.protocols.epicsV3.Master(self._base + ':' + name,maxSize,type)
        self._srv._addValue(mast)
        return mast

    def stop(self):
        # Add deprecration warning in the future
        self._stop()

    def start(self):
        # Add deprecration warning in the future
        self._start()

    def _stop(self):
        self._srv._stop()
        self._srv = None

    def _start(self):

        if self._started:
            return

        self._started = True

        if not self._root.running:
            raise Exception("Epics can not be setup on a tree which is not started")

        if self._pvMap is None:
            doAll = True
            self._pvMap = {}
        else:
            doAll = False

        # Create PVs
        for v in self._root.variableList:
            self._addPv(v,doAll,self._incGroups,self._excGroups)

        self._srv._start()

    def list(self):
        return self._pvMap

    def dump(self,fname=None):
        if fname is not None:
            try:
                with open(fname,'w') as f:
                    for k,v in self._pvMap.items():
                        print("{} -> {}".format(v,k),file=f)
            except Exception:
                raise Exception("Failed to dump epics map to {}".format(fname))
        else:
            for k,v in self._pvMap.items():
                print("{} -> {}".format(v,k))

    def _addPv(self,node,doAll,incGroups,excGroups):
        eName = self._base + ':'

        if doAll:
            if node.filterByGroup(incGroups,excGroups):
                eName += node.path.replace('.',':')
                self._pvMap[node.path] = eName
        elif node.path in self._pvMap:
            eName = self._pvMap[node.path]
        else:
            return

        if isinstance(node, pyrogue.BaseCommand):
            self._srv._addValue(rogue.protocols.epicsV3.Command(eName,node))
            self._log.info("Adding command {} mapped to {}".format(node.path,eName))
        else:

            # Add standard variable
            evar = rogue.protocols.epicsV3.Variable(eName,node,self._syncRead)
            node.addListener(evar.varUpdated)
            self._srv._addValue(evar)
            self._log.info("Adding variable {} mapped to {}".format(node.path,eName))
