#!/usr/bin/env python
#-----------------------------------------------------------------------------
# Title      : PyRogue epics support
#-----------------------------------------------------------------------------
# File       : pyrogue/protocols/epicsV4.py
# Author     : Ryan Herbst, rherbst@slac.stanford.edu
# Created    : 2019-08-08
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
import p4p.server.thread
import p4p.nt
import threading

class EpicsPvHandler(p4p.server.thread.Handler):
    def __init__(self, holder):
        self._holder = holder

    def put(self, pv, op):
        if self._holder.var.mode == 'RW' or self._holder.var.mode == 'WO':
            val = op.value().raw.value
            typ = type(val)
            print(f"PV Put called pv={pv} type={typ}, value={val}")
            self._holder.var.set(val)

    def rpc(self, pv, op):
        print(f"PV RPC called pv={pv} op={op}")

    def onFirstConnect(self, pv): # may be omitted
        print(f"PV First connect called pv={pv}")

    def onLastDisconnect(self, pv): # may be omitted
        print(f"PV Last Disconnect called pv={pv}")

class EpicsPvHolder(object):
    def __init__(self,name,var):
        self._var  = var
        self._name = name
        valType = 's'

        # Convert valType
        if 'UInt' in var.typeStr:
            if isinstance(var,pyrogue.RemoteVariable):
                if   sum(var.bitSize) <= 8:  valType = 'B'
                elif sum(var.bitSize) <= 16: valType = 'H'
                elif sum(var.bitSize) <= 32: valType = 'I'
                else: valType = 'L'
            else:
                valType = 'L'

        elif 'Int' in var.typeStr:
            if isinstance(var,pyrogue.RemoteVariable):
                if   sum(var.bitSize) <= 8:  valType = 'b'
                elif sum(var.bitSize) <= 16: valType = 'h'
                elif sum(var.bitSize) <= 32: valType = 'i'
                else: valType = 'l'
            else:
                valType = 'l'

        elif 'Float' in var.typeStr:
            if isinstance(var,pyrogue.RemoteVariable):
                if sum(var.bitSize)   <= 32: valType = 'f'
                else: valType = 'd'
            else: valType = 'd'

        elif var.typeStr == 'int':
            valType = 'i'
        elif var.typeStr == 'float':
            valType = 'd'
        elif var.typeStr == 'str':
            valType = 's'

#?	bool
#s	unicode

#v	variant
#U	union
#S	struct

#                if isinstance(node, pyrogue.BaseCommand):
#                    self._srv.addValue(rogue.protocols.epicsV3.Command(eName,node))
#                    self._log.info("Adding command {} mapped to {}".format(node.path,eName))
#                else:
#
#                    # Add standard variable
#                    evar = rogue.protocols.epicsV3.Variable(eName,node,self._syncRead)
#                    node.addListener(evar.varUpdated)
#                    self._srv.addValue(evar)
#                    self._log.info("Adding variable {} mapped to {}".format(node.path,eName))

#   // Enum type
#   if ( isEnum ) {
#      epicsType_ = aitEnumEnum16;
#      log_->info("Detected enum for %s typeStr=%s", epicsName_.c_str(),typeStr.c_str());
#   }

#   // Vector
#   if ( count != 0 ) {
#      log_->info("Create vector GDD for %s epicsType_=%i, size=%i",epicsName_.c_str(),epicsType_,count);
#      pValue_ = new gddAtomic (gddAppType_value, epicsType_, 1u, count);
#      size_   = count;
#      max_    = count;
#      array_  = true;
#   }
#
#   // Scalar
#   else {
#      log_->info("Create scalar GDD for %s epicsType_=%i",epicsName_.c_str(),epicsType_);
#      pValue_ = new gddScalar(gddAppType_value, epicsType_);
#   }

        self._pv = p4p.server.thread.SharedPV(queue=None, 
                                              handler=EpicsPvHandler(self),
                                              initial=p4p.nt.NTScalar(valType).wrap(var.value()),
                                              nt=p4p.nt.NTScalar(valType), 
                                              options={})

        var.addListener(self._varUpdated)

    def _varUpdated(self,path,value):
        pass

    @property
    def var(self):
        return self._var

    @property
    def name(self):
        return self._name

    @property
    def pv(self):
        return self._pv

class EpicsPvServer(object):
    """
    Class to contain an epics PV server
    """
    def __init__(self,*,base,root,pvMap=None, syncRead=True, threadCount=0):
        self._root      = root
        self._base      = base 
        self._log       = pyrogue.logInit(cls=self)
        self._syncRead  = syncRead

        self._provider = p4p.server.StaticProvider(__name__)
        self._list = []

        if not root.running:
            raise Exception("Epics can not be setup on a tree which is not started")

        # Figure out mapping mode
        if pvMap is None:
            doAll = True
            self._pvMap = {}
        else:
            doAll = False
            self._pvMap = pvMap

        # Create PVs
        for v in self._root.variableList:
            eName = None

            if doAll:
                eName = self._base + ':' + v.path.replace('.',':')
                self._pvMap[v.path] = eName
            elif v.path in self._pvMap:
                eName = self._pvMap[v.path]

            if eName is not None:
                print("Adding {}".format(eName))
                self._list.append(EpicsPvHolder(eName,v))

    def stop(self):
        self._server.stop()

    def start(self):
        print("Server starting")
        self._server = p4p.server.Server(providers=[{p.name:p.pv for p in self._list}])
        print("Server started")

    def list(self):
        return self._pvMap

    def dump(self):
        for k,v in self._pvMap.items():
            print("{} -> {}".format(v,k))

                
#        # Start server
#        self._thread = threading.Thread(target=self._run)
#        self._thread.start()
#
#    def createSlave(self, name, maxSize, type):
#        slave = rogue.protocols.epicsV3.Slave(self._base + ':' + name,maxSize,type)
#        self._srv.addValue(slave)
#        return slave
#
#    def createMaster(self, name, maxSize, type):
#        mast = rogue.protocols.epicsV3.Master(self._base + ':' + name,maxSize,type)
#        self._srv.addValue(mast)
#        return mast
#
#
