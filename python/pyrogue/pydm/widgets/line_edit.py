import locale
import numpy as np
import ast
from pydm.widgets import PyDMLineEdit, PyDMLabel
from qtpy.QtCore import Property, Qt
from qtpy.QtWidgets import QGridLayout
from pydm.widgets.base import refresh_style, str_types
from pydm.widgets.display_format import DisplayFormat, parse_value_for_display

logger = logging.getLogger(__name__)

class PyRogueLineEdit(PyDMLineEdit):
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

        self.textEdited.connect(self.text_edited)
        self._dirty = False

        self.setStyleSheet("*[dirty='true']\
                           {background-color: orange;}")

    def text_edited(self):
        self._dirty = True
        refresh_style(self)

    def focusOutEvent(self, event):
        self._dirty = False
        super(PyRogueLineEdit, self).focusOutEvent(event)
        refresh_style(self)

    @Property(bool)
    def dirty(self):
        return self._dirty

    def unit_changed(self, new_unit):
        super().unit_changed(new_unit)
        if self._show_units:
            self._unitWidget.setText(new_unit)

    def send_value(self):
        """
        Emit a :attr:`send_value_signal` to update channel value.

        The text is cleaned of all units, user-formatting and scale values
        before being sent back to the channel. This function is attached the
        ReturnPressed signal of the PyDMLineEdit
        """
        send_value = str(self.text())

        try:
            if self.channeltype not in [str, np.ndarray, bool]:
                scale = self._scale
                if scale is None or scale == 0:
                    scale = 1.0

                if self._display_format_type in [DisplayFormat.Default, DisplayFormat.String]:
                    if self.channeltype == float:
                        num_value = locale.atof(send_value)
                    else:
                        num_value = self.channeltype(send_value)
                    scale = self.channeltype(scale)
                elif self._display_format_type == DisplayFormat.Hex:
                    num_value = int(send_value, 16)
                elif self._display_format_type == DisplayFormat.Binary:
                    num_value = int(send_value, 2)
                elif self._display_format_type in [DisplayFormat.Exponential, DisplayFormat.Decimal]:
                    num_value = locale.atof(send_value)

                num_value = num_value / scale
                self.send_value_signal[self.channeltype].emit(num_value)
            elif self.channeltype == np.ndarray:
                # Arrays will be in the [1.2 3.4 22.214] format
                if self._display_format_type == DisplayFormat.String:
                    self.send_value_signal[str].emit(send_value)
                else:
                    arr_value = list(
                        filter(None, ast.literal_eval(str(send_value.replace("[", "").replace("]", "").split()))))
                    arr_value = np.array(arr_value, dtype=self.subtype)
                    self.send_value_signal[np.ndarray].emit(arr_value)
            elif self.channeltype == bool:
                try:
                    val = bool(PyDMLineEdit.strtobool(send_value))
                    self.send_value_signal[bool].emit(val)
                    # might want to add error to application screen
                except ValueError:
                    logger.error("Not a valid boolean: %r", send_value)
            else:
                # Channel Type is String
                # Lets just send what we have after all
                self.send_value_signal[str].emit(send_value)
        except ValueError:
            logger.exception("Error trying to set data '{0}' with type '{1}' and format '{2}' at widget '{3}'."
                         .format(self.text(), self.channeltype, self._display_format_type, self.objectName()))

        self.clearFocus()
        self.set_display()



    def set_display(self):
        """
        Set the text display of the PyDMLineEdit.

        The original value given by the PV is converted to a text entry based
        on the current settings for scale value, precision, a user-defined
        format, and the current units. If the user is currently entering a
        value in the PyDMLineEdit the text will not be changed.
        """
        if self.value is None:
            return

        if self.hasFocus():
            return

        new_value = self.value

        if self._display_format_type in [DisplayFormat.Default,
                                         DisplayFormat.Decimal,
                                         DisplayFormat.Exponential,
                                         DisplayFormat.Hex,
                                         DisplayFormat.Binary]:
            if self.channeltype not in (str, np.ndarray):
                try:
                    new_value *= self.channeltype(self._scale)
                except TypeError:
                    logger.error("Cannot convert the value '{0}', for channel '{1}', to type '{2}'. ".format(
                        self._scale, self._channel, self.channeltype))

        new_value = parse_value_for_display(value=new_value,  precision=self.precision,
                                            display_format_type=self._display_format_type,
                                            string_encoding=self._string_encoding,
                                            widget=self)

        if type(new_value) in str_types:
            self._display = new_value
        else:
            self._display = str(new_value)

        if self._display_format_type == DisplayFormat.Default:
            if isinstance(new_value, (int, float)):
                self._display = str(self.format_string.format(new_value))
                self.setText(self._display)
                return

        self.setText(self._display)
