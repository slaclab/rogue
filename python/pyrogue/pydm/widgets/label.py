#-----------------------------------------------------------------------------
# Company    : SLAC National Accelerator Laboratory
#-----------------------------------------------------------------------------
#  Description:
#
#-----------------------------------------------------------------------------
# This file is part of the rogue software platform. It is subject to
# the license terms in the LICENSE.txt file found in the top-level directory
# of this distribution and at:
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
# No part of the rogue software platform, including this file, may be
# copied, modified, propagated, or distributed except according to the terms
# contained in the LICENSE.txt file.
#-----------------------------------------------------------------------------
from pydm.widgets import PyDMLabel
from qtpy.QtCore import Qt
from qtpy.QtWidgets import QHBoxLayout
from pydm.widgets.base import str_types
from pydm.widgets.display_format import parse_value_for_display

class PyRogueLabel(PyDMLabel):
    def __init__(self, parent, init_channel=None, show_units=True):
        super().__init__(parent, init_channel=init_channel)

        self._show_units = show_units

        self._unitWidget = PyDMLabel(parent)
        self._unitWidget.setStyleSheet("QLabel { background-color: white; color : DimGrey; }")
        self._unitWidget.setAlignment(Qt.AlignRight)
        self._unitWidget.setText("")

        hbox = QHBoxLayout()
        hbox.addStretch(1)
        hbox.addWidget(self._unitWidget)
        hbox.setContentsMargins(0, 0, 0, 0)
        self.setLayout(hbox)

    def unit_changed(self, new_unit):
        if self._show_units:
            self._unitWidget.setText(new_unit)

    def value_changed(self, new_value):
        """
        Callback invoked when the Channel value is changed.
        Sets the value of new_value accordingly at the Label.

        Parameters
        ----------
        new_value : str, int, float, bool or np.ndarray
            The new value from the channel. The type depends on the channel.
        """
        super(PyDMLabel, self).value_changed(new_value)
        new_value = parse_value_for_display(value=new_value, precision=self.precision,
                                            display_format_type=self._display_format_type,
                                            string_encoding=self._string_encoding,
                                            widget=self)
        # If the value is a string, just display it as-is, no formatting
        # needed.
        if isinstance(new_value, str_types):
            self.setText(new_value)
            return
        # If the value is an enum, display the appropriate enum string for
        # the value.
        if self.enum_strings is not None and isinstance(new_value, int):
            try:
                self.setText(self.enum_strings[new_value])
            except IndexError:
                self.setText("**INVALID**")
            return
        # If the value is a number (float or int), display it using a
        # format string if necessary.
        if isinstance(new_value, (int, float)):
            self.setText(self.format_string.format(new_value))
            return
        # If you made it this far, just turn whatever the heck the value
        # is into a string and display it.
        self.setText(str(new_value))
