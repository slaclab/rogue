#!/usr/bin/env python3
# ----------------------------------------------------------------------------
# This file is part of the rogue software platform. It is subject to
# the license terms in the LICENSE.txt file found in the top-level directory
# of this distribution and at:
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
# No part of the rogue software platform, including this file, may be
# copied, modified, propagated, or distributed except according to the terms
# contained in the LICENSE.txt file.
# ----------------------------------------------------------------------------

import pyrogue


class LocalRoot(pyrogue.Root):
    def __init__(self):
        super().__init__(name="LocalRoot", description="Local root", pollEn=False)
        self.add(pyrogue.Process(name="Proc"))


def test_process_progress_helper_api_clamps_and_tracks_steps():
    with LocalRoot() as root:
        root.Proc.setProgress(1.5)
        assert root.Proc.Progress.value() == 1.0

        root.Proc.setProgress(-0.25)
        assert root.Proc.Progress.value() == 0.0

        root.Proc.setTotalSteps(4)
        root.Proc.setStep(2)
        assert root.Proc.Progress.value() == 0.5

        root.Proc.incrementSteps(10)
        assert root.Proc.Step.value() == 12
        assert root.Proc.Progress.value() == 1.0

        root.Proc.Progress.set(2.0)
        assert root.Proc.Progress.value() == 1.0

        root.Proc.Progress.set(-0.5)
        assert root.Proc.Progress.value() == 0.0


def test_process_progress_recomputes_on_direct_state_writes():
    with LocalRoot() as root:
        root.Proc.Step.set(5)
        assert root.Proc.Progress.value() == 1.0

        root.Proc.TotalSteps.set(10)
        assert root.Proc.Progress.value() == 0.5

        root.Proc.TotalSteps.set(0)
        assert root.Proc.Progress.value() == 0.0

        root.Proc.Step.set(-3)
        root.Proc.TotalSteps.set(4)
        assert root.Proc.Progress.value() == 0.0
