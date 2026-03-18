#-----------------------------------------------------------------------------
# This file is part of the rogue software platform. It is subject to
# the license terms in the LICENSE.txt file found in the top-level directory
# of this distribution and at:
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
# No part of the rogue software platform, including this file, may be
# copied, modified, propagated, or distributed except according to the terms
# contained in the LICENSE.txt file.
#-----------------------------------------------------------------------------

import pyrogue as pr
import pytest


class VariableCommandDevice(pr.Device):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._stored = 5
        self.callback_log = []

        self.add(pr.LocalVariable(
            name="ModeRW",
            value=1,
            mode="RW",
            groups=["Cfg"],
        ))

        self.add(pr.LocalVariable(
            name="ModeRO",
            value=2,
            mode="RO",
            groups=["Status"],
        ))

        self.add(pr.LocalVariable(
            name="ModeWO",
            value=3,
            mode="WO",
            groups=["Cfg"],
        ))

        self.add(pr.LocalVariable(
            name="EnumVar",
            value=0,
            enum={0: "Zero", 1: "One"},
        ))

        self.add(pr.LocalVariable(
            name="ArrayVar",
            value=[10, 20, 30],
        ))

        self.add(pr.LocalVariable(
            name="FormatterVar",
            value=255,
            disp="0x{:x}",
        ))

        self.add(pr.LocalVariable(
            name="PropertyVar",
            value=1.0,
            minimum=1.0,
            maximum=100.0,
        ))

        self.add(pr.LocalVariable(
            name="Source",
            value=7,
            localSet=self._set_stored,
            localGet=self._get_stored,
        ))

        self.add(pr.LinkVariable(
            name="Mirror",
            # Use the direct-variable shortcut so the test covers inherited
            # display/type metadata as well as dependency tracking.
            variable=self.Source,
        ))

        self.add(pr.LocalCommand(
            name="CommandWithArg",
            value=0,
            retValue="",
            function=self._command_with_arg,
        ))

        self.add(pr.LocalCommand(
            name="CommandNoArg",
            function=self._command_no_arg,
        ))

        self.add(pr.LocalCommand(
            name="CommandRaises",
            function=self._command_raises,
        ))

    def _set_stored(self, *, value, **_kwargs):
        self._stored = value

    def _get_stored(self, **_kwargs):
        return self._stored

    def _command_with_arg(self, root, dev, cmd, arg):
        self.callback_log.append((root.name, dev.name, cmd.name, arg))
        return f"{root.name}:{dev.name}:{cmd.name}:{arg}"

    def _command_no_arg(self, dev):
        self.callback_log.append(("no-arg", dev.name))
        return "done"

    def _command_raises(self):
        raise RuntimeError("boom")


class CommandRoot(pr.Root):
    def __init__(self):
        super().__init__(name="root", pollEn=False)
        self.add(VariableCommandDevice(name="Dev"))


def test_variable_disp_and_index_access():
    with CommandRoot() as root:
        root.Dev.EnumVar.setDisp("One")
        assert root.Dev.EnumVar.get() == 1
        assert root.Dev.EnumVar.getDisp() == "One"
        assert root.Dev.FormatterVar.valueDisp() == "0xff"

        root.Dev.ArrayVar.set(99, index=1)
        assert root.Dev.ArrayVar.get(index=1) == 99
        assert root.Dev.ArrayVar.value() == [10, 99, 30]


def test_variable_parse_errors_and_invalid_enum_display():
    with CommandRoot() as root:
        with pytest.raises(pr.VariableError):
            root.Dev.EnumVar.setDisp("Missing")

        root.Dev.EnumVar.set(3)
        assert root.Dev.EnumVar.getDisp(read=False) == "INVALID: 3"


def test_link_variable_tracks_dependency_and_variable_dict_filters():
    with CommandRoot() as root:
        root.Dev.Mirror.set(44)
        assert root.Dev.Source.get() == 44
        assert root.Dev.Mirror.get() == 44
        assert root.Dev.Mirror.dependencies == [root.Dev.Source]

        cfg = root.Dev._getDict(modes=["RW", "WO"], incGroups="Cfg")
        assert set(cfg.keys()) == {"ModeRW", "ModeWO"}

        status = root.Dev._getDict(modes=["RO"], incGroups="Status")
        assert set(status.keys()) == {"ModeRO"}


def test_local_variable_properties_and_poll_interval_round_trip():
    with CommandRoot() as root:
        root.Dev.PropertyVar.setPollInterval(1.0)
        assert root.Dev.PropertyVar.pollInterval == 1.0
        assert root.Dev.PropertyVar.minimum == 1.0
        assert root.Dev.PropertyVar.maximum == 100.0


def test_local_variable_constructor_errors():
    with pytest.raises(Exception):
        pr.LocalVariable(name="MissingValue")

    with pytest.raises(Exception):
        pr.LocalVariable(name="InvalidMode", value=0, mode="INV")


def test_command_call_metadata_and_exceptions():
    with CommandRoot() as root:
        assert root.Dev.CommandWithArg.arg is True
        assert root.Dev.CommandWithArg.retTypeStr == "str"
        assert root.Dev.CommandNoArg.arg is False

        ret = root.Dev.CommandWithArg.call(12)
        assert ret == "root:Dev:CommandWithArg:12"
        assert root.Dev.callback_log[-1] == ("root", "Dev", "CommandWithArg", 12)

        assert root.Dev.CommandWithArg.callDisp(13) == "root:Dev:CommandWithArg:13"
        assert root.Dev.CommandNoArg() == "done"

        with pytest.raises(RuntimeError, match="boom"):
            root.Dev.CommandRaises()
