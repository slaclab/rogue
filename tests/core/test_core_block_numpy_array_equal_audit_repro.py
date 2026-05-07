#-----------------------------------------------------------------------------
# This file is part of the rogue software platform. It is subject to
# the license terms in the LICENSE.txt file found in the top-level directory
# of this distribution and at:
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
# No part of the rogue software platform, including this file, may be
# copied, modified, propagated, or distributed except according to the terms
# contained in the LICENSE.txt file.
#-----------------------------------------------------------------------------
"""LocalBlock.set inverted np.array_equal change-detection repro.

`LocalBlock.set` in python/pyrogue/_Block.py line 380 computes:
    changed = np.array_equal(self._value, value)

`np.array_equal` returns True when arrays are EQUAL. The variable is named
`changed`, so True should indicate the value changed. The logic is inverted:
the `changed` flag passed to `localSet` is False when the value changes and
True when it stays the same.
"""

import numpy as np

import pyrogue as pr


def _make_np_device(*, localset_calls):
    """Return a Device class whose NpVar variable appends the `changed` flag
    on each localSet invocation."""

    class NpVarDevice(pr.Device):
        def __init__(self, **kwargs):
            super().__init__(**kwargs)
            self.add(pr.LocalVariable(
                name='NpVar',
                value=np.array([1, 2, 3]),
                typeCheck=False,
                localSet=lambda value, changed: localset_calls.append(changed),
            ))

    return NpVarDevice


class NpRoot(pr.Root):
    def __init__(self, *, localset_calls):
        super().__init__(name='root', pollEn=False)
        self.add(_make_np_device(localset_calls=localset_calls)(name='Dev'))


def test_localblock_set_numpy_array_equal_inversion():
    """Verify changed flag is True when numpy array value changes.

    On HEAD `changed = np.array_equal(self._value, value)` (line 380 of
    _Block.py) is inverted: the flag is False when the value changes and
    True when it stays the same. This test asserts `changed == True` for a
    clearly different new value; on HEAD it is False, failing the assertion.
    """
    localset_calls = []

    with NpRoot(localset_calls=localset_calls) as root:
        var = root.Dev.NpVar
        # Drain any initialization-time localSet calls
        localset_calls.clear()

        # Set to a CLEARLY DIFFERENT array: [10, 20, 30] vs initial [1, 2, 3]
        var.set(np.array([10, 20, 30]))

        assert len(localset_calls) >= 1, (
            "localSet was not called at all after setting a different numpy array"
        )

        changed_flag = localset_calls[-1]

        assert changed_flag is True, (
            "LocalBlock.set inverted np.array_equal logic; "
            "changed flag is False when the numpy array value changes "
            f"(expected True, got {changed_flag}). "
            "Bug: `changed = np.array_equal(...)` should be "
            "`changed = not np.array_equal(...)`"
        )

        # Verify the other direction: re-setting the SAME value => changed=False
        localset_calls.clear()
        var.set(np.array([10, 20, 30]))

        assert len(localset_calls) >= 1, (
            "localSet was not called after setting the same numpy array"
        )

        changed_flag = localset_calls[-1]

        assert changed_flag is False, (
            "LocalBlock.set reports changed=True for identical numpy array; "
            f"expected False, got {changed_flag}"
        )
