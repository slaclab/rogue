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

import time

import pyrogue as pr
import rogue.interfaces.stream
import pytest
import yaml

from pyrogue.interfaces.stream import Variable

from conftest import wait_for


class FrameCapture(rogue.interfaces.stream.Slave):
    """Capture frames as raw bytes."""

    def __init__(self):
        super().__init__()
        self.frames = []

    def _acceptFrame(self, frame):
        self.frames.append(bytes(frame.getBa()))


class StreamVarDevice(pr.Device):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.add(pr.LocalVariable(
            name='TestInt', value=0, mode='RW'))
        self.add(pr.LocalVariable(
            name='TestStr', value='hello', mode='RW'))
        self.add(pr.LocalVariable(
            name='GroupA', value=10, mode='RW',
            groups=['GroupA']))
        self.add(pr.LocalVariable(
            name='GroupB', value=20, mode='RW',
            groups=['GroupB']))


def test_variable_stream_yaml_full():
    capture = FrameCapture()
    root = pr.Root(name='root', pollEn=False)
    root.add(StreamVarDevice(name='Dev'))

    sv = Variable(root=root)
    sv >> capture

    with root:
        root.Dev.TestInt.set(42)
        root.Dev.TestStr.set('world')
        sv.streamYaml()

    assert len(capture.frames) >= 1
    yml_str = capture.frames[-1].decode('utf-8')
    parsed = yaml.safe_load(yml_str)
    assert parsed is not None


def test_variable_stream_emits_on_update():
    capture = FrameCapture()
    root = pr.Root(name='root', pollEn=False)
    root.add(StreamVarDevice(name='Dev'))

    sv = Variable(root=root)
    sv >> capture

    with root:
        root.Dev.TestInt.set(99)
        root.ReadAll()

        assert wait_for(lambda: len(capture.frames) >= 1, timeout=5.0)

        yml_str = capture.frames[-1].decode('utf-8')
        assert len(yml_str) > 0


def test_variable_stream_no_update_no_frame():
    capture = FrameCapture()
    root = pr.Root(name='root', pollEn=False)
    root.add(StreamVarDevice(name='Dev'))

    sv = Variable(root=root)
    sv >> capture

    with root:
        initial_count = len(capture.frames)
        sv._varDone()
        time.sleep(0.1)
        assert len(capture.frames) == initial_count


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
