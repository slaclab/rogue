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

import pytest

try:
    from pydm import Display  # noqa: F401
    from qtpy.QtWidgets import QWidget  # noqa: F401
except Exception as exc:
    pytest.skip(
        f"PyDM/Qt test dependencies unavailable: {exc}",
        allow_module_level=True,
    )


def test_import_pydm_top():
    from pyrogue.pydm.pydmTop import DefaultTop
    assert DefaultTop is not None


def test_import_time_plot_top():
    from pyrogue.pydm.TimePlotTop import TimePlotTop
    assert TimePlotTop is not None


def test_import_data_writer():
    from pyrogue.pydm.widgets.data_writer import DataWriter
    assert DataWriter is not None


def test_import_debug_tree():
    from pyrogue.pydm.widgets.debug_tree import DebugDev
    assert DebugDev is not None


def test_import_designer():
    from pyrogue.pydm.widgets import designer  # noqa: F401


def test_import_label():
    from pyrogue.pydm.widgets.label import PyRogueLabel
    assert PyRogueLabel is not None


def test_import_line_edit():
    from pyrogue.pydm.widgets.line_edit import PyRogueLineEdit
    assert PyRogueLineEdit is not None


def test_import_plot():
    from pyrogue.pydm.widgets.plot import Plotter
    assert Plotter is not None


def test_import_process():
    from pyrogue.pydm.widgets.process import Process
    assert Process is not None


def test_import_root_control():
    from pyrogue.pydm.widgets.root_control import RootControl
    assert RootControl is not None


def test_import_run_control():
    from pyrogue.pydm.widgets.run_control import RunControl
    assert RunControl is not None


def test_import_system_log():
    from pyrogue.pydm.widgets.system_log import SystemLog
    assert SystemLog is not None


def test_import_system_window():
    from pyrogue.pydm.widgets.system_window import SystemWindow
    assert SystemWindow is not None


def test_import_time_plotter():
    from pyrogue.pydm.widgets.time_plotter import DebugDev as TimePlotDebugDev
    assert TimePlotDebugDev is not None


def test_import_generic_file_tool():
    from pyrogue.pydm.tools.generic_file_tool import OpenFileBrowse
    assert OpenFileBrowse is not None


def test_import_node_info_tool():
    from pyrogue.pydm.tools.node_info_tool import NodeInformation
    assert NodeInformation is not None


def test_import_read_node_tool():
    from pyrogue.pydm.tools.read_node_tool import ReadNode
    assert ReadNode is not None


def test_import_read_recursive_tool():
    from pyrogue.pydm.tools.read_recursive_tool import ReadRecursive
    assert ReadRecursive is not None


def test_import_write_node_tool():
    from pyrogue.pydm.tools.write_node_tool import WriteVariable
    assert WriteVariable is not None


def test_import_write_recursive_tool():
    from pyrogue.pydm.tools.write_recursive_tool import WriteVariable as WriteRecursive
    assert WriteRecursive is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
