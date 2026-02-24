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

from pyrogue.pydm.widgets import TimePlotter

from pydm import Display

from qtpy.QtWidgets import QVBoxLayout, QWidget


Channel = 'rogue://0/root'

class TimePlotTop(Display):
    """Top-level PyDM display embedding the time-plotter widget.

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
        super().__init__(parent=parent, args=args, macros=macros)

        self.sizeX  = None
        self.sizeY  = None
        self.title  = None

        if args is None:
            args = []

        for a in args:
            if 'sizeX=' in a:
                self.sizeX = int(a.split('=')[1])
            if 'sizeY=' in a:
                self.sizeY = int(a.split('=')[1])
            if 'title=' in a:
                self.title = a.split('=')[1]

        if self.title is None:
            self.title = "Rogue Server: {}".format(os.getenv('ROGUE_SERVERS'))

        if self.sizeX is None:
            self.sizeX = 800
        if self.sizeY is None:
            self.sizeY = 1000

        self.setWindowTitle(self.title)

        vb = QVBoxLayout()
        self.setLayout(vb)

        tp = TimePlotter(parent=None, init_channel=Channel)
        vb.addWidget(tp)


        self.resize(self.sizeX, self.sizeY)

    def ui_filepath(self) -> None:
        """Return ``None`` because this display is code-constructed."""
        return None
