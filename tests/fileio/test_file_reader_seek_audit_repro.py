#-----------------------------------------------------------------------------
# Company    : SLAC National Accelerator Laboratory
#-----------------------------------------------------------------------------
# Description:
#   Audit repro for PYR-016.
#   _FileReader.records() batch mode calls
#   `self._currFile.seek(bHead.width-8)` (line 232) without specifying a
#   whence argument.  seek(n) defaults to os.SEEK_SET (absolute offset from
#   the beginning of the file), not os.SEEK_CUR (relative advance from the
#   current position).  For wide batch headers this seeks to the wrong
#   position.  The correct call is seek(bHead.width-8, os.SEEK_CUR).
#   On HEAD the whence argument is absent → assertion FAILS.
#-----------------------------------------------------------------------------
# This file is part of the rogue software platform. It is subject to
# the license terms in the LICENSE.txt file found in the top-level directory
# of this distribution and at:
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
# No part of the rogue software platform, including this file, may be
# copied, modified, propagated, or distributed except according to the terms
# contained in the LICENSE.txt file.
#-----------------------------------------------------------------------------

import inspect

import pyrogue.utilities.fileio._FileReader as file_reader_mod


def test_filereader_uses_seek_cur_pyr_016():
    """PYR-016: _FileReader batch-mode seek lacks os.SEEK_CUR; defaults to SEEK_SET."""
    src = inspect.getsource(file_reader_mod.FileReader.records)

    # The seek that advances past wide batch headers must specify SEEK_CUR to
    # perform a relative advance.  Assert SEEK_CUR is present in the method.
    assert "SEEK_CUR" in src, (
        "PYR-016: _FileReader.records() batch-mode seek(bHead.width-8) is "
        "missing the os.SEEK_CUR whence argument (line 232); the call defaults "
        "to os.SEEK_SET (absolute seek from file start), seeking to the wrong "
        "position for any batch header wider than 8 bytes"
    )
