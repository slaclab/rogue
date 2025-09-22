#-----------------------------------------------------------------------------
# Company    : SLAC National Accelerator Laboratory
#-----------------------------------------------------------------------------
#  Description:
#       PyRogue base module - Variable Class
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
import ast
import sys
from collections import OrderedDict as odict
from collections.abc import Iterable


class VariableError(Exception):
    """ """
    pass


def VariableWait(varList, testFunction, timeout=0):
    """
    Wait for a number of variable conditions to be true.
    Pass a variable or list of variables, and a test function.
    The test function is passed a list containing the current
    variableValue state indexed by position as passed in the wait list.
    Each variableValue entry has an additional field updated which indicates
    if the variable has refreshed while waiting. This can be used to trigger
    on any update to the variable, regardless of value.

    i.e. w = VariableWait([root.device.var1,root.device.var2],
                          lambda varValues: varValues[0].value >= 10 and \
                                            varValues[1].value >= 20)

    i.e. w = VariableWait([root.device.var1,root.device.var2],
                          lambda varValues: varValues[0].updated and \
                                            varValues[1].updated)

    Args:
        varList :
        testFunction :
        timeout (int) : (Default value = 0)

    Returns
    -------

    """

    # Container class
    class varStates(object):
        def __init__(self):
            self.vlist  = odict()
            self.cv     = threading.Condition()

        # Method to handle variable updates callback
        def varUpdate(self,path,varValue):
            """

            Args:
                path :
                varValue :

            Returns
            -------
            ret

            """
            with self.cv:
                if path in self.vlist:
                    self.vlist[path] = varValue
                    self.vlist[path].updated = True
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
            states.vlist[v.path].updated = False

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
    """ """
    def __init__(self, var, read=False, index=-1):
        self.value     = var.get(read=read,index=index)
        self.valueDisp = var.genDisp(self.value)
        self.disp      = var.disp
        self.enum      = var.enum

        self.status, self.severity = var._alarmState(self.value)

    def __repr__(self):
        return f'{str(self.__class__)}({self.__dict__})'


class VariableListData(object):
    """ """
    def __init__(self, numValues, valueBits, valueStride):
        self.numValues   = numValues
        self.valueBits   = valueBits
        self.valueStride = valueStride

    def __repr__(self):
        return f'{self.__class__}({self.__dict__})'



class BaseVariable(pr.Node):
    """The parent BaseVariable class to be used for all child variables.

    Initializes the BaseVariable class with the provided arguments.

    Args:
        name (str): The name of the variable.
        description (str): A brief description of the variable.
        mode (str): The operational mode. Options are RW, RO, and WO.
        value (str): The optional default value of the variable, or None.

        disp (str): A display string indicating how the variable value should be displayed and parsed.
        enum (dict): A dictionary of key value pairs for variables which have a set of selections.
        units (str): Optional string field indicting the unit type for this variable for display.

        hidden (bool): Whether the variable is visible to external classes.
        groups (str): Groups.

        minimum (int): Optional minimum value for a variable with a set range.
        maximum (int): Optional maximum value for a variable with a set range.

        lowWarning (int): The lower threshold to trigger a warning.
        lowAlarm (int): The alarm to trigger when the lower threshold is reached.
        highWarning (int): The higher threshold to trigger a warning.
        highAlarm (int): The alarm to trigger when the higher threshold is reached.

        pollInterval (int): The period at which this variable should be polled. A 0 value disables polling.
        updateNotify (bool): Whether the listeners should be notified on update.
        typeStr (str): A string definition of the variable data type.
        bulkOpEn (bool): Whether this is a bulk operation.
        offset (float): The offset.
        guiGroup (str): The GUI group.

    Attributes:
        _thread (object): thread.

        _bulkOpEn (bool): Set in init funtion.
        _updateNotify (bool): Set in init function. Whether the listeners should be notified on update.

        _mode (str): Set in init function. The operational mode. Options are RW.
        _units (str): The units.

        _minimum (int): Set in init funtion.
        _maximum (int): Set in init funtion.

        _lowWarning (int): Set in init funtion.
        _lowAlarm (int): Set in init funtion.
        _highWarning (int): Set in init funtion.
        _highAlarm (int): Set in init funtion.

        _default (str): The default value of the variable to prevent errors.
        _typeStr (str): The typestring.

        _block (str): The block.
        _pollInterval (int): Polling interval.
        _nativeType (str): Native type.
        _ndType (str): ndtype.
        _extraAttr (list): Any extra attributes passed in as kwargs.
        _listeners (list): List of listeners.

        __functions (list): List of functions.
        __dependencies (list): List of dependencies.
    """

    PROPS = ['name', 'path', 'mode', 'typeStr', 'enum',
             'disp', 'precision', 'units', 'minimum', 'maximum',
             'nativeType', 'ndType', 'updateNotify',
             'hasAlarm', 'lowWarning', 'highWarning', 'lowAlarm',
             'highAlarm', 'alarmStatus', 'alarmSeverity', 'pollInterval']

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
                 guiGroup=None,
                 **kwargs):

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
        self._typeStr       = typeStr
        self._block         = None
        self._pollInterval  = pollInterval
        self._nativeType    = None
        self._ndType        = None
        self._extraAttr     = kwargs
        self._listeners     = []
        self.__functions    = []
        self.__dependencies = []

        # Build enum if specified
        self._disp = disp
        self._enum = enum

        if isinstance(disp, dict):
            self._enum = disp
        elif isinstance(disp, list):
            self._enum = {k:str(k) for k in disp}
        elif isinstance(value, bool) and enum is None:
            self._enum = {False: 'False', True: 'True'}

        if self._enum is not None:
            self._disp = 'enum'

        # Create inverted enum
        self._revEnum = None
        if self._enum is not None:
            self._revEnum = {v:k for k,v in self._enum.items()}

        # Auto determine types
        if value is not None:
            self._nativeType = type(value)

            if self._enum is not None and (self._nativeType is np.ndarray or self._nativeType is list or self._nativeType is dict):
                raise VariableError(f"Invalid use of enum with value of type {self._nativeType}")

            if self._nativeType is np.ndarray:
                self._ndType = value.dtype
                self._typeStr = f'{value.dtype}{value.shape}'

            elif self._typeStr == 'Unknown':
                self._typeStr = value.__class__.__name__

        # Check modes
        if (self._mode != 'RW') and (self._mode != 'RO') and \
           (self._mode != 'WO'):
            raise VariableError(f'Invalid variable mode {self._mode}. Supported: RW, RO, WO')


        # Call super constructor
        pr.Node.__init__(self, name=name, description=description, hidden=hidden, groups=groups, guiGroup=guiGroup)


    @pr.expose
    @property
    def enum(self):
        """ """
        return self._enum

    @property
    def enumYaml(self):
        """ """
        return pr.dataToYaml(self._enum)

    @pr.expose
    @property
    def revEnum(self):
        """ """
        return self._revEnum

    @pr.expose
    @property
    def typeStr(self):
        """ """
        if self._typeStr == 'Unknown':
            v = self.value()
            if self.nativeType is np.ndarray:
                self._typeStr = f'{v.dtype}{v.shape}'
            else:
                self._typeStr = v.__class__.__name__
        return self._typeStr

    @pr.expose
    @property
    def disp(self):
        """ """
        return self._disp

    @pr.expose
    @property
    def precision(self):
        """ """
        if self.nativeType is float or self.nativeType is np.ndarray:
            res = re.search(r':([0-9])\.([0-9]*)f',self._disp)
            try:
                return int(res[2])
            except Exception:
                return 8
        else:
            return 0

    @pr.expose
    @property
    def mode(self):
        """ """
        return self._mode

    @pr.expose
    @property
    def units(self):
        """ """
        return self._units

    @pr.expose
    @property
    def minimum(self):
        """ """
        return self._minimum

    @pr.expose
    @property
    def maximum(self):
        """ """
        return self._maximum


    @pr.expose
    @property
    def hasAlarm(self):
        """ """
        return (self._lowWarning is not None or self._lowAlarm is not None or self._highWarning is not None or self._highAlarm is not None)

    @pr.expose
    @property
    def lowWarning(self):
        """ """
        return self._lowWarning

    @pr.expose
    @property
    def lowAlarm(self):
        """ """
        return self._lowAlarm

    @pr.expose
    @property
    def highWarning(self):
        """ """
        return self._highWarning

    @pr.expose
    @property
    def highAlarm(self):
        """ """
        return self._highAlarm

    @pr.expose
    @property
    def alarmStatus(self):
        """ """
        stat,sevr = self._alarmState(self.value())
        return stat

    @pr.expose
    @property
    def alarmSeverity(self):
        """ """
        stat,sevr = self._alarmState(self.value())
        return sevr

    def properties(self):
        d = odict()
        d['value'] = self.value()
        d['valueDisp'] = self.valueDisp()
        d['class'] = self.__class__.__name__

        for p in self.PROPS:
            d[p] = getattr(self, p)
        return d

    def getExtraAttribute(self, name):
        if name in self._extraAttr:
            return self._extraAttr[name]
        else:
            return None

    def addDependency(self, dep):
        """
        Args:
            dep :

        Returns
        -------

        """
        if dep not in self.__dependencies:
            self.__dependencies.append(dep)
            dep.addListener(self)

    @pr.expose
    @property
    def pollInterval(self):
        """ """
        return self._pollInterval

    @pr.expose
    def setPollInterval(self, interval):
        self._log.debug(f'{self.path}.setPollInterval({interval}]')
        self._pollInterval = interval
        self._updatePollInterval()


    @pr.expose
    @property
    def lock(self):
        """ """
        if self._block is not None:
            return self._block._lock
        else:
            return None

    @pr.expose
    @property
    def updateNotify(self):
        """ """
        return self._updateNotify

    @property
    def dependencies(self):
        """ """
        return self.__dependencies

    def addListener(self, listener):
        """
        Add a listener Variable or function to call when variable changes as a callback.
        This is useful when chaining variables together. (ADC conversions, etc)
        The variable and value class are passed as an arg: func(path,varValue)

        Args:
            listener (BaseVariable|func): Listener to add to class attribute _listeners or _functions.

        """
        if isinstance(listener, BaseVariable):
            if listener not in self._listeners:
                self._listeners.append(listener)
        else:
            if listener not in self.__functions:
                self.__functions.append(listener)

    def _addListenerCpp(self, func):
        self.addListener(lambda path, varValue: func(path, varValue.valueDisp))

    def delListener(self, listener):
        """
        Remove a listener Variable or function from list of listener functions.

        Args:
            listener (BaseVariable|func): Listener to remove.

        """
        if listener in self.__functions:
            self.__functions.remove(listener)

    @pr.expose
    def set(self, value, *, index=-1, write=True, verify=True, check=True):
        """
        Set the value and write to hardware if applicable
        Writes to hardware are blocking. An error will result in a logged exception.

        Args:
            value :
            * :
            index (int) :   (Default value = -1)
            write (bool) : (Default value = True)
            verify (bool) : (Default value = True)
            check (bool) : (Default value = True)

        Returns
        -------

        """
        pass

    @pr.expose
    def post(self, value, *, index=-1):
        """
        Set the value and write to hardware if applicable using a posted write.
        This method does not call through parent.writeBlocks(), but rather
        calls on self._block directly.

        Args:
            value :
            * :
            index (int) :   (Default value = -1)

        Returns
        -------

        """
        pass

    @pr.expose
    def get(self, *, index=-1, read=True, check=True):
        """
        Return the value after performing a read from hardware if applicable.
        Hardware read is blocking. An error will result in a logged exception.
        Listeners will be informed of the update.

        Args:
            * :
            index (int) :   (Default value = -1)
            read (bool) : (Default value = True) A True value will read the hardware before returning the value. False returns the shadow value.
            check (bool) : (Default value = True)

        Returns
        -------

        """
        return None

    @pr.expose
    def write(self, *, verify=True, check=True):
        """
        Force a write of the variable.

        Args:
            * :

            verify (bool) : (Default value = True)
            check (bool) : (Default value = True)

        Returns
        -------

        """
        pass

    @pr.expose
    def getVariableValue(self,read=True,index=-1):
        """
        Return the value after performing a read from hardware if applicable.
        Hardware read is blocking. An error will result in a logged exception.
        Listeners will be informed of the update.

        Args:
            read (bool) : (Default value = True)
            index (int) : (Default value = -1)

        Returns
        -------
        type
            Hardware read is blocking. An error will result in a logged exception.
            Listeners will be informed of the update.

        """
        return VariableValue(self,read=read,index=index)

    @pr.expose
    def value(self, index=-1):
        """ Equivalent function to get(read=False)
        """
        return self.get(read=False, index=index)

    @pr.expose
    def genDisp(self, value, *, useDisp=None):
        """ Converts the passed raw value into the display representation

        Args:
            value : Value to access the display representation.
            useDisp:  Optional display format override. Default behavior is to use display in class parameters.

        Returns:
            Formatted value for display representation.

        """
        try:

            if useDisp is None:
                useDisp=self.disp

            if useDisp == '':
                return ''

            elif isinstance(value,np.ndarray):
                return np.array2string(value,
                                       separator=', ',
                                       formatter={'all':useDisp.format},
                                       threshold=sys.maxsize,
                                       max_line_width=1000)

            elif useDisp == 'enum':
                if value in self.enum:
                    return self.enum[value]
                else:
                    self._log.warning("Invalid enum value {} in variable '{}'".format(value,self.path))
                    return f'INVALID: {value}'
            else:
                return useDisp.format(value)

        except Exception as e:
            pr.logException(self._log,e)
            self._log.error(f"Error generating disp for value {value} with type {type(value)} in variable {self.path}")
            raise e

    @pr.expose
    def getDisp(self, read=True, index=-1):
        """ Returns the display value with an optional read. Equivalent to genDisp(get(read+False)).

        Args:
            read (bool) : (Default value = True)
            index (int) : (Default value = -1)

        Returns:
            Formatted value for display representation.
        """
        return self.genDisp(self.get(read=read,index=index))

    @pr.expose
    def valueDisp(self, index=-1): #, read=True, index=-1):
        """ Return the display value without a read. Equivalent to genDisp(get(read=False))

        Args:
            read (bool) : (Default value = True)
            index (int) : (Default value = -1)

        Returns:
            Formatted value for display representation.
        """
        return self.getDisp(read=False, index=index)

    @pr.expose
    def parseDisp(self, sValue):
        """ Converts a string representation or enum value into a raw value.
        parseDisp will detect when it is being passed a raw value.

        Args:
            sValue : the value to be converted to a raw value.

        Returns:
            Raw value version of sValue.
        """
        try:
            if not isinstance(sValue,str):
                return sValue
            elif self.nativeType is np.ndarray:
                return np.array(ast.literal_eval(sValue),self._ndType)
            elif self.disp == 'enum':
                return self.revEnum[sValue]
            elif self.nativeType is str:
                return sValue
            else:
                return ast.literal_eval(sValue)

        except Exception as e:
            msg = "Invalid value {} for variable {} with type {}: {}".format(sValue,self.name,self.nativeType,e)
            self._log.error(msg)
            raise VariableError(msg)

    @pr.expose
    def setDisp(self, sValue, write=True, index=-1):
        """ Update the variable with the display value with optional write.
        Equivalent to set(parseDisp(sValue), write)

        Args:
            sValue : val
            write (bool) : (Default value = True)
            index (int) : (Default value = -1)

        """
        self.set(self.parseDisp(sValue), write=write, index=index)

    @property
    def nativeType(self):
        """ """
        return self._nativeType

    @property
    def ndType(self):
        """ """
        return self._ndType

    @property
    def ndTypeStr(self):
        """ """
        return str(self.ndType)

    def _setDefault(self):
        """ """
        if self._default is not None:
            self.setDisp(self._default, write=False)

    def _updatePollInterval(self):
        """ """
        if self.root is not None and self.root._pollQueue is not None:
            self.root._pollQueue.updatePollInterval(self)

    def _finishInit(self):
        """ """
        # Set the default value but dont write
        self._setDefault()
        self._updatePollInterval()

        # Setup native type
        if self._nativeType is None:
            v = self.value()
            self._nativeType = type(v)

            if self._nativeType is np.ndarray:
                self._ndType = v.dtype

    def _setDict(self,d,writeEach,modes,incGroups,excGroups,keys):
        """
        Args:
            d :
            writeEach :
            modes :
            incGroups :
            excGroups :
            keys :


        Returns
        -------

        """

        # If keys is not none, it should only contain one entry
        # and the variable should be a list variable
        if keys is not None:

            if len(keys) != 1 or (self.nativeType is not list and self.nativeType is not np.ndarray):
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
            else:
                self._log.warning(f"Skipping set for Entry {self.name} with mode {self._mode}. Enabled Modes={modes}.")

        # Standard set
        elif self._mode in modes:
            # Array variables can be set with a dict of index/value pairs
            if isinstance(d, dict):
                for k,v in d.items():
                    self.setDisp(v, index=k, write=writeEach)
            else:
                self.setDisp(d,writeEach)
        else:
            self._log.warning(f"Skipping set for Entry {self.name} with mode {self._mode}. Enabled Modes={modes}.")

    def _getDict(self, modes=['RW', 'RO', 'WO'], incGroups=None, excGroups=None, properties=False):
        """


        Args:
            modes :

            incGroups :

            excGroups :


        Returns
        -------

        """
        if self._mode in modes:
            if properties is False:
                return VariableValue(self)
            else:
                return self.properties()
        else:
            return None


    def _queueUpdate(self):
        """ """
        self._root._queueUpdates(self)

    def _doUpdate(self):
        """ """
        val = VariableValue(self)

        for func in self.__functions:
            func(self.path,val)

        return val

    def _alarmState(self,value):
        """


        Args:
            value :


        Returns
        -------
        type


        """

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

    def _genDocs(self,file):
        """

        Args:
            file :


        Returns
        -------

        """
        print(f".. topic:: {self.path}",file=file)

        print('',file=file)
        print(pr.genDocDesc(self.description,4),file=file)
        print('',file=file)

        print(pr.genDocTableHeader(['Field','Value'],4,100),file=file)

        for a in ['name', 'path', 'enum',
                 'typeStr', 'disp', 'precision', 'mode', 'units', 'minimum',
                 'maximum', 'lowWarning', 'lowAlarm', 'highWarning',
                 'highAlarm', 'alarmStatus', 'alarmSeverity']:

            astr = str(getattr(self,a))

            if astr != 'None':
                print(pr.genDocTableRow([a,astr],4,100),file=file)


class RemoteVariable(BaseVariable,rim.Variable):
    """ Used to manage a remote value typically located on the managed hardware.
    Associated with an address, offset, and size.

    A RegisterBlock serves as the gateway between the variable and a memory interface device.
    RemoteVariables are associated into common RegisterBlocks by detecting overlaps in accessed space.

    The typical use for offset, bitOffset and bitSize involves passing a single integer value to each to indicate the byte and bit offsets as well as the size.
    In some cases the variable value will be mapped to bits scattered around memory space.
    Lists and integers are supported for offset, bitOffset and bitSize, but lists must be equivalent lengths.

    Args:
        base (UInt|Int|UIntReversed|UIntBE|IntBE|UFixed|Fixed|Bool|String|Float|FloatBE|Double|DoubleBE) : Pointer
            to a Model class used to convert between the variable raw value and register bits
        offset (int|list): Defines the offset in bytes of the variable relative to the device
        bitOffset (int|list): Defines the offset in bits of the LSB relative to the offset in bytes
        bitSize (int|list): Number of bits occupied by the variable.
        verify (bool): Flag indicating if a verify should occur for a RW variable following a write.
        value : Optional default value. BaseVariable is used to determine type.
    """

    PROPS = BaseVariable.PROPS + [
        'address', 'overlapEn', 'offset', 'bitOffset', 'bitSize',
        'verifyEn', 'numValues', 'valueBits', 'valueStride', 'retryCount',
        'varBytes', 'bulkEn']

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
                 offset,
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
                 guiGroup=None,
                 **kwargs):

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
                              guiGroup=guiGroup, **kwargs)

        # If numValues > 0 the bit size array must only have one entry
        # Auto calculate the total number of bits
        if numValues != 0:
            self._nativeType = np.ndarray
            self._ndType = self._base.ndType
            self._typeStr = f'{self.ndType}({numValues},)'

            if len(bitSize) != 1:
                raise VariableError('BitSize array must have a length of one when numValues > 0')

            if valueBits > valueStride:
                raise VariableError(f'ValueBits {valueBits} is greater than valueStrude {valueStride}')

            # Override the bitSize
            bitSize[0] = numValues * valueBits

            if self._ndType is None:
                raise VariableError(f'Invalid base type {self._base} with numValues = {numValues}')

        else:
            self._typeStr = self._base.name

        listData = VariableListData(numValues,valueBits,valueStride)

        # Setup C++ Base class
        rim.Variable.__init__(
            self,
            self._name,
            self._mode,
            self._minimum,
            self._maximum,
            offset,
            bitOffset,
            bitSize,
            overlapEn,
            verify,
            self._bulkOpEn,
            self._updateNotify,
            self._base,
            listData,
            retryCount)


    ##############################
    # Properties held by C++ class
    ##############################


    @pr.expose
    @property
    def address(self):
        return self._block.address

    @property
    def numValues(self):
        return self._numValues()

    @property
    def valueBits(self):
        return self._valueBits()

    @property
    def valueStride(self):
        return self._valueStride()

    @property
    def retryCount(self):
        return self._retryCount()

    @pr.expose
    @property
    def varBytes(self):
        """ """
        return self._varBytes()

    @pr.expose
    @property
    def offset(self):
        """ """
        return self._offset()

    @pr.expose
    @property
    def overlapEn(self):
        """ """
        return self._overlapEn()

    @pr.expose
    @property
    def bitSize(self):
        """ """
        return self._bitSize()

    @pr.expose
    @property
    def bitOffset(self):
        """ """
        return self._bitOffset()

    @pr.expose
    @property
    def verifyEn(self):
        """ """
        return self._verifyEn()


    ########################
    # Local Properties
    ########################


    @pr.expose
    @property
    def base(self):
        """ """
        return self._base

    @pr.expose
    @property
    def bulkEn(self):
        """ """
        return self._bulkOpEn

    @pr.expose
    def set(self, value, *, index=-1, write=True, verify=True, check=True):
        """
        Set the value and write to hardware if applicable
        Writes to hardware are blocking if check=True, otherwise non-blocking.
        A verify will be performed according to self.verifyEn if verify=True
        A verify will not be performed if verify=False
        An error will result in a logged exception.

        Args:
            value :
                * :
            index (int) : (Default value = -1)
            write (bool) : (Default value = True) True value will immediately generate a blocking transaction to hardware.
                False will update a shadow value in anticipation of a future write during internal bulk operations.
            verify (bool) : (Default value = True) True value caauses a verify to be performed accoring to self.verifyEn.
            check (bool) : (Default value = True)

        Returns:

        """
        try:

            # Set value to block
            self._set(value,index)

            if write:
                self._parent.writeBlocks(force=True, recurse=False, variable=self, index=index)
                if verify:
                    self._parent.verifyBlocks(recurse=False, variable=self)
                if check:
                    self._parent.checkBlocks(recurse=False, variable=self)

        except Exception as e:
            pr.logException(self._log,e)
            self._log.error("Error setting value '{}' to variable '{}' with type {}. Exception={}".format(value,self.path,self.typeStr,e))
            raise e

    @pr.expose
    def post(self, value, *, index=-1):
        """
        Set the value and write to hardware if applicable using a posted write.
        This method does not call through parent.writeBlocks(), but rather
        calls on self._block directly.
        Generates an immediate non-blocking write.

        Args:
            value :
                * :
            index (int) : (Default value = -1)

        Returns
        -------

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
    def get(self, *, index=-1, read=True, check=True):
        """


        Args:
            * :

        index (int) :(Default value = -1)
        read : bool
             (Default value = True)
        check : bool
             (Default value = True)

        Returns
        -------
        type
            Hardware read is blocking if check=True, otherwise non-blocking.
            An error will result in a logged exception.
            Listeners will be informed of the update.

        """
        try:
            if read:
                self._parent.readBlocks(recurse=False, variable=self, index=index)
                if check:
                    self._parent.checkBlocks(recurse=False, variable=self)

            return self._get(index)

        except Exception as e:
            pr.logException(self._log,e)
            self._log.error("Error reading value from variable '{}'".format(self.path))
            raise e

    @pr.expose
    def write(self, *, verify=True, check=True):
        """
        Force a write of the variable.
        Hardware write is blocking if check=True.
        A verify will be performed according to self.verifyEn if verify=True
        A verify will not be performed if verify=False
        An error will result in a logged exception

        Args:
             * :

            verify (bool) : (Default value = True)
            check (bool) : (Default value = True)

        Returns
        -------

        """
        try:
            self._parent.writeBlocks(force=True, recurse=False, variable=self)
            if verify:
                self._parent.verifyBlocks(recurse=False, variable=self)
            if check:
                self._parent.checkBlocks(recurse=False, variable=self)

        except Exception as e:
            pr.logException(self._log,e)
            raise e

    def _parseDispValue(self, sValue):
        """


        Args:
            sValue :


        Returns
        -------

        """
        if self.disp == 'enum':
            return self.revEnum[sValue]
        else:
            return self._base.fromString(sValue)

    def _genDocs(self,file):
        """

        Args:
            file :


        Returns
        -------

        """
        BaseVariable._genDocs(self,file)

        for a in ['offset', 'numValues', 'bitSize', 'bitOffset', 'verifyEn', 'varBytes']:
            astr = str(getattr(self,a))

            if astr != 'None':
                print(pr.genDocTableRow([a,astr],4,100),file=file)


class LocalVariable(BaseVariable):
    """ Used to manage a local value such as a fileame, software mode, etc.
    Each LocalVariable is backed by a LocalBlock that holds the shadow value.

    Value param must be passed when creating a Local Variable. Used to set default value and determine native type.

    LocalVariables can contain complex data types such as lists and dictionaries
    typeStr and nativeType will return the container type
    setDisp, getDisp, valueDisp will not work properly
    localSet and localGet parameters are optional overrides to set and get called within the context
    of a lock associated with the variable. These are executed by the LocalBlock.

    C++ functions exposed through python are supported, but no args are passed.

    Args:
        localSet: Optional reference to function used for set calls if specialized behavior needed.
            Called when the variable's set method is called, after the internal shadow value is updated.
            Template is localSet(device, variable, value, changed (bool))
        localGet: Optional reference to function used for get calls if specialized behavior needed.
            Expected to return a new value, which will be stored in the shadow value.
            Template is localGet(device, variable)
    """

    def __init__(self, *,
                 name,
                 value=None,
                 description='',
                 mode='RW',
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
                 pollInterval=0,
                 updateNotify=True,
                 typeStr='Unknown',
                 bulkOpEn=True,
                 guiGroup=None,
                 **kwargs):

        if value is None and localGet is None:
            raise VariableError(f'LocalVariable {self.path} without localGet() must specify value= argument in constructor')

        BaseVariable.__init__(self, name=name, description=description,
                              mode=mode, value=value, disp=disp,
                              enum=enum, units=units, hidden=hidden, groups=groups,
                              minimum=minimum, maximum=maximum, typeStr=typeStr,
                              lowWarning=lowWarning, lowAlarm=lowAlarm,
                              highWarning=highWarning, highAlarm=highAlarm,
                              pollInterval=pollInterval,updateNotify=updateNotify, bulkOpEn=bulkOpEn,
                              guiGroup=guiGroup, **kwargs)

        self._block = pr.LocalBlock(variable=self,
                                    localSet=localSet,
                                    localGet=localGet,
                                    minimum=minimum,
                                    maximum=maximum,
                                    value=self._default)

    @pr.expose
    def set(self, value, *, index=-1, write=True, verify=True, check=True):
        """
        Set the value and write to hardware if applicable
        Writes to hardware are blocking. An error will result in a logged exception.

        Args:
            value :
            * :
            index (int) :   (Default value = -1)
            write (bool) : (Default value = True)
            verify (bool) : (Default value = True)
            check (bool) : (Default value = True)

        Returns
        -------

        """
        self._log.debug("{}.set({})".format(self, value))

        try:

            # Set value to block
            self._block.set(self, value, index)

            if write:
                self._block._checkTransaction()

        except Exception as e:
            pr.logException(self._log,e)
            self._log.error("Error setting value '{}' to variable '{}' with type {}. Exception={}".format(value,self.path,self.typeStr,e))
            raise e

    @pr.expose
    def post(self,value, *, index=-1):
        """
        Set the value and write to hardware if applicable using a posted write.
        This method does not call through parent.writeBlocks(), but rather
        calls on self._block directly.

        Args:
            value :

            * :

            index (int) :   (Default value = -1)

        Returns
        -------

        """
        self._log.debug("{}.post({})".format(self, value))

        try:
            self._block.set(self, value, index)
            self._block._checkTransaction()

        except Exception as e:
            pr.logException(self._log,e)
            self._log.error("Error posting value '{}' to variable '{}' with type {}".format(value,self.path,self.typeStr))
            raise e

    @pr.expose
    def get(self, *, index=-1, read=True, check=True):
        """


        Args:
                * :

            index (int) :   (Default value = -1)
            read (bool) : (Default value = True)
            check (bool) : (Default value = True)

        Returns
        -------
        type
            Hardware read is blocking. An error will result in a logged exception.
            Listeners will be informed of the update.

        """
        try:
            if read and check:
                self._block._checkTransaction()

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
    """A virtual variable which does not hold any local value.
    Passes values through with possible local modification using linkedSet and linkedGet functions.
    Dependent on other variable objects.

    Args:
        dependecies (list): List of variables that this variable is dependent on.
        linkedSet (func): Optional reference to function that is used for set calls. Must match following template of Device.linkedSet():
            linkedSet(device containing variable, variable, read arg passed to get())
        linkedGet (func): Optional reference to function that is used for get calls. Must match following template of Device.linkedGet():
            linkedGet(device containing variable, variable, raw value passed to set(), write arg passed to set())
        * : all other args passed to pr.BaseVariable
    """

    def __init__(self, *,
                 name,
                 variable=None,
                 dependencies=None,
                 linkedSet=None,
                 linkedGet=None,
                 minimum=None,
                 maximum=None,
                 **kwargs): # Args passed to BaseVariable

        # Set and get functions
        self._linkedGet = linkedGet
        self._linkedSet = linkedSet

        if minimum is not None or maximum is not None:
            raise VariableError("Invalid use of min or max values with LinkVariable")

        if variable is not None:
            # If directly linked to a variable, use it's value and set by defualt
            # for linkedGet and linkedSet unless overridden
            self._linkedGet = linkedGet if linkedGet else variable.get
            self._linkedSet = linkedSet if linkedSet else variable.set

            # Search the kwargs for overridden properties, otherwise the properties from the linked variable will be used
            args = ['disp', 'enum', 'units', 'minimum', 'maximum']
            for arg in args:
                if arg not in kwargs:
                    kwargs[arg] = getattr(variable, arg)

        # Why not inhertit mode from link variable?
        if not self._linkedSet:
            kwargs['mode'] = 'RO'
        if not self._linkedGet:
            kwargs['mode'] = 'WO'

        # Wrap linked get and set functions
        self._linkedGetWrap = pr.functionWrapper(function=self._linkedGet, callArgs=['dev', 'var', 'read', 'index', 'check'])
        self._linkedSetWrap = pr.functionWrapper(function=self._linkedSet, callArgs=['dev', 'var', 'value', 'write', 'index', 'verify', 'check'])

        # Call super constructor
        BaseVariable.__init__(self, name=name, **kwargs)

        # Dependency tracking
        if variable is not None:
            # Add the directly linked variable as a dependency
            self.addDependency(variable)

        if dependencies is not None:
            for d in dependencies:
                self.addDependency(d)

        self.__depBlocks = []

    def __getitem__(self, key):
        # Allow dependencies to be accessed as indices of self
        return self.dependencies[key]

    @pr.expose
    def set(self, value, *, write=True, index=-1, verify=True, check=True):
        """


        Args:
            value :
            * :
            write (bool) : (Default value = True)
            index (int) :   (Default value = -1)
            verify (bool) : (Default value = True)
            check (bool) : (Default value = True)

        Returns
        -------

        """
        try:
            self._linkedSetWrap(function=self._linkedSet, dev=self.parent, var=self, value=value, write=write, index=index, verify=verify, check=check)
        except Exception as e:
            pr.logException(self._log,e)
            self._log.error("Error setting link variable '{}'".format(self.path))
            raise e

    @pr.expose
    def get(self, read=True, index=-1, check=True):
        """


        Args:
            read (bool) : (Default value = True)
            index (int) :   (Default value = -1)
            check (bool) : (Default value = True)

        Returns
        -------

        """
        try:
            return self._linkedGetWrap(function=self._linkedGet, dev=self.parent, var=self, read=read, index=index, check=check)
        except Exception as e:
            pr.logException(self._log,e)
            self._log.error("Error getting link variable '{}'".format(self.path))
            raise e


    def __getBlocks(self):
        b = []
        for d in self.dependencies:
            if isinstance(d, LinkVariable):
                b.extend(d.__getBlocks())
            elif hasattr(d, '_block') and d._block is not None:
                b.append(d._block)

        return b

    def _finishInit(self):
        super()._finishInit()
        self.__depBlocks = self.__getBlocks()

    @property
    def depBlocks(self):
        """ Return a list of Blocks that this LinkVariable depends on """
        return self.__depBlocks

    @pr.expose
    @property
    def pollInterval(self):

        depIntervals = [dep.pollInterval for dep in self.dependencies if dep.pollInterval > 0]
        if len(depIntervals) == 0:
            return 0
        else:
            return min(depIntervals)
