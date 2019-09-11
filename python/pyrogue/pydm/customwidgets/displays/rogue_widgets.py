#-----------------------------------------------------------------------------
# This file is part of the rogue software platform. It is subject to 
# the license terms in the LICENSE.txt file found in the top-level directory 
# of this distribution and at: 
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html. 
# No part of the rogue software platform, including this file, may be 
# copied, modified, propagated, or distributed except according to the terms 
# contained in the LICENSE.txt file.
#-----------------------------------------------------------------------------

from os import path
from pydm import Display
from pydm import widgets
from qtpy.QtCore import Qt, Property, QObject, Q_ENUMS

class RogueWidget(Display):
    def __init__(self, parent=None, args=None, macros=None):
        super(RogueWidget, self).__init__(parent=parent, args=args, macros=None)

    def ui_filename(self):
        # Point to our UI file
        return 'test_widget.ui'

    def ui_filepath(self):
        # Return the full path to the UI file
        return path.join(path.dirname(path.realpath(__file__)), self.ui_filename())
