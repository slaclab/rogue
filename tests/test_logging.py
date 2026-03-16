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

import json
import logging

import pytest

import pyrogue as pr
import rogue
import rogue.interfaces.memory


class LoggingDevice(pr.Device):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)


class EmulateDevice(pr.Device):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.add(pr.RemoteVariable(
            name='TestValue',
            offset=0x0,
            bitSize=32,
            mode='RW',
            base=pr.UInt,
        ))


class ListHandler(logging.Handler):
    def __init__(self):
        super().__init__()
        self.records = []

    def emit(self, record):
        self.records.append(record)


def test_logging_name_and_level_helpers():
    dev = LoggingDevice(name='LogDev')
    logger = logging.getLogger('pyrogue.custom.logger')

    assert pr.logName('memory.Emulate') == 'pyrogue.memory.Emulate'
    assert pr.logName('pyrogue.memory.Emulate') == 'pyrogue.memory.Emulate'
    assert pr.logName(logger) == 'pyrogue.custom.logger'
    assert LoggingDevice.classLogName() == 'pyrogue.Device.LoggingDevice'
    assert dev.logName() == 'pyrogue.Device.LoggingDevice.LogDev'

    name = pr.setLogLevel(dev, 'INFO')
    assert name == dev.logName()
    assert logging.getLogger(name).level == logging.INFO

    class_name = LoggingDevice.setClassLogLevel('DEBUG', includeRogue=False)
    assert class_name == LoggingDevice.classLogName()
    assert logging.getLogger(class_name).level == logging.DEBUG

    dev_logger = logging.getLogger(dev.logName())
    dev_logger.setLevel(logging.WARNING)
    dev.setLogLevel('ERROR', includePython=False)
    assert dev_logger.level == logging.WARNING

    with pytest.raises(ValueError, match='Unknown logging level'):
        pr.setLogLevel(dev, 'NOT_A_LEVEL', includeRogue=False)


def test_unified_logging_helpers_toggle_native_state():
    pr.setUnifiedLogging(False)

    try:
        assert pr.unifiedLoggingEnabled() is False
        assert rogue.Logging.forwardPython() is False
        assert rogue.Logging.emitStdout() is True

        pr.setUnifiedLogging(True)

        assert pr.unifiedLoggingEnabled() is True
        assert rogue.Logging.forwardPython() is True
        assert rogue.Logging.emitStdout() is False

    finally:
        pr.setUnifiedLogging(False)


def test_unified_logging_forwards_cpp_logs_after_filter_update():
    logger_name = 'pyrogue.memory.Emulate'
    logger = logging.getLogger(logger_name)
    handler = ListHandler()

    logger.setLevel(logging.DEBUG)
    logger.addHandler(handler)
    pr.setUnifiedLogging(True)

    try:
        # Build a minimal memory-backed tree so a native C++ logger can emit
        # through a normal PyRogue write path.
        root = pr.Root(name='root', pollEn=False)
        emu = rogue.interfaces.memory.Emulate(4, 0x1000)
        root.addInterface(emu)
        root.add(EmulateDevice(name='Dev', offset=0x0, memBase=emu))

        try:
            root.start()
            assert handler.records == []

            # The logger already exists on the C++ side, so this checks that
            # post-creation filter updates are applied to active loggers.
            rogue.Logging.setFilter(logger_name, rogue.Logging.Debug)
            root.Dev.TestValue.set(1)

            matches = [record for record in handler.records if 'Allocating block at 0x0.' in record.getMessage()]
            assert len(matches) == 1

            record = matches[0]
            assert record.name == logger_name
            assert record.levelno == logging.DEBUG
            assert record.rogue_cpp is True
            assert record.rogue_logger == logger_name
            assert record.rogue_component == 'memory'
            assert record.rogue_tid is not None
            assert record.rogue_pid is not None
        finally:
            root.stop()

    finally:
        pr.setUnifiedLogging(False)
        logger.removeHandler(handler)


def test_non_unified_logging_does_not_forward_cpp_logs_to_python():
    logger_name = 'pyrogue.memory.Emulate'
    logger = logging.getLogger(logger_name)
    handler = ListHandler()

    logger.setLevel(logging.DEBUG)
    logger.addHandler(handler)
    pr.setUnifiedLogging(False)

    try:
        rogue.Logging.setFilter(logger_name, rogue.Logging.Debug)

        # Exercise the same native C++ logger path as the unified test, but
        # leave forwarding disabled and assert that Python sees nothing.
        root = pr.Root(name='root', pollEn=False)
        emu = rogue.interfaces.memory.Emulate(4, 0x1000)
        root.addInterface(emu)
        root.add(EmulateDevice(name='Dev', offset=0x0, memBase=emu))

        try:
            root.start()
            root.Dev.TestValue.set(1)
        finally:
            root.stop()

        assert handler.records == []

    finally:
        logger.removeHandler(handler)


def test_root_system_log_captures_metadata_and_limits_history():
    logger = logging.getLogger('pyrogue.test.logging')
    logger.setLevel(logging.INFO)

    pr.setUnifiedLogging(False)

    try:
        with pr.Root(name='root', pollEn=False, maxLog=3, unifyLogs=True) as root:
            assert pr.unifiedLoggingEnabled() is True

            root._clearLog()

            for idx in range(5):
                extra = {}

                if idx == 4:
                    # Mirror the extra fields attached to forwarded native
                    # Rogue records so RootLogHandler stores them in SystemLog.
                    extra = {
                        'rogue_cpp': True,
                        'rogue_tid': 11,
                        'rogue_pid': 22,
                        'rogue_logger': 'pyrogue.memory.Emulate',
                        'rogue_timestamp': 123.4,
                        'rogue_component': 'memory',
                    }

                logger.info('message %s', idx, extra=extra)

            last = json.loads(root.SystemLogLast.value())
            entries = json.loads(root.SystemLog.value())

        assert len(entries) == 3
        assert [entry['message'] for entry in entries] == ['message 2', 'message 3', 'message 4']
        assert last['name'] == 'pyrogue.test.logging'
        assert last['message'] == 'message 4'
        assert last['levelName'] == 'INFO'
        assert last['rogueCpp'] is True
        assert last['rogueTid'] == 11
        assert last['roguePid'] == 22
        assert last['rogueLogger'] == 'pyrogue.memory.Emulate'
        assert last['rogueTimestamp'] == 123.4
        assert last['rogueComponent'] == 'memory'

    finally:
        pr.setUnifiedLogging(False)
