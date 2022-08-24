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
from pyrogue.protocols.autosave import Autosave

class EpicsCaServer(object):
    """
    Class to contain an epics ca server
    """
    def __init__(self,*,base,root,incGroups=None,excGroups=None,pvMap=None, syncRead=True, 
                 threadCount=0, iocname=None):
        self._root      = root
        self._base      = base
        self._log       = pyrogue.logInit(cls=self)
        self._syncRead  = syncRead
        self._srv       = rogue.protocols.epicsV3.Server(threadCount)
        self._pvMap     = pvMap
        self._incGroups = incGroups
        self._excGroups = excGroups
        self._started   = False
        self._autosave  = Autosave(iocname, self)
        self._nodeMap   = {}

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
        self._nodeMap = {}
        for v in self._root.variableList:
            self._addPv(v,doAll,self._incGroups,self._excGroups)
        self._srv._start()
        self._autosave.start()

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
            self._nodeMap[eName] = node
            # Do autosave!
            ival = self._autosave.getInitialValue(eName)
            if ival is not None:
                # ival is a string.  We need to make it the proper type.
                t = node.nativeType()
                if t == bool:
                    ival = False if int(ival) == 0 else True
                elif t == int:
                    ival = int(ival)
                elif t == float:
                    ival = float(ival)
                node.set(ival)
            evar = rogue.protocols.epicsV3.Variable(eName,node,self._syncRead)
            node.addListener(evar.varUpdated)
            self._srv._addValue(evar)
            self._log.info("Adding variable {} mapped to {}".format(node.path,eName))

    """
    Value store interface for autosave.  Return the variable value as a string, or
    None if not a valid variable.
    """
    def getValue(self, name):
        try:
            v = self._nodeMap[name].value()
            if type(v) == float:
                return "%.14g" % v
            elif type(v) == bool:
                return "1" if True else "0"
            else:
                return str(v)
        except:
            pass
        return None

