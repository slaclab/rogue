from __future__ import annotations

#-----------------------------------------------------------------------------
# Company    : SLAC National Accelerator Laboratory
#-----------------------------------------------------------------------------
#  Description:
#       PyRogue PyDM Embedded IPython Console Widget
#-----------------------------------------------------------------------------
# This file is part of the rogue software platform. It is subject to
# the license terms in the LICENSE.txt file found in the top-level directory
# of this distribution and at:
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
# No part of the rogue software platform, including this file, may be
# copied, modified, propagated, or distributed except according to the terms
# contained in the LICENSE.txt file.
#-----------------------------------------------------------------------------

from qtpy.QtWidgets import QWidget

from pyrogue.pydm.data_plugins.rogue_plugin import parseAddress
from pyrogue.pydm.widgets.ipython_core import ipythonArgv
from pyrogue.pydm.widgets.terminal import TerminalPanel

# Same server index the System and Debug Tree tabs bind to, so the console talks
# to whatever ROGUE_SERVERS entry the rest of the GUI is using.
DEFAULT_CHANNEL = 'rogue://0/root'


class IPythonPanel(TerminalPanel):
    """An IPython session with a connected Rogue client, in a detachable tab.

    A pseudo-terminal running IPython, with
    :class:`pyrogue.interfaces.VirtualClient` already connected and bound as
    ``client``, and the tree root as ``root``. It is the session the Rogue server
    suggests at startup, opened for the user instead of typed out.

    The console runs on the machine displaying the GUI as the user who launched
    it, **not** on the Rogue server, and it reaches the tree the same way any
    other client does, over ZMQ. Anyone who can reach the GUI window can run
    arbitrary Python, and anything Python can reach, with that user's privileges,
    which is why the feature is opt-in.

    The connection is its own client in its own process, not the one the PyDM
    channels share, so a session that is stopped or wedged from the prompt cannot
    take the rest of the GUI's channels with it.

    IPython starts on first display rather than on construction, so enabling the
    feature costs nothing until the tab is opened, and the up to five second
    connection attempt never delays the GUI coming up. Exiting the session starts
    a fresh, reconnected one.

    Parameters
    ----------
    parent : QWidget | None, optional
        Parent Qt widget.
    init_channel : str | None, optional
        Rogue channel whose server the client connects to. Defaults to
        ``rogue://0/root``, the first entry of ``ROGUE_SERVERS``.
    """

    def __init__(self, parent: QWidget | None = None,
                 init_channel: str | None = None) -> None:
        addr, port, _path, _mode, _index = parseAddress(init_channel or DEFAULT_CHANNEL)

        TerminalPanel.__init__(
            self, parent,
            argv=ipythonArgv(addr, port),
            label='IPython',
            windowTitle=f'Rogue IPython Console: {addr}:{port}',
            noun='console',
        )
