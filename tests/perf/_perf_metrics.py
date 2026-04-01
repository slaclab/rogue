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

import json
import os
import re
import time
from pathlib import Path
from typing import Any


def emit_perf_result(name: str, **metrics: Any) -> dict[str, Any]:
    result = {
        "name": name,
        "timestamp": time.time(),
        **metrics,
    }

    outdir = os.getenv("PERF_RESULTS_DIR")
    if outdir:
        target_dir = Path(outdir)
        target_dir.mkdir(parents=True, exist_ok=True)
        slug = re.sub(r"[^A-Za-z0-9_.-]+", "_", name)
        (target_dir / f"{slug}.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")

    return result
