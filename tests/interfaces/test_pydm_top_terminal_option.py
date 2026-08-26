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

# Checks how DefaultTop parses the enableTerminal display argument and where the
# resulting tab lands. pydm, qtpy and the widget package are stubbed, so this
# needs no Qt binding and no display.

import contextlib
import importlib.util
import sys
import types
from pathlib import Path

import pytest


class FakeTabWidget:
    """Records tabs and the selected index."""

    def __init__(self):
        self.tabs = []
        self.currentIndex = None

    def addTab(self, widget, label):
        self.tabs.append((widget, label))

    def setCurrentIndex(self, index):
        self.currentIndex = index


@contextlib.contextmanager
def _stubbedPydmTop(terminalLog, tabLog):
    modulePath = Path(__file__).resolve().parents[2] / "python/pyrogue/pydm/pydmTop.py"

    fakePydm = types.ModuleType("pydm")

    class FakeDisplay:
        def __init__(self, parent=None, args=None, macros=None):
            pass

        def setWindowTitle(self, title):
            self.windowTitle = title

        def setLayout(self, layout):
            pass

        def resize(self, x, y):
            self.size = (x, y)

    fakePydm.Display = FakeDisplay

    class FakeLayout:
        def __init__(self):
            self.widgets = []

        def addWidget(self, widget, stretch=0):
            self.widgets.append(widget)

    def makeTab():
        tab = FakeTabWidget()
        tabLog.append(tab)
        return tab

    fakeQtpy = types.ModuleType("qtpy")
    fakeQtpy.__path__ = []
    fakeQtWidgets = types.ModuleType("qtpy.QtWidgets")
    fakeQtWidgets.QVBoxLayout = FakeLayout
    fakeQtWidgets.QTabWidget = makeTab
    fakeQtWidgets.QWidget = type("FakeQWidget", (), {})
    fakeQtpy.QtWidgets = fakeQtWidgets

    def makeTerminal(parent=None):
        terminal = object()
        terminalLog.append(terminal)
        return terminal

    fakeWidgets = types.ModuleType("pyrogue.pydm.widgets")
    fakeWidgets.SystemWindow = lambda parent=None, init_channel=None: object()
    fakeWidgets.DebugTree = lambda parent=None, init_channel=None: object()
    fakeWidgets.TerminalPanel = makeTerminal

    fakePyrogue = types.ModuleType("pyrogue")
    fakePyrogue.__path__ = []
    fakePyroguePydm = types.ModuleType("pyrogue.pydm")
    fakePyroguePydm.__path__ = []

    saved = {}
    for name, module in {
        "pydm": fakePydm,
        "qtpy": fakeQtpy,
        "qtpy.QtWidgets": fakeQtWidgets,
        "pyrogue": fakePyrogue,
        "pyrogue.pydm": fakePyroguePydm,
        "pyrogue.pydm.widgets": fakeWidgets,
    }.items():
        saved[name] = sys.modules.get(name)
        sys.modules[name] = module

    try:
        spec = importlib.util.spec_from_file_location("rogue_test_pydm_top", modulePath)
        module = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(module)
        yield module
    finally:
        for name, original in saved.items():
            if original is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = original


def _build(args):
    """Construct DefaultTop with the given display args."""
    terminalLog = []
    tabLog = []

    with _stubbedPydmTop(terminalLog, tabLog) as module:
        top = module.DefaultTop(parent=None, args=args, macros=None)

    return (top, terminalLog, tabLog[0])


def _labels(tab):
    return [label for _widget, label in tab.tabs]


# ---------------------------------------------------------------------------
# Boolean argument parsing
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("value,expected", [
    ("True", True),
    ("true", True),
    ("1", True),
    ("yes", True),
    ("on", True),
    ("False", False),
    ("false", False),
    ("0", False),
    ("", False),
])
def test_parse_bool_arg_values(value, expected):
    with _stubbedPydmTop([], []) as module:
        assert module._parseBoolArg([f"enableTerminal={value}"], "enableTerminal") is expected


def test_parse_bool_arg_absent_returns_none():
    # None rather than False so the caller keeps its own default.
    with _stubbedPydmTop([], []) as module:
        assert module._parseBoolArg(["sizeX=800"], "enableTerminal") is None


def test_parse_bool_arg_ignores_quotes():
    with _stubbedPydmTop([], []) as module:
        assert module._parseBoolArg(["enableTerminal='True'"], "enableTerminal") is True


# ---------------------------------------------------------------------------
# Tab layout
# ---------------------------------------------------------------------------

def test_default_tabs_are_unchanged_when_disabled():
    # Nothing about an existing GUI changes unless the terminal is asked for.
    top, terminals, tab = _build(["sizeX=800", "enableTerminal=False"])
    assert _labels(tab) == ['System', 'Debug Tree']
    assert terminals == []
    assert top.terminal is None


def test_terminal_is_added_as_a_top_level_tab():
    top, terminals, tab = _build(["enableTerminal=True"])
    assert _labels(tab) == ['System', 'Debug Tree', 'Terminal']
    assert len(terminals) == 1
    assert top.terminal is terminals[0]


def test_terminal_is_the_last_tab():
    # Appended last so the System and Debug Tree indexes are the same whether or
    # not the terminal is enabled.
    _top, _terminals, tab = _build(["enableTerminal=True"])
    assert _labels(tab).index('System') == 0
    assert _labels(tab).index('Debug Tree') == 1
    assert _labels(tab).index('Terminal') == 2


def test_default_tab_is_still_debug_tree():
    for args in (["enableTerminal=True"], ["enableTerminal=False"], []):
        _top, _terminals, tab = _build(args)
        assert tab.currentIndex == 1


def test_enable_terminal_inside_title_does_not_enable_it():
    # The older size and title arguments are matched with a substring test, so a
    # title containing the argument name would false-positive. _parseBoolArg
    # matches on a leading prefix instead.
    top, terminals, tab = _build(["title='enableTerminal=True'"])
    assert _labels(tab) == ['System', 'Debug Tree']
    assert terminals == []
    assert top.terminal is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
