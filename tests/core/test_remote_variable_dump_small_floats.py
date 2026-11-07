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

import pyrogue as pr

from conftest import MemoryRoot


SMALL_FLOAT_MODELS = [
    ('Float16', pr.Float16, 16),
    ('Float8', pr.Float8, 8),
    ('BFloat16', pr.BFloat16, 16),
    ('TensorFloat32', pr.TensorFloat32, 32),
    ('Float6', pr.Float6, 8),
    ('Float4', pr.Float4, 8),
]


class SmallFloatDevice(pr.Device):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        for i, (name, base, bitSize) in enumerate(SMALL_FLOAT_MODELS):
            self.add(pr.RemoteVariable(
                name      = name,
                offset    = 0x10 + 4 * i,
                bitSize   = bitSize,
                bitOffset = 0,
                base      = base,
                mode      = 'RW',
            ))


class SmallFloatRoot(MemoryRoot):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.add(SmallFloatDevice(name='Dev', offset=0x0, memBase=self._mem))


def test_remote_variable_dump_covers_small_float_models(tmp_path):
    dump_file = tmp_path / 'regdump.txt'

    with SmallFloatRoot() as root:
        for name, _, _ in SMALL_FLOAT_MODELS:
            root.Dev.node(name).set(1.5)

        assert root.remoteVariableDump(str(dump_file), ['RW'], False)

    lines = dump_file.read_text().splitlines()
    dumped = {name for name in (n for n, _, _ in SMALL_FLOAT_MODELS) if any(f'Dev.{name}' in line for line in lines)}

    assert dumped == {name for name, _, _ in SMALL_FLOAT_MODELS}
    for line in lines:
        assert 'UNDEFINED' not in line, line
