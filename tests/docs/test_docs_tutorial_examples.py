#-----------------------------------------------------------------------------
# This file is part of the rogue software platform. It is subject to
# the license terms in the LICENSE.txt file found in the top-level directory
# of this distribution and at:
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
# No part of the rogue software platform, including this file, may be
# copied, modified, propagated, or distributed except according to the terms
# contained in the LICENSE.txt file.
#-----------------------------------------------------------------------------

"""Execute the docs/src/tutorials examples.

Those pages ``literalinclude`` these files rather than inlining code, so these
tests are what keep the published tutorials from drifting away from working
behavior. Every example here runs without hardware.

The custom C++ module test is skipped unless the compiled ``BitInverter``
module is importable, since building it is a manual step in that tutorial.
"""

import importlib.util
import os
import pathlib
import sys
import tempfile

import pytest

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
EXAMPLE_DIR = REPO_ROOT / 'docs' / 'src' / 'tutorials' / 'examples'


def load_example(name):
    """Import an example module by file name, without installing it."""
    path = EXAMPLE_DIR / f'{name}.py'
    assert path.is_file(), f'missing documented example: {path}'

    if str(EXAMPLE_DIR) not in sys.path:
        sys.path.insert(0, str(EXAMPLE_DIR))

    spec = importlib.util.spec_from_file_location(f'docs_tutorial_{name}', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# ---------------------------------------------------------------------------
# protocol_stack.rst
# ---------------------------------------------------------------------------

def test_protocol_stack_srp_over_emulation():
    """protocol_stack.rst stage 1 promises this readback."""
    module = load_example('protocol_stack')

    with module.SrpRoot() as root:
        root.Dev.ScratchPad.set(0xCAFEBABE)
        assert root.Dev.ScratchPad.get() == 0xCAFEBABE
        assert root.Dev.ScratchPad.valueDisp() == '0xcafebabe'


def test_protocol_stack_tcp_bridge():
    """protocol_stack.rst stage 2: registers survive a TCP hop."""
    import time

    module = load_example('protocol_stack')

    # A port unlikely to collide with the loopback stack test below.
    with module.TcpBridgeRoot(port=11011) as root:
        time.sleep(1.0)
        root.Dev.ScratchPad.set(0xABCD1234)
        assert root.Dev.ScratchPad.get() == 0xABCD1234


def test_protocol_stack_udp_rssi_packetizer():
    """protocol_stack.rst stage 3: the full stack links up and carries SRP."""
    module = load_example('protocol_stack')

    with module.NetworkRoot(port=8213) as root:
        assert root.waitForLink(), 'RSSI link never opened'
        root.Dev.ScratchPad.set(0xFEEDFACE)
        assert root.Dev.ScratchPad.get() == 0xFEEDFACE


# ---------------------------------------------------------------------------
# commands_and_groups.rst
# ---------------------------------------------------------------------------

def test_all_three_command_flavours_fire():
    """commands_and_groups.rst claims each command type works."""
    module = load_example('commands_and_groups')

    with module.TutorialRoot() as root:
        # RemoteCommand: posts a write, no exception means it reached memory.
        root.Cmds.Pulse()

        # Decorator command: writes through to the Control register.
        root.Cmds.SetControl(0x55)
        assert root.Cmds.Control.get() == 0x55
        assert root.Cmds.Control.valueDisp() == '0x00000055'

        # LocalCommand: returns a host-side value.
        assert root.Cmds.Describe() == 'CommandDevice ready'


def test_packed_variables_share_one_block():
    """commands_and_groups.rst claims 3 fields at one offset = 1 Block."""
    module = load_example('commands_and_groups')

    with module.TutorialRoot() as root:
        assert len(root.Packed._blocks) == 1
        assert len(root.Spread._blocks) == 3

        root.Packed.Low.set(0xAA)
        root.Packed.Middle.set(0xBB)
        root.Packed.High.set(0xCC)

        # Fields are independent despite sharing a register.
        assert root.Packed.Low.get() == 0xAA
        assert root.Packed.Middle.get() == 0xBB
        assert root.Packed.High.get() == 0xCC

        root.Packed.Middle.set(0x00)
        assert root.Packed.Low.get() == 0xAA
        assert root.Packed.High.get() == 0xCC


def test_groups_filter_saved_configuration():
    """commands_and_groups.rst claims NoConfig drops out of getYaml()."""
    module = load_example('commands_and_groups')

    with module.TutorialRoot() as root:
        assert root.Groups.Volatile.groups == ['NoConfig']
        assert root.Groups.Private.groups == ['NoServe']

        everything = root.getYaml(readFirst=False, modes=['RW'],
                                  incGroups=None, excGroups=None)
        config = root.getYaml(readFirst=False, modes=['RW'],
                              incGroups=None, excGroups=['NoConfig'])

        assert 'Volatile' in everything
        assert 'Volatile' not in config
        assert 'Saved' in config


# ---------------------------------------------------------------------------
# file_capture.rst
# ---------------------------------------------------------------------------

def test_capture_writes_and_replays():
    """file_capture.rst claims a throttled capture is readable back."""
    module = load_example('file_capture')

    with tempfile.TemporaryDirectory() as workdir:
        path = os.path.join(workdir, 'capture.dat')

        with module.CaptureRoot() as root:
            size = root.captureTo(path, seconds=0.5)

        assert size > 0, 'capture file is empty'
        assert module.countRecords(path) > 0, 'no records replayed'


def test_rate_drop_keeps_the_capture_small():
    """The tutorial's RateDrop must actually bound the file size.

    Without it a 0.5 s PRBS capture reaches hundreds of megabytes. Assert a
    generous ceiling so this catches a removed or misconfigured limiter
    without being sensitive to machine speed.
    """
    module = load_example('file_capture')

    with tempfile.TemporaryDirectory() as workdir:
        path = os.path.join(workdir, 'capture.dat')

        with module.CaptureRoot(period=0.01) as root:
            size = root.captureTo(path, seconds=0.5)

        assert size < 10 * 1024 * 1024, f'capture unexpectedly large: {size} bytes'


def test_compression_is_lossless():
    """file_capture.rst claims StreamZip -> StreamUnZip round-trips."""
    module = load_example('file_capture')
    assert module.roundTripCheck() is True


# ---------------------------------------------------------------------------
# custom_cpp_module.rst
# ---------------------------------------------------------------------------

def test_custom_cpp_module_inverts_payload():
    """custom_cpp_module.rst claims the module inverts every byte.

    Skipped unless the reader has built it, which is a manual cmake step.
    """
    pytest.importorskip(
        'BitInverter',
        reason='compiled BitInverter module not on PYTHONPATH; '
               'build it per docs/src/tutorials/custom_cpp_module.rst')

    module = load_example('custom_cpp_module_check')

    sample = bytes([0x00, 0x0F, 0xFF])
    result = module.invertThroughModule(sample)

    assert result == bytes(byte ^ 0xFF for byte in sample)
