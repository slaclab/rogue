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
from qtpy.QtCore import Qt, Property, QObject, Q_ENUMS
from pyrogue.pydm.data_plugins.rogue_plugin import PydmRogueClient

class RogueFrame(PyDMFrame):
    def __init__(self, parent=None, init_channel=None):
        PyDMFrame.__init__(self, parent, init_channel)

        self._channel = init_channel
        self._rawPath = None
        self._client  = None
        self._node    = None

    @Property(str)
    def roguePath(self):
        return self._rawPath

    @roguePath.setter
    def roguePath(self, newPath):
        self._rawPath = newPath

        host, port, path = PydmRogueClient.parseAddr(self._rawPath)

        self._client = PydmRogueClient(host,port)
        self._node   = self._client.root.getNode(path)

        print("Connected to node {}".format(self._node))

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

