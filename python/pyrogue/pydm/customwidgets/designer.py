#-----------------------------------------------------------------------------
# This file is part of the rogue software platform. It is subject to 
# the license terms in the LICENSE.txt file found in the top-level directory 
# of this distribution and at: 
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html. 
# No part of the rogue software platform, including this file, may be 
# copied, modified, propagated, or distributed except according to the terms 
# contained in the LICENSE.txt file.
#-----------------------------------------------------------------------------

from pydm.widgets.qtplugin_base import qtplugin_factory

from pyrogue.pydm.customwidgets.displays.variable_tree import VariableTree
from pyrogue.pydm.customwidgets.displays.command_tree  import CommandTree
from pyrogue.pydm.customwidgets.displays.system_log    import SystemLog
from pyrogue.pydm.customwidgets.displays.run_control   import RunControl
from pyrogue.pydm.customwidgets.displays.data_writer   import DataWriter
from pyrogue.pydm.customwidgets.displays.system_window import SystemWindow

VariableTree = qtplugin_factory(VariableTree,  group="Rogue Widgets")
CommandTree  = qtplugin_factory(CommandTree,   group="Rogue Widgets")
SystemLog    = qtplugin_factory(SystemLog,     group="Rogue Widgets")
RunControl   = qtplugin_factory(RunControl,    group="Rogue Widgets")
DataWriter   = qtplugin_factory(DataWriter,    group="Rogue Widgets")
SystemWindow = qtplugin_factory(SystemWindow,  group="Rogue Widgets")
