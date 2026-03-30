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
import json
import logging

import pytest

import pyrogue as pr
import rogue
import rogue.interfaces.memory
from pyrogue._Root import RootLogHandler


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


class RaisingHandler(logging.Handler):
    def emit(self, record):
        raise RuntimeError('boom')


class FakeSystemLogVariable:
    def __init__(self, name):
        self._log = logging.getLogger(f'pyrogue.Variable.LocalVariable.root.{name}')
        self._value = '[]' if name == 'SystemLog' else ''
        self.calls = 0
        self.overflow = False
        self.lock = contextlib.nullcontext()
        self.path = f'root.{name}'

    def set(self, value):
        self.calls += 1

        if self.calls > 5:
            self.overflow = True
            return

        self._log.debug("%s.set(%r)", self.path, value)
        self._value = value

    def value(self):
        return self._value


class FakeLogRoot:
    running = True
    _maxLog = 5

    def __init__(self):
        self.SystemLog = FakeSystemLogVariable('SystemLog')
        self.SystemLogLast = FakeSystemLogVariable('SystemLogLast')

    @contextlib.contextmanager
    def updateGroup(self):
        yield


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


def test_unified_logging_respects_python_logger_level_filtering():
    logger_name = 'pyrogue.memory.Emulate'
    logger = logging.getLogger(logger_name)
    handler = ListHandler()

    logger.setLevel(logging.ERROR)
    logger.addHandler(handler)
    pr.setUnifiedLogging(True)

    try:
        root = pr.Root(name='root', pollEn=False)
        emu = rogue.interfaces.memory.Emulate(4, 0x1000)
        root.addInterface(emu)
        root.add(EmulateDevice(name='Dev', offset=0x0, memBase=emu))

        try:
            root.start()
            rogue.Logging.setFilter(logger_name, rogue.Logging.Debug)
            root.Dev.TestValue.set(1)
        finally:
            root.stop()

        assert handler.records == []

    finally:
        pr.setUnifiedLogging(False)
        logger.removeHandler(handler)


def test_unified_logging_swallows_python_handler_exceptions():
    logger_name = 'pyrogue.memory.Emulate'
    logger = logging.getLogger(logger_name)
    handler = RaisingHandler()

    logger.setLevel(logging.DEBUG)
    logger.addHandler(handler)
    pr.setUnifiedLogging(True)

    try:
        root = pr.Root(name='root', pollEn=False)
        emu = rogue.interfaces.memory.Emulate(4, 0x1000)
        root.addInterface(emu)
        root.add(EmulateDevice(name='Dev', offset=0x0, memBase=emu))

        try:
            root.start()
            rogue.Logging.setFilter(logger_name, rogue.Logging.Debug)
            root.Dev.TestValue.set(1)
        finally:
            root.stop()

    finally:
        pr.setUnifiedLogging(False)
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


def test_root_log_handler_ignores_system_log_bookkeeping_records():
    logger = logging.getLogger('pyrogue')
    handler = RootLogHandler(root=FakeLogRoot())
    old_level = logger.level
    old_handlers = list(logger.handlers)

    for existing in list(logger.handlers):
        logger.removeHandler(existing)

    logger.addHandler(handler)
    logger.setLevel(logging.DEBUG)

    try:
        logging.getLogger('pyrogue.test.feedback').debug('trigger')

        entries = json.loads(handler._root.SystemLog.value())

        assert handler._root.SystemLogLast.overflow is False
        assert handler._root.SystemLog.overflow is False
        assert handler._root.SystemLogLast.calls == 1
        assert handler._root.SystemLog.calls == 1
        assert [entry['message'] for entry in entries] == ['trigger']
    finally:
        logger.removeHandler(handler)
        logger.setLevel(old_level)
        for existing in old_handlers:
            logger.addHandler(existing)


def test_root_debug_logging_does_not_feedback_through_system_log(monkeypatch):
    logger = logging.getLogger('pyrogue')
    trigger_logger = logging.getLogger('pyrogue.test.feedback')
    old_level = logger.level
    old_trigger_level = trigger_logger.level

    try:
        logger.setLevel(logging.INFO)
        trigger_logger.setLevel(logging.DEBUG)

        with pr.Root(name='root', pollEn=False, maxLog=10) as root:
            counts = {'SystemLog': 0, 'SystemLogLast': 0}
            loop_detected = {'value': False}

            root.waitOnUpdate()
            root._clearLog()

            def wrap(name, original):
                def capped(*args, **kwargs):
                    counts[name] += 1

                    if counts[name] > 5:
                        loop_detected['value'] = True
                        return None

                    return original(*args, **kwargs)

                return capped

            monkeypatch.setattr(root.SystemLog, 'set', wrap('SystemLog', root.SystemLog.set))
            monkeypatch.setattr(root.SystemLogLast, 'set', wrap('SystemLogLast', root.SystemLogLast.set))

            logger.setLevel(logging.DEBUG)
            trigger_logger.debug('trigger')
            root.waitOnUpdate()
            logger.setLevel(logging.CRITICAL)

            entries = json.loads(root.SystemLog.value())

        assert loop_detected['value'] is False
        assert counts == {'SystemLog': 1, 'SystemLogLast': 1}
        assert [entry['message'] for entry in entries] == ['trigger']
    finally:
        logger.setLevel(old_level)
        trigger_logger.setLevel(old_trigger_level)
