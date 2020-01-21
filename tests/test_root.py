#!/usr/bin/env python3
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

def test_root():

    # Test __enter__ and __exit_ methods
    with pyrogue.Root(name='root',timeout=2.0, initRead=True, initWrite=True, serverPort=None) as root:
        # Test:
        # - a non-default poll value
        # - set the initRead to true
        # - set the initWrite to true
        pass

if __name__ == "__main__":
    test_root()
