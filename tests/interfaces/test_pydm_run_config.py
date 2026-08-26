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

import contextlib
import importlib.util
import sys
import types
from pathlib import Path


def _load_pydm_module(call_log, app_log=None):
    """Load the module under stubs and return it with the stubs removed again.

    Suitable for entry points that resolve everything they need at import time.
    Use :func:`_stubbedPydmModule` for ``runPyDM``, which imports lazily inside
    the function body and so needs the stubs to still be present when called.
    """
    with _stubbedPydmModule(call_log, app_log=app_log) as module:
        return module


@contextlib.contextmanager
def _stubbedPydmModule(call_log, app_log=None):
    module_path = Path(__file__).resolve().parents[2] / "python/pyrogue/pydm/__init__.py"

    class FakeMainWindow:
        home_widget = None

        def set_display_widget(self, widget):
            pass

    class FakeApp:
        """Records the display arguments runPyDM assembles."""

        def __init__(self, **kwargs):
            if app_log is not None:
                app_log.append(kwargs)
            self.main_window = FakeMainWindow()

        @staticmethod
        def instance():
            return None

        def exec(self):
            return 0

    fake_pydm = types.ModuleType("pydm")
    fake_pydm.PyDMApplication = FakeApp
    fake_pydm.Display = type("FakeDisplay", (), {})

    # runPyDM checks for a pre-existing QApplication before building its own.
    fake_qtpy = types.ModuleType("qtpy")
    fake_qtpy.__path__ = []
    fake_qtpy_widgets = types.ModuleType("qtpy.QtWidgets")
    fake_qtpy_widgets.QApplication = type(
        "FakeQApplication", (), {"instance": staticmethod(lambda: None)})
    fake_qtpy.QtWidgets = fake_qtpy_widgets

    fake_pydm_data_plugins = types.ModuleType("pydm.data_plugins")
    fake_pydm_data_plugins.plugin_modules = {}
    fake_pydm_data_plugins.initialize_plugins_if_needed = lambda: None
    fake_pydm_data_plugins.add_plugin = lambda plugin: None
    fake_pydm.data_plugins = fake_pydm_data_plugins

    fake_pydm_widgets = types.ModuleType("pydm.widgets")
    fake_pydm_widgets.__path__ = []

    fake_pydm_widgets_rules = types.ModuleType("pydm.widgets.rules")
    fake_pydm_widgets_rules.register_widget_rules = lambda widget: None

    fake_pydm_utilities = types.ModuleType("pydm.utilities")
    fake_pydm_utilities.establish_widget_connections = lambda widget: None

    fake_pyrogue = types.ModuleType("pyrogue")
    fake_pyrogue.__path__ = []

    fake_pyrogue_interfaces = types.ModuleType("pyrogue.interfaces")

    class FakeVirtualClient:
        def __init__(self, **kwargs):
            call_log.append(kwargs)

    fake_pyrogue_interfaces.VirtualClient = FakeVirtualClient

    fake_pyrogue_pydm = types.ModuleType("pyrogue.pydm")
    fake_pyrogue_pydm.__path__ = []

    fake_rogue_plugin_module = types.ModuleType("pyrogue.pydm.data_plugins.rogue_plugin")
    fake_rogue_plugin_module.RoguePlugin = object()

    saved_modules = {}
    for name, module in {
        "pydm": fake_pydm,
        "pydm.data_plugins": fake_pydm_data_plugins,
        "pydm.widgets": fake_pydm_widgets,
        "pydm.widgets.rules": fake_pydm_widgets_rules,
        "pydm.utilities": fake_pydm_utilities,
        "qtpy": fake_qtpy,
        "qtpy.QtWidgets": fake_qtpy_widgets,
        "pyrogue": fake_pyrogue,
        "pyrogue.interfaces": fake_pyrogue_interfaces,
        "pyrogue.pydm": fake_pyrogue_pydm,
        "pyrogue.pydm.data_plugins.rogue_plugin": fake_rogue_plugin_module,
    }.items():
        saved_modules[name] = sys.modules.get(name)
        sys.modules[name] = module

    try:
        spec = importlib.util.spec_from_file_location("rogue_test_pydm_module", module_path)
        module = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(module)
        yield module
    finally:
        for name, original in saved_modules.items():
            if original is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = original


def test_configure_virtual_clients_applies_timeouts_to_each_server():
    call_log = []
    module = _load_pydm_module(call_log)

    module._configureVirtualClients(
        "host-a:9099, host-b:9103",
        linkTimeout=25.0,
        requestStallTimeout=None,
    )

    assert call_log == [
        {
            "addr": "host-a",
            "port": 9099,
            "linkTimeout": 25.0,
            "requestStallTimeout": None,
        },
        {
            "addr": "host-b",
            "port": 9103,
            "linkTimeout": 25.0,
            "requestStallTimeout": None,
        },
    ]


def _runPyDMArgs(monkeypatch, **kwargs):
    """Run runPyDM against stubs and return the display argument list."""
    app_log = []

    with _stubbedPydmModule([], app_log=app_log) as module:
        # runPyDM installs process-wide handlers; keep them out of the session.
        monkeypatch.setattr(module.signal, "signal", lambda *a: None)
        monkeypatch.setenv("ROGUE_SERVERS", "")
        module.runPyDM(serverList="localhost:9099", **kwargs)

    assert len(app_log) == 1
    return app_log[0]["command_line_args"]


def test_run_pydm_defaults_enable_terminal_to_false(monkeypatch):
    assert "enableTerminal=False" in _runPyDMArgs(monkeypatch)


def test_run_pydm_forwards_enable_terminal(monkeypatch):
    # Pins the exact string DefaultTop._parseBoolArg has to consume. This is the
    # only part of the option plumbing that spans two files.
    assert "enableTerminal=True" in _runPyDMArgs(monkeypatch, enableTerminal=True)
