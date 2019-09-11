from os import path
from pydm import Display
from pydm import widgets
from qtpy.QtCore import Qt, Property, QObject, Q_ENUMS

class RogueWidget(Display):
    def __init__(self, parent=None, args=None, macros=None):
        super(RogueWidget, self).__init__(parent=parent, args=args, macros=None)

    def ui_filename(self):
        # Point to our UI file
        return 'test_widget.ui'

    def ui_filepath(self):
        # Return the full path to the UI file
        return path.join(path.dirname(path.realpath(__file__)), self.ui_filename())
