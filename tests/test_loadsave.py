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

# Comment added by rherbst for demonstration purposes.
import pyrogue as pr
import pyrogue.interfaces.simulation
import rogue.interfaces.memory

import pathlib

#rogue.Logging.setLevel(rogue.Logging.Debug)
#import logging
#logger = logging.getLogger('pyrogue')
#logger.setLevel(logging.DEBUG)

class SimpleDev(pr.Device):

    def __init__(self, depth, **kwargs):
        print(f"Init SimpleDev with offset {kwargs['offset']:x} and {depth=}")

        super().__init__(**kwargs)

        print(self.offset)

        self.add(pr.RemoteVariable(
            name         = "A",
            offset       =  0x00,
            bitSize      =  32,
            bitOffset    =  0x00,
            base         = pr.UInt,
            mode         = "RW",
        ))

        self.add(pr.RemoteVariable(
            name         = "B",
            offset       =  0x04,
            bitSize      =  32,
            bitOffset    =  0x00,
            base         = pr.UInt,
            mode         = "RW",
        ))

        self.add(pr.RemoteVariable(
            name         = "C",
            offset       =  0x08,
            bitSize      =  32,
            bitOffset    =  0x00,
            base         = pr.UInt,
            mode         = "RW",
        ))

        if depth > 0:
            self.add(SimpleDev(
                offset = self.offset >> 1,
                depth = depth-1))


class DummyTree(pr.Root):

    def __init__(self):
        pr.Root.__init__(self,
                         name='DummyTree',
                         description="Dummy tree for example",
                         timeout=2.0,
                         pollEn=False,
                         serverPort=None)

        # Use a memory space emulator
        #sim = pr.interfaces.simulation.MemEmulate()
        sim = rogue.interfaces.memory.Emulate(4,0x1000)
        self.addInterface(sim)

        # Add Device
        self.add(SimpleDev(
            offset     = 0x100000,
            depth      = 3,
            memBase    = sim,
        ))


def test_loadsave():

    filepath = pathlib.Path(__file__).parent.resolve()
    inputYaml = f'{filepath}/test_config_in.yml'
    outputYaml = f'{filepath}/test_config_out.yml'

    with DummyTree() as root:

        root.LoadConfig(inputYaml)

        inputDict = pr.yamlToData(fName=inputYaml)

        root.SaveConfig(outputYaml)
        root.SaveState(stateYaml)

        outputDict = pr.yamlToData(fName=outputYaml)

        if (inputDict != outputDict):
            raise AssertionError('Configuration does not match input yaml after loading')


if __name__ == "__main__":
    test_loadsave()
