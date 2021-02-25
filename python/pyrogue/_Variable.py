#-----------------------------------------------------------------------------
# Title      : PyRogue base module - Variable Class
#-----------------------------------------------------------------------------
# This file is part of the rogue software platform. It is subject to
# the license terms in the LICENSE.txt file found in the top-level directory
# of this distribution and at:
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
# No part of the rogue software platform, including this file, may be
# copied, modified, propagated, or distributed except according to the terms
# contained in the LICENSE.txt file.
#-----------------------------------------------------------------------------
import pyrogue as pr
import rogue.interfaces.memory as rim
import threading
import re
import time
import shlex
import numpy as np
from collections import OrderedDict as odict
from collections.abc import Iterable


class VariableError(Exception):
    """ Exception for variable access errors."""
    pass


def VariableWait(varList, testFunction, timeout=0):
    """
    Wait for a number of variable conditions to be true.
    Pass a variable or list of variables, and a test function.
    The test function is passed a dictionary containing the current
    variableValue state index by variable path
    i.e. w = VariableWait([root.device.var1,root.device.var2],
                          lambda varValues: varValues['root.device.var1'].value >= 10 and \
                                            varValues['root.device.var1'].value >= 20)
    """

    # Container class
    class varStates(object):

        def __init__(self):
            self.vlist  = odict()
            self.cv     = threading.Condition()

        # Method to handle variable updates callback
        def varUpdate(self,path,varValue):
            with self.cv:
                if path in self.vlist:
                    self.vlist[path] = varValue
                    self.cv.notify()

    # Convert single variable to a list
    if not isinstance(varList,list):
        varList = [varList]

    # Setup tracking
    states = varStates()

    # Add variable to list and register handler
    with states.cv:
        for v in varList:
            v.addListener(states.varUpdate)
            states.vlist[v.path] = v.getVariableValue(read=False)

    # Go into wait loop
    ret    = False
    start  = time.time()

    with states.cv:

        # Check current state
        ret = testFunction(list(states.vlist.values()))

        # Run until timeout or all conditions have been met
        while (not ret) and ((timeout == 0) or ((time.time()-start) < timeout)):
            states.cv.wait(0.5)
            ret = testFunction(list(states.vlist.values()))

        # Cleanup
        for v in varList:
            v.delListener(states.varUpdate)

    return ret


class VariableValue(object):
    def __init__(self, var, read=False):
        self.value     = var.get(read=read)
        self.valueDisp = var.genDisp(self.value)
        self.disp      = var.disp
        self.enum      = var.enum

        self.status, self.severity = var._alarmState(self.value)


class VariableListData(object):
    def __init__(self, numValues, valueBits, valueStride):
        self.numValues   = numValues
        self.valueBits   = valueBits
        self.valueStride = valueStride


class BaseVariable(pr.Node):

    def __init__(self, *,
                 name,
                 description='',
                 mode='RW',
                 value=None,
                 disp='{}',
                 enum=None,
                 units=None,
                 hidden=False,
                 groups=None,
                 minimum=None,
                 maximum=None,
                 lowWarning=None,
                 lowAlarm=None,
                 highWarning=None,
                 highAlarm=None,
                 pollInterval=0,
                 updateNotify=True,
                 typeStr='Unknown',
                 bulkOpEn=True,
                 offset=0,
                 guiGroup=None):

        # Public Attributes
        self._bulkOpEn      = bulkOpEn
        self._updateNotify  = updateNotify
        self._mode          = mode
        self._units         = units
        self._minimum       = minimum
        self._maximum       = maximum
        self._lowWarning    = lowWarning
        self._lowAlarm      = lowAlarm
        self._highWarning   = highWarning
        self._highAlarm     = highAlarm
        self._default       = value
        self._block         = None
        self._pollInterval  = pollInterval
        self._nativeType    = None
        self._isList        = False
        self._listeners     = []
        self.__functions    = []
        self.__dependencies = []

        # Build enum if specified
        self._disp = disp
        self._enum = enum
        if isinstance(disp, dict):
            self._disp = 'enum'
            self._enum = disp
        elif isinstance(disp, list):
            self._disp = 'enum'
            self._enum = {k:str(k) for k in disp}
        elif type(value) == bool and enum is None:
            self._disp = 'enum'
            self._enum = {False: 'False', True: 'True'}

        if enum is not None:
            self._disp = 'enum'

        if value is not None and (isinstance(value, list) or isinstance(value, np.ndarray)):
            self._isList = True

        # Determine typeStr from value type
        if typeStr == 'Unknown' and value is not None:
            if isinstance(value, list):
                self._typeStr = f'{value[0].__class__.__name__}[]'
            elif isinstance(value, np.ndarray):
                self._typeStr = str(value.dtype).capitalize() + '[np]'
            else:
                self._typeStr = value.__class__.__name__
        else:
            self._typeStr = typeStr

        # Create inverted enum
        self._revEnum = None
        if self._enum is not None:
            self._revEnum = {v:k for k,v in self._enum.items()}

        # Check modes
        if (self._mode != 'RW') and (self._mode != 'RO') and \
           (self._mode != 'WO'):
            raise VariableError(f'Invalid variable mode {self._mode}. Supported: RW, RO, WO')

        # Call super constructor
        pr.Node.__init__(self, name=name, description=description, hidden=hidden, groups=groups, guiGroup=guiGroup)

    @pr.expose
    @property
    def enum(self):
        return self._enum

    @pr.expose
    @property
    def revEnum(self):
        return self._revEnum

    @pr.expose
    @property
    def typeStr(self):
        return self._typeStr

    @pr.expose
    @property
    def disp(self):
        return self._disp

    @pr.expose
    @property
    def precision(self):
        if 'ndarray' in self.typeStr or 'Float' in self.typeStr or self.typeStr == 'float':
            res = re.search(r':([0-9])\.([0-9]*)f',self._disp)
            try:
                return int(res[2])
            except Exception:
                return 3
        else:
            return 0

    @pr.expose
    @property
    def mode(self):
        return self._mode

    @pr.expose
    @property
    def isList(self):
        return self._isList

    @pr.expose
    @property
    def units(self):
        return self._units

    @pr.expose
    @property
    def minimum(self):
        return self._minimum

    @pr.expose
    @property
    def maximum(self):
        return self._maximum

    @pr.expose
    @property
    def hasAlarm(self):
        return (self._lowWarning is not None or self._lowAlarm is not None or self._highWarning is not None or self._highAlarm is not None)

    @pr.expose
    @property
    def lowWarning(self):
        return self._lowWarning

    @pr.expose
    @property
    def lowAlarm(self):
        return self._lowAlarm

    @pr.expose
    @property
    def highWarning(self):
        return self._highWarning

    @pr.expose
    @property
    def highAlarm(self):
        return self._highAlarm

    @pr.expose
    @property
    def alarmStatus(self):
        stat,sevr = self._alarmState(self.value())
        return stat

    @pr.expose
    @property
    def alarmSeverity(self):
        stat,sevr = self._alarmState(self.value())
        return sevr

    def addDependency(self, dep):
        if dep not in self.__dependencies:
            self.__dependencies.append(dep)
            dep.addListener(self)

    @pr.expose
    @property
    def pollInterval(self):
        return self._pollInterval

    @pollInterval.setter
    def pollInterval(self, interval):
        self._pollInterval = interval
        self._updatePollInterval()

    @pr.expose
    @property
    def lock(self):
        if self._block is not None:
            return self._block._lock
        else:
            return None

    @pr.expose
    @property
    def updateNotify(self):
        return self._updateNotify

    @property
    def dependencies(self):
        return self.__dependencies

    def addListener(self, listener):
        """
        Add a listener Variable or function to call when variable changes.
        This is useful when chaining variables together. (ADC conversions, etc)
        The variable and value class are passed as an arg: func(path,varValue)
        """
        if isinstance(listener, BaseVariable):
            if listener not in self._listeners:
                self._listeners.append(listener)
        else:
            if listener not in self.__functions:
                self.__functions.append(listener)

    def delListener(self, listener):
        """
        Remove a listener Variable or function
        """
        if listener in self.__functions:
            self.__functions.remove(listener)

    @pr.expose
    def set(self, value, write=True, index=-1):
        """
        Set the value and write to hardware if applicable
        Writes to hardware are blocking. An error will result in a logged exception.
        """
        pass

    @pr.expose
    def post(self,value, index=-1):
        """
        Set the value and write to hardware if applicable using a posted write.
        This method does not call through parent.writeBlocks(), but rather
        calls on self._block directly.
        """
        pass

    @pr.expose
    def get(self,read=True, index=-1):
        """
        Return the value after performing a read from hardware if applicable.
        Hardware read is blocking. An error will result in a logged exception.
        Listeners will be informed of the update.
        """
        return None

    @pr.expose
    def write(self):
        """
        Force a write of the variable.
        """
        pass

    @pr.expose
    def getVariableValue(self,read=True):
        """
        Return the value after performing a read from hardware if applicable.
        Hardware read is blocking. An error will result in a logged exception.
        Listeners will be informed of the update.
        """
        return VariableValue(self,read=read)

    @pr.expose
    def value(self):
        return self.get(read=False, index=-1)

    @pr.expose
    def genDisp(self, value):
        try:
            if self.typeStr == 'ndarray':
                return str(value)
            elif self._isList:
                return "[" + ", ".join([pr.quoteComma(self._genDispValue(v)) for v in value]) + "]"
            else:
                return self._genDispValue(value)

        except Exception as e:
            pr.logException(self._log,e)
            self._log.error(f"Error generating disp for value {value} in variable {self.path}")
            raise e

    @pr.expose
    def getDisp(self, read=True, index=-1):
        return(self.genDisp(self.get(read=read,index=index)))

    @pr.expose
    def valueDisp(self, read=True, index=-1):
        return self.getDisp(read=False,index=index)

    @pr.expose
    def parseDisp(self, sValue):
        try:
            if self._isList and isinstance(sValue,str) and '[' in sValue and ']' in sValue:
                s = shlex.shlex(" " + sValue.lstrip('[').rstrip(']') + " ",posix=True)
                s.whitespace_split=True
                s.whitespace=','
                return [self._parseDispValue(v.strip()) for v in s]
            elif sValue is None or isinstance(sValue, self.nativeType()) or isinstance(sValue,list):
                return sValue
            else:
                return self._parseDispValue(sValue)

        except Exception:
            msg = "Invalid value {} for variable {} with type {}".format(sValue,self.name,self.nativeType())
            self._log.error(msg)
            raise VariableError(msg)

    @pr.expose
    def setDisp(self, sValue, write=True, index=-1):
        self.set(self.parseDisp(sValue), write=write, index=index)

    @pr.expose
    def nativeType(self):
        if self._nativeType is None:
            v = self.value()
            if isinstance(v,list):
                self._nativeType = type(v[0])
            else:
                self._nativeType = type(v)
        return self._nativeType

    def _genDispValue(self,value):
        #print('{}.genDisp(read={}) disp={} value={}'.format(self.path, read, self.disp, value))
        if self.disp == 'enum':
            if value in self.enum:
                return self.enum[value]
            else:
                self._log.warning("Invalid enum value {} in variable '{}'".format(value,self.path))
                return f'INVALID: {value}'

        elif (value == '' or value is None):
            return value
        else:
            return self.disp.format(value)

    def _parseDispValue(self, sValue):
        if sValue == '':
            return ''
        elif self.disp == 'enum':
            return self.revEnum[sValue]
        else:
            t = self.nativeType()
            if t == int:
                return int(sValue, 0)
            elif t == float:
                return float(sValue)
            elif t == bool:
                return str.lower(sValue) == "true"
            elif t == dict:
                return eval(sValue)
            else:
                return sValue

    def _setDefault(self):
        if self._default is not None:
            self.setDisp(self._default, write=False)

    def _updatePollInterval(self):
        if self.root is not None and self.root._pollQueue is not None:
            self.root._pollQueue.updatePollInterval(self)

    def _finishInit(self):
        # Set the default value but dont write
        self._setDefault()
        self._updatePollInterval()

    def _setDict(self,d,writeEach,modes,incGroups,excGroups,keys):

        # If keys is not none, it should only contain one entry
        # and the variable should be a list variable
        if keys is not None:

            if len(keys) != 1 or not self._isList:
                self._log.error(f"Entry {self.name} with key {keys} not found")

            elif self._mode in modes:
                if keys[0] == '*' or keys[0] == ':':
                    for i in range(self._numValues()):
                        self.setDisp(d, write=writeEach, index=i)
                else:
                    idxSlice = eval(f'[i for i in range(self._numValues())][{keys[0]}]')

                    # Single entry item
                    if ':' not in keys[0]:
                        self.setDisp(d, write=writeEach, index=idxSlice[0])

                    # Multi entry item
                    else:
                        if isinstance(d,str):
                            s = shlex.shlex(" " + d.lstrip('[').rstrip(']') + " ",posix=True)
                            s.whitespace_split=True
                            s.whitespace=','
                        else:
                            s = d

                        for val,i in zip(s,idxSlice):
                            self.setDisp(val.strip(), write=writeEach, index=i)

        # Standard set
        elif self._mode in modes:
            self.setDisp(d,writeEach)

    def _getDict(self,modes,incGroups,excGroups):
        if self._mode in modes:
            return VariableValue(self)
        else:
            return None

    def _queueUpdate(self):
        self._root._queueUpdates(self)

        for var in self._listeners:
            var._queueUpdate()

    def _doUpdate(self):
        val = VariableValue(self)

        for func in self.__functions:
            func(self.path,val)

        return val

    def _alarmState(self,value):
        """ Return status, severity """

        if isinstance(value,list) or isinstance(value,dict):
            return 'None','None'

        if (self.hasAlarm is False):
            return "None", "None"

        elif (self._lowAlarm  is not None and value < self._lowAlarm):
            return 'AlarmLoLo', 'AlarmMajor'

        elif (self._highAlarm  is not None and value > self._highAlarm):
            return 'AlarmHiHi', 'AlarmMajor'

        elif (self._lowWarning  is not None and value < self._lowWarning):
            return 'AlarmLow', 'AlarmMinor'

        elif (self._highWarning is not None and value > self._highWarning):
            return 'AlarmHigh', 'AlarmMinor'

        else:
            return 'Good','Good'


class RemoteVariable(BaseVariable,rim.Variable):

    def __init__(self, *,
                 name,
                 description='',
                 mode='RW',
                 value=None,
                 disp=None,
                 enum=None,
                 units=None,
                 hidden=False,
                 groups=None,
                 minimum=None,
                 maximum=None,
                 lowWarning=None,
                 lowAlarm=None,
                 highWarning=None,
                 highAlarm=None,
                 base=pr.UInt,
                 offset=None,
                 numValues=0,
                 valueBits=0,
                 valueStride=0,
                 bitSize=32,
                 bitOffset=0,
                 pollInterval=0,
                 updateNotify=True,
                 overlapEn=False,
                 bulkOpEn=True,
                 verify=True,
                 retryCount=0,
                 guiGroup=None):

        if disp is None:
            disp = base.defaultdisp

        self._block = None

        # Convert the address parameters into lists
        addrParams = [offset, bitOffset, bitSize] # Make a copy
        addrParams = [list(x) if isinstance(x, Iterable) else [x] for x in addrParams] # convert to lists
        length = max((len(x) for x in addrParams))
        addrParams = [x*length if len(x)==1 else x for x in addrParams] # Make single element lists as long as max
        offset, bitOffset, bitSize = addrParams # Assign back

        # Verify the the list lengths match
        if len(offset) != len(bitOffset) != len(bitSize):
            raise VariableError('Lengths of offset: {}, bitOffset: {}, bitSize {} must match'.format(offset, bitOffset, bitSize))

        # Check for invalid values
        if 0 in bitSize:
            raise VariableError('BitSize of 0 is invalid')

        # Normalize bitOffsets relative to the smallest offset
        baseAddr = min(offset)
        bitOffset = [x+((y-baseAddr)*8) for x,y in zip(bitOffset, offset)]
        offset = baseAddr

        if isinstance(base, pr.Model):
            self._base = base
        elif numValues != 0:
            self._base = base(valueBits)
        else:
            self._base = base(sum(bitSize))

        # Apply default min and max
        if minimum is None or (self._base.minValue() is not None and minimum < self._base.minValue()):
            minimum = self._base.minValue()

        if maximum is None or (self._base.maxValue() is not None and maximum > self._base.maxValue()):
            maximum = self._base.maxValue()

        BaseVariable.__init__(self, name=name, description=description,
                              mode=mode, value=value, disp=disp,
                              enum=enum, units=units, hidden=hidden, groups=groups,
                              minimum=minimum, maximum=maximum, bulkOpEn=bulkOpEn,
                              lowWarning=lowWarning, lowAlarm=lowAlarm,
                              highWarning=highWarning, highAlarm=highAlarm,
                              pollInterval=pollInterval,updateNotify=updateNotify,
                              guiGroup=guiGroup)

        self._typeStr = self._base.name

        # If numValues > 0 the bit size array must only have one entry and the total number of bits must be a multiple of the number of values
        if numValues != 0:
            self._typeStr = f'{self._base.name}[{numValues}]'
            self._isList = True

            if len(bitSize) != 1:
                raise VariableError('BitSize array must have a length of one when numValues > 0')

            if valueBits > valueStride:
                raise VariableError('ValueBits {valueBits} is greater than valueStrude {valueStride}')

            if (numValues * valueStride) != sum(bitSize):
                raise VariableError('Total bitSize {sum(bitSize)} is not equal to multile of numValues {numValues} and valueStride {valueStride}')

        else:
            self._typeStr = self._base.name

        listData = VariableListData(numValues,valueBits,valueStride)

        # Setup C++ Base class
        rim.Variable.__init__(self,self._name,self._mode,self._minimum,self._maximum,
                              offset, bitOffset, bitSize, overlapEn, verify,
                              self._bulkOpEn, self._updateNotify, self._base, listData, retryCount)

    @pr.expose
    @property
    def varBytes(self):
        return self._varBytes()

    @pr.expose
    @property
    def offset(self):
        return self._offset()

    @pr.expose
    @property
    def address(self):
        return self._block.address

    @pr.expose
    @property
    def bitSize(self):
        return self._bitSize()

    @pr.expose
    @property
    def bitOffset(self):
        return self._bitOffset()

    @pr.expose
    @property
    def verify(self):
        return self._verifyEn()

    @pr.expose
    @property
    def base(self):
        return self._base

    @pr.expose
    @property
    def overlapEn(self):
        return self._overlapEn()

    @pr.expose
    @property
    def bulkEn(self):
        return self._bulkOpEn

    @pr.expose
    def set(self, value, write=True, index=-1):
        """
        Set the value and write to hardware if applicable
        Writes to hardware are blocking. An error will result in a logged exception.
        """
        try:

            # Set value to block
            self._set(value,index)

            if write:
                self._parent.writeBlocks(force=True, recurse=False, variable=self, index=index)
                self._parent.verifyBlocks(recurse=False, variable=self)
                self._parent.checkBlocks(recurse=False, variable=self)

        except Exception as e:
            pr.logException(self._log,e)
            self._log.error("Error setting value '{}' to variable '{}' with type {}. Exception={}".format(value,self.path,self.typeStr,e))
            raise e

    @pr.expose
    def post(self,value, index=-1):
        """
        Set the value and write to hardware if applicable using a posted write.
        This method does not call through parent.writeBlocks(), but rather
        calls on self._block directly.
        """
        try:

            # Set value to block
            self._set(value,index)

            pr.startTransaction(self._block, type=rim.Post, forceWr=False, checkEach=True, variable=self, index=index)

        except Exception as e:
            pr.logException(self._log,e)
            self._log.error("Error posting value '{}' to variable '{}' with type {}".format(value,self.path,self.typeStr))
            raise e

    @pr.expose
    def get(self,read=True, index=-1):
        """
        Return the value after performing a read from hardware if applicable.
        Hardware read is blocking. An error will result in a logged exception.
        Listeners will be informed of the update.
        """
        try:
            if read:
                self._parent.readBlocks(recurse=False, variable=self, index=index)
                self._parent.checkBlocks(recurse=False, variable=self)

            return self._get(index)

        except Exception as e:
            pr.logException(self._log,e)
            self._log.error("Error reading value from variable '{}'".format(self.path))
            raise e

    @pr.expose
    def write(self):
        """
        Force a write of the variable.
        """
        try:
            self._parent.writeBlocks(force=True, recurse=False, variable=self)
            self._parent.verifyBlocks(recurse=False, variable=self)
            self._parent.checkBlocks(recurse=False, variable=self)

        except Exception as e:
            pr.logException(self._log,e)
            raise e

    def _parseDispValue(self, sValue):
        if self.disp == 'enum':
            return self.revEnum[sValue]
        else:
            return self._base.fromString(sValue)


class LocalVariable(BaseVariable):

    def __init__(self, *,
                 name,
                 description='',
                 mode='RW',
                 value=None,
                 disp='{}',
                 enum=None,
                 units=None,
                 hidden=False,
                 groups=None,
                 minimum=None,
                 maximum=None,
                 lowWarning=None,
                 lowAlarm=None,
                 highWarning=None,
                 highAlarm=None,
                 localSet=None,
                 localGet=None,
                 typeStr='Unknown',
                 pollInterval=0,
                 updateNotify=True,
                 bulkOpEn=True,
                 guiGroup=None):

        if value is None and localGet is None:
            raise VariableError(f'LocalVariable {self.path} without localGet() must specify value= argument in constructor')

        BaseVariable.__init__(self, name=name, description=description,
                              mode=mode, value=value, disp=disp,
                              enum=enum, units=units, hidden=hidden, groups=groups,
                              minimum=minimum, maximum=maximum, typeStr=typeStr,
                              lowWarning=lowWarning, lowAlarm=lowAlarm,
                              highWarning=highWarning, highAlarm=highAlarm,
                              pollInterval=pollInterval,updateNotify=updateNotify, bulkOpEn=bulkOpEn,
                              guiGroup=guiGroup)

        self._block = pr.LocalBlock(variable=self,localSet=localSet,localGet=localGet,value=self._default)

    @pr.expose
    def set(self, value, write=True, index=-1):
        """
        Set the value and write to hardware if applicable
        Writes to hardware are blocking. An error will result in a logged exception.
        """
        self._log.debug("{}.set({})".format(self, value))

        try:

            # Set value to block
            self._block.set(self, value, index)

            if write:
                self._parent.writeBlocks(force=True, recurse=False, variable=self, index=index)
                self._parent.verifyBlocks(recurse=False, variable=self)
                self._parent.checkBlocks(recurse=False, variable=self)

        except Exception as e:
            pr.logException(self._log,e)
            self._log.error("Error setting value '{}' to variable '{}' with type {}. Exception={}".format(value,self.path,self.typeStr,e))
            raise e

    @pr.expose
    def post(self,value,index=-1):
        """
        Set the value and write to hardware if applicable using a posted write.
        This method does not call through parent.writeBlocks(), but rather
        calls on self._block directly.
        """
        self._log.debug("{}.post({})".format(self, value))

        try:
            self._block.set(self, value, index)

            pr.startTransaction(self._block, type=rim.Post, forceWr=False, checkEach=True, variable=self, index=index)

        except Exception as e:
            pr.logException(self._log,e)
            self._log.error("Error posting value '{}' to variable '{}' with type {}".format(value,self.path,self.typeStr))
            raise e

    @pr.expose
    def get(self,read=True, index=-1):
        """
        Return the value after performing a read from hardware if applicable.
        Hardware read is blocking. An error will result in a logged exception.
        Listeners will be informed of the update.
        """
        try:
            if read:
                self._parent.readBlocks(recurse=False, variable=self, index=index)
                self._parent.checkBlocks(recurse=False, variable=self)

            return self._block.get(self,index)

        except Exception as e:
            pr.logException(self._log,e)
            self._log.error("Error reading value from variable '{}'".format(self.path))
            raise e

    def __get__(self):
        return self.get(read=False)

    def __iadd__(self, other):
        self._block._iadd(other)
        return self

    def __isub__(self, other):
        self._block._isub(other)
        return self

    def __imul__(self, other):
        self._block._imul(other)
        return self

    def __imatmul__(self, other):
        self._block._imatmul(other)
        return self

    def __itruediv__(self, other):
        self._block._itruediv(other)
        return self

    def __ifloordiv__(self, other):
        self._block._ifloordiv(other)
        return self

    def __imod__(self, other):
        self._block._imod(other)
        return self

    def __ipow__(self, other):
        self._block._ipow(other)
        return self

    def __ilshift__(self, other):
        self._block._ilshift(other)
        return self

    def __irshift__(self, other):
        self._block._irshift(other)
        return self

    def __iand__(self, other):
        self._block._iand(other)
        return self

    def __ixor__(self, other):
        self._block._ixor(other)
        return self

    def __ior__(self, other):
        self._block._ior(other)
        return self


class LinkVariable(BaseVariable):

    def __init__(self, *,
                 name,
                 variable=None,
                 dependencies=None,
                 typeStr='Linked',
                 linkedSet=None,
                 linkedGet=None,
                 **kwargs): # Args passed to BaseVariable

        # Set and get functions
        self._linkedGet = linkedGet
        self._linkedSet = linkedSet

        if variable is not None:
            # If directly linked to a variable, use it's value and set by defualt
            # for linkedGet and linkedSet unless overridden
            self._linkedGet = linkedGet if linkedGet else variable.value
            self._linkedSet = linkedSet if linkedSet else variable.set

            # Search the kwargs for overridden properties, otherwise the properties from the linked variable will be used
            args = ['disp', 'enum', 'units', 'minimum', 'maximum']
            for arg in args:
                if arg not in kwargs:
                    kwargs[arg] = getattr(variable, arg)

        if not self._linkedSet:
            kwargs['mode'] = 'RO'
        if not self._linkedGet:
            kwargs['mode'] = 'WO'

        # Need to have at least 1 of linkedSet or linkedGet, otherwise error

        # Call super constructor
        BaseVariable.__init__(self, name=name, typeStr=typeStr, **kwargs)

        # Dependency tracking
        if variable is not None:
            # Add the directly linked variable as a dependency
            self.addDependency(variable)

        if dependencies is not None:
            for d in dependencies:
                self.addDependency(d)

    def __getitem__(self, key):
        # Allow dependencies to be accessed as indices of self
        return self.dependencies[key]

    @pr.expose
    def set(self, value, write=True, index=-1):
        if self._linkedSet is not None:

            # Possible args
            pargs = {'dev' : self.parent, 'var' : self, 'value' : value, 'write' : write, 'index' : index}

            pr.functionHelper(self._linkedSet,pargs,self._log,self.path)

    @pr.expose
    def get(self, read=True, index=-1):
        if self._linkedGet is not None:

            # Possible args
            pargs = {'dev' : self.parent, 'var' : self, 'read' : read, 'index' : index}

            return pr.functionHelper(self._linkedGet,pargs,self._log,self.path)
        else:
            return None
