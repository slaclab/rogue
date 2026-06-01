#-----------------------------------------------------------------------------
# Company    : SLAC National Accelerator Laboratory
#-----------------------------------------------------------------------------
#  Description:
#       PyRogue base module - Configuration Process Classes
#-----------------------------------------------------------------------------
# This file is part of the rogue software platform. It is subject to
# the license terms in the LICENSE.txt file found in the top-level directory
# of this distribution and at:
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
# No part of the rogue software platform, including this file, may be
# copied, modified, propagated, or distributed except according to the terms
# contained in the LICENSE.txt file.
#-----------------------------------------------------------------------------
from __future__ import annotations

import threading
from typing import Any

import pyrogue as pr


class LoadConfigProcess(pr.Process):
    """Process that loads configuration into the tree from a file or YAML string.

    Exposes the same configuration load paths as the built-in ``LoadConfig``
    and ``SetYamlConfig`` Root commands, but as a ``Process`` with operator-
    visible progress and status reporting.

    The ``LoadMode`` Variable selects the data source:

    * ``File`` (0): reads from the path stored in ``ConfigFile``.  Equivalent
      to the ``LoadConfig`` Root command.
    * ``String`` (1): applies the YAML text stored in ``YamlString``.
      Equivalent to the ``SetYamlConfig`` Root command.

    Both modes apply only RW and WO Variables while excluding those tagged
    with the ``NoConfig`` group.  If ``Root.InitAfterConfig`` is enabled the
    root will call ``initialize()`` after the configuration is applied.

    The ``Stop`` command has no effect because the underlying YAML load
    operations are not interruptible.  Any error during the operation is
    captured in ``Message`` and ``Progress`` is set to 100 %.

    Parameters
    ----------
    **kwargs : Any
        Additional arguments forwarded to ``Process``.
    """

    def __init__(self, **kwargs: Any) -> None:
        pr.Process.__init__(self, **kwargs)

        self.add(pr.LocalVariable(
            name='LoadMode',
            mode='RW',
            value=0,
            disp={0: 'File', 1: 'String'},
            description='Source of configuration data: File reads from ConfigFile; String applies YamlString.'))

        self.add(pr.LocalVariable(
            name='ConfigFile',
            mode='RW',
            value='',
            description='Path to YAML configuration file. Used when LoadMode is File.'))

        self.add(pr.LocalVariable(
            name='YamlString',
            mode='RW',
            value='',
            description='YAML configuration text to apply. Used when LoadMode is String.'))

    def _stopProcess(self) -> None:
        # loadYaml and setYaml are not interruptible; Stop is ignored.
        self._log.warning('%s: Stop is not supported; operation will run to completion.', self.name)

    def _stop(self) -> None:
        # Wait for any in-flight operation to finish before device teardown.
        thr = self._thread
        if thr is not None and thr.is_alive() and threading.current_thread() is not thr:
            thr.join()
        pr.Device._stop(self)

    def _process(self) -> None:
        self.Message.setDisp('Running')
        self.setProgress(0.0)

        try:
            if self.LoadMode.value() == 0:
                cfg = str(self.ConfigFile.value()).strip()
                if not cfg:
                    raise ValueError('ConfigFile is empty')
                self.root.loadYaml(
                    name=cfg,
                    writeEach=False,
                    modes=['RW', 'WO'],
                    incGroups=None,
                    excGroups='NoConfig',
                )
            else:
                yml = str(self.YamlString.value())
                if not yml.strip():
                    raise ValueError('YamlString is empty')
                self.root.setYaml(
                    yml=yml,
                    writeEach=False,
                    modes=['RW', 'WO'],
                    incGroups=None,
                    excGroups='NoConfig',
                )
            self.Message.setDisp('Done')
            self.setProgress(1.0)
        except Exception as e:
            self.Message.setDisp(f'Error: {e}')
            self.setProgress(1.0)


class SaveConfigProcess(pr.Process):
    """Process that saves configuration or state to a file or YAML string variable.

    Exposes the same save and export paths as the built-in ``SaveConfig``,
    ``SaveState``, ``GetYamlConfig``, and ``GetYamlState`` Root commands, but
    as a ``Process`` with operator-visible progress and status reporting.

    Two Variables control what is saved and where:

    ``DataType`` selects the variable filter set:

    * ``Config`` (0): includes RW and WO Variables, excludes ``NoConfig``
      group.  Equivalent to ``SaveConfig`` / ``GetYamlConfig``.
    * ``Status`` (1): includes RW, RO, and WO Variables, excludes ``NoState``
      group.  Equivalent to ``SaveState`` / ``GetYamlState``.

    ``SaveMode`` selects the output destination:

    * ``File`` (0): writes YAML to the path in ``ConfigFile``.  If
      ``ConfigFile`` is empty a timestamped filename is generated automatically
      (``config_YYYYMMDD_HHMMSS.yml`` for Config, ``state_YYYYMMDD_HHMMSS.yml.zip``
      for Status).
    * ``String`` (1): stores the YAML text in the ``YamlString`` Variable.

    The ``Stop`` command has no effect because the underlying YAML save
    operations are not interruptible.  Any error during the operation is
    captured in ``Message`` and ``Progress`` is set to 100 %.

    Parameters
    ----------
    **kwargs : Any
        Additional arguments forwarded to ``Process``.
    """

    def __init__(self, **kwargs: Any) -> None:
        pr.Process.__init__(self, **kwargs)

        self.add(pr.LocalVariable(
            name='DataType',
            mode='RW',
            value=0,
            disp={0: 'Config', 1: 'Status'},
            description='Variable set to include: Config uses RW/WO modes excluding NoConfig; Status uses RW/RO/WO modes excluding NoState.'))

        self.add(pr.LocalVariable(
            name='SaveMode',
            mode='RW',
            value=0,
            disp={0: 'File', 1: 'String'},
            description='Output destination: File writes to ConfigFile; String stores the result in YamlString.'))

        self.add(pr.LocalVariable(
            name='ConfigFile',
            mode='RW',
            value='',
            description='Output file path. Used when SaveMode is File. Auto-named with a timestamp prefix if empty.'))

        self.add(pr.LocalVariable(
            name='YamlString',
            mode='RO',
            value='',
            description='Captured YAML output. Populated when SaveMode is String.'))

    def _stopProcess(self) -> None:
        # saveYaml and getYaml are not interruptible; Stop is ignored.
        self._log.warning('%s: Stop is not supported; operation will run to completion.', self.name)

    def _stop(self) -> None:
        # Wait for any in-flight operation to finish before device teardown.
        thr = self._thread
        if thr is not None and thr.is_alive() and threading.current_thread() is not thr:
            thr.join()
        pr.Device._stop(self)

    def _process(self) -> None:
        self.Message.setDisp('Running')
        self.setProgress(0.0)

        try:
            if self.DataType.value() == 0:
                modes = ['RW', 'WO']
                excGroups: str | list[str] | None = 'NoConfig'
                autoPrefix = 'config'
                autoCompress = False
            else:
                modes = ['RW', 'RO', 'WO']
                excGroups = 'NoState'
                autoPrefix = 'state'
                autoCompress = True

            if self.SaveMode.value() == 0:
                self.root.saveYaml(
                    name=self.ConfigFile.value(),
                    readFirst=True,
                    modes=modes,
                    incGroups=None,
                    excGroups=excGroups,
                    autoPrefix=autoPrefix,
                    autoCompress=autoCompress,
                )
            else:
                yml = self.root.getYaml(
                    readFirst=True,
                    modes=modes,
                    incGroups=None,
                    excGroups=excGroups,
                    recurse=True,
                )
                self.YamlString.set(yml)

            self.Message.setDisp('Done')
            self.setProgress(1.0)
        except Exception as e:
            self.Message.setDisp(f'Error: {e}')
            self.setProgress(1.0)
