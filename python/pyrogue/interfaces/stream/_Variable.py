#-----------------------------------------------------------------------------
# Company    : SLAC National Accelerator Laboratory
#-----------------------------------------------------------------------------
# Description:
# Class to generate variable update streams
#-----------------------------------------------------------------------------
# This file is part of the rogue software platform. It is subject to
# the license terms in the LICENSE.txt file found in the top-level directory
# of this distribution and at:
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
# No part of the rogue software platform, including this file, may be
# copied, modified, propagated, or distributed except according to the terms
# contained in the LICENSE.txt file.
#-----------------------------------------------------------------------------

import pyrogue
import rogue.interfaces.stream
from typing import Any


class Variable(rogue.interfaces.stream.Master):
    """Stream master that emits variable values as YAML frames.

    Parameters
    ----------
    root : pyrogue.Root
        PyRogue root node to monitor.
    incGroups : str | list[str] | None, optional
        Groups to include in variable updates.
    excGroups : str | list[str] | None, optional
        Groups to exclude from variable updates.
    """

    def __init__(
        self,
        *,
        root: pyrogue.Root,
        incGroups: str | list[str] | None = None,
        excGroups: str | list[str] | None = ['NoStream'],
    ) -> None:
        super().__init__()
        self._updateList = {}
        root.addVarListener(func=self._varUpdate, done=self._varDone, incGroups=incGroups, excGroups=excGroups)

        self._root = root
        self._incGroups = incGroups
        self._excGroups = excGroups

    def streamYaml(self) -> None:
        """
        Generate a frame containing all variable values in YAML format.
        A hardware read is not generated before the frame is generated.
        """
        self._sendYamlFrame(self._root.getYaml(readFirst=False,
                                               modes=['RW','RO','WO'],
                                               incGroups=self._incGroups,
                                               excGroups=self._excGroups,
                                               recurse=True))

    def _varUpdate(self, path: str, value: Any) -> None:
        """Queue a variable update for the next batch."""
        self._updateList[path] = value

    def _varDone(self) -> None:
        """Flush queued updates and send as a YAML frame."""
        if len(self._updateList) > 0:
            self._sendYamlFrame(pyrogue.dataToYaml(self._updateList))
            self._updateList = {}

    def _sendYamlFrame(self, yml: str) -> None:
        """Serialize YAML to a frame and send it."""
        b = bytearray(yml,'utf-8')
        frame = self._reqFrame(len(b),True)
        frame.write(b,0)
        self._sendFrame(frame)
