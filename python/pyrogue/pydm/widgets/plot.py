#-----------------------------------------------------------------------------
# Title      : PyRogue PyDM Plot Window
#-----------------------------------------------------------------------------
# This file is part of the rogue software platform. It is subject to
# the license terms in the LICENSE.txt file found in the top-level directory
# of this distribution and at:
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
# No part of the rogue software platform, including this file, may be
# copied, modified, propagated, or distributed except according to the terms
# contained in the LICENSE.txt file.
#-----------------------------------------------------------------------------

from pydm.widgets.frame import PyDMFrame
from pyrogue.pydm.data_plugins.rogue_plugin import nodeFromAddress
from qtpy.QtWidgets import QVBoxLayout
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar

class Plotter(PyDMFrame):
    def __init__(self, parent=None, init_channel=None):
        PyDMFrame.__init__(self, parent, init_channel)

        self._systemLog = None
        self._node = None
        self._canvas = None
        self._fig = None

    def connection_changed(self, connected):
        build = (self._node is None) and (self._connected != connected and connected is True)
        super(Plotter, self).connection_changed(connected)

        if not build:
            return

        self._node = nodeFromAddress(self.channel)

        self._vb = QVBoxLayout()
        self.setLayout(self._vb)

    def value_changed(self, new_val):
        if self._canvas is not None:
            self._vb.removeWidget(self._canvas)
            self._vb.removeWidget(self._nav)
            self._canvas.setParent(None)
            self._nav.setParent(None)
            del self._canvas, self._nav, self._fig

        self._fig = new_val
        self._canvas = FigureCanvas(self._fig)
        self._nav = NavigationToolbar(self._canvas, self)
        self._vb.addWidget(self._nav)
        self._vb.addWidget(self._canvas)
