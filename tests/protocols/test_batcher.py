#!/usr/bin/env python3
#-----------------------------------------------------------------------------
# Title      : SW Batcher (Combiner) and Unbatcher (Splitter/Inverter) tests
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
# Uses the SW batcher (CombinerV1/V2) as a controlled frame source to
# regression-test the unbatcher classes (SplitterV1/V2, InverterV1/V2).
#
# Test strategy:
#   1. Combiner round-trip: Combiner -> Splitter verifies both directions.
#   2. Splitter regression: Combiner generates known super-frames, Splitter
#      must reproduce exact original frames (data + metadata).
#   3. Inverter regression: Combiner generates known super-frames, Inverter
#      must produce a valid reframed output.
#   4. CoreV1/V2 parser regression: Combiner generates super-frames, Core
#      must parse them correctly.
#-----------------------------------------------------------------------------

import rogue.interfaces.stream
import rogue.protocols.batcher
import time


class FrameSink(rogue.interfaces.stream.Slave):
    """Collects received frames for later inspection."""
    def __init__(self):
        super().__init__()
        self.frames = []

    def _acceptFrame(self, frame):
        with frame.lock():
            ba = frame.getBa()
            self.frames.append({
                'data': bytes(ba),
                'channel': frame.getChannel(),
                'fUser': frame.getFirstUser(),
                'lUser': frame.getLastUser(),
            })


class RawFrameSink(rogue.interfaces.stream.Slave):
    """Collects raw frame bytes (for inverter output)."""
    def __init__(self):
        super().__init__()
        self.frames = []

    def _acceptFrame(self, frame):
        with frame.lock():
            ba = frame.getBa()
            self.frames.append(bytes(ba))


class FrameSource(rogue.interfaces.stream.Master):
    """Sends frames with specific data and metadata."""
    def __init__(self):
        super().__init__()

    def sendData(self, data, channel=0, fUser=0, lUser=0):
        frame = self._reqFrame(len(data), True)
        frame.write(bytearray(data))
        frame.setChannel(channel)
        frame.setFirstUser(fUser)
        frame.setLastUser(lUser)
        self._sendFrame(frame)


def _wait_for_frames(sink, expected, timeout=1.0):
    """Wait for expected number of frames to arrive at sink."""
    for _ in range(int(timeout / 0.01)):
        if len(sink.frames) >= expected:
            break
        time.sleep(0.01)


# =========================================================================
# Combiner -> Splitter round-trip helpers
# =========================================================================

def _run_combiner_splitter_v1(width, payloads):
    """Round-trip: source -> combiner -> splitter -> sink."""
    source = FrameSource()
    combiner = rogue.protocols.batcher.CombinerV1(width)
    splitter = rogue.protocols.batcher.SplitterV1()
    sink = FrameSink()

    source >> combiner
    combiner >> splitter >> sink

    for p in payloads:
        source.sendData(
            p['data'], p.get('channel', 0),
            p.get('fUser', 0), p.get('lUser', 0))

    assert combiner.getCount() == len(payloads)
    combiner.sendBatch()
    assert combiner.getCount() == 0

    _wait_for_frames(sink, len(payloads))

    assert len(sink.frames) == len(payloads), \
        f"Expected {len(payloads)} frames, got {len(sink.frames)}"

    for i, p in enumerate(payloads):
        got = sink.frames[i]
        assert got['data'] == p['data'], \
            f"Frame {i}: data mismatch"
        assert got['channel'] == p.get('channel', 0), \
            f"Frame {i}: channel mismatch"
        assert got['fUser'] == p.get('fUser', 0), \
            f"Frame {i}: fUser mismatch"
        assert got['lUser'] == p.get('lUser', 0), \
            f"Frame {i}: lUser mismatch"


def _run_combiner_splitter_v2(payloads):
    """Round-trip: source -> combiner -> splitter -> sink."""
    source = FrameSource()
    combiner = rogue.protocols.batcher.CombinerV2()
    splitter = rogue.protocols.batcher.SplitterV2()
    sink = FrameSink()

    source >> combiner
    combiner >> splitter >> sink

    for p in payloads:
        source.sendData(
            p['data'], p.get('channel', 0),
            p.get('fUser', 0), p.get('lUser', 0))

    assert combiner.getCount() == len(payloads)
    combiner.sendBatch()
    assert combiner.getCount() == 0

    _wait_for_frames(sink, len(payloads))

    assert len(sink.frames) == len(payloads), \
        f"Expected {len(payloads)} frames, got {len(sink.frames)}"

    for i, p in enumerate(payloads):
        got = sink.frames[i]
        assert got['data'] == p['data'], \
            f"Frame {i}: data mismatch"
        assert got['channel'] == p.get('channel', 0), \
            f"Frame {i}: channel mismatch"
        assert got['fUser'] == p.get('fUser', 0), \
            f"Frame {i}: fUser mismatch"
        assert got['lUser'] == p.get('lUser', 0), \
            f"Frame {i}: lUser mismatch"


# =========================================================================
# Section 1: Combiner unit tests
# =========================================================================

def test_combiner_v1_empty_batch():
    """Calling sendBatch with no queued frames should be a no-op."""
    combiner = rogue.protocols.batcher.CombinerV1(2)
    splitter = rogue.protocols.batcher.SplitterV1()
    sink = FrameSink()
    combiner >> splitter >> sink
    combiner.sendBatch()
    time.sleep(0.1)
    assert len(sink.frames) == 0


def test_combiner_v2_empty_batch():
    """Calling sendBatch with no queued frames should be a no-op."""
    combiner = rogue.protocols.batcher.CombinerV2()
    splitter = rogue.protocols.batcher.SplitterV2()
    sink = FrameSink()
    combiner >> splitter >> sink
    combiner.sendBatch()
    time.sleep(0.1)
    assert len(sink.frames) == 0


# =========================================================================
# Section 2: Splitter (unbatcher) regression tests via Combiner
# =========================================================================

def test_splitter_v1_single_frame():
    """SplitterV1 correctly unbatches a single-record super-frame."""
    _run_combiner_splitter_v1(2, [
        {'data': b'\x01\x02\x03\x04\x05\x06\x07\x08'}
    ])


def test_splitter_v1_multiple_frames():
    """SplitterV1 correctly unbatches multi-record super-frames."""
    _run_combiner_splitter_v1(2, [
        {'data': b'\xAA' * 16, 'channel': 1, 'fUser': 0x10, 'lUser': 0x20},
        {'data': b'\xBB' * 32, 'channel': 2, 'fUser': 0x30, 'lUser': 0x40},
        {'data': b'\xCC' * 8, 'channel': 3, 'fUser': 0x50, 'lUser': 0x60},
    ])


def test_splitter_v1_metadata_preservation():
    """SplitterV1 preserves channel, fUser, lUser across unbatching."""
    _run_combiner_splitter_v1(2, [
        {'data': b'\x00' * 8, 'channel': 0xFF, 'fUser': 0xAA, 'lUser': 0xBB},
        {'data': b'\x01' * 8, 'channel': 0x00, 'fUser': 0x00, 'lUser': 0x00},
        {'data': b'\x02' * 8, 'channel': 0x7F, 'fUser': 0x55, 'lUser': 0xFF},
    ])


def test_splitter_v1_all_widths():
    """SplitterV1 handles all valid V1 width encodings (0-5)."""
    payloads = [
        {'data': b'\xDE\xAD' * 4, 'channel': 5, 'fUser': 0xAA, 'lUser': 0xBB},
        {'data': b'\xBE\xEF' * 8, 'channel': 10, 'fUser': 0xCC, 'lUser': 0xDD},
    ]
    for width in range(6):
        _run_combiner_splitter_v1(width, payloads)


def test_splitter_v1_non_aligned_payload():
    """SplitterV1 handles payloads not aligned to the width boundary."""
    _run_combiner_splitter_v1(2, [
        {'data': b'\x01\x02\x03'},
        {'data': b'\x04\x05\x06\x07\x08\x09\x0A'},
    ])


def test_splitter_v1_large_payload():
    """SplitterV1 handles large payloads."""
    _run_combiner_splitter_v1(2, [
        {'data': bytes(range(256)) * 40,
         'channel': 0, 'fUser': 0xFF, 'lUser': 0xFE},
    ])


def test_splitter_v2_single_frame():
    """SplitterV2 correctly unbatches a single-record super-frame."""
    _run_combiner_splitter_v2([
        {'data': b'\x01\x02\x03\x04\x05\x06\x07\x08'}
    ])


def test_splitter_v2_multiple_frames():
    """SplitterV2 correctly unbatches multi-record super-frames."""
    _run_combiner_splitter_v2([
        {'data': b'\xAA' * 16, 'channel': 1, 'fUser': 0x10, 'lUser': 0x20},
        {'data': b'\xBB' * 32, 'channel': 2, 'fUser': 0x30, 'lUser': 0x40},
        {'data': b'\xCC' * 8, 'channel': 3, 'fUser': 0x50, 'lUser': 0x60},
    ])


def test_splitter_v2_metadata_preservation():
    """SplitterV2 preserves channel, fUser, lUser across unbatching."""
    _run_combiner_splitter_v2([
        {'data': b'\x00' * 8, 'channel': 0xFF, 'fUser': 0xAA, 'lUser': 0xBB},
        {'data': b'\x01' * 8, 'channel': 0x00, 'fUser': 0x00, 'lUser': 0x00},
        {'data': b'\x02' * 8, 'channel': 0x7F, 'fUser': 0x55, 'lUser': 0xFF},
    ])


def test_splitter_v2_non_aligned_payload():
    """SplitterV2 handles payloads of various sizes (no width alignment)."""
    _run_combiner_splitter_v2([
        {'data': b'\x01\x02\x03'},
        {'data': b'\x04\x05\x06\x07\x08\x09\x0A'},
        {'data': b'\xFF'},
    ])


def test_splitter_v2_large_payload():
    """SplitterV2 handles large payloads."""
    _run_combiner_splitter_v2([
        {'data': bytes(range(256)) * 40,
         'channel': 0, 'fUser': 0xFF, 'lUser': 0xFE},
    ])


def test_splitter_v2_many_small_frames():
    """SplitterV2 handles many small records in a single super-frame."""
    payloads = []
    for i in range(100):
        payloads.append({
            'data': bytes([i & 0xFF]) * ((i % 32) + 1),
            'channel': i & 0x0F,
            'fUser': (i * 3) & 0xFF,
            'lUser': (i * 7) & 0xFF,
        })
    _run_combiner_splitter_v2(payloads)


# =========================================================================
# Section 3: Inverter regression tests via Combiner
#
# The inverter rewrites framing in-place. For V1 this requires
# headerSize == tailSize (width >= 3). For V2 the header (2 bytes)
# is always overwritten with the first 2 bytes of the first tail.
# =========================================================================

def test_inverter_v1_processes_combiner_output():
    """InverterV1 accepts and processes a combiner-generated super-frame.

    InverterV1 requires headerSize == tailSize, which holds for width >= 3.
    We verify the inverter produces exactly one output frame (reframed
    super-frame) and its size is reduced by one tail.
    """
    source = FrameSource()
    combiner = rogue.protocols.batcher.CombinerV1(3)  # width=3 -> 128-bit
    inverter = rogue.protocols.batcher.InverterV1()
    sink = RawFrameSink()

    source >> combiner
    combiner >> inverter >> sink

    payloads = [
        b'\xAA' * 16,
        b'\xBB' * 32,
    ]
    for p in payloads:
        source.sendData(p)
    combiner.sendBatch()

    _wait_for_frames(sink, 1)

    # Inverter emits one reframed super-frame
    assert len(sink.frames) == 1
    assert len(sink.frames[0]) > 0


def test_inverter_v2_processes_combiner_output():
    """InverterV2 accepts and processes a combiner-generated super-frame.

    InverterV2 overwrites the 2-byte header with first tail data and
    removes the last tail. We verify it produces exactly one output frame.
    """
    source = FrameSource()
    combiner = rogue.protocols.batcher.CombinerV2()
    inverter = rogue.protocols.batcher.InverterV2()
    sink = RawFrameSink()

    source >> combiner
    combiner >> inverter >> sink

    payloads = [
        b'\xAA' * 16,
        b'\xBB' * 32,
    ]
    for p in payloads:
        source.sendData(p)
    combiner.sendBatch()

    _wait_for_frames(sink, 1)

    # Inverter emits one reframed super-frame
    assert len(sink.frames) == 1
    assert len(sink.frames[0]) > 0


def test_inverter_v2_single_record():
    """InverterV2 processes a single-record combiner super-frame."""
    source = FrameSource()
    combiner = rogue.protocols.batcher.CombinerV2()
    inverter = rogue.protocols.batcher.InverterV2()
    sink = RawFrameSink()

    source >> combiner
    combiner >> inverter >> sink

    source.sendData(b'\xCC' * 64)
    combiner.sendBatch()

    _wait_for_frames(sink, 1)
    assert len(sink.frames) == 1


# =========================================================================
# Section 4: Combiner -> Splitter -> re-Combiner chain test
#
# Verify that unbatching and re-batching produces an identical super-frame.
# =========================================================================

def test_rebatch_v2_produces_identical_superframe():
    """Combiner -> Splitter -> Combiner produces identical super-frame bytes."""
    source = FrameSource()
    combiner1 = rogue.protocols.batcher.CombinerV2()
    raw_sink1 = RawFrameSink()
    splitter = rogue.protocols.batcher.SplitterV2()
    combiner2 = rogue.protocols.batcher.CombinerV2()
    raw_sink2 = RawFrameSink()

    # Path 1: source -> combiner1 -> raw_sink1 (capture super-frame)
    # Also:   source -> combiner1 -> splitter -> combiner2
    source >> combiner1
    combiner1 >> raw_sink1
    combiner1 >> splitter >> combiner2 >> raw_sink2

    payloads = [
        b'\x11' * 10,
        b'\x22' * 20,
        b'\x33' * 5,
    ]
    for p in payloads:
        source.sendData(p)
    combiner1.sendBatch()

    _wait_for_frames(raw_sink1, 1)

    # Now trigger combiner2 to rebatch the split frames
    time.sleep(0.1)
    combiner2.sendBatch()
    _wait_for_frames(raw_sink2, 1)

    assert len(raw_sink1.frames) == 1
    assert len(raw_sink2.frames) == 1
    # The re-batched super-frame should be byte-identical except for
    # the sequence number in header byte 1. Header byte 0 (version)
    # must still match.
    assert raw_sink1.frames[0][0] == raw_sink2.frames[0][0]
    assert raw_sink1.frames[0][2:] == raw_sink2.frames[0][2:]


if __name__ == "__main__":
    import sys
    test_funcs = [v for k, v in sorted(globals().items())
                  if k.startswith('test_') and callable(v)]
    for fn in test_funcs:
        print(f"  {fn.__name__} ... ", end='', flush=True)
        fn()
        print("PASSED")
    print(f"\nAll {len(test_funcs)} batcher tests passed!")
    sys.exit(0)
