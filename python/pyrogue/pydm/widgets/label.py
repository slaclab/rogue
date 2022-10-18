from pydm.widgets import PyDMLabel
from qtpy.QtCore import Qt
from qtpy.QtWidgets import QGridLayout
from pydm.widgets.base import refresh_style

class PyRogueLabel(PyDMLabel):
    def __init__(self, parent, init_channel=None):
        super().__init__(parent, init_channel=init_channel)                

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
        self._unitWidget.setText(new_unit)
