from __future__ import annotations

#-----------------------------------------------------------------------------
# Company    : SLAC National Accelerator Laboratory
#-----------------------------------------------------------------------------
#  Description:
#       PyRogue PyDM Plot Window
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
from qtpy.QtWidgets import QVBoxLayout, QWidget
from qtpy.QtCore import QCoreApplication, QEvent
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure
import matplotlib.pyplot as plt


class Plotter(PyDMFrame):
    """PyDM widget that displays an incoming matplotlib figure published by a pyrogue Variable."""

    def __init__(
        self,
        parent: QWidget | None = None,
        init_channel: str | None = None,
        show_toolbar: bool = True,
    ) -> None:
        super().__init__(parent, init_channel)

        self._systemLog = None
        self._node = None
        self._vb: QVBoxLayout | None = None

        self._canvas: FigureCanvas | None = None
        self._nav: NavigationToolbar | None = None
        self._fig: Figure | None = None

        self._show_toolbar = show_toolbar

    def _ensure_layout(self) -> None:
        """Build the widget layout before embedding the plot widgets."""
        if self._vb is not None:
            return

        if self._node is None and self.channel is not None:
            self._node = nodeFromAddress(self.channel)

        self._vb = QVBoxLayout()
        self.setLayout(self._vb)

    def _clear_plot(self) -> None:
        """Release the current toolbar, canvas, and figure."""
        if self._vb is None:
            self._canvas = None
            self._nav = None
            self._fig = None
            return

        old_nav = self._nav
        old_canvas = self._canvas
        old_fig = self._fig

        # Drop our own references first.
        self._nav = None
        self._canvas = None
        self._fig = None

        # Remove toolbar first because it may hold references to the canvas.
        if old_nav is not None:
            self._vb.removeWidget(old_nav)
            old_nav.hide()
            old_nav.setParent(None)
            old_nav.deleteLater()

        # Then remove canvas.
        if old_canvas is not None:
            self._vb.removeWidget(old_canvas)

            # Break the canvas -> figure reference if possible.
            try:
                old_canvas.figure = None
            except Exception:
                pass

            old_canvas.hide()
            old_canvas.setParent(None)
            old_canvas.deleteLater()

        # Finally release figure-side resources.
        if old_fig is not None:
            try:
                old_fig.clear()
            except Exception:
                pass

            try:
                plt.close(old_fig)
            except Exception:
                pass

        # Flush deferred deletes so old Qt objects do not pile up.
        QCoreApplication.sendPostedEvents(None, QEvent.DeferredDelete)

    def connection_changed(self, connected: bool) -> None:
        """Build the layout after the first successful channel connection."""
        build = (self._vb is None) and (self._connected != connected and connected is True)
        super().connection_changed(connected)

        if not build:
            return

        self._ensure_layout()

    def value_changed(self, new_val: object) -> None:
        """Replace the displayed plot with the latest incoming figure."""
        self._ensure_layout()
        self._clear_plot()

        fig = new_val
        canvas = FigureCanvas(fig)
        nav = NavigationToolbar(canvas, self) if self._show_toolbar else None

        self._fig = fig
        self._canvas = canvas
        self._nav = nav

        if nav is not None:
            self._vb.addWidget(nav)
        self._vb.addWidget(canvas)

    def closeEvent(self, event) -> None:
        """Release embedded plot resources when the widget closes."""
        self._clear_plot()
        super().closeEvent(event)
