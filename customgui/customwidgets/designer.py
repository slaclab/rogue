from pydm.widgets.qtplugin_base import qtplugin_factory

from .displays.rogue_widgets import RogueWidget

ROGUEWidget = qtplugin_factory(RogueWidget, group="Rogue Widgets")
