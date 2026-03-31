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
from __future__ import annotations

import ast
import re
import shlex
import sys
import threading
import time
from typing import Any, Callable, Type

import numpy as np
import pyrogue as pr
import rogue.interfaces.memory as rim
from collections import OrderedDict as odict
from collections.abc import Iterable


class VariableError(Exception):
    """Raised when variable configuration or access fails."""
    pass


class VariableWaitClass(object):
    """Wait for variable conditions to become true.

    Pass a variable or list of variables, and a test function.
    The test function is passed a list containing the current
    variableValue state indexed by position as passed in the wait list.
    Each variableValue entry has an additional field updated which indicates
    if the variable has refreshed while waiting. This can be used to trigger
    on any update to the variable, regardless of value.

    i.e. w = VariableWaitClass([root.device.var1,root.device.var2],
                                lambda varValues: varValues[0].value >= 10 and \
                                            varValues[1].value >= 20)

         w.wait()

    i.e. w = VariableWaitClass([root.device.var1,root.device.var2],
                                lambda varValues: varValues[0].updated and \
                                            varValues[1].updated)

         w.wait()

    If no function is provided, the class will return when all variables are updated,
    regardless of value.

    The routine wait class can be used multiple times with subsequent calls using arm() to trigger:

        w.wait()
        w.arm()
        w.wait()

    getValues() can be called to get the final version of the tiles after the test passed.

    Parameters
    ----------
    varList : object or list
        Variable or list of variables to monitor.
    testFunction : callable, optional
        Predicate callback of the form
        ``testFunction(varValues: list[VariableValue]) -> bool``.
    timeout : int or float, optional (default = 0)
        Time in seconds to wait before timing out. ``0`` disables timeout.
    """
    def __init__(
        self,
        varList: pr.BaseVariable | list[pr.BaseVariable],
        testFunction: Callable[[list["VariableValue"]], bool] | None = None,
        timeout: float = 0,
    ) -> None:
        """Initialize a wait condition across one or more variables."""
        self._values   = odict()
        self._updated  = odict()
        self._cv       = threading.Condition()
        self._testFunc = testFunction
        self._timeout  = timeout

        # Convert single variable to a list
        if not isinstance(varList,list):
            self._vlist = [varList]
        else:
            self._vlist = varList

        self.arm()

    def arm(self) -> None:
        """Arm the wait by registering variable listeners."""
        with self._cv:
            for v in self._vlist:
                v.addListener(self._varUpdate)
                self._values[v.path]  = v.getVariableValue(read=False)
                self._values[v.path].updated = False
                self._updated[v.path] = False

    def wait(self) -> bool:
        """Wait until the condition is met or timeout occurs."""
        start  = time.time()

        with self._cv:
            ret = self._check()

            # Run until timeout or all conditions have been met
            while (not ret) and ((self._timeout == 0) or ((time.time()-start) < self._timeout)):
                self._cv.wait(0.5)
                ret = self._check()

            # Cleanup
            for v in self._vlist:
                v.delListener(self._varUpdate)

        return ret

    def get_values(self) -> dict:
        """Return the latest collected variable values."""
        return {k: self._values[k.path] for k in self._vlist}

    def _varUpdate(self, path: str, varValue: Any) -> None:
        """Listener callback used to capture variable updates."""
        with self._cv:
            if path in self._values:
                varValue.updated = True
                self._values[path] = varValue
                self._updated[path] = True
                self._cv.notify()

    def _check(self) -> bool:
        """Evaluate wait completion state using callback or update flags."""
        if self._testFunc is not None:
            return (self._testFunc(list(self._values.values())))
        else:
            return (all(self._updated.values()))


def VariableWait(
    varList: Any,
    testFunction: Callable[[list["VariableValue"]], bool] | None = None,
    timeout: float = 0,
) -> bool:
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

    If no function is provided, the class will return when all variables are updated,
    regardless of value.

    Parameters
    ----------
    varList :
        List of variables to monitor.

    testFunction :
        Function of the form
        ``testFunction(varValues: list[VariableValue]) -> bool``.
        Use ``None`` to trigger on update only.

    timeout : int, optional (default = 0)
        Timeout in seconds.

    Returns
    -------
    bool
        True if conditions were met, False if there was a timeout.
    """
    wc = VariableWaitClass(varList, testFunction, timeout)
    return wc.wait()


class VariableValue(object):
    """Snapshot of a variable value with display metadata."""
    def __init__(self, var: Any, read: bool = False, index: int = -1) -> None:
        """Capture value, display text, and alarm metadata for a variable."""
        self.value     = var.get(read=read,index=index)
        self.valueDisp = var.genDisp(self.value)
        self.disp      = var.disp
        self.enum      = var.enum
        self.updated   = False

        self.status, self.severity = var._alarmState(self.value)

    def __repr__(self) -> str:
        """Return a debug representation of stored value metadata."""
        return f'{str(self.__class__)}({self.__dict__})'


class VariableListData(object):
    """Container describing list-type variable storage."""
    def __init__(self, numValues: int, valueBits: int, valueStride: int) -> None:
        """Initialize list-shape metadata for array variables."""
        self.numValues   = numValues
        self.valueBits   = valueBits
        self.valueStride = valueStride

    def __repr__(self) -> str:
        """Return a debug representation of list-shape metadata."""
        return f'{self.__class__}({self.__dict__})'



class BaseVariable(pr.Node):
    """Base class for variables in the PyRogue tree.

    Parameters
    ----------
    name : str
        Variable name.
    description : str, optional (default = "")
        Human-readable description.
    mode : str, optional (default = "RW")
        Access mode: ``RW``, ``RO``, or ``WO``.
    value : object, optional
        Default value for the variable.
    disp : object, optional (default = "{}")
        Display formatter or enumeration mapping.
    enum : dict, optional
        Mapping from object values to display strings.
    units : str, optional
        Engineering units.
    hidden : bool, optional (default = False)
        If True, add the variable to the ``Hidden`` group.
    groups : list[str], optional
        Groups to assign.
    minimum : object, optional
        Minimum allowed value.
    maximum : object, optional
        Maximum allowed value.
    lowWarning : object, optional
        Low warning threshold.
    lowAlarm : object, optional
        Low alarm threshold.
    highWarning : object, optional
        High warning threshold.
    highAlarm : object, optional
        High alarm threshold.
    pollInterval : object, optional (default = 0)
        Polling interval in seconds.
    updateNotify : bool, optional (default = True)
        Enable update notifications.
    typeStr : str, optional (default = "Unknown")
        Type string for display.
    typeCheck : bool, optional (default = True)
        If True, raise an error when later writes change the seeded Python type.
    bulkOpEn : bool, optional (default = True)
        Enable bulk operations.
    offset : int, optional (default = 0)
        Offset used by remote variables.
    guiGroup : str, optional
        GUI grouping label.
    **kwargs : Any
        Additional attributes.
    """

    PROPS = ['name', 'path', 'mode', 'typeStr', 'enum',
             'disp', 'precision', 'units', 'minimum', 'maximum',
             'nativeType', 'ndType', 'updateNotify',
             'hasAlarm', 'lowWarning', 'highWarning', 'lowAlarm',
             'highAlarm', 'alarmStatus', 'alarmSeverity', 'pollInterval']

    def __init__(
        self,
        *,
        name: str,
        description: str = '',
        mode: str = 'RW',
        value: Any = None,
        disp: Any = '{}',
        enum: dict[object, str] | None = None,
        units: str | None = None,
        hidden: bool = False,
        groups: list[str] | None = None,
        minimum: Any | None = None,
        maximum: Any | None = None,
        lowWarning: Any | None = None,
        lowAlarm: Any | None = None,
        highWarning: Any | None = None,
        highAlarm: Any | None = None,
        pollInterval: Any = 0,
        updateNotify: bool = True,
        typeStr: str = 'Unknown',
        typeCheck: bool = True,
        bulkOpEn: bool = True,
        offset: int = 0,
        guiGroup: str | None = None,
        **kwargs: Any,
    ) -> None:
        """Initialize a base variable."""

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
        self._typeCheck     = typeCheck
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
    def enum(self) -> dict[object, str] | None:
        """Return the enum mapping, if any."""
        return self._enum

    @property
    def enumYaml(self) -> str:
        """Return the enum mapping as YAML."""
        return pr.dataToYaml(self._enum)

    @pr.expose
    @property
    def revEnum(self) -> dict[str, object] | None:
        """Return the reverse enum mapping, if available."""
        return self._revEnum

    @pr.expose
    @property
    def typeStr(self) -> str:
        """Return the type string for this variable."""
        if self._typeStr == 'Unknown':
            v = self.value()
            if self.nativeType is np.ndarray:
                self._typeStr = f'{v.dtype}{v.shape}'
            else:
                self._typeStr = v.__class__.__name__
        return self._typeStr

    @pr.expose
    @property
    def disp(self) -> str:
        """Return the display formatter."""
        return self._disp

    @pr.expose
    @property
    def precision(self) -> int:
        """Return the display precision for float-like values."""
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
    def mode(self) -> str:
        """Return the access mode (``RW``, ``RO``, ``WO``)."""
        return self._mode

    @pr.expose
    @property
    def units(self) -> str | None:
        """Return the engineering units."""
        return self._units

    @pr.expose
    @property
    def minimum(self) -> Any | None:
        """Return the minimum allowed value."""
        return self._minimum

    @pr.expose
    @property
    def maximum(self) -> Any | None:
        """Return the maximum allowed value."""
        return self._maximum


    @pr.expose
    @property
    def hasAlarm(self) -> bool:
        """Return True if any alarm thresholds are configured."""
        return (self._lowWarning is not None or self._lowAlarm is not None or self._highWarning is not None or self._highAlarm is not None)

    @pr.expose
    @property
    def lowWarning(self) -> Any | None:
        """Return the low warning threshold."""
        return self._lowWarning

    @pr.expose
    @property
    def lowAlarm(self) -> Any | None:
        """Return the low alarm threshold."""
        return self._lowAlarm

    @pr.expose
    @property
    def highWarning(self) -> Any | None:
        """Return the high warning threshold."""
        return self._highWarning

    @pr.expose
    @property
    def highAlarm(self) -> Any | None:
        """Return the high alarm threshold."""
        return self._highAlarm

    @pr.expose
    @property
    def alarmStatus(self) -> str:
        """Return the current alarm status."""
        stat,sevr = self._alarmState(self.value())
        return stat

    @pr.expose
    @property
    def alarmSeverity(self) -> str:
        """Return the current alarm severity."""
        stat,sevr = self._alarmState(self.value())
        return sevr

    def properties(self) -> dict[str, Any]:
        """Return a dictionary of properties and current value."""
        d = odict()
        d['value'] = self.value()
        d['valueDisp'] = self.valueDisp()
        d['class'] = self.__class__.__name__

        for p in self.PROPS:
            d[p] = getattr(self, p)
        return d

    def getExtraAttribute(self, name: str) -> Any | None:
        """Return an extra attribute by name, if present.

        Parameters
        ----------
        name : str
            Attribute name to look up.
        """
        if name in self._extraAttr:
            return self._extraAttr[name]
        else:
            return None

    def addDependency(self, dep: BaseVariable) -> None:
        """Add a dependency variable.
        When this variable changes, the dependency variable will be notified.

        Parameters
        ----------
        dep : BaseVariable
            The dependency variable to add.
        """
        if dep not in self.__dependencies:
            self.__dependencies.append(dep)
            dep.addListener(self)

    @pr.expose
    @property
    def pollInterval(self) -> float:
        """Return the poll interval."""
        return self._pollInterval

    @pr.expose
    def setPollInterval(self, interval: float) -> None:
        """Set the poll interval.

        Parameters
        ----------
        interval : object
            Poll interval to use.
        """
        self._log.debug("%s.setPollInterval(%s)", self.path, interval)
        self._pollInterval = interval
        self._updatePollInterval()


    @pr.expose
    @property
    def lock(self) -> threading.Lock | None:
        """Return the underlying lock, if available."""
        if self._block is not None:
            return self._block._lock
        else:
            return None

    @pr.expose
    @property
    def updateNotify(self) -> bool:
        """Return True if update notifications are enabled."""
        return self._updateNotify

    @property
    def dependencies(self) -> list[BaseVariable]:
        """Return registered dependency variables."""
        return self.__dependencies

    def addListener(self, listener: BaseVariable | Callable[[str, VariableValue], None]) -> None:
        """
        Add a listener Variable or function to call when variable changes.
        This is useful when chaining variables together. (ADC conversions, etc)
        The variable and value class are passed as an arg: func(path,varValue)

        Parameters
        ----------
        listener : BaseVariable or Callable[[str, VariableValue], None]
            Variable or callback function to notify.


        Returns
        -------
        None
        """
        if isinstance(listener, BaseVariable):
            if listener not in self._listeners:
                self._listeners.append(listener)
        else:
            if listener not in self.__functions:
                self.__functions.append(listener)

    def _addListenerCpp(self, func: Callable[[str, str], None]) -> None:
        """Add a C++/string listener callback.

        Parameters
        ----------
        func : callable
            Callback of the form ``func(path, valueDisp)`` where both
            arguments are strings.
        """
        self.addListener(lambda path, varValue: func(path, varValue.valueDisp))

    def delListener(self, listener: BaseVariable | Callable[[str, VariableValue], None]) -> None:
        """
        Remove a listener Variable or function

        Parameters
        ----------
        listener : BaseVariable or Callable[[str, VariableValue], None]
            Variable or callback function to remove.


        Returns
        -------
        None
        """
        if isinstance(listener, BaseVariable):
            if listener in self._listeners:
                self._listeners.remove(listener)
        else:
            if listener in self.__functions:
                self.__functions.remove(listener)

    @pr.expose
    def set(
        self,
        value: Any,
        *,
        index: int = -1,
        write: bool = True,
        verify: bool = True,
        check: bool = True,
    ) -> None:
        """
        Set the value and write to hardware if applicable
        Writes to hardware are blocking. An error will result in a logged exception.

        Parameters
        ----------
        value : object
            Value to set.

        index : int, optional (default = -1)
            Optional index for array variables.
        write : bool, optional (default = True)
            If True, perform a write transaction.
        verify : bool, optional (default = True)
            If True, verify after write.
        check : bool, optional (default = True)
            If True, wait for the transaction to complete.

        Returns
        -------

        """
        pass

    @pr.expose
    def post(self, value: Any, *, index: int = -1) -> None:
        """
        Set the value and write to hardware if applicable using a posted write.
        This method does not call through parent.writeBlocks(), but rather
        calls on self._block directly.

        Parameters
        ----------
        value : object
            Value to set.
        index : int, optional (default = -1)
            Optional index for array variables.

        Returns
        -------

        """
        pass

    @pr.expose
    def get(self, *, index: int = -1, read: bool = True, check: bool = True) -> Any:
        """
        Return the value after performing a read from hardware if applicable.
        Hardware read is blocking. An error will result in a logged exception.
        Listeners will be informed of the update.

        Parameters
        ----------
        index : int, optional (default = -1)
            Optional index for array variables.
        read : bool, optional (default = True)
            If True, perform a read transaction.
        check : bool, optional (default = True)
            If True, check transaction completion.

        Returns
        -------

        """
        return None

    @pr.expose
    def write(self, *, verify: bool = True, check: bool = True) -> None:
        """
        Force a write of the variable.

        Parameters
        ----------
        verify : bool, optional (default = True)
            If True, verify after write.
        check : bool, optional (default = True)
            If True, check transaction completion.

        Returns
        -------

        """
        pass

    @pr.expose
    def getVariableValue(self, read: bool = True, index: int = -1) -> VariableValue:
        """
        Return the value after performing a read from hardware if applicable.
        Hardware read is blocking. An error will result in a logged exception.
        Listeners will be informed of the update.

        Parameters
        ----------
        read : bool, optional (default = True)
            If True, perform a read transaction.
        index : int, optional (default = -1)
            Optional index for array variables.

        Returns
        -------
        VariableValue

        """
        return VariableValue(self,read=read,index=index)

    @pr.expose
    def value(self, index: int = -1) -> Any:
        """Return the current value without reading.

        Parameters
        ----------
        index : int, optional (default = -1)
            Optional index for array variables.
        """
        return self.get(read=False, index=index)

    @pr.expose
    def genDisp(self, value: Any, *, useDisp: str | None = None) -> str:
        """Generate a display string for a value.


        Parameters
        ----------
        value : object
            Value to format for display.
        useDisp : str, optional
            Display formatter override. If None, use the variable's disp formatter.


        Returns
        -------
        String representation of the Variable value for display.
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
                    self._log.warning("Invalid enum value %s in variable '%s'", value, self.path)
                    return f'INVALID: {value}'
            else:
                return useDisp.format(value)

        except Exception as e:
            pr.logException(self._log,e)
            self._log.error(
                "Error generating disp for value %r with type %s in variable %s",
                value,
                type(value),
                self.path,
            )
            raise e

    @pr.expose
    def getDisp(self, read: bool = True, index: int = -1) -> str:
        """Perform a get() and return the display string for the value.


        Parameters
        ----------
        read : bool, optional (default = True)
            If True, perform a read transaction.
        index : int, optional (default = -1)
            Optional index for array variables.

        Returns
        -------
        String representation of the Variable value for display.
        """
        return self.genDisp(self.get(read=read,index=index))

    @pr.expose
    def valueDisp(self, index: int = -1) -> str: #, read=True, index=-1):
        """Return a display string for the current value without reading.


        Parameters
        ----------
        index : int, optional (default = -1)
            Optional index for array variables.

        Returns
        -------
        String representation of the Variable value for display.
        """
        return self.getDisp(read=False, index=index)

    @pr.expose
    def parseDisp(self, sValue: str) -> object:
        """Parse a string representation of a value into a Python object.


        Parameters
        ----------
        sValue : object
            Display-formatted value to parse.


        Returns
        -------
        Python object representation of the string value.
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
    def setDisp(self, sValue: str, write: bool = True, index: int = -1) -> None:
        """Set the value of the variable using a string representation of the value.


        Parameters
        ----------
        sValue : str
            Display-formatted value to set.
        write : bool, optional (default = True)
            If True, write the value to the hardware.
        index : int, optional (default = -1)
            Optional index for array variables.

        Returns
        -------
        None
        """
        value = self.parseDisp(sValue)

        # Indexed writes into ndarray-backed variables expect a scalar element,
        # not the 0-D ndarray produced by np.array(ast.literal_eval(...)).
        if index >= 0 and isinstance(value, np.ndarray) and value.ndim == 0:
            value = value.item()

        self.set(value, write=write, index=index)

    @property
    def nativeType(self) -> Type[object]:
        """Return the native Python type."""
        return self._nativeType

    @property
    def ndType(self) -> Type[np.dtype]:
        """Return the numpy dtype for array variables."""
        return self._ndType

    @property
    def ndTypeStr(self) -> str:
        """Return the numpy dtype as a string."""
        return str(self.ndType)

    def _setDefault(self) -> None:
        """ """
        if self._default is not None:
            self.setDisp(self._default, write=False)

    def _updatePollInterval(self) -> None:
        """ """
        if self.root is not None and self.root._pollQueue is not None:
            self.root._pollQueue.updatePollInterval(self)

    def _finishInit(self) -> None:
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

    def _setDict(
        self,
        d: dict[str, str] | object,
        writeEach: bool,
        modes: list[str],
        incGroups: str | list[str] | None = None,
        excGroups: str | list[str] | None = None,
        keys: list[str] | None = None,
    ) -> None:
        """
        Set variable values from a dictionary.

        Invoked recursively from parent Device's _setDict method.
        Override in BaseVariable subclasses to set values using setDisp method.

        Parameters
        ----------
        d : dict[str, str] | object
            If a dictionary, keys are the indexes of the array variable, values are the values to set.
            If a single value, it is set using the Variable's setDisp method.

        writeEach : bool
            If True, wait for each variable write transaction to complete before setting the next variable.
        modes : list['RW' | 'WO' | 'RO']
            Variable modes to include. Allowed values are ``'RW'``, ``'WO'``, and ``'RO'``.
        incGroups : str or list[str], optional
            Group name or group names to include.
        excGroups : str or list[str], optional
            Group name or group names to exclude.
        keys : list[str], optional
            Keys to include.
            If keys is not none, it should only contain one entry
            and the variable should be a list or array variable

        Returns
        -------
        None
        """

        if keys is not None:

            if len(keys) != 1 or (self.nativeType is not list and self.nativeType is not np.ndarray):
                self._log.error("Entry %s with key %s not found", self.name, keys)

            elif self._mode in modes:
                if keys[0] == '*' or keys[0] == ':':
                    for i in range(self._numValues()):
                        self.setDisp(d, write=writeEach, index=i)
                else:
                    idxSlice = eval(f'[i for i in range(self._numValues())][{keys[0]}]')

                    # Single entry item
                    if ':' not in keys[0]:
                        if isinstance(idxSlice, list):
                            idx = idxSlice[0]
                        else:
                            idx = idxSlice
                        self.setDisp(d, write=writeEach, index=idx)

                    # Multi entry item
                    else:
                        if isinstance(d,str):
                            s = shlex.shlex(" " + d.lstrip('[').rstrip(']') + " ",posix=True)
                            s.whitespace_split=True
                            s.whitespace=','
                            values = [val.strip() for val in s]
                        elif isinstance(d, Iterable):
                            values = list(d)
                        else:
                            values = [d]

                        # A scalar YAML value should broadcast across the
                        # entire selected slice, matching the documented
                        # ``Array[1:3]: value`` semantics.
                        if len(values) == 1 and len(idxSlice) > 1:
                            values *= len(idxSlice)

                        for val,i in zip(values,idxSlice):
                            if isinstance(val, str):
                                val = val.strip()
                            self.setDisp(val, write=writeEach, index=i)
            else:
                self._log.warning(
                    "Skipping set for Entry %s with mode %s. Enabled Modes=%s.",
                    self.name,
                    self._mode,
                    modes,
                )

        # Standard set
        elif self._mode in modes:
            # Array variables can be set with a dict of index/value pairs
            if isinstance(d, dict):
                for k,v in d.items():
                    self.setDisp(v, index=k, write=writeEach)
            else:
                self.setDisp(d,writeEach)
        else:
            self._log.warning(
                "Skipping set for Entry %s with mode %s. Enabled Modes=%s.",
                self.name,
                self._mode,
                modes,
            )

    def _getDict(
        self,
        modes: list[str] = ['RW', 'RO', 'WO'],
        incGroups: str | list[str] | None = None,
        excGroups: str | list[str] | None = None,
        properties: bool = False,
    ) -> Any | None:
        """


        Parameters
        ----------
        modes : list['RW' | 'WO' | 'RO'], optional (default = ['RW', 'RO', 'WO'])
            Variable modes to include. Allowed values are ``'RW'``, ``'WO'``, and ``'RO'``.

        incGroups : str or list[str], optional
            Group name or group names to include.
        excGroups : str or list[str], optional
            Group name or group names to exclude.


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


    def _queueUpdate(self) -> None:
        """ """
        self._root._queueUpdates(self)

    def _doUpdate(self) -> None:
        """ """
        val = VariableValue(self)

        for func in self.__functions:
            func(self.path,val)

        return val

    def _alarmState(self, value: Any) -> tuple[str, str]:
        """


        Parameters
        ----------
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

    def _genDocs(self, file: Any) -> None:
        """

        Parameters
        ----------
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


LocalSetCallback = Callable[[Any, Any, BaseVariable | None, bool | None], Any]
LocalGetCallback = Callable[[Any, BaseVariable | None], Any]
LinkedSetCallback = Callable[[Any, BaseVariable, Any, bool, int, bool, bool], Any]
LinkedGetCallback = Callable[[Any, BaseVariable, bool, int, bool], Any]


class RemoteVariable(BaseVariable,rim.Variable):
    """Remote variable backed by a memory-mapped interface.

    Parameters
    ----------
    name
        Variable name.
    description
        Human-readable description.
    mode
        Access mode: ``RW``, ``RO``, or ``WO``.
    value
        Default value.
    disp
        Display formatter or mapping.
    enum
        Mapping from object values to display strings.
    units
        Engineering units.
    hidden
        If True, add the variable to the ``Hidden`` group.
    groups
        Groups to assign.
    minimum
        Minimum allowed value.
    maximum
        Maximum allowed value.
    lowWarning
        Low warning threshold.
    lowAlarm
        Low alarm threshold.
    highWarning
        High warning threshold.
    highAlarm
        High alarm threshold.
    base
        Base model instance or model factory.
    offset
        Memory offset or list of offsets.
    numValues
        Number of values for array variables.
    valueBits
        Bits per value for array variables.
    valueStride
        Bit stride between values.
    bitSize
        Bit size of the variable.
    bitOffset
        Bit offset of the variable.
    pollInterval
        Polling interval.
    updateNotify
        Enable update notifications.
    overlapEn
        Allow overlapping variables.
    bulkOpEn
        Enable bulk operations.
    verify
        Enable verify on write.
    retryCount
        Retry count for transactions.
    guiGroup
        GUI grouping label.
    **kwargs
        Additional arguments forwarded to ``BaseVariable``.
    """

    PROPS = BaseVariable.PROPS + [
        'address', 'overlapEn', 'offset', 'bitOffset', 'bitSize',
        'verifyEn', 'numValues', 'valueBits', 'valueStride', 'retryCount',
        'varBytes', 'bulkEn']

    def __init__(self, *,
                 name: str,
                 description: str = '',
                 mode: str = 'RW',
                 value: Any = None,
                 disp: Any | None = None,
                 enum: dict[object, str] | None = None,
                 units: str | None = None,
                 hidden: bool = False,
                 groups: list[str] | None = None,
                 minimum: Any | None = None,
                 maximum: Any | None = None,
                 lowWarning: Any | None = None,
                 lowAlarm: Any | None = None,
                 highWarning: Any | None = None,
                 highAlarm: Any | None = None,
                 base: pr.Model | Callable[[int], pr.Model] = pr.UInt,
                 offset: int | list[int],
                 numValues: int = 0,
                 valueBits: int = 0,
                 valueStride: int = 0,
                 bitSize: int | list[int] = 32,
                 bitOffset: int | list[int] = 0,
                 pollInterval: Any = 0,
                 updateNotify: bool = True,
                 overlapEn: bool = False,
                 bulkOpEn: bool = True,
                 verify: bool = True,
                 retryCount: int = 0,
                 guiGroup: str | None = None,
                 **kwargs: Any) -> None:
        """Initialize a remote variable."""

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
    def address(self) -> int:
        """Return the absolute address of the variable."""
        return self._block.address

    @property
    def numValues(self) -> int:
        """Return the configured number of values for array variables."""
        return self._numValues()

    @property
    def valueBits(self) -> int:
        """Return number of valid bits per array value."""
        return self._valueBits()

    @property
    def valueStride(self) -> int:
        """Return bit-stride between adjacent array values."""
        return self._valueStride()

    @property
    def retryCount(self) -> int:
        """Return transaction retry count for this variable."""
        return self._retryCount()

    @pr.expose
    @property
    def varBytes(self) -> int:
        """Return the byte size of the variable."""
        return self._varBytes()

    @pr.expose
    @property
    def offset(self) -> int:
        """Return the memory offset."""
        return self._offset()

    @pr.expose
    @property
    def overlapEn(self) -> bool:
        """Return True if overlap is enabled."""
        return self._overlapEn()

    @pr.expose
    @property
    def bitSize(self) -> int:
        """Return the bit size."""
        return self._bitSize()

    @pr.expose
    @property
    def bitOffset(self) -> int:
        """Return the bit offset."""
        return self._bitOffset()

    @pr.expose
    @property
    def verifyEn(self) -> bool:
        """Return True if verify is enabled."""
        return self._verifyEn()


    ########################
    # Local Properties
    ########################


    @pr.expose
    @property
    def base(self) -> pr.Model:
        """Return the base model or type."""
        return self._base

    @pr.expose
    @property
    def bulkEn(self) -> bool:
        """Return True if bulk operations are enabled."""
        return self._bulkOpEn

    @pr.expose
    def set(
        self,
        value: Any,
        *,
        index: int = -1,
        write: bool = True,
        verify: bool = True,
        check: bool = True,
    ) -> None:
        """
        Set the value and write to hardware if applicable
        Writes to hardware are blocking if check=True, otherwise non-blocking.
        A verify will be performed according to self.verifyEn if verify=True
        A verify will not be performed if verify=False
        An error will result in a logged exception.

        Parameters
        ----------
        value : object
            Value to set.
        index : int, optional (default = -1)
            Optional index for array variables.
        write : bool, optional (default = True)
            If True, perform a write transaction.
        verify : bool, optional (default = True)
            If True, verify after write.
        check : bool, optional (default = True)
            If True, check transaction completion.

        Returns
        -------

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
            self._log.error(
                "Error setting value %r to variable %s with type %s. Exception=%s",
                value,
                self.path,
                self.typeStr,
                e,
            )
            raise e

    @pr.expose
    def post(self, value: Any, *, index: int = -1) -> None:
        """
        Set the value and write to hardware if applicable using a posted write.
        This method does not call through parent.writeBlocks(), but rather
        calls on self._block directly.

        Parameters
        ----------
        value : object
            Value to set.
        index : int, optional (default = -1)
            Optional index for array variables.

        Returns
        -------

        """
        try:

            # Set value to block
            self._set(value,index)

            pr.startTransaction(self._block, type=rim.Post, forceWr=False, checkEach=True, variable=self, index=index)

        except Exception as e:
            pr.logException(self._log,e)
            self._log.error(
                "Error posting value %r to variable %s with type %s",
                value,
                self.path,
                self.typeStr,
            )
            raise e

    @pr.expose
    def get(self, *, index: int = -1, read: bool = True, check: bool = True) -> Any:
        """Return the value, optionally reading from hardware.

        Hardware read is blocking if check=True, otherwise non-blocking.
        An error will result in a logged exception.
        Listeners will be informed of the update.

        Parameters
        ----------
        index : int, optional (default = -1)
            Optional index for array variables.
        read : bool, optional (default = True)
            If True, perform a read transaction.
        check : bool, optional (default = True)
            If True, check transaction completion.
        """
        try:
            if read:
                self._parent.readBlocks(recurse=False, variable=self, index=index)
                if check:
                    self._parent.checkBlocks(recurse=False, variable=self)

            return self._get(index)

        except Exception as e:
            pr.logException(self._log,e)
            self._log.error("Error reading value from variable %s", self.path)
            raise e

    @pr.expose
    def write(self, *, verify: bool = True, check: bool = True) -> None:
        """
        Force a write of the variable.
        Hardware write is blocking if check=True.
        A verify will be performed according to self.verifyEn if verify=True
        A verify will not be performed if verify=False
        An error will result in a logged exception

        Parameters
        ----------
        verify : bool, optional (default = True)
            If True, verify after write.
        check : bool, optional (default = True)
            If True, check transaction completion.

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

    def _parseDispValue(self, sValue: str) -> Any:
        """Parse a string representation of a value into a Python object.


        Parameters
        ----------
        sValue : str
            String representation of the value to parse.


        Returns
        -------

        """
        if self.disp == 'enum':
            return self.revEnum[sValue]
        else:
            return self._base.fromString(sValue)

    def _genDocs(self, file: Any) -> None:
        """

        Parameters
        ----------
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
    """Local variable backed by an in-process value.

    Parameters
    ----------
    name : str
        Variable name.
    value : object, optional
        Default value.
    description : str, optional (default = "")
        Human-readable description.
    mode : str, optional (default = "RW")
        Access mode: ``RW``, ``RO``, or ``WO``.
    disp : object, optional (default = "{}")
        Display formatter or mapping.
    enum : dict, optional
        Mapping from object values to display strings.
    units : str, optional
        Engineering units.
    hidden : bool, optional (default = False)
        If True, add the variable to the ``Hidden`` group.
    groups : list[str], optional
        Groups to assign.
    minimum : object, optional
        Minimum allowed value.
    maximum : object, optional
        Maximum allowed value.
    lowWarning : object, optional
        Low warning threshold.
    lowAlarm : object, optional
        Low alarm threshold.
    highWarning : object, optional
        High warning threshold.
    highAlarm : object, optional
        High alarm threshold.
    localSet : callable, optional
        Setter callback. Expected form:
        ``localSet(value, dev=None, var=None, changed=None)``.
        The callback may accept any subset of these named arguments.
    localGet : callable, optional
        Getter callback. Expected form:
        ``localGet(dev=None, var=None)``.
        The callback may accept any subset of these named arguments.
    pollInterval : object, optional (default = 0)
        Polling interval.
    updateNotify : bool, optional (default = True)
        Enable update notifications.
    typeStr : str, optional (default = "Unknown")
        Type string for display.
    typeCheck : bool, optional (default = True)
        If True, raise an error when later writes change the seeded Python type.
    bulkOpEn : bool, optional (default = True)
        Enable bulk operations.
    guiGroup : str, optional
        GUI grouping label.
    **kwargs : Any
        Additional arguments forwarded to ``BaseVariable``.
    """

    def __init__(self, *,
                 name: str,
                 value: Any = None,
                 description: str = '',
                 mode: str = 'RW',
                 disp: Any = '{}',
                 enum: dict[object, str] | None = None,
                 units: str | None = None,
                 hidden: bool = False,
                 groups: list[str] | None = None,
                 minimum: Any | None = None,
                 maximum: Any | None = None,
                 lowWarning: Any | None = None,
                 lowAlarm: Any | None = None,
                 highWarning: Any | None = None,
                 highAlarm: Any | None = None,
                 localSet: LocalSetCallback | None = None,
                 localGet: LocalGetCallback | None = None,
                 pollInterval: Any = 0,
                 updateNotify: bool = True,
                 typeStr: str = 'Unknown',
                 typeCheck: bool = True,
                 bulkOpEn: bool = True,
                 guiGroup: str | None = None,
                 **kwargs: Any) -> None:
        """Initialize a local variable."""

        if value is None and localGet is None:
            raise VariableError(f'LocalVariable {self.path} without localGet() must specify value= argument in constructor')

        BaseVariable.__init__(self, name=name, description=description,
                              mode=mode, value=value, disp=disp,
                              enum=enum, units=units, hidden=hidden, groups=groups,
                              minimum=minimum, maximum=maximum, typeStr=typeStr,
                              lowWarning=lowWarning, lowAlarm=lowAlarm,
                              highWarning=highWarning, highAlarm=highAlarm,
                              pollInterval=pollInterval,updateNotify=updateNotify, typeCheck=typeCheck, bulkOpEn=bulkOpEn,
                              guiGroup=guiGroup, **kwargs)

        self._block = pr.LocalBlock(variable=self,
                                    localSet=localSet,
                                    localGet=localGet,
                                    minimum=minimum,
                                    maximum=maximum,
                                    value=self._default)

    @pr.expose
    def set(
        self,
        value: Any,
        *,
        index: int = -1,
        write: bool = True,
        verify: bool = True,
        check: bool = True,
    ) -> None:
        """
        Set the value and write to hardware if applicable
        Writes to hardware are blocking. An error will result in a logged exception.

        Parameters
        ----------
        value : object
            Value to set.
        index : int, optional (default = -1)
            Optional index for array variables.
        write : bool, optional (default = True)
            If True, perform a write transaction.
        verify : bool, optional (default = True)
            If True, verify after write.
        check : bool, optional (default = True)
            If True, check transaction completion.

        Returns
        -------

        """
        self._log.debug("%s.set(%r)", self, value)

        try:

            # Set value to block
            self._block.set(self, value, index)

            if write:
                self._block._checkTransaction()

        except Exception as e:
            pr.logException(self._log,e)
            self._log.error(
                "Error setting value %r to variable %s with type %s. Exception=%s",
                value,
                self.path,
                self.typeStr,
                e,
            )
            raise e

    @pr.expose
    def post(self, value: Any, *, index: int = -1) -> None:
        """
        Set the value and write to hardware if applicable using a posted write.
        This method does not call through parent.writeBlocks(), but rather
        calls on self._block directly.

        Parameters
        ----------
        value : object
            Value to set.
        index : int, optional (default = -1)
            Optional index for array variables.

        Returns
        -------

        """
        self._log.debug("%s.post(%r)", self, value)

        try:
            self._block.set(self, value, index)
            self._block._checkTransaction()

        except Exception as e:
            pr.logException(self._log,e)
            self._log.error(
                "Error posting value %r to variable %s with type %s",
                value,
                self.path,
                self.typeStr,
            )
            raise e

    @pr.expose
    def get(self, *, index: int = -1, read: bool = True, check: bool = True) -> Any:
        """


        Parameters
        ----------
        index : int, optional (default = -1)
            Optional index for array variables.
        read : bool, optional (default = True)
            If True, perform a read transaction.
        check : bool, optional (default = True)
            If True, check transaction completion.

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
            self._log.error("Error reading value from variable %s", self.path)
            raise e

    def __get__(self) -> Any:
        """Return the current local-variable value without hardware read."""
        return self.get(read=False)

    def __iadd__(self, other: Any) -> LocalVariable:
        """In-place add on the local variable value."""
        self._block._iadd(other)
        return self

    def __isub__(self, other: Any) -> LocalVariable:
        """In-place subtract on the local variable value."""
        self._block._isub(other)
        return self

    def __imul__(self, other: Any) -> LocalVariable:
        """In-place multiply on the local variable value."""
        self._block._imul(other)
        return self

    def __imatmul__(self, other: Any) -> LocalVariable:
        """In-place matrix-multiply on the local variable value."""
        self._block._imatmul(other)
        return self

    def __itruediv__(self, other: Any) -> LocalVariable:
        """In-place true-division on the local variable value."""
        self._block._itruediv(other)
        return self

    def __ifloordiv__(self, other: Any) -> LocalVariable:
        """In-place floor-division on the local variable value."""
        self._block._ifloordiv(other)
        return self

    def __imod__(self, other: Any) -> LocalVariable:
        """In-place modulo on the local variable value."""
        self._block._imod(other)
        return self

    def __ipow__(self, other: Any) -> LocalVariable:
        """In-place exponentiation on the local variable value."""
        self._block._ipow(other)
        return self

    def __ilshift__(self, other: Any) -> LocalVariable:
        """In-place left-shift on the local variable value."""
        self._block._ilshift(other)
        return self

    def __irshift__(self, other: Any) -> LocalVariable:
        """In-place right-shift on the local variable value."""
        self._block._irshift(other)
        return self

    def __iand__(self, other: Any) -> LocalVariable:
        """In-place bitwise-and on the local variable value."""
        self._block._iand(other)
        return self

    def __ixor__(self, other: Any) -> LocalVariable:
        """In-place bitwise-xor on the local variable value."""
        self._block._ixor(other)
        return self

    def __ior__(self, other: Any) -> LocalVariable:
        """In-place bitwise-or on the local variable value."""
        self._block._ior(other)
        return self

class LinkVariable(BaseVariable):
    """Variable linked to another variable or custom functions.

    Parameters
    ----------
    name : str
        Variable name.
    variable : object, optional
        Optional variable to link to.
        This is a useful shortcut for linking to a variable without having to declare dependencies.
    dependencies : iterable, optional
        List of variables that this variable depends on.
    linkedSet : callable, optional
        Setter callback. Expected keyword arguments are
        ``dev, var, value, write, index, verify, check``.
        These match the parameters of BaseVariable.set().
        The callback may accept any subset of these names.
        Only value is required.
        If not provided, will infer mode = 'RO'.
    linkedGet : callable, optional
        Getter callback. Expected keyword arguments are
        ``dev, var, read, index, check``.
        These match the parameters of BaseVariable.get().
        The callback may accept any subset of these names.
    minimum : object, optional
        Minimum allowed value.
    maximum : object, optional
        Maximum allowed value.
    **kwargs : Any
        Additional arguments forwarded to ``BaseVariable``.
    """

    def __init__(self, *,
                 name: str,
                 variable: BaseVariable | None = None,
                 dependencies: Iterable[BaseVariable] | None = None,
                 linkedSet: LinkedSetCallback | None = None,
                 linkedGet: LinkedGetCallback | None = None,
                 minimum: Any | None = None,
                 maximum: Any | None = None,
                 **kwargs: Any) -> None: # Args passed to BaseVariable
        """Initialize a link variable."""

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

    def __getitem__(self, key: Any) -> Any:
        """Return dependency by index/key from ``dependencies``."""
        # Allow dependencies to be accessed as indices of self
        return self.dependencies[key]

    @pr.expose
    def set(
        self,
        value: Any,
        *,
        write: bool = True,
        index: int = -1,
        verify: bool = True,
        check: bool = True,
    ) -> None:
        """


        Parameters
        ----------
        value : object
            Value to set.
        write : bool, optional (default = True)
            If True, perform a write transaction.
        index : int, optional (default = -1)
            Optional index for array variables.
        verify : bool, optional (default = True)
            If True, verify after write.
        check : bool, optional (default = True)
            If True, check transaction completion.

        Returns
        -------

        """
        try:
            self._linkedSetWrap(function=self._linkedSet, dev=self.parent, var=self, value=value, write=write, index=index, verify=verify, check=check)
        except Exception as e:
            pr.logException(self._log,e)
            self._log.error("Error setting link variable %s", self.path)
            raise e

    @pr.expose
    def get(self, read: bool = True, index: int = -1, check: bool = True) -> Any:
        """


        Parameters
        ----------
        read : bool, optional (default = True)
            If True, perform a read transaction.
        index : int, optional (default = -1)
            Optional index for array variables.
        check : bool, optional (default = True)
            If True, check transaction completion.

        Returns
        -------

        """
        try:
            return self._linkedGetWrap(function=self._linkedGet, dev=self.parent, var=self, read=read, index=index, check=check)
        except Exception as e:
            pr.logException(self._log,e)
            self._log.error("Error getting link variable %s", self.path)
            raise e


    def __getBlocks(self) -> list[pr.Block]:
        """Collect dependency blocks recursively for this link variable."""
        b = []
        for d in self.dependencies:
            if isinstance(d, LinkVariable):
                b.extend(d.__getBlocks())
            elif hasattr(d, '_block') and d._block is not None:
                b.append(d._block)

        return b

    def _finishInit(self) -> None:
        """Resolve dependency blocks after tree attachment."""
        super()._finishInit()
        self.__depBlocks = self.__getBlocks()

    @property
    def depBlocks(self) -> list[pr.Block]:
        """Return a list of blocks that this LinkVariable depends on."""
        return self.__depBlocks

    @pr.expose
    @property
    def pollInterval(self) -> float:
        """Return the minimum non-zero poll interval across dependencies."""
        depIntervals = [dep.pollInterval for dep in self.dependencies if dep.pollInterval > 0]
        if len(depIntervals) == 0:
            return 0
        else:
            return min(depIntervals)
