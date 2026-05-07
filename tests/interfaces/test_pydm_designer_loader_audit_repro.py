#-----------------------------------------------------------------------------
# Company    : SLAC National Accelerator Laboratory
#-----------------------------------------------------------------------------
# Description:
#   Regression test pinning the post-fix invariant: no top-level print()
#   statements remain in pyrogue.pydm.rogue_plugin — a library module must
#   not produce side-effect console output on import.  Historical regression:
#   pre-fix HEAD had a top-level print("Loading Rogue Widgets Designer
#   Plugins") that fired on every import.  The test uses AST inspection and
#   does not require PyDM or Qt to be installed; it always runs.
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


def test_rogue_plugin_no_top_level_print():
    """rogue_plugin.py must not contain top-level print() calls.

    Post-fix invariant: importing pyrogue.pydm.rogue_plugin produces no
    side-effect console output — a library module should not print on
    import outside of an explicit Qt Designer context.  Historical
    regression: pre-fix HEAD had a top-level
    ``print("Loading Rogue Widgets Designer Plugins")`` that executed on
    every import of the module.
    """
    plugin_path = (
        pathlib.Path(__file__).parent.parent.parent
        / "python" / "pyrogue" / "pydm" / "rogue_plugin.py"
    )
    src = plugin_path.read_text()
    tree = ast.parse(src)

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
        "rogue_plugin.py has top-level print() call(s) at "
        "line(s) " + str(top_level_prints) + " that execute on every "
        "import of the module; side-effect console output in a library "
        "module is unconventional and noisy"
    )
