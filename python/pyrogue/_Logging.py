#-----------------------------------------------------------------------------
# Company    : SLAC National Accelerator Laboratory
#-----------------------------------------------------------------------------
#  Description:
#       PyRogue logging helpers
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

import inspect
import logging
import sys
from typing import TYPE_CHECKING, Any

import rogue

if TYPE_CHECKING:
    from pyrogue._Node import Node as _NodeType
else:
    _NodeType = Any


LogTarget = str | logging.Logger | _NodeType | type[_NodeType]


def _logger_family_name(cls: type[Any]) -> str:
    """Return the logger family name for a PyRogue class."""
    precedence = (
        ('pyrogue._Command', 'BaseCommand', 'Command'),
        ('pyrogue._Variable', 'BaseVariable', 'Variable'),
        ('pyrogue._Root', 'Root', 'Root'),
        ('pyrogue._Device', 'Device', 'Device'),
    )

    mro = inspect.getmro(cls)

    for module_name, class_name, family_name in precedence:
        for base in mro:
            if base.__module__ == module_name and base.__name__ == class_name:
                return family_name

    return ''


def logException(log: logging.Logger, e: Exception) -> None:
    """Log a memory error or a generic exception.

    Parameters
    ----------
    log : logging.Logger
        Logger used to record the exception.
    e : Exception
        Exception instance to log.
    """
    import pyrogue as pr

    if isinstance(e, pr.MemoryError):
        log.error(e)
    else:
        log.exception(e)


def logInit(
    cls: object | None = None,
    name: str | None = None,
    path: str | None = None,
) -> logging.Logger:
    """Initialize a logger with a consistent PyRogue name.

    Parameters
    ----------
    cls : object, optional
        PyRogue object used to derive the logger family and class name.
    name : str, optional
        Node name to include in the logger.
    path : str, optional
        Full node path to include in the logger.

    Returns
    -------
    logging.Logger
        Configured logger instance.
    """
    logging.basicConfig(
        format="%(levelname)s:%(name)s:%(message)s",
        stream=sys.stdout)

    ln = 'pyrogue'

    if cls is not None:
        family_name = _logger_family_name(cls.__class__)
        if family_name:
            ln += f'.{family_name}'

        ln += f'.{cls.__class__.__name__}'

    if path is not None:
        ln += f'.{path}'
    elif name is not None:
        ln += f'.{name}'

    return logging.getLogger(ln)


def _classLogName(cls: type[Any]) -> str:
    """Return the canonical Python logger name for a PyRogue Node class."""
    family_name = _logger_family_name(cls)
    ln = 'pyrogue'

    if family_name:
        ln += f'.{family_name}'

    return f'{ln}.{cls.__name__}'


def logName(target: LogTarget) -> str:
    """Resolve a supported logging target to a logger name.

    Parameters
    ----------
    target : str or logging.Logger or pyrogue.Node or type[pyrogue.Node]
        Logging target to resolve. Supported forms are:

        - a string logger name or shorthand accepted by
          ``rogue.Logging.normalizeName()``
        - a Python ``logging.Logger`` instance
        - a PyRogue ``Node`` instance
        - a PyRogue ``Node`` class

        String targets are normalized through
        ``rogue.Logging.normalizeName()`` so short names such as ``"udp"`` map
        to the canonical Rogue/PyRogue logger name. ``Node`` classes resolve to
        their class logger family, and ``Node`` instances resolve through their
        attached logger.

    Returns
    -------
    str
        Canonical logger name for the supplied target.

    Raises
    ------
    AttributeError
        Raised when the target does not expose a usable logger name.
    """
    if isinstance(target, str):
        return rogue.Logging.normalizeName(target)

    if isinstance(target, logging.Logger):
        return target.name

    if inspect.isclass(target):
        return _classLogName(target)

    log = getattr(target, '_log', None)
    if log is not None:
        name = getattr(log, 'name', None)
        if callable(name):
            return name()
        if isinstance(name, str):
            return name

    raise AttributeError(f'Object {target!r} does not expose a logger name')


def setLogLevel(
    target: LogTarget,
    level: int | str,
    *,
    includePython: bool = True,
    includeRogue: bool = True,
) -> str:
    """Set the logging level for a supported target.

    Parameters
    ----------
    target : str or logging.Logger or pyrogue.Node or type[pyrogue.Node]
        Logging target accepted by :func:`logName`.
    level : int or str
        Logging level to apply. String values are interpreted with the standard
        Python logging names such as ``"DEBUG"`` or ``"INFO"``.
    includePython : bool, optional
        If ``True``, update the Python ``logging`` logger level.
    includeRogue : bool, optional
        If ``True``, update the Rogue C++ logging filter for the same resolved
        logger name.

    Returns
    -------
    str
        Canonical logger name that was updated.

    Raises
    ------
    ValueError
        Raised when ``level`` is a string that Python logging does not
        recognize.
    AttributeError
        Raised when ``target`` cannot be resolved to a logger name.

    Notes
    -----
    For unified Rogue/PyRogue logging, the default ``includePython=True`` and
    ``includeRogue=True`` updates both sides together. Passing only one of the
    flags allows callers to change the Python logger or Rogue filter
    independently.
    """
    if isinstance(level, str):
        pyLevel = logging.getLevelName(level.upper())
        if not isinstance(pyLevel, int):
            raise ValueError(f'Unknown logging level: {level}')
    else:
        pyLevel = level

    name = logName(target)

    if includePython:
        logging.getLogger(name).setLevel(pyLevel)

    if includeRogue:
        rogue.Logging.setFilter(name, pyLevel)

    return name
