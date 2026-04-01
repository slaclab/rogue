#!/usr/bin/env python3
# ----------------------------------------------------------------------------
# This file is part of the rogue software platform. It is subject to
# the license terms in the LICENSE.txt file found in the top-level directory
# of this distribution and at:
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
# No part of the rogue software platform, including this file, may be
# copied, modified, propagated, or distributed except according to the terms
# contained in the LICENSE.txt file.
# ----------------------------------------------------------------------------

import queue
import threading

import pyrogue
import rogue.interfaces.memory

from pyrogue.protocols._uart import UartMemory


class FakeTransaction:
    def __init__(self, transaction_type):
        self._transaction_type = transaction_type
        self._lock = threading.Lock()
        self.errors = []
        self.done_called = False

    def lock(self):
        return self._lock

    def type(self):
        return self._transaction_type

    def error(self, msg):
        self.errors.append(msg)

    def done(self):
        self.done_called = True


def test_uart_worker_marks_task_done_when_write_transaction_raises():
    uart = UartMemory.__new__(UartMemory)
    uart._log = pyrogue.logInit(name="test-uart")
    uart._workerQueue = queue.Queue()

    def fail_transaction(transaction):
        raise ValueError("boom")

    uart._doWrite = fail_transaction
    uart._doRead = lambda transaction: None

    transaction = FakeTransaction(rogue.interfaces.memory.Write)
    uart._workerQueue.put(transaction)
    uart._workerQueue.put(None)

    uart._worker()

    assert uart._workerQueue.unfinished_tasks == 0
    assert not transaction.done_called
    assert len(transaction.errors) == 1
    assert "Unhandled UART worker exception: boom" in transaction.errors[0]


def test_uart_worker_marks_task_done_when_verify_transaction_raises():
    uart = UartMemory.__new__(UartMemory)
    uart._log = pyrogue.logInit(name="test-uart")
    uart._workerQueue = queue.Queue()

    def fail_transaction(transaction):
        raise ValueError("boom")

    uart._doWrite = lambda transaction: None
    uart._doRead = fail_transaction

    transaction = FakeTransaction(rogue.interfaces.memory.Verify)
    uart._workerQueue.put(transaction)
    uart._workerQueue.put(None)

    uart._worker()

    assert uart._workerQueue.unfinished_tasks == 0
    assert not transaction.done_called
    assert len(transaction.errors) == 1
    assert "Unhandled UART worker exception: boom" in transaction.errors[0]
