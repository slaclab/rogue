#-----------------------------------------------------------------------------
# Title      : PyRogue PyDM Read Node Tool
#-----------------------------------------------------------------------------
# This file is part of the rogue software platform. It is subject to
# the license terms in the LICENSE.txt file found in the top-level directory
# of this distribution and at:
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
# No part of the rogue software platform, including this file, may be
# copied, modified, propagated, or distributed except according to the terms
# contained in the LICENSE.txt file.
#-----------------------------------------------------------------------------

import logging
from pydm.tools import ExternalTool
from pydm.utilities.iconfont import IconFont

import pyrogue
from pyrogue.interfaces import VirtualClient
from pyrogue.pydm.data_plugins.rogue_plugin import parseAddress

logger = logging.getLogger(__name__)


class ReadNode(ExternalTool):

    def __init__(self):
        icon = IconFont().icon("cogs")
        name = "Read Node"
        group = "Rogue"
        use_with_widgets = True
        ExternalTool.__init__(self, icon=icon, name=name, group=group, use_with_widgets=use_with_widgets)

    def call(self, channels, sender):
        addr, port, path, mode = parseAddress(channels[0].address)
        self._client = VirtualClient(addr, port)
        node = self._client.root.getNode(path)

        if node.isinstance(pyrogue.Device):
            node.ReadDevice(False)

        elif node.isinstance(pyrogue.BaseCommand):
            logger.warning("Can't read from non variable: {}".format(node.path))

        elif node.isinstance(pyrogue.BaseVariable):
            if node.mode == 'WO':
                logger.warning("Can't read from write only variable: {}".format(node.path))
            else:
                node.get()
        else:
            logger.warning("Invalid node for read: {}".format(node.path))

    def to_json(self):
        return ""

    def from_json(self, content):
        pass

    def get_info(self):
        ret = ExternalTool.get_info(self)
        ret.update({'file': __file__})
        return ret
