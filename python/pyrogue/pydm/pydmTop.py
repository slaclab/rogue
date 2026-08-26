#-----------------------------------------------------------------------------
# Company    : SLAC National Accelerator Laboratory
#-----------------------------------------------------------------------------
#  Description:
#       PyRogue PyDM Top Level GUI
#-----------------------------------------------------------------------------
# This file is part of the rogue software platform. It is subject to
# the license terms in the LICENSE.txt file found in the top-level directory
# of this distribution and at:
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
# No part of the rogue software platform, including this file, may be
# copied, modified, propagated, or distributed except according to the terms
# contained in the LICENSE.txt file.
#-----------------------------------------------------------------------------
import os
from pydm import Display
from qtpy.QtWidgets import (QVBoxLayout, QTabWidget, QWidget)

from pyrogue.pydm.widgets import DebugTree
from pyrogue.pydm.widgets import TerminalPanel
from pyrogue.pydm.widgets import SystemWindow

Channel = 'rogue://0/root'


def _parseBoolArg(args: list[str], name: str) -> bool | None:
    """Return the boolean value of a ``name=<value>`` display argument.

    Returns ``None`` when the argument is absent so the caller keeps its own
    default. Matches on a leading prefix rather than the substring test used by
    the older size and title arguments, which would otherwise false-positive on
    a title that happened to contain the argument name.

    Parameters
    ----------
    args : list[str]
        Display argument list, each entry formatted as ``key=value``.
    name : str
        Argument name to look for.

    Returns
    -------
    bool | None
        Parsed value, or ``None`` when the argument is not present.
    """
    prefix = name + '='

    for a in args:
        if a.startswith(prefix):
            return a[len(prefix):].strip().strip('\'"').lower() in ('1','true','yes','on')

    return None


class DefaultTop(Display):
    """Default top-level Rogue PyDM display.

    Parameters
    ----------
    parent : QWidget | None, optional
        Parent Qt widget.
    args : list[str] | None, optional
        Display argument list (for example ``sizeX=...`` and ``sizeY=...``).
    macros : dict[str, str] | None, optional
        PyDM macro substitutions forwarded to :class:`pydm.Display`.
    """

    def __init__(self, parent: QWidget | None = None, args: list[str] | None = None, macros: dict[str, str] | None = None) -> None:
        super(DefaultTop, self).__init__(parent=parent, args=args, macros=macros)

        #self.setStyleSheet("*[dirty='true']\
        #                   {background-color: orange;}")

        self.sizeX  = None
        self.sizeY  = None
        self.title  = None
        self.enableTerminal = False

        if args is None:
            args = []

        for a in args:
            if 'sizeX=' in a:
                self.sizeX = int(a.split('=')[1])
            if 'sizeY=' in a:
                self.sizeY = int(a.split('=')[1])
            if 'title=' in a:
                self.title = a.split('=')[1]

        enableTerminal = _parseBoolArg(args, 'enableTerminal')
        if enableTerminal is not None:
            self.enableTerminal = enableTerminal

        if self.title is None:
            self.title = "Rogue Server: {}".format(os.getenv('ROGUE_SERVERS'))

        if self.sizeX is None:
            self.sizeX = 800
        if self.sizeY is None:
            self.sizeY = 1000

        self.setWindowTitle(self.title)

        vb = QVBoxLayout()
        self.setLayout(vb)

        self.tab = QTabWidget()
        vb.addWidget(self.tab)

        # System Tab  (Tab Index=0)
        sys = SystemWindow(parent=None, init_channel=Channel)
        self.tab.addTab(sys,'System')

        # Debug Tree Tab  (Tab Index=1)
        var = DebugTree(parent=None, init_channel=Channel)
        self.tab.addTab(var,'Debug Tree')

        # Terminal Tab  (Tab Index=2), added last so the existing tab indexes
        # are unchanged whether or not the terminal is enabled. A top level tab
        # gives the terminal the full window height, and unlike the other tabs
        # it needs no Rogue channel, so it also works while the link is down.
        self.terminal = None
        if self.enableTerminal:
            self.terminal = TerminalPanel(parent=None)
            self.tab.addTab(self.terminal,'Terminal')

        # Set the default Tab view
        self.tab.setCurrentIndex(1)

        self.resize(self.sizeX, self.sizeY)

    def ui_filepath(self) -> None:
        """Return ``None`` because this display is code-constructed."""
        return None
