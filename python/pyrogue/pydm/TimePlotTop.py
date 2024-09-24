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

from qtpy.QtWidgets import QVBoxLayout


Channel = 'rogue://0/root'

class TimePlotTop(Display):
    def __init__(self, parent=None, args=[], macros=None):
        super().__init__(parent=parent, args=args, macros=None)

        self.sizeX  = None
        self.sizeY  = None
        self.title  = None

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

    def ui_filepath(self):
        # No UI file is being used
        return None
