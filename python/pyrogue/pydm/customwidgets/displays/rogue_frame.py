#-----------------------------------------------------------------------------
# This file is part of the rogue software platform. It is subject to 
# the license terms in the LICENSE.txt file found in the top-level directory 
# of this distribution and at: 
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html. 
# No part of the rogue software platform, including this file, may be 
# copied, modified, propagated, or distributed except according to the terms 
# contained in the LICENSE.txt file.
#-----------------------------------------------------------------------------

#from os import path
from pydm.widgets.frame import PyDMFrame
#from pydm import widgets
from pydm import utilities
from qtpy.QtCore import Qt, Property, QObject, Q_ENUMS
from pyrogue.pydm.data_plugins.rogue_plugin import ParseAddress
import pyrogue.interfaces

class RogueFrame(PyDMFrame):
    def __init__(self, parent=None, init_channel=None):
        PyDMFrame.__init__(self, parent, init_channel)

        self._client  = None
        self._node    = None

        self._rawPath   = None
        self._incGroups = None
        self._excGroups = None

    def _build(self):
        if (not utilities.is_pydm_app()) or self._rawPath is None:
            return

        host, port, path, disp = ParseAddress(self._rawPath)

        self._client = pyrogue.interfaces.VirtualClient(host,port)
        self._node   = self._client.root.getNode(path)

        print("Building frame for node {}".format(self._node))


    @Property(str)
    def incGroups(self):
        if self._incGroups is None or len(self._incGroups) == 0:
            return ''
        else:
            return ','.join(self._incGroups)

    @incGroups.setter
    def incGroups(self, value):
        if value == '':
            self._incGroups = None
        else:
            self._incGroups = value.split(',')
        print("Setting incGroups to {}".format(self._incGroups))

    @Property(str)
    def excGroups(self):
        if self._excGroups is None or len(self._excGroups) == 0:
            return ''
        else:
            return ','.join(self._excGroups)

    @excGroups.setter
    def excGroups(self, value):
        if value == '':
            self._excGroups = None
        else:
            self._excGroups = value.split(',')
        print("Setting excGroups to {}".format(self._excGroups))

    @Property(str)
    def path(self):
        return self._rawPath

    @path.setter
    def path(self, newPath):
        self._rawPath = newPath
        print("Setting path to {}".format(self._rawPath))
        self._build()


#    def __init__(self, parent=None, args=None, macros=None):
#        super(RogueWidget, self).__init__(parent=parent, args=args, macros=None)
#        print("Args = {}".format(args))
#        print("Macros = {}".format(macros))
#
#    def ui_filename(self):
#        # Point to our UI file
#        return 'test_widget.ui'
#
#    def ui_filepath(self):
#        # Return the full path to the UI file
#        return path.join(path.dirname(path.realpath(__file__)), self.ui_filename())

