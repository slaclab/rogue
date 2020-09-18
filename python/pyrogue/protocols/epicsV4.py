#-----------------------------------------------------------------------------
# Title      : PyRogue epics support
#-----------------------------------------------------------------------------
# Description:
# Module containing epics support classes and routines
# TODO:
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
import warnings
import re

try:
    import p4p.server.thread
    import p4p.nt
except Exception:
    warnings.warn("P4P Is not installed")


def EpicsConvStatus(varValue):
    if varValue.status == "AlarmLoLo":
        return 5 # epicsAlarmLoLo
    elif varValue.status == "AlarmLow":
        return 6 # epicsAlarmLow
    elif varValue.status == "AlarmHiHi":
        return 3 # epicsAlarmHiHi
    elif varValue.status == "AlarmHigh":
        return 4 # epicsAlarmHigh
    else:
        return 0


def EpicsConvSeverity(varValue):
    if varValue.severity == "AlarmMinor":
        return 1 # epicsSevMinor
    elif varValue.severity == "AlarmMajor":
        return 2 # epicsSevMajor
    else:
        return 0


class EpicsPvHandler(p4p.server.thread.Handler):
    def __init__(self, valType, var):
        self._valType = valType
        self._var     = var

    def put(self, pv, op):
        if self._var.isVariable and (self._var.mode == 'RW' or self._var.mode == 'WO'):
            try:
                if self._valType == 'enum':
                    self._var.setDisp(str(op.value()))
                elif self._valType == 's':
                    self._var.setDisp(op.value().raw.value)
                else:
                    self._var.set(op.value().raw.value)

                # Need enum processing
                op.done()

            except Exception as msg:
                op.done(error=msg)

        else:
            op.done(error='Put Not Supported On This Variable')

    def rpc(self, pv, op):
        if self._var.isCommand:
            val = op.value().query

            try:
                if 'arg' in val:
                    ret = self._var(val.arg)
                else:
                    ret = self._var()

                if ret is None:
                    ret = 'None'

                v = p4p.Value(p4p.Type([('value',self._valType)]), {'value':ret})
                op.done(value=(v))

            except Exception as msg:
                op.done(error=msg)

        else:
            op.done(error='Rpc Not Supported On Variables')

    def onFirstConnect(self, pv): # may be omitted
        #print(f"PV First connect called pv={pv}")
        pass

    def onLastDisconnect(self, pv): # may be omitted
        #print(f"PV Last Disconnect called pv={pv}")
        pass


class EpicsPvHolder(object):
    def __init__(self,provider,name,var,log):
        self._var  = var
        self._name = name
        self._log  = log
        self._pv   = None

        if self._var.isCommand:
            typeStr = self._var.retTypeStr
        else:
            typeStr = self._var.typeStr

        # Convert valType
        if self._var.disp == 'enum':
            self._valType = 'enum'
        elif typeStr is None:
            self._valType = 's'
        else:

            # Unsigned
            if 'UInt' in typeStr:
                m = re.search('^UInt(\\d+)\\.*',typeStr)

                if m is not None and m.lastindex == 1:
                    bits = int(m[1])

                    if bits <= 8:
                        self._valType = 'B'
                    elif bits <= 16:
                        self._valType = 'H'
                    elif bits <= 32:
                        self._valType = 'I'
                    elif bits <= 64:
                        self._valType = 'L'
                    else:
                        self._valType = 's'
                else:
                    self._valType = 'L'

            # Signed
            elif 'int' in typeStr or 'Int' in typeStr:
                m = re.search('^Int(\\d+)\\.*',typeStr)

                if m is not None and m.lastindex == 1:
                    bits = int(m[1])

                    if bits <= 8:
                        self._valType = 'b'
                    elif bits <= 16:
                        self._valType = 'h'
                    elif bits <= 32:
                        self._valType = 'i'
                    elif bits <= 64:
                        self._valType = 'l'
                    else:
                        self._valType = 's'
                else:
                    self._valType = 'l'

            # Float
            elif 'float' in typeStr or 'Float32' in typeStr:
                self._valType = 'f'

            # Double
            elif 'Double64' in typeStr or 'Float64' in typeStr:
                self._valType = 'd'

            # Default to string
            else:
                self._valType = 's'

        # Get initial value
        varVal = var.getVariableValue(read=False)

        # Detect array
        if self._var.isList:
            self._valType = 'a' + self._valType

        self._log.info("Adding {} with type {} init={}".format(self._name,self._valType,varVal.valueDisp))
        try:
            if self._valType == 'enum':
                nt = p4p.nt.NTEnum(display=False, control=False, valueAlarm=False)
                enum = list(self._var.enum.values())
                iv = {'choices':enum, 'index':enum.index(varVal.valueDisp)}
            elif self._valType == 's':
                nt = p4p.nt.NTScalar(self._valType, display=False, control=False, valueAlarm=False)
                iv = nt.wrap(varVal.valueDisp)
            else:
                nt = p4p.nt.NTScalar(self._valType, display=True, control=True,  valueAlarm=True)
                #print(f"Setting value {varVal.value} to {self._name}")
                iv = nt.wrap(varVal.value)
        except Exception as e:
            raise Exception("Failed to add {} with type {} init={}. Error={}".format(self._name,self._valType,varVal.valueDisp,e))

        # Setup variable
        self._pv = p4p.server.thread.SharedPV(queue=None,
                                              handler=EpicsPvHandler(self._valType,self._var),
                                              initial=iv,
                                              nt=nt,
                                              options={})

        provider.add(self._name,self._pv)
        self._var.addListener(self._varUpdated)

        # Update fields in numeric types
        if self._valType != 'enum' and self._valType != 's':
            curr = self._pv.current()
            curr.raw.value = varVal.value
            curr.raw.alarm.status = EpicsConvStatus(varVal)
            curr.raw.alarm.severity = EpicsConvSeverity(varVal)
            curr.raw.display.description = self._var.description

            if self._var.units       is not None:
                curr.raw.display.units     = self._var.units
            if self._var.maximum     is not None:
                curr.raw.display.limitHigh = self._var.maximum
            if self._var.minimum     is not None:
                curr.raw.display.limitLow  = self._var.minimum

            if self._var.lowWarning  is not None:
                curr.raw.valueAlarm.lowWarningLimit   = self._var.lowWarning
            if self._var.lowAlarm    is not None:
                curr.raw.valueAlarm.lowAlarmLimit     = self._var.lowAlarm
            if self._var.highWarning is not None:
                curr.raw.valueAlarm.highWarningLimit  = self._var.highWarning
            if self._var.highAlarm   is not None:
                curr.raw.valueAlarm.highAlarmLimit    = self._var.highAlarm

            # Precision ?
            self._pv.post(curr)

    def _varUpdated(self,path,value):
        if self._valType == 'enum' or self._valType == 's':
            self._pv.post(value.valueDisp)
        else:
            curr = self._pv.current()
            curr.raw.value          = value.value
            curr.raw.alarm.status   = EpicsConvStatus(value)
            curr.raw.alarm.severity = EpicsConvSeverity(value)
            curr.raw['timeStamp.secondsPastEpoch'], curr.raw['timeStamp.nanoseconds'] = divmod(float(time.time_ns()), 1.0e9)
            self._pv.post(curr)


class EpicsPvServer(object):
    """
    Class to contain an epics PV server
    """
    def __init__(self,*,base,root,incGroups,excGroups,pvMap=None):
        self._root      = root
        self._base      = base
        self._log       = pyrogue.logInit(cls=self)
        self._server    = None
        self._incGroups = incGroups
        self._excGroups = excGroups
        self._pvMap     = pvMap
        self._started   = False

        self._provider = p4p.server.StaticProvider(__name__)

    def start(self):
        # Add deprecration warning in the future
        self._start()

    def stop(self):
        # Add deprecration warning in the future
        self._stop()

    def _stop(self):
        if self._server is not None:
            self._server.stop()

    def _start(self):

        if self._started:
            return

        self._started = True

        self._stop()
        self._list = []

        if not self._root.running:
            raise Exception("Epics can not be setup on a tree which is not started")

        # Figure out mapping mode
        if self._pvMap is None:
            doAll = True
            self._pvMap = {}
        else:
            doAll = False

        # Create PVs
        for v in self._root.variableList:
            eName = None

            if doAll:
                if v.filterByGroup(self._incGroups,self._excGroups):
                    eName = self._base + ':' + v.path.replace('.',':')
                    self._pvMap[v.path] = eName
            elif v.path in self._pvMap:
                eName = self._pvMap[v.path]

            if eName is not None:
                pvh = EpicsPvHolder(self._provider,eName,v,self._log)
                self._list.append(pvh)

        self._server = p4p.server.Server(providers=[self._provider])

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
