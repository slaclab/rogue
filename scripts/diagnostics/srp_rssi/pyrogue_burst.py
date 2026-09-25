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
"""Real PyRogue block/device reads over the instrumented C++ asynchronous stack.

The register layout is synthetic; the Root, Device, RemoteVariable, Block,
Hub, transaction submission, update grouping, and completion paths are real.
Run through run.py so each case imports the matching exported Rogue revision.
"""
import argparse
import json
import os
import sys
import time
import traceback

import numpy as np
import pyrogue as pr
import rogue


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--window', type=int, required=True)
    p.add_argument('--size', type=int, required=True)
    p.add_argument('--count', type=int, required=True)
    p.add_argument('--trace', required=True)
    p.add_argument('--workload', choices=['blocks', 'device'], required=True)
    p.add_argument('--retran-ms', type=int, default=20)
    args = p.parse_args()
    stack = rogue._BurstStack(int(os.environ.get('BURST_SEGMENT', 1024)),
                             int(os.environ.get('BURST_RSSI_WINDOW', 8)),
                             args.retran_ms, 'inproc')
    stack.start()
    deadline = time.monotonic() + 5
    while not stack.open() and time.monotonic() < deadline:
        time.sleep(.001)  # Startup only; no sleeps or artificial holds during reads.
    if not stack.open():
        raise RuntimeError('RSSI handshake did not complete')
    root = pr.Root(name='Burst', timeout=3, pollEn=False, initRead=False, initWrite=False)
    devices, variables, writers, expected = [], [], [], []
    writer = pr.Device(name='SeedRegisters', memBase=stack.memory())
    seed_root = pr.Root(name='Seed', timeout=3, pollEn=False, initRead=False, initWrite=False)
    seed_root.add(writer)
    for base in range(0, args.count, args.window):
        dev = pr.Device(name=f'Group[{base // args.window}]',
                        offset=base * 4096, memBase=stack.memory())
        root.add(dev)
        devices.append(dev)
        for index in range(base, min(args.count, base + args.window)):
            shape = dict(bitSize=32) if args.size == 4 else dict(
                numValues=args.size // 4, valueBits=32, valueStride=32)
            var = pr.RemoteVariable(name=f'Reg[{index}]', offset=(index-base)*4096,
                                    base=pr.UInt, mode='RO', verify=False, retryCount=0, **shape)
            dev.add(var)
            variables.append(var)
            write_var = pr.RemoteVariable(name=f'Reg[{index}]', offset=index*4096,
                                         base=pr.UInt, mode='RW', verify=False, retryCount=0, **shape)
            writer.add(write_var)
            writers.append(write_var)
            pattern = np.asarray([(index*17 + word*7 + 1) & 0xffffffff
                                  for word in range(args.size // 4)], dtype=np.uint32)
            expected.append(int(pattern[0]) if args.size == 4 else pattern)
    seed_root.start()
    for var, value in zip(writers, expected):
        var.set(value, write=True)
    seed_root.stop()
    root.start()
    # Read-only blocks have untouched zero caches. A separate device wrote the
    # peer; staging writes in the read blocks would cause Rogue to skip reads.
    for var in variables:
        assert np.all(np.asarray(var.get(read=False)) == 0)
    block_count = len(set(var._block for var in variables))
    assert block_count == args.count, (block_count, args.count)
    print(json.dumps(dict(workload=args.workload, blocks=block_count,
                          rogue_module=rogue.__file__, pyrogue_module=pr.__file__)), flush=True)
    completed, ok = 0, False
    stack.begin(args.window, args.size, args.count, args.trace)
    try:
        with root.updateGroup():
            for dev in devices:
                if args.workload == 'device':
                    dev.readBlocks()
                    dev.checkBlocks()
                else:
                    # Deduplicate dependency blocks and batch reads then checks.
                    # The historical helper's name is
                    # readAndCheckBlocks (newer versions use readAndWaitBlocks).
                    blocks = list(dict.fromkeys(v._block for v in dev.variables.values()
                                                if isinstance(v, pr.RemoteVariable)))
                    pr.readAndCheckBlocks(blocks)
                for var in dev.variables.values():
                    if isinstance(var, pr.RemoteVariable):
                        completed += 1
        for var, value in zip(variables, expected):
            assert np.array_equal(var.get(read=False), value), var.path
        ok = completed == args.count
    except Exception:
        traceback.print_exc()
    print(stack.finish(completed, ok), flush=True)
    # Cases are process isolated. Historical transport ownership cycles lack a
    # uniform shutdown API; successful read completion is measured above.
    root.stop()
    stack.stop()
    sys.stdout.flush()
    sys.stderr.flush()
    os._exit(0 if ok else 1)


if __name__ == '__main__':
    main()
