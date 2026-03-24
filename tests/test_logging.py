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

import pyrogue as pr
from pyrogue._Root import RootLogHandler


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
