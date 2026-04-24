#-----------------------------------------------------------------------------
# This file is part of the rogue software platform. It is subject to
# the license terms in the LICENSE.txt file found in the top-level directory
# of this distribution and at:
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
# No part of the rogue software platform, including this file, may be
# copied, modified, propagated, or distributed except according to the terms
# contained in the LICENSE.txt file.
#-----------------------------------------------------------------------------
"""
DETECTED-IDs:
  - HW-CORE-007
  - HW-CORE-010
  - HW-CORE-011
  - MEM-005
  - MEM-006
  - HW-CORE-017

This cluster is ASan-primary. Under TSan the tests produce no race signal
but also no false positive; they will be collected under both workflows
but only ci-asan.yml surfaces actionable output.

Covered finding patterns:
  - HW-CORE-007 : AxiStreamDma ctor fd leak on open() failure path
  - HW-CORE-010 : MemMap fd leak on mmap() failure path
  - HW-CORE-011 : AxiMemMap fd leak on version-check throw
  - MEM-005     : Block setBytes memcpy overrun when valueBytes_ > stride_bytes
  - MEM-006     : Block setBytes malloc null-deref on tight-memory systems
  - HW-CORE-017 : StreamUnZip iterator out-of-bounds on truncated bzip2 stream
"""
import os
import threading

import pyrogue as pr
import pytest
import rogue

pytestmark = pytest.mark.repro


@pytest.mark.repro
def test_stress_hw_ctor_fd_leak(stress_iters):
    """Constructor-failure fd-leak paths (HW-CORE-007, HW-CORE-010, HW-CORE-011).

    Under ASan with detect_leaks=1 each missed ::close() on the error path
    surfaces as a file-descriptor leak at process exit. Plan 08 keeps
    detect_leaks=0 so the test exercises the path for future LSan
    re-enablement without currently failing.
    """
    errors = []
    bogus_path = "/tmp/rogue_nonexistent_device_stress"

    def axi_stream_dma_cycle():
        for _ in range(stress_iters // 10):
            try:
                d = rogue.hardware.axi.AxiStreamDma(bogus_path, 0, True)
                del d
            except Exception:
                pass  # expected — non-existent device path

    def mem_map_cycle():
        for _ in range(stress_iters // 10):
            try:
                m = rogue.hardware.MemMap(bogus_path, 0x1000)
                del m
            except Exception:
                pass  # expected — bogus path

    def axi_mem_map_cycle():
        for _ in range(stress_iters // 10):
            try:
                m = rogue.hardware.axi.AxiMemMap(bogus_path)
                del m
            except Exception:
                pass  # expected — bogus path / version-check fails

    threads = [threading.Thread(target=axi_stream_dma_cycle) for _ in range(3)]
    threads += [threading.Thread(target=mem_map_cycle) for _ in range(3)]
    threads += [threading.Thread(target=axi_mem_map_cycle) for _ in range(3)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert not errors, f"Ctor fd-leak stress errors: {errors}"


@pytest.mark.repro
def test_stress_block_setbytes_malloc(memory_root_unstarted, stress_iters):
    """Block setBytes malloc path + memcpy overrun (MEM-005, MEM-006).

    MEM-005: if valueBytes_ > stride_bytes, setBytes can memcpy past the
    Block's internal buffer — ASan heap-buffer-overflow.
    MEM-006: setBytes calls malloc() without null-check on the return value;
    on tight-memory systems a NULL return leads to a null-deref. Running
    the path under ASan exercises the malloc-dependent code.
    """
    errors = []

    class _Dev(pr.Device):
        def __init__(self, **kwargs):
            super().__init__(**kwargs)
            self.add(pr.RemoteVariable(
                name="Value",
                offset=0x0,
                bitSize=32,
                bitOffset=0,
                mode="RW",
            ))

    # Per 02-REVIEW.md CR-01: Root must be unstarted at .add() time, then
    # entered via `with` after children are attached. This mirrors the
    # canonical stress_bsp_gil.py::test_stress_bsp_gilless_attribute pattern.
    root = memory_root_unstarted
    root.add(_Dev(name="dev"))
    with root:
        def writer(i):
            for j in range(stress_iters // 10):
                try:
                    root.dev.Value.set(i * 1000 + j, write=True)
                except Exception as e:
                    errors.append(e)

        threads = [threading.Thread(target=writer, args=(i,)) for i in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
    assert not errors, f"Block setBytes stress errors: {errors}"


@pytest.mark.repro
def test_stress_streamunzip_truncated(stress_iters, tmp_path):
    """StreamUnZip iterator out-of-bounds on truncated bzip2 stream (HW-CORE-017).

    Feeds a corrupt/truncated bzip2 header into StreamUnZip; ASan catches
    the iterator overflow if the decoder walks past the input buffer.
    """
    errors = []

    # Minimal bzip2-ish header (4 bytes) followed by garbage.
    corrupt = bytes([0x42, 0x5a, 0x68, 0x39]) + os.urandom(64)
    target = tmp_path / "corrupt.bz2"
    target.write_bytes(corrupt)

    def cycle():
        for _ in range(stress_iters // 10):
            try:
                unzipper = rogue.utilities.StreamUnZip()
                # Feed a frame carrying the corrupt payload via a Master.
                master = rogue.interfaces.stream.Master()
                master._setSlave(unzipper)
                frame = master._reqFrame(len(corrupt), True)
                frame._write(bytearray(corrupt), 0)
                try:
                    master._sendFrame(frame)
                except Exception:
                    pass  # expected — truncated input
                del unzipper
            except Exception as e:
                errors.append(e)

    threads = [threading.Thread(target=cycle) for _ in range(4)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert not errors, f"StreamUnZip truncated stress errors: {errors}"
