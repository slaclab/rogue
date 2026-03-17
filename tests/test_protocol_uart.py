import contextlib

import pyrogue.protocols._uart as uart_mod
import rogue.interfaces.memory


class FakeSerial:
    def __init__(self, _device, _baud, timeout=1, **_kwargs):
        self.timeout = timeout
        self.writes = []
        self.read_bytes = bytearray()
        self.closed = False

    def queue_text(self, text):
        self.read_bytes.extend(text.encode("ASCII"))

    def read(self):
        if not self.read_bytes:
            return b""
        return bytes([self.read_bytes.pop(0)])

    def write(self, payload):
        self.writes.append(payload)

    def close(self):
        self.closed = True


class FakeThread:
    def __init__(self, target):
        self.target = target
        self.started = False

    def start(self):
        self.started = True


class FakeQueue:
    def __init__(self):
        self.items = []

    def put(self, item):
        self.items.append(item)

    def get(self):
        return self.items.pop(0)

    def join(self):
        pass

    def task_done(self):
        pass


class FakeTransaction:
    def __init__(self, *, address, size, tx_type, payload=None):
        self._address = address
        self._size = size
        self._type = tx_type
        self._payload = bytearray(payload or bytes(size))
        self.error_msg = None
        self.done_called = False
        self.readback = bytearray(size)

    def address(self):
        return self._address

    def size(self):
        return self._size

    def type(self):
        return self._type

    def getData(self, buffer, offset):
        buffer[:] = self._payload[offset:offset + len(buffer)]

    def setData(self, buffer, offset):
        self.readback[offset:offset + len(buffer)] = buffer

    def done(self):
        self.done_called = True

    def error(self, msg):
        self.error_msg = msg

    def lock(self):
        return contextlib.nullcontext()


def test_uart_memory_readline_and_context_manager(monkeypatch):
    serials = []
    monkeypatch.setattr(uart_mod.serial, "Serial", lambda *args, **kwargs: serials.append(FakeSerial(*args, **kwargs)) or serials[-1])
    monkeypatch.setattr(uart_mod.threading, "Thread", FakeThread)
    monkeypatch.setattr(uart_mod.queue, "Queue", FakeQueue)

    with uart_mod.UartMemory("/dev/ttyUSB0", 115200) as uart:
        assert uart._workerThread.started is True
        serials[0].queue_text("ok\r")
        assert uart.readline() == "ok\r"
        assert uart._workerQueue.items == []

    assert serials[0].closed is True


def test_uart_memory_write_and_read_transactions(monkeypatch):
    fake_serial = FakeSerial("/dev/null", 9600)
    monkeypatch.setattr(uart_mod.serial, "Serial", lambda *args, **kwargs: fake_serial)
    monkeypatch.setattr(uart_mod.threading, "Thread", FakeThread)

    uart = uart_mod.UartMemory("/dev/null", 9600)

    fake_serial.queue_text("w 00000010 04030201 00000000\n")
    write_tx = FakeTransaction(
        address=0x10,
        size=4,
        tx_type=rogue.interfaces.memory.Write,
        payload=b"\x01\x02\x03\x04",
    )
    uart._doWrite(write_tx)
    assert fake_serial.writes == [b"w 00000010 04030201 \n"]
    assert write_tx.done_called is True

    fake_serial.queue_text("r 00000020 11223344 00000000\n")
    read_tx = FakeTransaction(address=0x20, size=4, tx_type=rogue.interfaces.memory.Read)
    uart._doRead(read_tx)
    assert fake_serial.writes[-1] == b"r 00000020 \n"
    assert bytes(read_tx.readback) == b"\x44\x33\x22\x11"
    assert read_tx.done_called is True


def test_uart_memory_error_paths_and_worker_dispatch(monkeypatch):
    fake_serial = FakeSerial("/dev/null", 9600)
    monkeypatch.setattr(uart_mod.serial, "Serial", lambda *args, **kwargs: fake_serial)
    monkeypatch.setattr(uart_mod.threading, "Thread", FakeThread)

    uart = uart_mod.UartMemory("/dev/null", 9600)

    fake_serial.queue_text("")
    timeout_tx = FakeTransaction(address=0x30, size=4, tx_type=rogue.interfaces.memory.Read)
    uart._doRead(timeout_tx)
    assert "Empty transaction response" in timeout_tx.error_msg

    fake_serial.queue_text("w 00000040 deadbeef 00000001\n")
    status_tx = FakeTransaction(address=0x40, size=4, tx_type=rogue.interfaces.memory.Write, payload=b"\xef\xbe\xad\xde")
    uart._doWrite(status_tx)
    assert "Non zero status" in status_tx.error_msg

    # The worker should dispatch transactions by type and mark queue tasks done
    # so _stop() can safely join the queue.
    seen = []
    monkeypatch.setattr(uart, "_doWrite", lambda tx: seen.append(("write", tx.address())))
    monkeypatch.setattr(uart, "_doRead", lambda tx: seen.append(("read", tx.address())))

    write_tx = FakeTransaction(address=0x50, size=4, tx_type=rogue.interfaces.memory.Write)
    read_tx = FakeTransaction(address=0x54, size=4, tx_type=rogue.interfaces.memory.Verify)
    bad_tx = FakeTransaction(address=0x58, size=4, tx_type=rogue.interfaces.memory.Post)

    uart._workerQueue.put(write_tx)
    uart._workerQueue.put(read_tx)
    uart._workerQueue.put(bad_tx)
    uart._workerQueue.put(None)
    uart._worker()

    assert seen == [("write", 0x50), ("read", 0x54)]
    assert "Unsupported transaction type" in bad_tx.error_msg
