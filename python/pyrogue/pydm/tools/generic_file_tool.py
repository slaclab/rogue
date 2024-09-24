#-----------------------------------------------------------------------------
# Company    : SLAC National Accelerator Laboratory
#-----------------------------------------------------------------------------
#  Description:
#       PyRogue PyDM Generic File Browser
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
from qtpy.QtWidgets import QFileDialog

import pyrogue
from pyrogue.interfaces import VirtualClient
from pyrogue.pydm.data_plugins.rogue_plugin import parseAddress

logger = logging.getLogger(__name__)


class OpenFileBrowse(ExternalTool):

    def __init__(self,save=False):
        icon = IconFont().icon("cogs")
        self.save = save

        if self.save:
            name = "File Save Browser"
        else:
            name = "File Open Browser"

        group = "Rogue"
        use_with_widgets = True
        ExternalTool.__init__(self, icon=icon, name=name, group=group, use_with_widgets=use_with_widgets)

    def call(self, channels, sender):
        addr, port, path, mode, index = parseAddress(channels[0].address)
        self._client = VirtualClient(addr, port)
        node = self._client.root.getNode(path)

        dlg = QFileDialog()

        if self.save:
            dataFile = dlg.getSaveFileName(caption='Select Save File', filter='YAML Files(*.yml);;Data Files(*.dat);;CSV Files(*.csv);;Numpy Files(*.npy);;All Files(*.*)')
        else:
            dataFile = dlg.getOpenFileName(caption='Select Open File', filter='YAML Files(*.yml);;Data Files(*.dat);;CSV Files(*.csv);;Numpy Files(*.npy);;All Files(*.*)')

        # Detect QT5 return
        if isinstance(dataFile,tuple):
            dataFile = dataFile[0]

        if dataFile == '':
            logger.warning(f"Skipping empty file name for node {node.name}")

        if node.isinstance(pyrogue.BaseCommand):
            node.call(dataFile)

        elif node.isinstance(pyrogue.BaseVariable):
            if node.mode == 'RO':
                logger.warning(f"Can't set file to RO node: {node.name}")

            else:
                node.set(dataFile)
                node.get()

        else:
            logger.warning(f"File browser used with invalid node: {node.name}")

    def to_json(self):
        return ""

    def from_json(self, content):
        pass

    def get_info(self):
        ret = ExternalTool.get_info(self)
        ret.update({'file': __file__})
        return ret

class SaveFileBrowse(OpenFileBrowse):
    def __init__(self):
        OpenFileBrowse.__init__(self, save=True)
