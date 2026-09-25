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
"""Export revisions and build the identical native or PyRogue diagnostic.

Run in the existing activated Miniforge build environment. Never installs or
changes environments, stages files, or checks out another working branch.
"""
import argparse
import io
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tarfile

from overlay import instrument

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]


def run(*args, **kwargs):
    return subprocess.check_output(args, cwd=ROOT, **kwargs)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--variants', nargs='+', choices=['current', 'baseline', 'working'], default=['current'])
    parser.add_argument('--baseline-ref', help='Git revision to export as the baseline variant')
    parser.add_argument('--output', type=Path, default=ROOT / 'build/srp-rssi')
    parser.add_argument('--threshold', type=int, default=2)
    parser.add_argument('--no-timer-probes', action='store_true')
    parser.add_argument('--python', action='store_true', help='Build instrumented Rogue and the diagnostic Python binding')
    args = parser.parse_args()
    if not os.environ.get('CONDA_PREFIX'):
        parser.error('Activate the existing Miniforge build environment first')
    if 'baseline' in args.variants and not args.baseline_ref:
        parser.error('The baseline variant requires --baseline-ref')
    for variant in args.variants:
        ref = args.baseline_ref if variant == 'baseline' else 'HEAD'
        dest = args.output.resolve() / variant
        source = dest / 'source'
        if source.exists():
            shutil.rmtree(source)
        source.mkdir(parents=True)
        archive = run('git', 'archive', ref)
        with tarfile.open(fileobj=io.BytesIO(archive)) as tar:
            tar.extractall(source, filter='data')
        working_patch = b''
        if variant == 'working':
            # Export HEAD plus tracked production-source edits only. Tests and
            # generated diagnostics are supplied separately, never staged.
            working_patch = run('git', 'diff', '--binary', 'HEAD', '--', 'src', 'include')
            (dest / 'working.patch').write_bytes(working_patch)
            changed = run('git', 'diff', '--name-only', '-z', 'HEAD', '--', 'src', 'include')
            for name in changed.decode().split('\0'):
                if not name:
                    continue
                current, target = ROOT / name, source / name
                if current.exists():
                    target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(current, target)
                elif target.exists():
                    target.unlink()
        instrument(source, timer_locks=not args.no_timer_probes)
        path = source / 'src/rogue/protocols/rssi/Controller.cpp'
        threshold = 'appQueue_.setThold({});'.format(args.threshold)
        path.write_text(path.read_text().replace('appQueue_.setThold(2);', threshold))
        for filename in ('Trace.h', 'Stack.h', 'Probe.cpp', 'burst.cpp'):
            shutil.copy2(HERE / filename, source / filename)
        with (source / 'CMakeLists.txt').open('a') as f:
            f.write('\ninclude_directories(${CMAKE_SOURCE_DIR})\n'
                    'target_sources(rogue-core PRIVATE ${CMAKE_SOURCE_DIR}/Probe.cpp)\n'
                    'if (NO_PYTHON)\n'
                    '  add_executable(srp-rssi-burst burst.cpp)\n'
                    '  target_link_libraries(srp-rssi-burst PRIVATE rogue-core-static)\n'
                    'else()\n'
                    '  set_target_properties(rogue rogue-core-shared PROPERTIES SKIP_BUILD_RPATH FALSE BUILD_RPATH "${CMAKE_BINARY_DIR};$ENV{CONDA_PREFIX}/lib")\n'
                    'endif()\n')
        if args.python:
            module = source / 'src/rogue/module.cpp'
            module.write_text(module.read_text().replace('void rogue::setup_module() {',
                'void setupBurstPython();\nvoid rogue::setup_module() {').replace(
                'rogue::Version::setup_python();', 'rogue::Version::setup_python();\n    setupBurstPython();'))
        metadata = dict(variant=variant, working_patch_sha256=hashlib.sha256(working_patch).hexdigest(), revision=run('git', 'rev-parse', ref).decode().strip(),
                        conda_prefix=os.environ['CONDA_PREFIX'], threshold=args.threshold, python=args.python, timer_probes=not args.no_timer_probes,
                        compiler=run(os.environ.get('CXX', 'c++'), '--version').decode(),
                        probe_sha256={name: hashlib.sha256((HERE / name).read_bytes()).hexdigest()
                                      for name in ('Trace.h', 'Stack.h', 'Probe.cpp', 'burst.cpp', 'overlay.py')})
        (dest / 'build.json').write_text(json.dumps(metadata, indent=2))
        with (dest / 'build.log').open('w') as log:
            subprocess.run(['cmake', '-S', str(source), '-B', str(dest / 'build'),
                            f'-DNO_PYTHON={0 if args.python else 1}', '-DSTATIC_LIB=1', '-DNO_ROCEV2=ON',
                            '-DROGUE_INSTALL=local', '-DCMAKE_BUILD_TYPE=Release'],
                           stdout=log, stderr=subprocess.STDOUT, check=True)
            subprocess.run(['cmake', '--build', str(dest / 'build'), '--target',
                            'rogue' if args.python else 'srp-rssi-burst', '-j', '8'],
                           stdout=log, stderr=subprocess.STDOUT, check=True)
        print(dest / ('source/python/rogue.so' if args.python else 'build/srp-rssi-burst'), flush=True)


if __name__ == '__main__':
    main()
