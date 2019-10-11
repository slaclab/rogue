#!/usr/bin/env python3

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
