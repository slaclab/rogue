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
# TODO:
#   Proper enum support
#   Add support for array variables
#   Add stream to epics array interface ?????
#   Add epics array to stream interface ?????
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

def EpicsConvSeverity(varValue):
    if   varValue.status == "AlarmLoLo": return 5 # epicsAlarmLoLo
    elif varValue.status == "AlarmLow":  return 6 # epicsAlarmLow
    elif varValue.status == "AlarmHiHi": return 3 # epicsAlarmHiHi
    elif varValue.status == "AlarmHigh": return 4 # epicsAlarmHigh
    else: return 0

def EpicsConvStatus(varValue):
    if   varValue.severity == "AlarmMinor": return 1 # epicsSevMinor
    elif varValue.severity == "AlarmMajor": return 2 # epicsSevMajor
    else: return 0;

class EpicsPvHandler(p4p.server.thread.Handler):
    def __init__(self, holder):
        self._holder = holder

    def put(self, pv, op):
        if self._holder.var.mode == 'RW' or self._holder.var.mode == 'WO':
            val = op.value().raw.value
            typ = type(val)
            #print(f"PV Put called pv={pv} type={typ}, value={val}")

            if self._holder.var.isinstance(pr.BaseCommand):
                self._holder.var.call(val)
            elif self._holder.valType == 's':
                self._holder.var.setDisp(val)
            else:
                self._holder.var.set(val)

            # Need enum processing

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
        #self._enum = None

        varVal = var.getVariableValue(read=False)

        # Convert valType
        if self._var.disp == 'enum':

            # Detect bool
            if len(self._var.enum) == 2 and False in self._var.enum and True in self._var.enum:
                self._valType = '?'

            # Treat ENUMs as string for now
            else:
                self._valType = 's'


            self._pv = p4p.server.thread.SharedPV(queue=None, 
                                                  handler=EpicsPvHandler(self),
                                                  initial=p4p.nt.NTScalar(self._valType).wrap(varVal.valueDisp),
                                                  nt=p4p.nt.NTScalar(self._valType),
                                                  options={})

        else:

            # Unsigned
            if 'UInt' in self._var.typeStr:
                if isinstance(self._var,pyrogue.RemoteVariable):
                    if   sum(self._var.bitSize) <= 8:  self._valType = 'B'
                    elif sum(self._var.bitSize) <= 16: self._valType = 'H'
                    elif sum(self._var.bitSize) <= 32: self._valType = 'I'
                    else: self._valType = 'L'
                else:
                    self._valType = 'L'

            # Signed
            elif self._var.typeStr == 'int' or 'Int' in self._var.typeStr:
                if isinstance(self._var,pyrogue.RemoteVariable):
                    if   sum(self._var.bitSize) <= 8:  self._valType = 'b'
                    elif sum(self._var.bitSize) <= 16: self._valType = 'h'
                    elif sum(self._var.bitSize) <= 32: self._valType = 'i'
                    else: self._valType = 'l'
                else:
                    self._valType = 'l'

            # Float
            elif self._var.typeStr == 'float' or 'Float' in self._var.typeStr:
                if isinstance(self._var,pyrogue.RemoteVariable):
                    if sum(self._var.bitSize)   <= 32: self._valType = 'f'
                    else: self._valType = 'd'
                else: self._valType = 'd'

            else:
                self._valType = 's'

            if 'List' in self._var.typeStr:
                print("Skipping array variable!!!!!!!!!")
                #count = len(self._var.value())
                #self._pv = p4p.server.thread.SharedPV(queue=None, 
                                                      #handler=EpicsPvHandler(self),
                                                      #initial=p4p.nt.NTScalar(self._valType).wrap(varVal.valueDisp),
                                                      #nt=p4p.nt.NTScalar(self._valType),
                                                      #options={})
            else:

        # https://mdavidsaver.github.io/p4p/_modules/p4p/nt/scalar.html
        # :param bool display: Include optional fields for display meta-data
        # :param bool control: Include optional fields for control meta-data
        # :param bool valueAlarm: Include optional fields for alarm level meta-data


                #ntt=p4p.nt.NTScalar(self._valType,display=True,valueAlarm=True)

                #if self._valType == 's':
                    #ntt.wrap(varVal.valueDisp),
                #else:
                    #ntt.wrap(varVal.value),

                self._pv = p4p.server.thread.SharedPV(queue=None, 
                                                      handler=EpicsPvHandler(self),
                                                      #initial=ntt,
                                                      #nt=ntt,
                                                      nt=p4p.nt.NTScalar(self._valType),
                                                      options={})

        var.addListener(self._varUpdated)
        self._varUpdated(self._var.path,varVal)

    def _varUpdated(self,path,value):
        curr = self._pv.current()

        if self._valType == 's':
            curr.value = value.valueDisp
        else:
            curr.value = value.value

        curr.status    = EpicsConvStatus(value)
        curr.serverity = EpicsConvSeverity(value)

        self._pv.post(curr)

    @property
    def var(self):
        return self._var

    @property
    def name(self):
        return self._name

    @property
    def pv(self):
        return self._pv

    @property
    def valType(self):
        return self._valType


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
