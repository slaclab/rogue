from pydm.widgets import PyDMLineEdit, PyDMLabel
from qtpy.QtCore import Property, Qt
from qtpy.QtWidgets import QWidget, QGridLayout
from pydm.widgets.base import refresh_style

class PyRogueLineEdit(PyDMLineEdit):
    def __init__(self, parent=None, init_channel=None):
        PyDMLineEdit.__init__(self,parent=parent,init_channel=init_channel)

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

class PyRogueVariableDisplay(QWidget):
    def __init__(self, parent, init_channel, widget):
        QWidget.__init__(self, parent)

        self._valueWidget = widget(parent, init_channel = init_channel)
        self._valueWidget.precisionFromPV       = True
        self._valueWidget.alarmSensitiveContent = False
        self._valueWidget.alarmSensitiveBorder  = True
        self._valueWidget.setStyleSheet("* { background-color: rgba(0, 0, 0, 0); }")


        self._unitWidget = widget(parent, init_channel = None)
        self._unitWidget.precisionFromPV       = True
        self._unitWidget.alarmSensitiveContent = False
        self._unitWidget.alarmSensitiveBorder  = True
        self._unitWidget.set_opacity(0.7)
        self._unitWidget.setAlignment(Qt.AlignRight)
        self._unitWidget.setText("")

        # Monkey patch!
        def unit_changed(new_unit):
            self._unitWidget.setText(new_unit)
        self._valueWidget.unit_changed = unit_changed

        grid = QGridLayout()
        grid.addWidget(self._unitWidget, 0, 0)
        grid.addWidget(self._valueWidget, 0, 0)
        grid.setVerticalSpacing(0)
        grid.setHorizontalSpacing(0)
        grid.setContentsMargins(0, 0, 0, 0)
        self.setLayout(grid)


class PyRogueVariableLineEdit(PyRogueVariableDisplay):
    def __init__(self, parent, init_channel):
        super().__init__(parent, init_channel, PyRogueLineEdit)

class PyRogueVariableLabel(PyRogueVariableDisplay):
    def __init__(self, parent, init_channel):
        super().__init__(parent, init_channel, PyDMLabel)
