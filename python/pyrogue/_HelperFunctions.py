#-----------------------------------------------------------------------------
# Company    : SLAC National Accelerator Laboratory
#-----------------------------------------------------------------------------
#  Description:
#
#-----------------------------------------------------------------------------
# This file is part of the rogue software platform. It is subject to
# the license terms in the LICENSE.txt file found in the top-level directory
# of this distribution and at:
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
# No part of the rogue software platform, including this file, may be
# copied, modified, propagated, or distributed except according to the terms
# contained in the LICENSE.txt file.
#-----------------------------------------------------------------------------
import sys
import os
import signal
import yaml
import time
import zipfile
import inspect

import pyrogue as pr
import rogue.interfaces.stream
import rogue.interfaces.memory

from collections import OrderedDict as odict


def addLibraryPath(path):
    """
    Append the past string or list of strings to the python library path.
    Passed strings can either be relative: ../path/to/library
    or absolute: /path/to/library

    Parameters
    ----------
    path :


    Returns
    -------

    """
    if len(sys.argv) == 0:
        base = os.path.dirname(os.path.realpath(__file__))

    else:
        base = os.path.dirname(sys.argv[0])

    # If script was not started with ./       # If script was not started with ./
    if base == '':
        base = '.'

    # If script was not started with ./
    if base == '':
        base = '.'

    # Allow either a single string or list to be passed
    if not isinstance(path,list):
        path = [path]

    for p in path:

        # Full path
        if p[0] == '/':
            np = p

        # Relative path
        else:
            np = base + '/' + p

        # Verify directory or archive exists and is readable
        if '.zip/' in np:
            # zipimport does not support compression: https://bugs.python.org/issue21751
            tst = np[:np.find('.zip/')+4]
        else:
            tst = np

        if not os.access(tst,os.R_OK):
            raise Exception("Library path {} does not exist or is not readable".format(tst))
        sys.path.insert(0,np)


def waitCntrlC():
    """Helper Function To Wait For Cntrl-c"""

    class monitorSignal(object):
        """ """

        def __init__(self):
            """ """
            self.runEnable = True

        def receiveSignal(self,*args):
            """


            Parameters
            ----------
            *args :


            Returns
            -------

            """
            print("Got SIGTERM, exiting")
            self.runEnable = False

    mon = monitorSignal()
    signal.signal(signal.SIGTERM, mon.receiveSignal)

    print(f"Running. Hit cntrl-c or send SIGTERM to {os.getpid()} to exit.")
    try:
        while mon.runEnable:
            time.sleep(0.5)
    except KeyboardInterrupt:
        print("Got cntrl-c, exiting")
        return


def streamConnect(source, dest):
    """
    Attach the passed dest object to the source a stream.
    Connect source and destination stream devices.
    source is either a stream master sub class or implements
    the _getStreamMaster call to return a contained master.
    Similarly dest is either a stream slave sub class or implements
    the _getStreamSlave call to return a contained slave.

    Parameters
    ----------
    source :

    dest :


    Returns
    -------

    """

    # Is object a native master or wrapped?
    if isinstance(source,rogue.interfaces.stream.Master):
        master = source
    else:
        master = source._getStreamMaster()

    # Is object a native slave or wrapped?
    if isinstance(dest,rogue.interfaces.stream.Slave):
        slave = dest
    else:
        slave = dest._getStreamSlave()

    master._addSlave(slave)

def streamConnectBiDir(deviceA, deviceB):
    """
    Attach the passed dest object to the source a stream.
    Connect source and destination stream devices.
    source is either a stream master sub class or implements
    the _getStreamMaster call to return a contained master.
    Similarly dest is either a stream slave sub class or implements
    the _getStreamSlave call to return a contained slave.

    Parameters
    ----------
    deviceA :

    deviceB :


    Returns
    -------

    """

    """
    Connect deviceA and deviceB as end points to a
    bi-directional stream. This method calls the
    streamConnect method to perform the actual connection.
    See streamConnect description for object requirements.
    """

    streamConnect(deviceA,deviceB)
    streamConnect(deviceB,deviceA)


def busConnect(source,dest):
    """
    Connect the source object to the dest object for
    memory accesses.
    source is either a memory master sub class or implements
    the _getMemoryMaster call to return a contained master.
    Similarly dest is either a memory slave sub class or implements
    the _getMemorySlave call to return a contained slave.

    Parameters
    ----------
    source :

    dest :


    Returns
    -------

    """

    # Is object a native master or wrapped?
    if isinstance(source,rogue.interfaces.memory.Master):
        master = source
    else:
        master = source._getMemoryMaster()

    # Is object a native slave or wrapped?
    if isinstance(dest,rogue.interfaces.memory.Slave):
        slave = dest
    else:
        slave = dest._getMemorySlave()

    master._setSlave(slave)


def yamlToData(stream='',fName=None):
    """
    Load yaml to data structure.
    A yaml string or file path may be passed.

    Parameters
    ----------
    stream :
         (Default value = '')
    fName :
         (Default value = None)

    Returns
    -------

    """

    log = pr.logInit(name='yamlToData')

    class PyrogueLoader(yaml.Loader):
        """ """
        pass

    def include_mapping(loader, node):
        """


        Parameters
        ----------
        loader :

        node :


        Returns
        -------

        """
        rel = loader.construct_scalar(node)

        # Filename starts with absolute path
        if rel[0] == '/':
            filename = rel

        # Filename is relative and we know the base path
        elif fName is not None:
            filename = os.path.join(os.path.dirname(fName), rel)

        # File is relative without a base path, assume cwd (Current working directory)
        else:
            filename = node

        # Recursive call, flatten relative jumps
        return yamlToData(fName=os.path.abspath(filename))

    def construct_mapping(loader, node):
        """


        Parameters
        ----------
        loader :

        node :


        Returns
        -------

        """
        loader.flatten_mapping(node)
        return odict(loader.construct_pairs(node))

    PyrogueLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,construct_mapping)
    PyrogueLoader.add_constructor('!include',include_mapping)

    # Use passed string
    if fName is None:
        return yaml.load(stream,Loader=PyrogueLoader)

    # Main or sub-file is in a zip
    elif '.zip' in fName:
        base = fName.split('.zip')[0] + '.zip'
        sub = fName.split('.zip')[1][1:] # Strip leading '/'

        log.debug("loading {} from zipfile {}".format(sub,base))

        with zipfile.ZipFile(base, 'r', compression=zipfile.ZIP_LZMA) as myzip:
            with myzip.open(sub) as myfile:
                return yaml.load(myfile.read(),Loader=PyrogueLoader)

    # Non zip file
    else:
        log.debug("loading {}".format(fName))
        with open(fName,'r') as f:
            return yaml.load(f.read(),Loader=PyrogueLoader)


def dataToYaml(data):
    """
    Convert data structure to yaml

    Parameters
    ----------
    data :


    Returns
    -------

    """

    class PyrogueDumper(yaml.Dumper):
        """ """
        pass

    def _var_representer(dumper, data):
        """


        Parameters
        ----------
        dumper :

        data :


        Returns
        -------

        """
        if isinstance(data.value, bool):
            enc = 'tag:yaml.org,2002:bool'
        elif data.enum is not None:
            enc = 'tag:yaml.org,2002:str'
        elif isinstance(data.value, int):
            enc = 'tag:yaml.org,2002:int'
        elif isinstance(data.value, float):
            enc = 'tag:yaml.org,2002:float'
        else:
            enc = 'tag:yaml.org,2002:str'

        if data.valueDisp is None:
            return dumper.represent_scalar('tag:yaml.org,2002:null',u'null')
        else:
            return dumper.represent_scalar(enc, data.valueDisp)

    def _dict_representer(dumper, data):
        """


        Parameters
        ----------
        dumper :

        data :


        Returns
        -------

        """
        return dumper.represent_mapping(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, data.items())

    PyrogueDumper.add_representer(pr.VariableValue, _var_representer)
    PyrogueDumper.add_representer(odict, _dict_representer)

    return yaml.dump(data, Dumper=PyrogueDumper, default_flow_style=False)


def keyValueUpdate(old, key, value):
    """


    Parameters
    ----------
    old :

    key :

    value :


    Returns
    -------

    """
    d = old
    parts = key.split('.')
    for part in parts[:-1]:
        if part not in d:
            d[part] = {}
        d = d.get(part)
    d[parts[-1]] = value


def dictUpdate(old, new):
    """


    Parameters
    ----------
    old :

    new :


    Returns
    -------

    """
    for k,v in new.items():
        if '.' in k:
            keyValueUpdate(old, k, v)
        elif k in old:
            old[k].update(v)
        else:
            old[k] = v


def yamlUpdate(old, new):
    """


    Parameters
    ----------
    old :

    new :


    Returns
    -------

    """
    dictUpdate(old, pr.yamlToData(new))


def recreate_OrderedDict(name, values):
    """


    Parameters
    ----------
    name :

    values :


    Returns
    -------

    """
    return odict(values['items'])

# Creation function wrapper for methods with variable args
def functionWrapper(function, callArgs):
    """


    Parameters
    ----------
    function :

    callArgs :


    Returns
    -------

    """

    if function is None:
        return eval("lambda " + ", ".join(['function'] + callArgs) + ": None")

    # Find the arg overlaps
    try:
        # Function args
        fargs = inspect.getfullargspec(function).args + inspect.getfullargspec(function).kwonlyargs

        # Build overlapping arg list
        args = [f'{k}={k}' for k in fargs if k != 'self' and k in callArgs]

    # handle c++ functions, no args supported for now
    except Exception:
        args = []

    # Build the function
    ls = "lambda " + ", ".join(['function'] + callArgs) + ": function(" + ", ".join(args) + ")"
    #print("Creating Function: " + ls)
    return eval(ls)


def genDocTableHeader(fields, indent, width):
    """


    Parameters
    ----------
    fields :

    indent :

    width :


    Returns
    -------

    """
    r = ' ' * indent + '+'

    for _ in range(len(fields)):
        r += '-' * width + '+'

    r += '\n' + ' ' * indent + '|'

    for f in fields:
        r += f + ' '
        r += ' ' * (width-len(f)-1) + '|'

    r += '\n' + ' ' * indent + '+'

    for _ in range(len(fields)):
        r += '=' * width + '+'

    return r

def genDocTableRow(fields, indent, width):
    """


    Parameters
    ----------
    fields :

    indent :

    width :


    Returns
    -------

    """
    r = ' ' * indent + '|'

    for f in fields:
        r += f + ' '
        r += ' ' * (width-len(f)-1) + '|'

    r += '\n' + ' ' * indent + '+'

    for _ in range(len(fields)):
        r += '-' * width + '+'

    return r

def genDocDesc(desc, indent):
    """


    Parameters
    ----------
    desc :

    indent :


    Returns
    -------

    """
    r = ''

    for f in desc.split('.'):
        f = f.strip()
        if len(f) > 0:
            r += ' ' * indent
            r += '| ' + f + '.\n'

    return r
