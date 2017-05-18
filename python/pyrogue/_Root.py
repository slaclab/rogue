#!/usr/bin/env python
#-----------------------------------------------------------------------------
# Title      : PyRogue base module - Root Class
#-----------------------------------------------------------------------------
# File       : pyrogue/_Root.py
# Created    : 2017-05-16
#-----------------------------------------------------------------------------
# This file is part of the rogue software platform. It is subject to 
# the license terms in the LICENSE.txt file found in the top-level directory 
# of this distribution and at: 
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html. 
# No part of the rogue software platform, including this file, may be 
# copied, modified, propagated, or distributed except according to the terms 
# contained in the LICENSE.txt file.
#-----------------------------------------------------------------------------
import rogue.interfaces.memory
import yaml
import threading
from collections import OrderedDict as odict
import logging
import pyrogue as pr
import functools as ft

class RootLogHandler(logging.Handler):
    """ Class to listen to log entries and add them to syslog variable"""
    def __init__(self,root):
        logging.Handler.__init__(self)
        self._root = root

    def emit(self,record):
        with self._root._sysLogLock:
            val = self._root.systemLog.value()
            val += (self.format(record) + '\n')
            self._root.systemLog.set(write=False,value=val)
        self._root.systemLog._updated() # Update outside of lock

class Root(rogue.interfaces.stream.Master,pr.Device):
    """
    Class which serves as the root of a tree of nodes.
    The root is the interface point for tree level access and updats.
    The root is a stream master which generates frames containing tree
    configuration and status values. This allows confiuration and status
    to be stored in data files.
    """

    def __init__(self, name, description, pollEn=True, readBeforeConfig=False, **dump):
        """Init the node with passed attributes"""

        rogue.interfaces.stream.Master.__init__(self)

        # Create log listener to add to systemlog variable
        formatter = logging.Formatter("%(msg)s")
        handler = RootLogHandler(self)
        handler.setLevel(logging.ERROR)
        handler.setFormatter(formatter)
        self._logger = logging.getLogger('pyrogue')
        self._logger.addHandler(handler)

        # Trigger read from hardware before loading config file
        self._readBeforeConfig = readBeforeConfig

        # Keep of list of errors, exposed as a variable
        self._sysLogLock = threading.Lock()

        # Polling
        if pollEn:
            self._pollQueue = pr.PollQueue(self)
        else:
            self._pollQueue = None

        # Variable update list
        self._updatedDict = None
        self._updatedList = None
        self._updatedLock = threading.Lock()

        # Variable update listener
        self._varListeners = []

        # Init after _updatedLock exists
        pr.Device.__init__(self, name=name, description=description, classType='root')

        # Variables
        self.add(pr.LocalVariable(name='systemLog', value='', mode='RO', hidden=True,
            description='String containing newline seperated system logic entries'))


    def stop(self):
        """Stop the polling thread. Must be called for clean exit."""
        if self._pollQueue:
            self._pollQueue.stop()

    def addVarListener(self,func,form='dual'):
        """
        Add a variable update listener function.
        Form = 'dual,'dict','yaml','list'
        The passed function depends on form
            dual: func(yaml,dict)  # Yaml and dictionary formats
            dict: func(dict)       # Dictionary only
            yaml: func(yaml)       # Yaml only
            list: func(list)       # List of updated elements
        """
        self._varListeners.append({'func':func,'form':form})

    def getYamlStructure(self):
        """Get structure as a yaml string"""
        return dictToYaml({self.name:self._getStructure()},default_flow_style=False)

    def getYamlVariables(self,readFirst,modes=['RW']):
        """
        Get current values as a yaml dictionary.
        modes is a list of variable modes to include.
        If readFirst=True a full read from hardware is performed.
        """
        ret = None

        if readFirst: self._read()
        try:
            ret = dictToYaml({self.name:self._getVariables(modes)},default_flow_style=False)
        except Exception as e:
            self._log.error(e)

        return ret

    def setOrExecYaml(self,yml,writeEach,modes=['RW']):
        """
        Set variable values or execute commands from a dictionary.
        modes is a list of variable modes to act on.
        writeEach is set to true if accessing a single variable at a time.
        Writes will be performed as each variable is updated. If set to 
        false a bulk write will be performed after all of the variable updates
        are completed. Bulk writes provide better performance when updating a large
        quanitty of variables.
        """
        d = yamlToDict(yml)

        self._initUpdatedVars()

        for key, value in d.items():
            if key == self.name:
                self._setOrExec(value,writeEach,modes)

        self._doneUpdatedVars()

        if not writeEach: self._write()

    @ft.lru_cache(maxsize=None)
    def getNodeByPath(self,path):
        if '.' in path:
            npath = path[path.find('.')+1:]
            return self._walkPath(npath)
        elif path == self.name:
            return self
        else:
            return None

    def setOrExecPath(self,path,value):
        """
        Set variable values or execute commands from a path
        Pass the variable or command path and associated value or arg.
        """
        obj = getNodeByPath(path)

        # Execute if command
        if isinstance(obj,pr.BaseCommand):
            obj(value)

        # Set value if variable with enabled mode
        elif isinstance(obj,pr.BaseVariable):
            obj.set(value)

    def setTimeout(self,timeout):
        """
        Set timeout value on all devices & blocks
        """
        for key,value in self._nodes.items():
            if isinstance(value,pr.Device):
                value._setTimeout(timeout)

    def _updateVarListeners(self, yml, d, l):
        """Send update to listeners"""
        for tar in self._varListeners:
            if   tar['form'] == 'list': tar['func'](l)
            elif tar['form'] == 'dual': tar['func'](yml,d)
            elif tar['form'] == 'dict': tar['func'](d)
            elif tar['form'] == 'yaml': tar['func'](yml)

    def _streamYaml(self,yml):
        """
        Generate a frame containing the passed yaml string.
        """
        frame = self._reqFrame(len(yml),True,0)
        b = bytearray(yml,'utf-8')
        frame.write(b,0)
        self._sendFrame(frame)

    def _streamYamlVariables(self,modes=['RW','RO']):
        """
        Generate a frame containing all variables values in yaml format.
        A hardware read is not generated before the frame is generated.
        Vlist can contain an optional list of variale paths to include in the
        stream. If this list is not NULL only these variables will be included.
        """
        self._streamYaml(self.getYamlVariables(False,modes))

    def _initUpdatedVars(self):
        """Initialize the update tracking log before a bulk variable update"""
        with self._updatedLock:
            self._updatedDict = odict()
            self._updatedList = []

    def _doneUpdatedVars(self):
        """Stream the results of a bulk variable update and update listeners"""
        yml = ''
        d   = None
        l   = []
        with self._updatedLock:
            if self._updatedDict:
                d = self._updatedDict
                l = self._updatedList
                yml = dictToYaml(self._updatedDict,default_flow_style=False)
                self._updatedDict = None
                self._updatedList = None

        if d is not None:
            self._updateVarListeners(yml,d,l)
            self._streamYaml(yml)

    @pr.command(order=7, name='writeAll', description='Write all values to the hardware')
    def _write(self,dev=None,cmd=None,arg=None):
        """Write all blocks"""
        self._log.info("Start root write")
        try:
            self._backgroundTransaction(rogue.interfaces.memory.Write)
            self._log.info("Verify root read")
            self._backgroundTransaction(rogue.interfaces.memory.Verify)
            self._log.info("Check root read")
            self._checkTransaction(update=False)
        except Exception as e:
            self._log.error(e)
        self._log.info("Done root write")

    @pr.command(order=6, name="readAll", description='Read all values from the hardware')
    def _read(self,dev=None,cmd=None,arg=None):
        """Read all blocks"""
        self._log.info("Start root read")
        self._initUpdatedVars()
        try:
            self._backgroundTransaction(rogue.interfaces.memory.Read)
            self._log.info("Check root read")
            self._checkTransaction(update=True)
        except Exception as e:
            self._log.error(e)
        self._doneUpdatedVars()
        self._log.info("Done root read")

    @pr.command(order=0, name='writeConfig', base='string', description='Write configuration to passed filename in YAML format')
    def _writeConfig(self,dev,cmd,arg):
        """Write YAML configuration to a file. Called from command"""
        try:
            with open(arg,'w') as f:
                f.write(self.getYamlVariables(True,modes=['RW']))
        except Exception as e:
            self._log.error(e)

    @pr.command(order=1, name='readConfig', base='string', description='Read configuration from passed filename in YAML format')
    def _readConfig(self,dev,cmd,arg):
        """Read YAML configuration from a file. Called from command"""
        if self._readBeforeConfig: 
            self._read()
        try:
            with open(arg,'r') as f:
                self.setOrExecYaml(f.read(),False,['RW'])
        except Exception as e:
            self._log.error(e)

    @pr.command(order=3, name='softReset', description='Generate a soft reset to each device in the tree')
    def _softReset(self,dev,cmd,arg):
        """Generate a soft reset on all devices"""
        self._devReset('soft')

    @pr.command(order=2, name='hardReset', description='Generate a hard reset to each device in the tree')
    def _hardReset(self,dev,cmd,arg):
        """Generate a hard reset on all devices"""
        self._devReset('hard')
        self._clearLog(dev,cmd,arg)

    @pr.command(order=4, name='countReset', description='Generate a count reset to each device in the tree')
    def _countReset(self,dev,cmd,arg):
        """Generate a count reset on all devices"""
        self._devReset('count')

    @pr.command(order=5, name='clearLog', description='Clear the message log cntained in the systemLog variable')
    def _clearLog(self,dev,cmd,arg):
        """Clear the system log"""
        with self._sysLogLock:
            self.systemLog.set(value='',write=False)
        self.systemLog._updated()

    def _varUpdated(self,var,value):
        """ Log updated variables"""
        yml = None
        l   = []

        with self._updatedLock:

            # Log is active add to log
            if self._updatedDict is not None:
                addPathToDict(self._updatedDict,var.path,value)
                self._updatedList.append(var)

            # Otherwise act directly
            else:
                d = {}
                l = [var]
                addPathToDict(d,var.path,value)
                yml = dictToYaml(d,default_flow_style=False)

        if yml is not None:
            self._streamYaml(yml)
            self._updateVarListeners(yml,d,l)


def addPathToDict(d, path, value):
    """Helper function to add a path/value pair to a dictionary tree"""
    npath = path
    sd = d

    # Transit through levels
    while '.' in npath:
        base  = npath[:npath.find('.')]
        npath = npath[npath.find('.')+1:]

        if base in sd:
           sd = sd[base]
        else:
           sd[base] = odict()
           sd = sd[base]

    # Add final node
    sd[npath] = value


def treeFromYaml(yml,setFunction,cmdFunction):
    """
    Create structure from yaml.
    """
    d = yamlToDict(yml)
    root = None

    for key, value in d.items():
        root = Root(pollEn=False,**value)
        root._addStructure(value,setFunction,cmdFunction)

    return root


def yamlToDict(stream, Loader=yaml.Loader, object_pairs_hook=odict):
    """Load yaml to ordered dictionary"""
    class OrderedLoader(Loader):
        pass
    def construct_mapping(loader, node):
        loader.flatten_mapping(node)
        return object_pairs_hook(loader.construct_pairs(node))
    OrderedLoader.add_constructor(
        yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
        construct_mapping)
    return yaml.load(stream, OrderedLoader)


def dictToYaml(data, stream=None, Dumper=yaml.Dumper, **kwds):
    """Convert ordered dictionary to yaml"""
    class OrderedDumper(Dumper):
        pass
    def _dict_representer(dumper, data):
        return dumper.represent_mapping(
            yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,data.items())
        OrderedDumper.add_representer(odict, _dict_representer)
    try:
        ret = yaml.dump(data, stream, OrderedDumper, **kwds)
    except Exception as e:
        print("Error: {} dict {}".format(e,data))
        return None
    return ret

