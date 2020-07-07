
from pydm.widgets import PyDMLineEdit
from qtpy.QtCore import Property
from pydm.widgets.base import refresh_style

class PyRogueLineEdit(PyDMLineEdit):
    def __init__(self, parent=None, init_channel=None):
        PyDMLineEdit.__init__(self,parent=parent,init_channel=init_channel)

        self.textEdited.connect(self.text_edited)
        self._dirty = False

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
