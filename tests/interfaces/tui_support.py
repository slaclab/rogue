#-----------------------------------------------------------------------------
# This file is part of the rogue software platform. It is subject to
# the license terms in the LICENSE.txt file found in the top-level directory
# of this distribution and at:
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
# No part of the rogue software platform, including this file, may be
# copied, modified, propagated, or distributed except according to the terms
# contained in the LICENSE.txt file.
#-----------------------------------------------------------------------------

# Shared tree for the TUI tests: one of each widget kind the Debug Tree
# distinguishes (RW value, enum, Hidden, guiGroup member, command with arg).

import pyrogue as pr
import pyrogue.interfaces as pr_interfaces


class TuiDevice(pr.Device):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.add(pr.LocalVariable(name='Value', value=1, mode='RW'))
        self.add(pr.LocalVariable(name='Mode', value=0, mode='RW', enum={0: 'Idle', 1: 'Run'}))
        self.add(pr.LocalVariable(name='Secret', value=5, mode='RW', groups=['Hidden']))
        self.add(pr.LocalVariable(name='Bias0', value=0.0, mode='RW', guiGroup='Biases'))
        self.add(pr.LocalCommand(name='Multiply', value=0, retValue=0, function=lambda arg: arg * 3))


class TuiRoot(pr.Root):
    def __init__(self, *, port):
        super().__init__(name='Top', pollEn=False)
        self.add(TuiDevice(name='Dev'))
        self.zmqServer = pr_interfaces.ZmqServer(root=self, addr='*', port=port)
        self.addInterface(self.zmqServer)
