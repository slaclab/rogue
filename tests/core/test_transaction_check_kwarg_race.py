#-----------------------------------------------------------------------------
# This file is part of the rogue software platform. It is subject to
# the license terms in the LICENSE.txt file found in the top-level directory
# of this distribution and at:
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
# No part of the rogue software platform, including this file, may be
# copied, modified, propagated, or distributed except according to the terms
# contained in the LICENSE.txt file.
#-----------------------------------------------------------------------------
#
# Regression coverage for the transaction-completion contract on every public
# PyRogue path that issues a single-block hardware transaction.
#
# Background
# ----------
# pr.startTransaction() accepts a `wait` keyword argument; when True it
# instructs rim::Block::startTransaction to wait for the slave to acknowledge
# the transaction before returning. Several callers in pyrogue historically
# passed `checkEach=True` instead of the then-required `check=True`, which was
# silently dropped into the function's **kwargs. The wait was
# therefore disabled, allowing back-to-back operations (notably
# BaseCommand.toggle which issues set(1); set(0)) to race the shared
# blockData_ buffer: the second caller mutates the buffer before the slave's
# worker has consumed the data pointer for the first transaction, the slave
# observes the post-mutation value for both, and the hardware never sees the
# rising edge. In the field this manifests as "status counter reset never
# fires" on PGPv4 and any other RemoteCommand that uses BaseCommand.toggle
# against an asynchronous memory slave (SRP-over-UDP/TCP, network bridges,
# DMA-backed AXI masters).
#
# The typo was introduced by commit cff241ea (2020-08-11, "Fix command and
# poll queue") on RemoteCommand.set/get, and the same pattern was cloned
# into RemoteVariable.post and Device.{write,read,verify}Blocks. The
# block-list helpers in _Block.py (writeBlocks, readBlocks, verifyBlocks,
# writeAndVerifyBlocks, readAndWaitBlocks) correctly translate
# `waitEach=` to `wait=` and are not affected.
#
# These tests pin the contract at two levels:
#   - Contract: each caller must pass `wait=True` (or `wait=waitEach`
#     where waitEach is the caller's own parameter) to pr.startTransaction
#     so the underlying C++ Block waits for slave completion before
#     returning.
#   - Behavior: with a memory slave that consumes the staged data
#     asynchronously, the toggle pattern must deliver 1 then 0 to the slave
#     in order. Without the wait the slave observes 0 twice.

import threading
import time

import pyrogue as pr
import rogue
import rogue.interfaces.memory as rim
from conftest import MemoryRoot


# ---------------------------------------------------------------------------
# Shared device fixtures
# ---------------------------------------------------------------------------

class _CmdDevice(pr.Device):
    """Device exposing both a RemoteCommand and a RemoteVariable so a single
    test root can exercise every transaction-issuing PyRogue path."""

    def __init__(self, mem_base, **kwargs):
        super().__init__(memBase=mem_base, **kwargs)
        self.add(pr.RemoteCommand(
            name="CountReset",
            description="Status Counter Reset Command",
            offset=0x0,
            bitOffset=0,
            bitSize=1,
            function=pr.BaseCommand.toggle,
        ))
        self.add(pr.RemoteVariable(
            name="Strobe",
            description="Posted-write strobe register",
            offset=0x4,
            bitSize=8,
            base=pr.UInt,
            mode="RW",
        ))


class _CmdRoot(MemoryRoot):
    def __init__(self):
        super().__init__(name="root")
        self.add(_CmdDevice(name="Dev", mem_base=self._mem))


def _record_call(calls):
    """Build a monkeypatch target for pr.startTransaction that captures the
    full kwarg dict for later assertions."""
    def fake_start(block, **kwargs):
        calls.append({
            "type": kwargs.get("type"),
            "forceWr": kwargs.get("forceWr"),
            "wait": kwargs.get("wait"),
            "variable": kwargs.get("variable"),
            "index": kwargs.get("index"),
        })
    return fake_start


# ---------------------------------------------------------------------------
# Contract tests: RemoteCommand.set / RemoteCommand.get
# ---------------------------------------------------------------------------

def test_remote_command_set_passes_wait_true(monkeypatch):
    """RemoteCommand.set must request a waited write so BaseCommand.toggle
    cannot race the second set(0) against the first set(1)'s staged data."""
    calls = []
    monkeypatch.setattr(pr, "startTransaction", _record_call(calls))

    with _CmdRoot() as root:
        root.Dev.CountReset.set(1)

    assert len(calls) == 1
    assert calls[0]["type"] == rogue.interfaces.memory.Write
    assert calls[0]["forceWr"] is True
    assert calls[0]["wait"] is True, (
        "RemoteCommand.set() must pass wait=True to pr.startTransaction; "
        "missing wait causes BaseCommand.toggle to race the block buffer."
    )
    assert calls[0]["variable"] is root.Dev.CountReset
    assert calls[0]["index"] == -1


def test_remote_command_get_passes_wait_true(monkeypatch):
    """RemoteCommand.get must wait for the read transaction to complete
    before returning the cached block contents to the caller."""
    calls = []
    monkeypatch.setattr(pr, "startTransaction", _record_call(calls))

    with _CmdRoot() as root:
        root.Dev.CountReset.get()

    assert len(calls) == 1
    assert calls[0]["type"] == rogue.interfaces.memory.Read
    assert calls[0]["forceWr"] is False
    assert calls[0]["wait"] is True, (
        "RemoteCommand.get() must pass wait=True to pr.startTransaction."
    )
    assert calls[0]["variable"] is root.Dev.CountReset
    assert calls[0]["index"] == -1


# ---------------------------------------------------------------------------
# Contract test: RemoteVariable.post
# ---------------------------------------------------------------------------

def test_remote_variable_post_passes_wait_true(monkeypatch):
    """RemoteVariable.post must wait for the slave to consume the staged
    data. Two consecutive post() calls otherwise race the block buffer in
    exactly the same way as BaseCommand.toggle."""
    calls = []
    monkeypatch.setattr(pr, "startTransaction", _record_call(calls))

    with _CmdRoot() as root:
        root.Dev.Strobe.post(0xAA)

    assert len(calls) == 1
    assert calls[0]["type"] == rogue.interfaces.memory.Post
    assert calls[0]["forceWr"] is False
    assert calls[0]["wait"] is True, (
        "RemoteVariable.post() must pass wait=True to pr.startTransaction."
    )
    assert calls[0]["variable"] is root.Dev.Strobe
    assert calls[0]["index"] == -1


# ---------------------------------------------------------------------------
# Contract tests: Device.writeBlocks / readBlocks / verifyBlocks
#
# Two distinct code paths per direction:
#   - variable=<var> path:    issues one startTransaction(variable._block)
#   - block-iteration path:   issues one startTransaction per device block
# Both must forward the user-supplied waitEach value into `wait`.
# ---------------------------------------------------------------------------

def test_device_write_blocks_variable_path_propagates_wait(monkeypatch):
    """Device.writeBlocks(variable=X, waitEach=True) must call
    startTransaction with wait=True for the targeted variable's block."""
    calls = []
    monkeypatch.setattr(pr, "startTransaction", _record_call(calls))

    with _CmdRoot() as root:
        root.Dev.writeBlocks(force=True, recurse=False,
                             variable=root.Dev.Strobe, waitEach=True)

    assert len(calls) == 1
    assert calls[0]["type"] == rogue.interfaces.memory.Write
    assert calls[0]["forceWr"] is True
    assert calls[0]["wait"] is True
    assert calls[0]["variable"] is root.Dev.Strobe


def test_device_write_blocks_block_path_propagates_wait(monkeypatch):
    """Device.writeBlocks(waitEach=True) must call startTransaction with
    wait=True for every bulk-enabled block it iterates over."""
    calls = []
    monkeypatch.setattr(pr, "startTransaction", _record_call(calls))

    with _CmdRoot() as root:
        root.Dev.writeBlocks(force=True, recurse=False, waitEach=True)

    assert len(calls) >= 1
    for call in calls:
        assert call["type"] == rogue.interfaces.memory.Write
        assert call["forceWr"] is True
        assert call["wait"] is True


def test_device_read_blocks_variable_path_propagates_wait(monkeypatch):
    """Device.readBlocks(variable=X, waitEach=True) must call
    startTransaction with wait=True for the targeted variable's block."""
    calls = []
    monkeypatch.setattr(pr, "startTransaction", _record_call(calls))

    with _CmdRoot() as root:
        root.Dev.readBlocks(recurse=False, variable=root.Dev.Strobe,
                            waitEach=True)

    assert len(calls) == 1
    assert calls[0]["type"] == rogue.interfaces.memory.Read
    assert calls[0]["wait"] is True
    assert calls[0]["variable"] is root.Dev.Strobe


def test_device_read_blocks_block_path_propagates_wait(monkeypatch):
    """Device.readBlocks(waitEach=True) must call startTransaction with
    wait=True for every bulk-enabled block it iterates over."""
    calls = []
    monkeypatch.setattr(pr, "startTransaction", _record_call(calls))

    with _CmdRoot() as root:
        root.Dev.readBlocks(recurse=False, waitEach=True)

    assert len(calls) >= 1
    for call in calls:
        assert call["type"] == rogue.interfaces.memory.Read
        assert call["wait"] is True


def test_device_verify_blocks_variable_path_propagates_wait(monkeypatch):
    """Device.verifyBlocks(variable=X, waitEach=True) must call
    startTransaction with wait=True for the targeted variable's block.

    Unlike the write and read paths, the verify path forwards only the
    block (verify range is set by the prior write) and does not pass the
    variable through to startTransaction. Only the `wait` propagation is
    asserted here; the block-targeting is verified by call count.
    """
    calls = []
    monkeypatch.setattr(pr, "startTransaction", _record_call(calls))

    with _CmdRoot() as root:
        root.Dev.verifyBlocks(recurse=False, variable=root.Dev.Strobe,
                              waitEach=True)

    assert len(calls) == 1
    assert calls[0]["type"] == rogue.interfaces.memory.Verify
    assert calls[0]["wait"] is True


def test_device_verify_blocks_block_path_propagates_wait(monkeypatch):
    """Device.verifyBlocks(waitEach=True) must call startTransaction with
    wait=True for every bulk-enabled block it iterates over."""
    calls = []
    monkeypatch.setattr(pr, "startTransaction", _record_call(calls))

    with _CmdRoot() as root:
        root.Dev.verifyBlocks(recurse=False, waitEach=True)

    assert len(calls) >= 1
    for call in calls:
        assert call["type"] == rogue.interfaces.memory.Verify
        assert call["wait"] is True


# ---------------------------------------------------------------------------
# Behavioral regression: BaseCommand.toggle against an async slave
# ---------------------------------------------------------------------------

class AsyncDelayedMemorySlave(rim.Slave):
    """Memory slave that defers transaction consumption to a worker thread.

    Real-world memory slaves (SRP-over-UDP/TCP, network bridges, PCIe DMA
    masters with their own work queues) consume the caller's data pointer
    some time after doTransaction() returns. The Rogue Transaction stores
    iter_ as a raw pointer into the caller's blockData_ buffer; if the
    caller mutates that buffer before the slave's worker calls getData(),
    the slave reads the new value.

    This emulation lets a Python test reproduce that timing without needing
    a real network. Each transaction is handed off to a thread that sleeps
    ``delay`` seconds before snapshotting the data via getData().
    """

    def __init__(self, *, delay=0.05, mem_size=0x10000):
        rim.Slave.__init__(self, 4, mem_size)
        self._delay = delay
        self._mem_size = mem_size
        self._lock = threading.Lock()
        self._writes = []          # list of (address, value)
        self._reads_value = 0      # value returned on read transactions
        self._workers = []         # joined for clean test shutdown

    def _doMinAccess(self):
        return 4

    def _doMaxAccess(self):
        return self._mem_size

    def _doTransaction(self, transaction):
        t_type = transaction.type()
        t_size = transaction.size()
        t_addr = transaction.address()
        delay = self._delay

        def worker(tran=transaction):
            time.sleep(delay)
            try:
                with tran.lock():
                    if t_type in (rim.Write, rim.Post):
                        buf = bytearray(t_size)
                        tran.getData(buf, 0)
                        val = int.from_bytes(buf, "little", signed=False)
                        with self._lock:
                            self._writes.append((t_addr, val))
                        tran.done()
                    else:
                        with self._lock:
                            val = self._reads_value
                        tran.setData(val.to_bytes(t_size, "little", signed=False), 0)
                        tran.done()
            except Exception as exc:
                tran.error(str(exc))

        thread = threading.Thread(target=worker, daemon=True)
        with self._lock:
            self._workers.append(thread)
        thread.start()

    def join_workers(self, timeout=5.0):
        with self._lock:
            workers = list(self._workers)
        for t in workers:
            t.join(timeout)


class _RaceCommandDevice(pr.Device):
    def __init__(self, mem_base, **kwargs):
        super().__init__(memBase=mem_base, **kwargs)
        self.add(pr.RemoteCommand(
            name="CountReset",
            description="Status Counter Reset Command",
            offset=0x0,
            bitOffset=0,
            bitSize=1,
            function=pr.BaseCommand.toggle,
        ))


class _RaceRoot(pr.Root):
    def __init__(self, slave):
        super().__init__(name="root", pollEn=False)
        self._slave = slave
        self.addInterface(slave)
        self.add(_RaceCommandDevice(name="Dev", mem_base=slave))


def test_basecommand_toggle_delivers_one_then_zero_with_async_slave():
    """End-to-end regression: BaseCommand.toggle on a RemoteCommand must
    deliver value 1 followed by value 0 to the slave, even when the slave
    consumes the staged data asynchronously.

    With ``wait=True`` flowing through to rim::Block::startTransaction, the
    first set(1) blocks until the slave's worker has copied the data and
    acknowledged the transaction. Only then does set(0) get a chance to
    mutate the block buffer. The slave records ``[(addr, 1), (addr, 0)]``.

    Without the wait (the historical bug), set(0) returns to Python the
    moment its setBytes mutates blockData_ to 0, well before the slave's
    worker has read the buffer for transaction 1. Both transactions end
    up snapshotting the same (post-mutation) buffer value of 0, the slave
    records ``[(addr, 0), (addr, 0)]``, and the hardware never sees a
    rising edge on the reset bit.
    """
    slave = AsyncDelayedMemorySlave(delay=0.05)
    with _RaceRoot(slave) as root:
        cmd = root.Dev.CountReset
        pr.BaseCommand.toggle(cmd)
        slave.join_workers()

    values = [v for _, v in slave._writes]
    assert values == [1, 0], (
        f"BaseCommand.toggle should deliver [1, 0] to the slave but the slave "
        f"observed {values}. This indicates RemoteCommand.set() is not waiting "
        f"for transaction completion, allowing the second set() to race the "
        f"shared block buffer."
    )
