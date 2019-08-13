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
# Issues:
#   Bools don't seem to work
#   Not clear on to force a read on get
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

def EpicsConvStatus(varValue):
    if   varValue.status == "AlarmLoLo": return 5 # epicsAlarmLoLo
    elif varValue.status == "AlarmLow":  return 6 # epicsAlarmLow
    elif varValue.status == "AlarmHiHi": return 3 # epicsAlarmHiHi
    elif varValue.status == "AlarmHigh": return 4 # epicsAlarmHigh
    else: return 0

def EpicsConvSeverity(varValue):
    if   varValue.severity == "AlarmMinor": return 1 # epicsSevMinor
    elif varValue.severity == "AlarmMajor": return 2 # epicsSevMajor
    else: return 0;

class EpicsPvHandler(p4p.server.thread.Handler):
    def __init__(self, holder):
        self._valType = holder.valType
        self._var     = holder.var

    def put(self, pv, op):
        if self._var.isVariable and (self._var.mode == 'RW' or self._var.mode == 'WO'):
            val = op.value().raw.value

            if self._var.isCommand:
                self._var.call(val)
            elif self._valType == 's':
                self._var.setDisp(val)
            else:
                self._var.set(val)

            # Need enum processing
            op.done()

        else: op.done(error='Put Not Supported On This Variable')

    def rpc(self, pv, op):
        if self._var.isCommand:
            val = op.value().query

            if 'arg' in val:
                ret = self._var.call(val.arg)
            else:
                ret = self._var.call()

            if ret is None: ret = 'None'

            v = p4p.Value(p4p.Type([('value',self._valType)]), {'value':ret})
            op.done(value=(v))

        else: op.done(error='Rpc Not Supported On Variables')

    def onFirstConnect(self, pv): # may be omitted
        #print(f"PV First connect called pv={pv}")
        pass

    def onLastDisconnect(self, pv): # may be omitted
        #print(f"PV Last Disconnect called pv={pv}")
        pass

class EpicsPvHolder(object):
    def __init__(self,provider,name,var):
        self._var        = var
        self._name       = name
        self._pv         = None
        #self._enum = None

        # Convert valType
        if False and self._var.disp == 'enum':

            # Detect bool
            if len(self._var.enum) == 2 and False in self._var.enum and True in self._var.enum:
                self._valType = '?'

            # Treat ENUMs as string for now
            else:
                self._valType = 's'

        else:

            if self._var.isCommand:
                typeStr = self._var.retTypeStr
            else:
                typeStr = self._var.typeStr

            # Unsigned
            if typeStr is not None and 'UInt' in typeStr:
                if isinstance(self._var,pyrogue.RemoteVariable):
                    if   sum(self._var.bitSize) <= 8:  self._valType = 'B'
                    elif sum(self._var.bitSize) <= 16: self._valType = 'H'
                    elif sum(self._var.bitSize) <= 32: self._valType = 'I'
                    else: self._valType = 'L'
                else:
                    self._valType = 'L'

            # Signed
            elif typeStr is not None and (typeStr == 'int' or 'Int' in typeStr):
                if isinstance(self._var,pyrogue.RemoteVariable):
                    if   sum(self._var.bitSize) <= 8:  self._valType = 'b'
                    elif sum(self._var.bitSize) <= 16: self._valType = 'h'
                    elif sum(self._var.bitSize) <= 32: self._valType = 'i'
                    else: self._valType = 'l'
                else:
                    self._valType = 'l'

            # Float
            elif typeStr is not None and (typeStr == 'float' or 'Float' in typeStr):
                if isinstance(self._var,pyrogue.RemoteVariable):
                    if sum(self._var.bitSize)   <= 32: self._valType = 'f'
                    else: self._valType = 'd'
                else: self._valType = 'd'

            else:
                self._valType = 's'

        # Get initial value
        varVal = var.getVariableValue(read=False)

        if self._valType == 's':
            nt = p4p.nt.NTScalar(self._valType, display=False, control=False, valueAlarm=False)
            iv = nt.wrap(varVal.valueDisp)
        else:
            nt = p4p.nt.NTScalar(self._valType, display=True, control=True,  valueAlarm=True)
            iv = nt.wrap(varVal.value)

        if typeStr is not None and 'List' in typeStr:
            print("Skipping array variable!!!!!!!!!")
        else:

            self._pv = p4p.server.thread.SharedPV(queue=None, 
                                                  handler=EpicsPvHandler(self),
                                                  initial=iv,
                                                  nt=nt,
                                                  options={})

            provider.add(self._name,self._pv)

            curr = self._pv.current()

            if self._valType == 's':
                curr.raw.value = varVal.valueDisp
            elif self._valType == '?':
                curr.raw.value = varVal.value
            else:
                curr.raw.value = varVal.value
                curr.raw.alarm.status = EpicsConvStatus(varVal)
                curr.raw.alarm.severity = EpicsConvSeverity(varVal)
                curr.raw.display.description = self._var.description

                if self._var.units       is not None: curr.raw.display.units     = self._var.units
                if self._var.maximum     is not None: curr.raw.display.limitHigh = self._var.maximum
                if self._var.minimum     is not None: curr.raw.display.limitLow  = self._var.minimum

                if self._var.lowWarning  is not None: curr.raw.valueAlarm.lowWarningLimit   = self._var.lowWarning
                if self._var.lowAlarm    is not None: curr.raw.valueAlarm.lowAlarmLimit     = self._var.lowAlarm
                if self._var.highWarning is not None: curr.raw.valueAlarm.highWarningLimit  = self._var.highWarning
                if self._var.highAlarm   is not None: curr.raw.valueAlarm.highAlarmLimit    = self._var.highAlarm

                # Precision ?
                # Mode ?

            self._pv.post(curr)
            self._var.addListener(self._varUpdated)

    def _varUpdated(self,path,value):
        curr = self._pv.current()

        if self._valType == 's':
            curr.raw.value = value.valueDisp
        else:
            curr.raw.value          = value.value
            curr.raw.alarm.status   = EpicsConvStatus(value)
            curr.raw.alarm.severity = EpicsConvSeverity(value)

        curr.raw['timeStamp.secondsPastEpoch'], curr.raw['timeStamp.nanoseconds'] = divmod(float(time.time_ns()), 1.0e9)

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
        self._server    = None

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
                pvh = EpicsPvHolder(self._provider,eName,v)
                self._list.append(pvh)

    def stop(self):
        if self._server is not None:
            self._server.stop()

    def start(self):
        self.stop()
        self._server = p4p.server.Server(providers=[self._provider])

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
