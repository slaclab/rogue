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

import struct
import time

import rogue.interfaces.stream
import pytest

from conftest import wait_for

pytestmark = pytest.mark.integration

DRAIN_TIMEOUT = 5.0


class FrameCapture(rogue.interfaces.stream.Slave):
    """Capture frames as raw bytes."""

    def __init__(self):
        super().__init__()
        self.frames = []

    def _acceptFrame(self, frame):
        self.frames.append(bytes(frame.getBa()))


def _inject_frame(master, data):
    """Send a frame with given bytes through a stream.Master."""
    frame = master._reqFrame(len(data), True)
    frame.write(data)
    master._sendFrame(frame)


def test_stream_tcp_single_frame(free_tcp_port):
    server = rogue.interfaces.stream.TcpServer("127.0.0.1", free_tcp_port)
    client = rogue.interfaces.stream.TcpClient("127.0.0.1", free_tcp_port)

    inject = rogue.interfaces.stream.Master()
    capture = FrameCapture()

    server << inject
    capture << client

    try:
        time.sleep(1.0)

        payload = struct.pack('<IIII', 0xDEADBEEF, 0xCAFEBABE, 0x12345678, 0x9ABCDEF0)
        _inject_frame(inject, payload)

        assert wait_for(lambda: len(capture.frames) == 1, timeout=DRAIN_TIMEOUT)
        assert capture.frames[0] == payload
    finally:
        server.close()
        client.close()


def test_stream_tcp_bidirectional(free_tcp_port):
    server = rogue.interfaces.stream.TcpServer("127.0.0.1", free_tcp_port)
    client = rogue.interfaces.stream.TcpClient("127.0.0.1", free_tcp_port)

    inject_srv = rogue.interfaces.stream.Master()
    inject_cli = rogue.interfaces.stream.Master()
    capture_srv = FrameCapture()
    capture_cli = FrameCapture()

    server << inject_srv
    capture_cli << client

    client << inject_cli
    capture_srv << server

    try:
        time.sleep(1.0)

        payload_a = b'\xAA' * 64
        payload_b = b'\xBB' * 64
        _inject_frame(inject_srv, payload_a)
        _inject_frame(inject_cli, payload_b)

        assert wait_for(lambda: len(capture_cli.frames) >= 1, timeout=DRAIN_TIMEOUT)
        assert wait_for(lambda: len(capture_srv.frames) >= 1, timeout=DRAIN_TIMEOUT)

        assert capture_cli.frames[0] == payload_a
        assert capture_srv.frames[0] == payload_b
    finally:
        server.close()
        client.close()


def test_stream_tcp_multiple_frames(free_tcp_port):
    server = rogue.interfaces.stream.TcpServer("127.0.0.1", free_tcp_port)
    client = rogue.interfaces.stream.TcpClient("127.0.0.1", free_tcp_port)

    inject = rogue.interfaces.stream.Master()
    capture = FrameCapture()

    server << inject
    capture << client

    try:
        time.sleep(1.0)

        count = 50
        for i in range(count):
            payload = struct.pack('<I', i) + b'\x00' * 28
            _inject_frame(inject, payload)

        assert wait_for(lambda: len(capture.frames) == count, timeout=DRAIN_TIMEOUT)

        for i, frame_data in enumerate(capture.frames):
            val = struct.unpack_from('<I', frame_data, 0)[0]
            assert val == i
    finally:
        server.close()
        client.close()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
