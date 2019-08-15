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

MIN_PYTHON = (3,6)
if sys.version_info < MIN_PYTHON:
    raise Exception("Python %s.%s or later is required.\n" % MIN_PYTHON)

from pyrogue._Node      import *
from pyrogue._Block     import *
from pyrogue._Model     import *
from pyrogue._Variable  import *
from pyrogue._Command   import *
from pyrogue._Device    import *
from pyrogue._Memory    import *
from pyrogue._Root      import *
from pyrogue._PollQueue import *
from pyrogue._Virtual   import *
from pyrogue._Process   import *
from pyrogue._DataWriter import *
from pyrogue._RunControl import *

def addLibraryPath(path):
    """
    Append the past string or list of strings to the python library path.
    Passed strings can either be relative: ../path/to/library
    or absolute: /path/to/library
    """
    base = os.path.dirname(sys.argv[0])

    # If script was not started with ./
    if base == '': base = '.'

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
        
        # Verify directory exists and is readable
        if not os.access(np,os.R_OK):
            raise Exception("Library path {} does not exist or is not readable".format(np))
        sys.path.append(np)


def streamConnect(source, dest):
    """
    Attach the passed dest object to the source a stream.
    Connect source and destination stream devices.
    source is either a stream master sub class or implements
    the _getStreamMaster call to return a contained master.
    Similiarly dest is either a stream slave sub class or implements
    the _getStreamSlave call to return a contained slave.
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

    master._setSlave(slave)


def streamTap(source, tap):
    """
    Attach the passed dest object to the source for a streams
    as a secondary destination.
    Connect source and destination stream devices.
    source is either a stream master sub class or implements
    the _getStreamMaster call to return a contained master.
    Similiarly dest is either a stream slave sub class or implements
    the _getStreamSlave call to return a contained slave.
    """

    # Is object a native master or wrapped?
    if isinstance(source,rogue.interfaces.stream.Master):
        master = source
    else:
        master = source._getStreamMaster()

    # Is object a native slave or wrapped?
    if isinstance(tap,rogue.interfaces.stream.Slave):
        slave = tap
    else:
        slave = tap._getStreamSlave()

    master._addSlave(slave)


def streamConnectBiDir(deviceA, deviceB):
    """
    Attach the passed dest object to the source a stream.
    Connect source and destination stream devices.
    source is either a stream master sub class or implements
    the _getStreamMaster call to return a contained master.
    Similiarly dest is either a stream slave sub class or implements
    the _getStreamSlave call to return a contained slave.
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
    Similiarly dest is either a memory slave sub class or implements
    the _getMemorySlave call to return a contained slave.
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


# Add __version__ attribute with the module version number
__version__ = rogue.Version.pythonVersion()

