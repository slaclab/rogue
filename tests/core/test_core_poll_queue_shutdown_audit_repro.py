#-----------------------------------------------------------------------------
# This file is part of the rogue software platform. It is subject to
# the license terms in the LICENSE.txt file found in the top-level directory
# of this distribution and at:
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
# No part of the rogue software platform, including this file, may be
# copied, modified, propagated, or distributed except according to the terms
# contained in the LICENSE.txt file.
#-----------------------------------------------------------------------------
"""PollQueue._poll() TOCTOU on stop check repro.

`_poll()` in python/pyrogue/_PollQueue.py evaluates `self.empty()` and
`self.paused()` at line 164 OUTSIDE any lock context. Between the two checks
and the subsequent `with self._condLock: wait()`, `_stop()` can set
`_run=False` and call `notify()`. The notification fires before the thread
enters `wait()`, so it is lost and the thread sleeps indefinitely, stalling
shutdown.

The fix is to evaluate these checks INSIDE a `with self._condLock:` block
so that `_run` cannot be modified between the condition check and the
`wait()` call.

This test uses source-text invariant analysis: verifies the unsafe
out-of-lock pattern is absent (assertion fires when pattern exists).
"""

import pathlib


def test_pollqueue_toctou_stop_check():
    """Verify PollQueue._poll() checks empty()/paused() inside the condition lock.

    On HEAD, _poll() at line 164 evaluates `self.empty() or self.paused()`
    OUTSIDE `_condLock`. This creates a TOCTOU window: _stop() can set
    _run=False and deliver the wakeup notification BEFORE the thread enters
    wait(), causing the notification to be lost. The thread then sleeps for
    the full poll interval before checking _run again.

    Source-text invariant: the unsafe pattern `if self.empty() or self.paused():`
    appears in _poll() without a preceding `with self._condLock:` on the same
    or immediately prior line. On HEAD this pattern is present => assertion fails.
    """
    src_file = pathlib.Path(__file__).parent.parent.parent / 'python' / 'pyrogue' / '_PollQueue.py'

    assert src_file.exists(), (
        "cannot locate python/pyrogue/_PollQueue.py relative to test tree"
    )

    lines = src_file.read_text().splitlines()

    # Find the line containing the unsafe pattern in _poll()
    unsafe_pattern = 'if self.empty() or self.paused():'
    unsafe_line_idx = None
    for i, line in enumerate(lines):
        if unsafe_pattern in line:
            unsafe_line_idx = i
            break

    assert unsafe_line_idx is None, (
        "PollQueue._poll() evaluates empty()/paused() outside "
        f"_condLock at line {unsafe_line_idx + 1} of _PollQueue.py. "
        "The TOCTOU window between the check and _condLock.wait() allows "
        "_stop() to fire notify() before the thread enters wait(), losing "
        "the wakeup and stalling shutdown. "
        "Fix: evaluate empty()/paused() inside `with self._condLock:`."
    )
