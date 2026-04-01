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
import sys
from pathlib import Path


def _fmt(value):
    if isinstance(value, bool):
        return "yes" if value else "no"
    if isinstance(value, float):
        return f"{value:.3f}"
    return str(value)


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: ci_perf_summary.py <perf-results-dir>", file=sys.stderr)
        return 2

    result_dir = Path(sys.argv[1])
    files = sorted(result_dir.glob("*.json"))

    if not files:
        print("## Performance Results\n\nNo perf result files were found.")
        return 0

    print("## Performance Results\n")
    print("| Benchmark | Complete | Rx Errors | Rate / Throughput | Notes |")
    print("| --- | --- | --- | --- | --- |")

    for path in files:
        data = json.loads(path.read_text())
        notes = []

        if "avg_ns" in data:
            rate = f"{_fmt(data.get('avg_ns'))} ns/op, {_fmt(data.get('rate_hz'))} ops/s"
            if "cycles" in data:
                notes.append(f"cycles={_fmt(data['cycles'])}")
            if "threshold_pass" in data:
                notes.append(f"threshold_pass={_fmt(data['threshold_pass'])}")
        else:
            throughput = data.get("throughput_mb_s")
            if throughput is not None:
                rate = f"{_fmt(throughput)} MB/s"
            else:
                rate = ""

            if "frames_received" in data and "frames_sent" in data:
                notes.append(f"frames={data['frames_received']}/{data['frames_sent']}")
            if "elapsed_sec" in data:
                notes.append(f"elapsed={_fmt(data['elapsed_sec'])} s")
            if "version" in data:
                notes.append(f"ver={data['version']}")
            if "jumbo" in data:
                notes.append(f"jumbo={_fmt(data['jumbo'])}")

        print(
            f"| {data['name']} | {_fmt(data.get('drain_complete', data.get('threshold_pass', 'n/a')))} "
            f"| {_fmt(data.get('rx_errors', 'n/a'))} | {rate} | {'; '.join(notes)} |"
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
