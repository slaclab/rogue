#-----------------------------------------------------------------------------
# Company    : SLAC National Accelerator Laboratory
#-----------------------------------------------------------------------------
# Description:
#   Audit repro for PYDM-008.
#   python/pyrogue/pydm/rogue_plugin.py line 17 contains a top-level
#   `print("Loading Rogue Widgets Designer Plugins")` that executes on every
#   import of the module, not just in a Qt Designer context.  A library
#   module should not produce side-effect console output on import.
#   This test uses AST inspection and does not require PyDM or Qt to be
#   installed; it always runs.  On HEAD the print is present → FAILS.
#-----------------------------------------------------------------------------
# This file is part of the rogue software platform. It is subject to
# the license terms in the LICENSE.txt file found in the top-level directory
# of this distribution and at:
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
# No part of the rogue software platform, including this file, may be
# copied, modified, propagated, or distributed except according to the terms
# contained in the LICENSE.txt file.
#-----------------------------------------------------------------------------

import ast
import pathlib


def test_rogue_plugin_no_top_level_print_pydm_008():
    """PYDM-008: rogue_plugin.py has a top-level print() that runs on every import."""
    plugin_path = (
        pathlib.Path(__file__).parent.parent.parent
        / "python" / "pyrogue" / "pydm" / "rogue_plugin.py"
    )
    src = plugin_path.read_text()
    tree = ast.parse(src)

    # Walk only top-level statements (direct children of the module body).
    # A top-level print() is an ast.Expr whose value is an ast.Call to print.
    top_level_prints = []
    for node in ast.iter_child_nodes(tree):
        if (
            isinstance(node, ast.Expr)
            and isinstance(node.value, ast.Call)
            and isinstance(node.value.func, ast.Name)
            and node.value.func.id == "print"
        ):
            top_level_prints.append(node.lineno)

    assert len(top_level_prints) == 0, (
        "PYDM-008: rogue_plugin.py has top-level print() call(s) at "
        "line(s) " + str(top_level_prints) + " that execute on every "
        "import of the module; side-effect console output in a library "
        "module is unconventional and noisy"
    )
