#-----------------------------------------------------------------------------
# This file is part of the rogue software platform. It is subject to
# the license terms in the LICENSE.txt file found in the top-level directory
# of this distribution and at:
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
# No part of the rogue software platform, including this file, may be
# copied, modified, propagated, or distributed except according to the terms
# contained in the LICENSE.txt file.
#-----------------------------------------------------------------------------

from contextlib import contextmanager

import numpy
import pyrogue as pr


class FakeFrame:
    def __init__(self, payload, error=0):
        self._payload = payload
        self._error = error

    @contextmanager
    def lock(self):
        yield self

    def getError(self):
        return self._error

    def getPayload(self):
        return len(self._payload)

    def getNumpy(self, start, length):
        return numpy.array(self._payload[start:start + length], dtype=numpy.uint8)


def test_data_receiver_processes_frames_and_counts():
    rx = pr.DataReceiver(name="Rx", enableOnStart=False)
    root = pr.Root(name="root", pollEn=False)
    root.add(rx)

    with root:
        # Start disabled so the test can verify the early-return path first.
        rx._acceptFrame(FakeFrame([1, 2, 3]))
        assert rx.FrameCount.value() == 0
        assert rx.ByteCount.value() == 0

        rx.RxEnable.set(True)
        rx._acceptFrame(FakeFrame([1, 2, 3, 4]))

        assert rx.FrameCount.value() == 1
        assert rx.ErrorCount.value() == 0
        assert rx.ByteCount.value() == 4
        assert rx.Updated.value() is True
        assert rx.Data.value().tolist() == [1, 2, 3, 4]


def test_data_receiver_error_path_reset_and_stream_connect(monkeypatch):
    rx = pr.DataReceiver(name="Rx")
    root = pr.Root(name="root", pollEn=False)
    root.add(rx)

    with root:
        rx._acceptFrame(FakeFrame([9, 8], error=1))
        assert rx.FrameCount.value() == 0
        assert rx.ErrorCount.value() == 1
        assert rx.ByteCount.value() == 0

        rx.FrameCount.set(9)
        rx.ErrorCount.set(3)
        rx.ByteCount.set(12)
        rx.countReset()
        assert rx.FrameCount.value() == 0
        assert rx.ErrorCount.value() == 0
        assert rx.ByteCount.value() == 0

        rx._stop()
        assert rx.RxEnable.value() is False
        rx._start()
        assert rx.RxEnable.value() is True

    connections = []
    monkeypatch.setattr(pr, "streamConnect", lambda source, dest: connections.append((source, dest)))

    marker = object()
    assert (rx >> marker) is marker
    assert (rx << marker) is marker
    assert connections == [(rx, marker), (marker, rx)]


def test_data_receiver_disables_type_check():
    root = pr.Root(name="root", pollEn=False)
    root.add(pr.DataReceiver(name="Rx"))

    with root:
        root.Rx.Data.set({"decoded": 1}, write=True)
        assert root.Rx.Data.get() == {"decoded": 1}
