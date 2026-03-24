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
from __future__ import annotations

import sys
import os
import signal
import yaml
import time
import zipfile
import inspect
from typing import Any, Callable, Mapping, MutableMapping, Sequence

import pyrogue as pr
import rogue.interfaces.stream as ris
import rogue.interfaces.memory as rim

from collections import OrderedDict as odict


def addLibraryPath(path: str | list[str]) -> None:
    """
    Append one or more paths to ``sys.path``.

    Parameters
    ----------
    path : str or list[str]
        Path string or list of path strings to append. Each path may be
        absolute (for example ``/path/to/library``) or relative to the
        calling script location (for example ``../path/to/library``).

    Raises
    ------
    Exception
        Raised when a path does not exist or is not readable.
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


def waitCntrlC() -> None:
    """
    Block until ``SIGTERM`` or keyboard interrupt is received.
    """

    class monitorSignal(object):
        """ """

        def __init__(self) -> None:
            """Initialize signal-monitor state."""
            self.runEnable = True

        def receiveSignal(self, *args: Any) -> None:
            """Handle SIGTERM by stopping the wait loop."""
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


def streamConnect(source: ris.Master, dest: ris.Slave) -> None:
    """
    Connect a stream source object to a stream destination object.

    Parameters
    ----------
    source : ris.Master
        Stream master instance or wrapper object implementing
        ``_getStreamMaster()``.
    dest : ris.Slave
        Stream slave instance or wrapper object implementing
        ``_getStreamSlave()``.
    """

    # Is object a native master or wrapped?
    if isinstance(source, ris.Master):
        master = source
    else:
        master = source._getStreamMaster()

    # Is object a native slave or wrapped?
    if isinstance(dest, ris.Slave):
        slave = dest
    else:
        slave = dest._getStreamSlave()

    master._addSlave(slave)

def streamConnectBiDir(deviceA: Any, deviceB: Any) -> None:
    """
    Connect two devices as bi-directional stream endpoints.

    Parameters
    ----------
    deviceA : object
        First device endpoint.
    deviceB : object
        Second device endpoint.
    """

    streamConnect(deviceA,deviceB)
    streamConnect(deviceB,deviceA)


def busConnect(source: rim.Master, dest: rim.Slave) -> None:
    """
    Connect a memory source object to a memory destination object.

    Parameters
    ----------
    source : rim.Master
        Memory master instance or wrapper object implementing
        ``_getMemoryMaster()``.
    dest : rim.Slave
        Memory slave instance or wrapper object implementing
        ``_getMemorySlave()``.
    """

    # Is object a native master or wrapped?
    if isinstance(source,rim.Master):
        master = source
    else:
        master = source._getMemoryMaster()

    # Is object a native slave or wrapped?
    if isinstance(dest,rim.Slave):
        slave = dest
    else:
        slave = dest._getMemorySlave()

    master._setSlave(slave)


def yamlToData(stream: str = '', fName: str | None = None) -> Any:
    """
    Parse YAML content into a Python data structure.

    Parameters
    ----------
    stream : str, optional (default = '')
        YAML content as a string.
    fName : str, optional
        YAML file path. If provided, file content is loaded instead of
        ``stream``. Zip archive paths are supported.

    Returns
    -------
    object
        Parsed YAML data.
    """

    log = pr.logInit(name='yamlToData')

    class PyrogueLoader(yaml.Loader):
        pass

    def include_mapping(loader: yaml.Loader, node: Any) -> Any:
        """Resolve and load a ``!include`` YAML reference."""
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

    def construct_mapping(loader: yaml.Loader, node: Any) -> odict:
        """Construct mappings as ``OrderedDict`` to preserve key order."""
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


def dataToYaml(data: Any) -> str:
    """
    Convert a Python data structure to YAML text.

    Parameters
    ----------
    data : object
        Data structure to serialize.

    Returns
    -------
    str
        YAML serialized output.
    """

    class PyrogueDumper(yaml.Dumper):
        pass

    def _var_representer(dumper: yaml.Dumper, data: pr.VariableValue) -> Any:
        """Represent ``VariableValue`` using display formatting and YAML typing."""
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

    def _dict_representer(dumper: yaml.Dumper, data: odict) -> Any:
        """Represent ``OrderedDict`` values while preserving key order."""
        return dumper.represent_mapping(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, data.items())

    PyrogueDumper.add_representer(pr.VariableValue, _var_representer)
    PyrogueDumper.add_representer(odict, _dict_representer)

    return yaml.dump(data, Dumper=PyrogueDumper, default_flow_style=False)


def keyValueUpdate(old: MutableMapping[str, Any], key: str, value: Any) -> None:
    """
    Update a nested key in a mapping using dotted key notation.

    Parameters
    ----------
    old : dict[str, object]
        Mapping to modify in place.
    key : str
        Dotted key path (for example ``root.child.leaf``).
    value : object
        Value assigned to the final key.
    """
    d = old
    parts = key.split('.')
    for part in parts[:-1]:
        if part not in d:
            d[part] = {}
        d = d.get(part)
    d[parts[-1]] = value


def dictUpdate(old: MutableMapping[str, Any], new: Mapping[str, Any]) -> None:
    """
    Update a mapping using flattened dotted keys and nested dictionaries.

    Parameters
    ----------
    old : dict[str, object]
        Mapping to modify in place.
    new : dict[str, object]
        Update data. Keys containing ``.`` are expanded as nested keys.
    """
    for k,v in new.items():
        if '.' in k:
            keyValueUpdate(old, k, v)
        elif k in old:
            old[k].update(v)
        else:
            old[k] = v


def yamlUpdate(old: MutableMapping[str, Any], new: str) -> None:
    """
    Update a mapping using YAML content.

    Parameters
    ----------
    old : dict[str, object]
        Mapping to modify in place.
    new : str
        YAML content string parsed with :func:`pyrogue.yamlToData`.
    """
    dictUpdate(old, pr.yamlToData(new))


def recreate_OrderedDict(name: str, values: Mapping[str, Any]) -> odict:
    """
    Recreate an ordered dictionary from serialized state.

    Parameters
    ----------
    name : str
        Serialized object name.
    values : dict[str, object]
        Serialized values containing an ``items`` entry.

    Returns
    -------
    collections.OrderedDict
        Reconstructed ordered dictionary.
    """
    return odict(values['items'])

# Creation function wrapper for methods with variable args
def functionWrapper(
    function: Callable[..., Any] | None,
    callArgs: Sequence[str],
) -> Callable[..., Any]:
    """Build an adapter that forwards only the callback args it supports.

    This helper is the compatibility layer used by many PyRogue callback
    entry-points. Call sites can always provide a standard superset of named
    arguments (for example ``root``, ``dev``, ``cmd``, ``arg``), while user
    callbacks are free to accept any subset of those names.

    The generated wrapper:

    - receives all names listed in ``callArgs`` plus ``function``
    - inspects ``function`` to find accepted positional/keyword-only argument
      names
    - forwards only overlapping names (excluding ``self``) when invoking
      ``function``

    This enables these callback styles to coexist:

    - ``cb()``
    - ``cb(arg)``
    - ``cb(dev, arg)``
    - ``cb(root, dev, cmd, arg)``

    Parameters
    ----------
    function : callable or None
        Callback to adapt. If ``None``, a no-op wrapper returning ``None`` is
        produced.
    callArgs : Sequence[str]
        Canonical argument-name superset the call site will provide.

    Returns
    -------
    callable
        Wrapper callable that accepts ``function=...`` plus keyword arguments
        from ``callArgs`` and invokes ``function`` using only supported names.

    Notes
    -----
    - C++-bound callables may not be introspectable; in that case this wrapper
      currently forwards no callback arguments.
    - ``callArgs`` defines the canonical callback keyword names that may be
      forwarded to ``function``.
    """

    # Build a stable no-op wrapper for unset callbacks.
    if function is None:
        def _none_wrapper(*, function: Callable[..., Any] | None = None, **kwargs: Any) -> None:
            return None
        return _none_wrapper

    # Determine accepted callback keyword names once at wrapper construction.
    accepted_names: set[str] = set()
    accepts_var_kwargs = False
    introspection_failed = False

    try:
        sig = inspect.signature(function)
        for name, param in sig.parameters.items():
            if name == 'self':
                continue
            if param.kind in (inspect.Parameter.POSITIONAL_OR_KEYWORD, inspect.Parameter.KEYWORD_ONLY):
                accepted_names.add(name)
            elif param.kind == inspect.Parameter.VAR_KEYWORD:
                accepts_var_kwargs = True
    except Exception:
        # Preserve legacy behavior for non-introspectable callables (for
        # example some C++ bindings): call with no forwarded callback args.
        introspection_failed = True

    def _wrapper(*, function: Callable[..., Any], **kwargs: Any) -> Any:
        if function is None:
            return None

        if introspection_failed:
            return function()

        if accepts_var_kwargs:
            forwarded = {k: kwargs[k] for k in callArgs if k in kwargs}
        else:
            forwarded = {k: kwargs[k] for k in accepted_names if k in kwargs}

        return function(**forwarded)

    return _wrapper


def genDocTableHeader(fields: Sequence[str], indent: int, width: int) -> str:
    """
    Generate a reStructuredText table header.

    Parameters
    ----------
    fields : list[str]
        Column header strings.
    indent : int
        Number of leading spaces.
    width : int
        Column width.

    Returns
    -------
    str
        Header text including separator lines.
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

def genDocTableRow(fields: Sequence[str], indent: int, width: int) -> str:
    """
    Generate a reStructuredText table row.

    Parameters
    ----------
    fields : list[str]
        Row field strings.
    indent : int
        Number of leading spaces.
    width : int
        Column width.

    Returns
    -------
    str
        Row text including separator line.
    """
    r = ' ' * indent + '|'

    for f in fields:
        r += f + ' '
        r += ' ' * (width-len(f)-1) + '|'

    r += '\n' + ' ' * indent + '+'

    for _ in range(len(fields)):
        r += '-' * width + '+'

    return r

def genDocDesc(desc: str, indent: int) -> str:
    """
    Format sentence-delimited text into table-style description lines.

    Parameters
    ----------
    desc : str
        Description text split on ``.`` characters.
    indent : int
        Number of leading spaces for each line.

    Returns
    -------
    str
        Formatted description block.
    """
    r = ''

    for f in desc.split('.'):
        f = f.strip()
        if len(f) > 0:
            r += ' ' * indent
            r += '| ' + f + '.\n'

    return r
