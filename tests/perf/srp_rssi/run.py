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
"""Run isolated burst cases and summarize their buffered C++ timelines."""
import argparse
import csv
from collections import defaultdict, deque
import json
import hashlib
import os
from pathlib import Path
import platform
import subprocess
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]


def summarize(path):
    if not path.exists():
        return {}
    with path.open() as stream:
        events = [{k: v if k == 'event' else int(v) for k, v in row.items()}
                  for row in csv.DictReader(stream)]
    if not events:
        return {}
    events.sort(key=lambda e: e['ns'])
    begin = next((e['ns'] for e in events if e['event'] == 'measure_begin'), 0)
    end = next((e['ns'] for e in events if e['event'] == 'measure_end'), events[-1]['ns'])
    queues = {e['a']: e['object'] for e in events if e['event'] == 'rssi_queue' and e['b'] == 0}
    host = set(queues.values())
    apps = {e['object'] for e in events if e['event'] == 'host_app'}
    srps = {e['object'] for e in events if e['event'] == 'host_srp'}
    packet_apps = {e['object'] for e in events if e['event'] == 'host_packet_app'}
    packet_queues = {e['a'] for e in events if e['event'] == 'packet_app_queue' and e['object'] in packet_apps}
    peer_tx = {e['a'] for e in events if e['event'] == 'packet_tx_queue' and e['c'] == 1}
    host_tx = {e['a'] for e in events if e['event'] == 'packet_tx_queue' and e['c'] == 0}
    peer_queues = {e['a'] for e in events if e['event'] == 'rssi_queue' and e['b'] == 1}
    peer_controllers = {e['object'] for e in events if e['event'] == 'rssi_queue' and e['b'] == 1}
    all_full_waits, peer_waits, window_waits, lock_holds = {}, {}, {}, {}
    queue_max = defaultdict(int)
    peer_busy_start = None
    last_host_dequeue = last_peer_dequeue = None
    measured_requests = measured_responses = measured_done = 0
    waits = {}
    depths = 0
    packet_depth = 0
    full_waits = {}
    refresh_waits = {}
    map_waits = {}
    durations = defaultdict(list)
    pending = defaultdict(deque)
    busy_start = None
    callbacks = {}
    packet_waits = {}
    responses = {}
    lock_waits = []
    timeline = []
    for e in events:
        name, obj, a, b, t = e['event'], e['object'], e['a'], e['b'], e['ns']
        if not begin <= t <= end:
            continue
        key = (e['thread'], obj)
        role = ('host_receive' if obj in packet_queues else 'peer_transmit' if obj in peer_tx
                else 'host_transmit' if obj in host_tx else 'peer_rssi' if obj in peer_queues else 'other')
        if name == 'queue_push':
            queue_max[role] = max(queue_max[role], a)
        if name == 'queue_full_wait_begin':
            all_full_waits[key] = (t, role, a)
        if name == 'queue_full_wait_end' and key in all_full_waits:
            started, wait_role, depth = all_full_waits.pop(key)
            durations[wait_role + '_capacity_wait_ms'].append((t-started)/1e6)
        if name == 'peer_request_push':
            queue_max['peer_requests'] = max(queue_max['peer_requests'], a)
        if name == 'peer_request_wait_begin':
            peer_waits[key] = t
        if name == 'peer_request_wait_end' and key in peer_waits:
            durations['peer_request_capacity_wait_ms'].append((t-peer_waits.pop(key))/1e6)
        if name == 'rssi_window_enter':
            window_waits[key] = (t, 'host' if obj in host else 'peer', a, b)
        if name == 'rssi_window_ready' and key in window_waits:
            started, side, _, _ = window_waits.pop(key)
            durations[side + '_rssi_window_wait_ms'].append((t-started)/1e6)
        if obj in peer_controllers and name == 'local_busy':
            if a and peer_busy_start is None:
                peer_busy_start = t
            elif not a and peer_busy_start is not None:
                durations['peer_busy_ms'].append((t-peer_busy_start)/1e6)
                peer_busy_start = None
        if name == 'rssi_dequeue':
            if obj in host:
                last_host_dequeue = t
            else:
                last_peer_dequeue = t
        if obj in srps:
            measured_requests += name == 'srp_request'
            measured_responses += name == 'srp_response'
            measured_done += name == 'srp_done'
        if name == 'lock_acquired':
            lock_holds[key] = (t, a)
        if name == 'lock_release' and key in lock_holds:
            started, transaction = lock_holds.pop(key)
            durations['transaction_lock_hold_ms'].append((t-started)/1e6)
        if obj in packet_queues:
            if name == 'queue_push':
                packet_depth = max(packet_depth, a)
            if name == 'queue_full_wait_begin':
                full_waits[key] = t
                timeline.append(dict(ms=(t-begin)/1e6, event=name, depth=a))
            if name == 'queue_full_wait_end' and key in full_waits:
                durations['packet_receive_full_wait_ms'].append((t-full_waits.pop(key))/1e6)
                timeline.append(dict(ms=(t-begin)/1e6, event=name, depth=a))
        if obj in queues:
            if name == 'queue_push':
                pending[obj].append(t)
                depths = max(depths, a)
            if name == 'queue_pop' and pending[obj]:
                durations['queue_residence_ms'].append((t-pending[obj].popleft())/1e6)
        if obj in host and name == 'local_busy':
            if a and busy_start is None:
                busy_start = t
            elif not a and busy_start is not None:
                durations['busy_ms'].append((t-busy_start)/1e6)
                busy_start = None
        if name == 'srp_response' and obj in srps:
            responses[e['thread']] = a
        if name == 'refresh_wait':
            refresh_waits[key] = (t, a, b)
        if name == 'refresh_acquired' and key in refresh_waits:
            started, target_id, response_id = refresh_waits.pop(key)
            ms = (t-started)/1e6
            durations['timer_refresh_lock_ms'].append(ms)
            if ms >= 1:
                timeline.append(dict(ms=(t-begin)/1e6, event='refresh_acquired', wait_ms=ms,
                                     lock_transaction=target_id, response=response_id))
        if name == 'map_lock_wait':
            map_waits[key] = t
        if name == 'map_lock_acquired' and key in map_waits:
            durations['transaction_map_lock_ms'].append((t-map_waits.pop(key))/1e6)
        if name == 'packet_queue_wait_begin':
            packet_waits[key] = t
        if name == 'packet_queue_wait_end' and key in packet_waits:
            durations['packet_queue_wait_ms'].append((t-packet_waits.pop(key))/1e6)
        if name == 'lock_wait':
            waits[key] = t
        if name == 'lock_acquired' and key in waits:
            ms = (t-waits.pop(key))/1e6
            durations['transaction_lock_ms'].append(ms)
            if e['thread'] in responses:
                lock_waits.append(ms)
            if ms >= 1:
                timeline.append(dict(ms=(t-begin)/1e6, event='lock_acquired', wait_ms=ms,
                                     lock_transaction=a, response=responses.get(e['thread'])))
        if name in ('rssi_callback', 'srp_callback', 'packet_rx', 'packet_callback', 'srp_submit', 'rssi_send', 'packet_app_callback', 'packet_app_push', 'map_get', 'map_add', 'peer_process', 'packet_send'):
            if name == 'rssi_callback' and obj not in apps:
                continue
            if name.startswith('packet_app_') and obj not in packet_apps:
                continue
            if a == 0:
                callbacks[(name, key)] = t
            elif (name, key) in callbacks:
                ms = (t-callbacks.pop((name, key)))/1e6
                durations[name+'_ms'].append(ms)
                if ms >= 10:
                    timeline.append(dict(ms=(t-begin)/1e6, event=name, duration_ms=ms))
        if name.startswith(('stall_', 'reset', 'ack_freeze')) or (obj in host and name == 'local_busy'):
            timeline.append(dict(ms=(t-begin)/1e6, event=name, a=a, b=b))
    if busy_start is not None:
        durations['busy_ms'].append((end-busy_start)/1e6)
    for key, (started, target_id, response_id) in refresh_waits.items():
        timeline.append(dict(ms=(started-begin)/1e6, event='refresh_wait_unfinished',
                             lock_transaction=target_id, response=response_id, duration_ms=(end-started)/1e6))
    for key, start in waits.items():
        timeline.append(dict(ms=(start-begin)/1e6, event='lock_wait_unfinished',
                             object=key[1], duration_ms=(end-start)/1e6))
    for key, start in packet_waits.items():
        timeline.append(dict(ms=(start-begin)/1e6, event='packet_queue_wait_unfinished',
                             object=key[1], duration_ms=(end-start)/1e6))
    for (name, key), start in callbacks.items():
        timeline.append(dict(ms=(start-begin)/1e6, event=name+'_unfinished', duration_ms=(end-start)/1e6))
    if peer_busy_start is not None:
        durations['peer_busy_ms'].append((end-peer_busy_start)/1e6)
    for key, (started, role, depth) in all_full_waits.items():
        timeline.append(dict(ms=(started-begin)/1e6, event='capacity_wait_unfinished',
                             role=role, object=key[1], depth=depth, duration_ms=(end-started)/1e6))
    for key, started in peer_waits.items():
        timeline.append(dict(ms=(started-begin)/1e6, event='peer_request_wait_unfinished', duration_ms=(end-started)/1e6))
    for key, (started, side, used, limit) in window_waits.items():
        timeline.append(dict(ms=(started-begin)/1e6, event='rssi_window_unfinished', side=side,
                             used=used, limit=limit, duration_ms=(end-started)/1e6))
    for key, (started, transaction) in lock_holds.items():
        timeline.append(dict(ms=(started-begin)/1e6, event='transaction_hold_unfinished',
                             transaction=transaction, duration_ms=(end-started)/1e6))
    for key, started in map_waits.items():
        timeline.append(dict(ms=(started-begin)/1e6, event='map_wait_unfinished', duration_ms=(end-started)/1e6))
    stats = dict(queue_max=dict(queue_max), measured_requests=measured_requests,
                 measured_responses=measured_responses, measured_done=measured_done,
                 measurement_ms=(end-begin)/1e6,
                 last_host_dequeue_ms=(last_host_dequeue-begin)/1e6 if last_host_dequeue else None,
                 last_peer_dequeue_ms=(last_peer_dequeue-begin)/1e6 if last_peer_dequeue else None,
                 injected_stalls=sum(e['event'] == 'stall_begin' for e in events),
                 trace_retransmits=sum(e['event'] == 'retransmit' and begin <= e['ns'] <= end for e in events),
                 trace_resets=sum(e['event'] == 'reset' and begin <= e['ns'] <= end for e in events))
    for name, values in durations.items():
        values.sort()
        stats[name] = dict(max=max(values), p50=values[len(values)//2], p99=values[int((len(values)-1)*.99)])
    stats['max_host_rssi_depth'] = depths
    stats['max_host_packet_app_depth'] = packet_depth
    stats['response_lock_max_ms'] = max(lock_waits, default=0)
    stats['timeline'] = sorted(timeline, key=lambda e: e['ms'])
    return stats


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--build-root', type=Path, default=ROOT / 'build/srp-rssi')
    p.add_argument('--variants', nargs='+', default=['before', 'after'])
    p.add_argument('--windows', nargs='+', type=int, default=[1, 2, 8, 24, 64, 256, 600])
    p.add_argument('--sizes', nargs='+', type=int, default=[4, 256, 4096])
    p.add_argument('--modes', nargs='+', choices=['none', 'app', 'srp', 'tx', 'submit', 'ack'], default=['none'])
    p.add_argument('--count', type=int, default=600)
    p.add_argument('--repeat', type=int, default=3)
    p.add_argument('--delay-ms', type=int, default=200)
    p.add_argument('--retran-ms', type=int, default=20)
    p.add_argument('--transport', choices=['inproc', 'udp'], default='inproc')
    p.add_argument('--split', action='store_true')
    p.add_argument('--workers', type=int, default=1)
    p.add_argument('--no-trace', action='store_true')
    p.add_argument('--stall-after', type=int, default=1)
    p.add_argument('--segment', type=int, default=1400)
    p.add_argument('--rssi-window', type=int, default=32)
    p.add_argument('--peer-requests', type=int, default=0, help='Queued SRP requests; 0 is unbounded')
    p.add_argument('--peer-responses', type=int, default=0, help='Queued response segments; 0 is unbounded')
    p.add_argument('--workload', choices=['native', 'blocks', 'device'], default='native')
    p.add_argument('--output', type=Path, required=True)
    args = p.parse_args()
    if min(args.windows + [args.count, args.repeat, args.workers, args.stall_after]) < 1:
        p.error('windows, count, repeat, workers, and stall-after must be positive')
    if any(size < 4 or size > 4096 or size % 4 for size in args.sizes):
        p.error('sizes must be multiples of 4 in [4, 4096]')
    if args.split and args.sizes != [4096]:
        p.error('--split requires --sizes 4096 for full data validation')
    if args.transport == 'udp' and 'ack' in args.modes:
        p.error('the ACK rewriting peer requires --transport inproc')
    if not 1 <= args.rssi_window <= 255 or not 64 <= args.segment <= 65535:
        p.error('RSSI window must be in [1, 255], segment in [64, 65535]')
    if min(args.peer_requests, args.peer_responses) < 0:
        p.error('peer limits cannot be negative')
    if args.workload != 'native' and (args.modes != ['none'] or args.split or args.workers != 1 or args.transport != 'inproc'):
        p.error('PyRogue workloads use inproc, none, one submitting thread, no split')
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / 'environment.json').write_text(json.dumps(dict(platform=platform.platform(),
        args={k: str(v) if isinstance(v, Path) else v for k, v in vars(args).items()},
        runner_sha256={name: hashlib.sha256((HERE / name).read_bytes()).hexdigest()
                       for name in ('run.py', 'pyrogue_burst.py')}), indent=2))
    results = []
    for size in args.sizes:
        for window in args.windows:
            for mode in args.modes:
                for rep in range(args.repeat):
                    # Alternate order each repetition to reduce drift bias.
                    variants = args.variants if rep % 2 == 0 else list(reversed(args.variants))
                    for variant in variants:
                        name = f'{variant}-{size}-{window}-{mode}-{rep}'
                        trace = args.output.resolve() / (name + '.csv')
                        binary = args.build_root / variant / 'build/srp-rssi-burst'
                        command = [str(binary), str(window), str(size), str(args.count), mode,
                                   str(args.delay_ms), str(trace), args.transport, str(int(args.split)), str(args.retran_ms), str(args.workers)]
                        env = dict(os.environ, BURST_STALL_AFTER=str(args.stall_after),
                                   BURST_SEGMENT=str(args.segment), BURST_RSSI_WINDOW=str(args.rssi_window),
                                   BURST_PEER_REQUESTS=str(args.peer_requests), BURST_PEER_RESPONSES=str(args.peer_responses))
                        if args.no_trace:
                            env['BURST_TRACE_OFF'] = '1'
                        if args.workload != 'native':
                            source = args.build_root.resolve() / variant / 'source/python'
                            env['PYTHONPATH'] = str(source)
                            command = [sys.executable, str(HERE / 'pyrogue_burst.py'),
                                       '--window', str(window), '--size', str(size), '--count', str(args.count),
                                       '--trace', str(trace), '--workload', args.workload, '--retran-ms', str(args.retran_ms)]
                        try:
                            proc = subprocess.run(command, text=True, stdout=subprocess.PIPE,
                                                  stderr=subprocess.STDOUT, timeout=45 if args.workload != 'native' else 18,
                                                  env=env)
                            log, code = proc.stdout, proc.returncode
                        except subprocess.TimeoutExpired as exc:
                            log, code = str(exc.stdout), 124
                        (args.output / (name + '.log')).write_text(log)
                        result = dict(variant=variant, size=size, window=window, mode=mode, rep=rep,
                                      exit_code=code, transport=args.transport, split=args.split, workers=args.workers,
                                      workload=args.workload, segment=args.segment, rssi_window=args.rssi_window,
                                      peer_requests=args.peer_requests, peer_responses=args.peer_responses)
                        for line in log.splitlines():
                            if line.startswith('{'):
                                result.update(json.loads(line))
                        result.update(summarize(trace))
                        results.append(result)
                        (args.output / 'results.json').write_text(json.dumps(results, indent=2))
                        print(name, code, result.get('elapsed_ms'), 'depth', result.get('max_host_rssi_depth'), flush=True)
    if any(r['exit_code'] or r.get('trace_overflow', False) for r in results):
        raise SystemExit(1)


if __name__ == '__main__':
    main()
