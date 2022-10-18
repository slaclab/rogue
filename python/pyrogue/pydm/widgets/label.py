from pydm.widgets import PyDMLabel
from qtpy.QtCore import Qt
from qtpy.QtWidgets import QGridLayout
from pydm.widgets.base import refresh_style, str_types
from pydm.widgets.display_format import parse_value_for_display

class PyRogueLabel(PyDMLabel):
    def __init__(self, parent, init_channel=None, show_units=True):
        super().__init__(parent, init_channel=init_channel)

        self._show_units = show_units

        self._unitWidget = PyDMLabel(parent)
        self._unitWidget.setStyleSheet("QLabel { color : DimGrey; }")
        self._unitWidget.setAlignment(Qt.AlignRight)
        self._unitWidget.setText("")

        grid = QGridLayout()
        grid.addWidget(self._unitWidget, 0, 0)
        grid.setVerticalSpacing(0)
        grid.setHorizontalSpacing(0)
        grid.setContentsMargins(0, 0, 0, 0)
        self.setLayout(grid)

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

