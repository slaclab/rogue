#-----------------------------------------------------------------------------
# This file is part of the rogue software platform. It is subject to
# the license terms in the LICENSE.txt file found in the top-level directory
# of this distribution and at:
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
# No part of the rogue software platform, including this file, may be
# copied, modified, propagated, or distributed except according to the terms
# contained in the LICENSE.txt file.
#-----------------------------------------------------------------------------
#
# Regression coverage for rim::SlaveWrap access size queries from Python.
# SlaveWrap::defDoMaxAccess previously forwarded to Slave::doMinAccess, so a
# Python caller of _doMaxAccess() received the minimum access size.
#
import rogue.interfaces.memory as rim


def test_slave_access_sizes_from_python():
    slave = rim.Slave(4, 16)

    assert slave._doMinAccess() == 4
    assert slave._doMaxAccess() == 16


def test_slave_subclass_can_override_access_sizes():
    class CustomSlave(rim.Slave):
        def __init__(self):
            rim.Slave.__init__(self, 4, 16)

        def _doMinAccess(self):
            return 8

        def _doMaxAccess(self):
            return 32

    slave = CustomSlave()

    assert slave._doMinAccess() == 8
    assert slave._doMaxAccess() == 32


def test_slave_subclass_can_derive_max_access_from_base():
    class OffsetSlave(rim.Slave):
        def __init__(self):
            rim.Slave.__init__(self, 4, 64)

        def _doMaxAccess(self):
            return rim.Slave._doMaxAccess(self) - 16

    slave = OffsetSlave()

    assert slave._doMinAccess() == 4
    assert slave._doMaxAccess() == 48
