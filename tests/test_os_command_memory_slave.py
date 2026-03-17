import pyrogue as pr
import pyrogue.interfaces._OsCommandMemorySlave as ocms_mod
import rogue.interfaces.memory
import pytest


class FakeTransaction:
    def __init__(self, *, address, size, tx_type, payload=None):
        self._address = address
        self._size = size
        self._type = tx_type
        self._payload = bytearray(payload or bytes(size))
        self.error_msg = None
        self.done_called = False
        self.readback = None

    def address(self):
        return self._address

    def size(self):
        return self._size

    def type(self):
        return self._type

    def getData(self, buffer, offset):
        buffer[:] = self._payload[offset:offset + len(buffer)]

    def setData(self, buffer, offset):
        self.readback = bytes(buffer[offset:offset + len(buffer)])

    def done(self):
        self.done_called = True

    def error(self, msg):
        self.error_msg = msg


def test_os_command_memory_slave_dispatches_reads_and_writes():
    slave = ocms_mod.OsCommandMemorySlave()
    calls = []

    @slave.command(0x10, pr.UInt(8))
    def write_read(_slave, arg):
        calls.append(arg)
        if arg is None:
            return 9

    write_tx = FakeTransaction(address=0x10, size=1, tx_type=rogue.interfaces.memory.Write, payload=b"\x07")
    slave._doTransaction(write_tx)
    assert calls == [7]
    assert write_tx.done_called is True

    read_tx = FakeTransaction(address=0x10, size=1, tx_type=rogue.interfaces.memory.Read)
    slave._doTransaction(read_tx)
    assert calls == [7, None]
    assert read_tx.readback == b"\x09"
    assert read_tx.done_called is True


def test_os_command_memory_slave_reports_errors_and_duplicate_addresses():
    slave = ocms_mod.OsCommandMemorySlave()

    missing_tx = FakeTransaction(address=0x44, size=1, tx_type=rogue.interfaces.memory.Read)
    slave._doTransaction(missing_tx)
    assert "not found" in missing_tx.error_msg

    @slave.command(0x20, pr.UInt(8))
    def boom(_slave, arg):
        raise RuntimeError(f"bad {arg}")

    write_tx = FakeTransaction(address=0x20, size=1, tx_type=rogue.interfaces.memory.Post, payload=b"\x03")
    slave._doTransaction(write_tx)
    assert "Transaction write error" in write_tx.error_msg

    read_tx = FakeTransaction(address=0x20, size=1, tx_type=rogue.interfaces.memory.Read)
    slave._doTransaction(read_tx)
    assert "Transaction read error" in read_tx.error_msg

    with pytest.raises(pr.CommandError, match="Duplicate address"):
        @slave.command(0x20, pr.UInt(8))
        def duplicate(_slave, arg):
            return arg
