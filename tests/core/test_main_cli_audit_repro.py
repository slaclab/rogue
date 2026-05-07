#-----------------------------------------------------------------------------
# Company    : SLAC National Accelerator Laboratory
#-----------------------------------------------------------------------------
# Description:
#   Regression test.
#   pyrogue/__main__.py lines 122-137: the dispatch block handles
#   get/value/set/exec but has no `else: ret = None` guard before the
#   trailing `if ret is not None: print(...)` at line 139.
#   If a future branch is added that does not set `ret`, or if the argparse
#   `choices` guard is ever relaxed, the `print` at line 139 will raise
#   UnboundLocalError.  On HEAD no else-guard → assertion FAILS.
#-----------------------------------------------------------------------------
# This file is part of the rogue software platform. It is subject to
# the license terms in the LICENSE.txt file found in the top-level directory
# of this distribution and at:
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
# No part of the rogue software platform, including this file, may be
# copied, modified, propagated, or distributed except according to the terms
# contained in the LICENSE.txt file.
#-----------------------------------------------------------------------------

import pathlib


def test_main_cli_else_initializes_ret():
    """__main__.py CLI dispatch lacks else: ret = None guard."""
    main_path = pathlib.Path(__file__).parent.parent.parent / "python" / "pyrogue" / "__main__.py"
    src = main_path.read_text()

    outer_else_start = src.find("# All Other Commands\nelse:")
    ret_check_start = src.find("if ret is not None:")

    if outer_else_start == -1 or ret_check_start == -1:
        raise AssertionError(
            "Could not locate dispatch block or `if ret is not None:` "
            "in __main__.py — file structure may have changed"
        )

    dispatch_block = src[outer_else_start:ret_check_start]

    has_else_ret = (
        "else:\n        ret = None" in dispatch_block
        or "else:\n            ret = None" in dispatch_block
        or "else: ret = None" in dispatch_block
    )

    assert has_else_ret, (
        "__main__.py CLI dispatch block (lines 114-138) has no "
        "`else: ret = None` guard before `if ret is not None: print(...)`; "
        "any unrecognised cmd value or future branch that omits `ret =...` "
        "will raise UnboundLocalError at line 139"
    )
