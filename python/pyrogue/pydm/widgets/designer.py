#-----------------------------------------------------------------------------
# Title      : PyRogue PyDM Designer Setup
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

from pyrogue.pydm.widgets import DebugTree
from pyrogue.pydm.widgets import SimpleDebugTree
from pyrogue.pydm.widgets import RootControl
from pyrogue.pydm.widgets import SystemLog
from pyrogue.pydm.widgets import RunControl
from pyrogue.pydm.widgets import DataWriter
from pyrogue.pydm.widgets import SystemWindow
from pyrogue.pydm.widgets import Process
from pyrogue.pydm.widgets import PyRogueLineEdit
from pyrogue.pydm.widgets import Plotter

LineEdit     = qtplugin_factory(PyRogueLineEdit, group="Rogue Widgets")
DebugTree    = qtplugin_factory(DebugTree,       group="Rogue Widgets")
SimpleDebugTree    = qtplugin_factory(SimpleDebugTree,       group="Rogue Widgets")
RootControl  = qtplugin_factory(RootControl,     group="Rogue Widgets")
SystemLog    = qtplugin_factory(SystemLog,       group="Rogue Widgets")
RunControl   = qtplugin_factory(RunControl,      group="Rogue Widgets")
DataWriter   = qtplugin_factory(DataWriter,      group="Rogue Widgets")
SystemWindow = qtplugin_factory(SystemWindow,    group="Rogue Widgets")
Procsss      = qtplugin_factory(Process,         group="Rogue Widgets")
Plotter      = qtplugin_factory(Plotter,         group="Rogue Widgets")
