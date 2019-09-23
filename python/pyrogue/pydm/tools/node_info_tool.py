import subprocess
import logging
from pydm.tools import ExternalTool
from pydm.utilities.iconfont import IconFont
from pydm.utilities.remove_protocol import remove_protocol

logger = logging.getLogger(__name__)

class ProbeTool(ExternalTool):

    def __init__(self):
        print("Probe tool created")
        icon = IconFont().icon("cogs")
        name = "Probe"
        group = "EPICS"
        use_with_widgets = True
        ExternalTool.__init__(self, icon=icon, name=name, group=group, use_with_widgets=use_with_widgets)

    def call(self, channels, sender):
        cmd = "probe"
        args = [cmd]
        if not channels:
            channels = []
        for ch in channels:
            args.append(remove_protocol(ch.address))
        try:
            subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        except Exception as e:
            logger.error("Error while invoking Probe. Exception was: %s", str(e))


    def _variable(self, node, channel):


    def _command(self, node, channel):


    def _device(self, node, channel):



    def to_json(self):
        return ""

    def from_json(self, content):
        pass

    def get_info(self):
        ret = ExternalTool.get_info(self)
        ret.update({'file': __file__})
        return ret
