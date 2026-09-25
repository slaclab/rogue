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
"""Plot the host consumer, SRP response waits, queue and wire ACK/BUSY timeline."""
import argparse
import csv
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('trace', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--until-ms', type=float, help='Zoom the displayed time range')
    parser.add_argument('--title', help='Figure title (default: trace filename)')
    args = parser.parse_args()
    with args.trace.open() as f:
        rows = [{k: v if k == 'event' else int(v) for k, v in r.items()} for r in csv.DictReader(f)]
    rows.sort(key=lambda e: e['ns'])
    start = next(e['ns'] for e in rows if e['event'] == 'measure_begin')
    end = next((e['ns'] for e in rows if e['event'] == 'measure_end'), rows[-1]['ns'])
    queue = next(e['a'] for e in rows if e['event'] == 'rssi_queue' and e['b'] == 0)
    controller = next(e['object'] for e in rows if e['event'] == 'rssi_queue' and e['b'] == 0)
    app = next(e['object'] for e in rows if e['event'] == 'host_app')
    srp = next(e['object'] for e in rows if e['event'] == 'host_srp')
    packet_app = next(e['object'] for e in rows if e['event'] == 'host_packet_app')
    packet_queue = next(e['a'] for e in rows if e['event'] == 'packet_app_queue' and e['object'] == packet_app)
    fig, axes = plt.subplots(5, 1, figsize=(11, 10), sharex=True)
    packet_points = []
    spans = {0: [], 1: []}
    active, queue_points, wire_points, ack_points = {}, [], [], []
    rx_threads = set()
    for e in rows:
        if e['ns'] < start or e['ns'] > end:
            continue
        t = (e['ns']-start)/1e6
        name, obj, a, b = e['event'], e['object'], e['a'], e['b']
        key = (name, e['thread'], obj)
        if (name == 'rssi_callback' and obj == app) or (name == 'srp_callback' and obj == srp):
            y = 1 if name == 'rssi_callback' else 0
            if a == 0:
                active[key] = t
                rx_threads.add(e['thread'])
            elif key in active:
                x = active.pop(key)
                spans[y].append((x, max(t-x, .001)))
        if name == 'lock_wait' and e['thread'] in rx_threads:
            active[('lock', e['thread'], obj)] = t
        if name == 'lock_acquired' and ('lock', e['thread'], obj) in active:
            x = active.pop(('lock', e['thread'], obj))
            if t-x >= .01:
                axes[1].plot([x, t], [t-x, t-x], color='C3', linewidth=2)
        if name == 'refresh_wait' and e['thread'] in rx_threads:
            active[('refresh', e['thread'], obj)] = t
        if name == 'refresh_acquired' and ('refresh', e['thread'], obj) in active:
            x = active.pop(('refresh', e['thread'], obj))
            if t-x >= .01:
                axes[1].plot([x, t], [t-x, t-x], color='C4', linewidth=2)
        if obj == packet_queue and name in ('queue_push', 'queue_pop'):
            packet_points.append((t, a))
        if obj == queue and name in ('queue_push', 'queue_pop'):
            queue_points.append((t, a))
        if obj == controller and name == 'rssi_tx':
            wire_points.append((t, e['c'] & 1))
            ack_points.append((t, b))
        if name in ('stall_begin', 'stall_end', 'ack_freeze_begin', 'ack_freeze_end'):
            for ax in axes:
                ax.axvline(t, color='gray', linestyle='--', alpha=.7)
    end_ms = (end-start)/1e6
    for (name, thread, obj), x in active.items():
        if name in ('rssi_callback', 'srp_callback'):
            spans[1 if name == 'rssi_callback' else 0].append((x, end_ms-x))
        if name in ('lock', 'refresh'):
            axes[1].plot([x, end_ms], [end_ms-x, end_ms-x],
                         color='C3' if name == 'lock' else 'C4', linestyle='--')
    for points in (packet_points, queue_points, wire_points, ack_points):
        if points:
            points.append((end_ms, points[-1][1]))
    for y, bars in spans.items():
        axes[0].broken_barh(bars, (y-.3, .6), facecolor='C0' if y else 'C1')
    axes[0].set_yticks([0, 1], ['SRP callback', 'RssiApp callback'])
    axes[1].set_ylabel('Lock wait (ms)\nred: response / purple: timer')
    if packet_points:
        axes[2].step(*zip(*packet_points), where='post', color='C2')
    axes[2].axhline(8, color='gray', linestyle=':')
    axes[2].set_ylabel('Packetizer receive\nqueue (max 8)')
    if queue_points:
        axes[3].step(*zip(*queue_points), where='post', label='RSSI queue depth')
    axes[3].set_ylabel('RSSI queued segments')
    busy_axis = axes[3].twinx()
    if wire_points:
        busy_axis.step(*zip(*wire_points), where='post', color='C3', alpha=.6)
    busy_axis.set_ylabel('Advertised BUSY', color='C3')
    busy_axis.set_yticks([0, 1])
    if ack_points:
        axes[4].step(*zip(*ack_points), where='post')
    axes[4].set_ylabel('Host ACK (mod 256)')
    axes[4].set_xlabel('Milliseconds since measured burst began')
    for ax in axes:
        ax.grid(alpha=.2)
    if args.until_ms:
        axes[4].set_xlim(0, args.until_ms)
    fig.suptitle(args.title or args.trace.stem)
    fig.tight_layout()
    fig.savefig(args.output, bbox_inches='tight')
    plt.close(fig)


if __name__ == '__main__':
    main()
