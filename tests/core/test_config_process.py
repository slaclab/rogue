#-----------------------------------------------------------------------------
# This file is part of the rogue software platform. It is subject to
# the license terms in the LICENSE.txt file found in the top-level directory
# of this distribution and at:
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
# No part of the rogue software platform, including this file, may be
# copied, modified, propagated, or distributed except according to the terms
# contained in the LICENSE.txt file.
#-----------------------------------------------------------------------------

import glob

import pyrogue as pr


class ConfigProcessRoot(pr.Root):
    """Minimal root with one RW variable for config round-trip tests."""

    def __init__(self):
        super().__init__(name='root', pollEn=False)
        dev = pr.Device(name='TestDev')
        dev.add(pr.LocalVariable(name='TestValue', value=0, mode='RW'))
        self.add(dev)


# ---------------------------------------------------------------------------
# LoadConfig presence
# ---------------------------------------------------------------------------

def test_load_config_process_present_on_root():
    with ConfigProcessRoot() as root:
        assert isinstance(root.LoadConfigProcess, pr.LoadConfigProcess)
        assert hasattr(root.LoadConfigProcess, 'LoadMode')
        assert hasattr(root.LoadConfigProcess, 'ConfigFile')
        assert hasattr(root.LoadConfigProcess, 'YamlString')


# ---------------------------------------------------------------------------
# LoadConfig — String mode
# ---------------------------------------------------------------------------

def test_load_config_from_string(wait_until):
    with ConfigProcessRoot() as root:
        root.TestDev.TestValue.set(42)
        yml = root.getYaml(
            readFirst=False,
            modes=['RW', 'WO'],
            incGroups=None,
            excGroups='NoConfig',
            recurse=True,
        )

        root.TestDev.TestValue.set(0)
        assert root.TestDev.TestValue.value() == 0

        root.LoadConfigProcess.LoadMode.setDisp('String')
        root.LoadConfigProcess.YamlString.set(yml)
        root.LoadConfigProcess.Start()

        assert wait_until(lambda: root.LoadConfigProcess.Running.value() is False)
        assert root.TestDev.TestValue.value() == 42


def test_load_config_from_string_sets_message_and_progress(wait_until):
    with ConfigProcessRoot() as root:
        yml = root.getYaml(
            readFirst=False,
            modes=['RW', 'WO'],
            incGroups=None,
            excGroups='NoConfig',
            recurse=True,
        )
        root.LoadConfigProcess.LoadMode.setDisp('String')
        root.LoadConfigProcess.YamlString.set(yml)
        root.LoadConfigProcess.Start()

        assert wait_until(lambda: root.LoadConfigProcess.Running.value() is False)
        assert root.LoadConfigProcess.Message.value() == 'Done'
        assert root.LoadConfigProcess.Progress.value() == 1.0


# ---------------------------------------------------------------------------
# LoadConfig — File mode
# ---------------------------------------------------------------------------

def test_load_config_from_file(tmp_path, wait_until):
    with ConfigProcessRoot() as root:
        root.TestDev.TestValue.set(99)
        yml = root.getYaml(
            readFirst=False,
            modes=['RW', 'WO'],
            incGroups=None,
            excGroups='NoConfig',
            recurse=True,
        )
        cfg_file = tmp_path / 'config.yml'
        cfg_file.write_text(yml)

        root.TestDev.TestValue.set(0)
        assert root.TestDev.TestValue.value() == 0

        root.LoadConfigProcess.LoadMode.setDisp('File')
        root.LoadConfigProcess.ConfigFile.set(str(cfg_file))
        root.LoadConfigProcess.Start()

        assert wait_until(lambda: root.LoadConfigProcess.Running.value() is False)
        assert root.TestDev.TestValue.value() == 99


def test_load_config_from_file_sets_message_and_progress(tmp_path, wait_until):
    with ConfigProcessRoot() as root:
        yml = root.getYaml(
            readFirst=False,
            modes=['RW', 'WO'],
            incGroups=None,
            excGroups='NoConfig',
            recurse=True,
        )
        cfg_file = tmp_path / 'config.yml'
        cfg_file.write_text(yml)

        root.LoadConfigProcess.LoadMode.setDisp('File')
        root.LoadConfigProcess.ConfigFile.set(str(cfg_file))
        root.LoadConfigProcess.Start()

        assert wait_until(lambda: root.LoadConfigProcess.Running.value() is False)
        assert root.LoadConfigProcess.Message.value() == 'Done'
        assert root.LoadConfigProcess.Progress.value() == 1.0


# ---------------------------------------------------------------------------
# SaveConfig presence
# ---------------------------------------------------------------------------

def test_save_config_process_present_on_root():
    with ConfigProcessRoot() as root:
        assert isinstance(root.SaveConfigProcess, pr.SaveConfigProcess)
        assert hasattr(root.SaveConfigProcess, 'DataType')
        assert hasattr(root.SaveConfigProcess, 'SaveMode')
        assert hasattr(root.SaveConfigProcess, 'ConfigFile')
        assert hasattr(root.SaveConfigProcess, 'YamlString')


# ---------------------------------------------------------------------------
# SaveConfig — String mode
# ---------------------------------------------------------------------------

def test_save_config_as_string(wait_until):
    with ConfigProcessRoot() as root:
        root.TestDev.TestValue.set(7)

        root.SaveConfigProcess.DataType.setDisp('Config')
        root.SaveConfigProcess.SaveMode.setDisp('String')
        root.SaveConfigProcess.Start()

        assert wait_until(lambda: root.SaveConfigProcess.Running.value() is False)
        yml = root.SaveConfigProcess.YamlString.value()
        assert yml != ''
        assert 'TestValue' in yml


def test_save_status_as_string(wait_until):
    with ConfigProcessRoot() as root:
        root.TestDev.TestValue.set(3)

        root.SaveConfigProcess.DataType.setDisp('Status')
        root.SaveConfigProcess.SaveMode.setDisp('String')
        root.SaveConfigProcess.Start()

        assert wait_until(lambda: root.SaveConfigProcess.Running.value() is False)
        yml = root.SaveConfigProcess.YamlString.value()
        assert yml != ''
        assert 'TestValue' in yml


def test_save_config_as_string_sets_message_and_progress(wait_until):
    with ConfigProcessRoot() as root:
        root.SaveConfigProcess.DataType.setDisp('Config')
        root.SaveConfigProcess.SaveMode.setDisp('String')
        root.SaveConfigProcess.Start()

        assert wait_until(lambda: root.SaveConfigProcess.Running.value() is False)
        assert root.SaveConfigProcess.Message.value() == 'Done'
        assert root.SaveConfigProcess.Progress.value() == 1.0


# ---------------------------------------------------------------------------
# SaveConfig — File mode
# ---------------------------------------------------------------------------

def test_save_config_to_file(tmp_path, wait_until):
    with ConfigProcessRoot() as root:
        root.TestDev.TestValue.set(55)
        cfg_file = tmp_path / 'out.yml'

        root.SaveConfigProcess.DataType.setDisp('Config')
        root.SaveConfigProcess.SaveMode.setDisp('File')
        root.SaveConfigProcess.ConfigFile.set(str(cfg_file))
        root.SaveConfigProcess.Start()

        assert wait_until(lambda: root.SaveConfigProcess.Running.value() is False)
        assert cfg_file.exists()
        content = cfg_file.read_text()
        assert 'TestValue' in content


def test_save_status_to_file(tmp_path, wait_until):
    with ConfigProcessRoot() as root:
        root.TestDev.TestValue.set(11)
        state_file = tmp_path / 'state.yml'

        root.SaveConfigProcess.DataType.setDisp('Status')
        root.SaveConfigProcess.SaveMode.setDisp('File')
        root.SaveConfigProcess.ConfigFile.set(str(state_file))
        root.SaveConfigProcess.Start()

        assert wait_until(lambda: root.SaveConfigProcess.Running.value() is False)
        assert state_file.exists()
        content = state_file.read_text()
        assert 'TestValue' in content


def test_save_config_autonames_file_when_config_file_is_empty(tmp_path, monkeypatch, wait_until):
    monkeypatch.chdir(tmp_path)
    with ConfigProcessRoot() as root:
        root.SaveConfigProcess.DataType.setDisp('Config')
        root.SaveConfigProcess.SaveMode.setDisp('File')
        root.SaveConfigProcess.ConfigFile.set('')
        root.SaveConfigProcess.Start()

        assert wait_until(lambda: root.SaveConfigProcess.Running.value() is False)
        matches = glob.glob('config_*.yml')
        assert len(matches) == 1


# ---------------------------------------------------------------------------
# Round-trip: SaveConfig String → LoadConfig String
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Error handling — bad inputs
# ---------------------------------------------------------------------------

def test_load_config_file_mode_empty_path_sets_error_message(wait_until):
    with ConfigProcessRoot() as root:
        root.LoadConfigProcess.LoadMode.setDisp('File')
        root.LoadConfigProcess.ConfigFile.set('')
        root.LoadConfigProcess.Start()

        assert wait_until(lambda: root.LoadConfigProcess.Running.value() is False)
        assert root.LoadConfigProcess.Message.value().startswith('Error:')
        assert root.LoadConfigProcess.Progress.value() == 1.0


def test_load_config_string_mode_empty_yaml_sets_error_message(wait_until):
    with ConfigProcessRoot() as root:
        root.LoadConfigProcess.LoadMode.setDisp('String')
        root.LoadConfigProcess.YamlString.set('')
        root.LoadConfigProcess.Start()

        assert wait_until(lambda: root.LoadConfigProcess.Running.value() is False)
        assert root.LoadConfigProcess.Message.value().startswith('Error:')
        assert root.LoadConfigProcess.Progress.value() == 1.0


def test_load_config_file_mode_missing_file_sets_error_message(wait_until):
    with ConfigProcessRoot() as root:
        root.LoadConfigProcess.LoadMode.setDisp('File')
        root.LoadConfigProcess.ConfigFile.set('/nonexistent/path/config.yml')
        root.LoadConfigProcess.Start()

        assert wait_until(lambda: root.LoadConfigProcess.Running.value() is False)
        assert root.LoadConfigProcess.Message.value().startswith('Error:')
        assert root.LoadConfigProcess.Progress.value() == 1.0


def test_save_config_file_mode_bad_path_sets_error_message(wait_until):
    with ConfigProcessRoot() as root:
        root.SaveConfigProcess.DataType.setDisp('Config')
        root.SaveConfigProcess.SaveMode.setDisp('File')
        root.SaveConfigProcess.ConfigFile.set('/nonexistent/dir/out.yml')
        root.SaveConfigProcess.Start()

        assert wait_until(lambda: root.SaveConfigProcess.Running.value() is False)
        assert root.SaveConfigProcess.Message.value().startswith('Error:')
        assert root.SaveConfigProcess.Progress.value() == 1.0


# ---------------------------------------------------------------------------
# Stop is ignored
# ---------------------------------------------------------------------------

def test_load_config_stop_is_ignored(wait_until):
    with ConfigProcessRoot() as root:
        yml = root.getYaml(
            readFirst=False, modes=['RW', 'WO'],
            incGroups=None, excGroups='NoConfig', recurse=True,
        )
        root.LoadConfigProcess.LoadMode.setDisp('String')
        root.LoadConfigProcess.YamlString.set(yml)
        root.LoadConfigProcess.Start()
        root.LoadConfigProcess.Stop()  # should not crash or abort

        assert wait_until(lambda: root.LoadConfigProcess.Running.value() is False)
        assert root.LoadConfigProcess.Message.value() == 'Done'


def test_save_config_stop_is_ignored(wait_until):
    with ConfigProcessRoot() as root:
        root.SaveConfigProcess.DataType.setDisp('Config')
        root.SaveConfigProcess.SaveMode.setDisp('String')
        root.SaveConfigProcess.Start()
        root.SaveConfigProcess.Stop()  # should not crash or abort

        assert wait_until(lambda: root.SaveConfigProcess.Running.value() is False)
        assert root.SaveConfigProcess.Message.value() == 'Done'


# ---------------------------------------------------------------------------
# Round-trip
# ---------------------------------------------------------------------------

def test_save_then_load_config_round_trip(wait_until):
    with ConfigProcessRoot() as root:
        root.TestDev.TestValue.set(123)

        root.SaveConfigProcess.DataType.setDisp('Config')
        root.SaveConfigProcess.SaveMode.setDisp('String')
        root.SaveConfigProcess.Start()
        assert wait_until(lambda: root.SaveConfigProcess.Running.value() is False)
        saved_yml = root.SaveConfigProcess.YamlString.value()
        assert saved_yml != ''

        root.TestDev.TestValue.set(0)

        root.LoadConfigProcess.LoadMode.setDisp('String')
        root.LoadConfigProcess.YamlString.set(saved_yml)
        root.LoadConfigProcess.Start()
        assert wait_until(lambda: root.LoadConfigProcess.Running.value() is False)

        assert root.TestDev.TestValue.value() == 123
