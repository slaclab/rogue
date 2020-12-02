#-----------------------------------------------------------------------------
# Title      : PyRogue AXI-Lite Version Module Test
#-----------------------------------------------------------------------------
# Description:
# PyRogue AXI-Lite Version Module
#-----------------------------------------------------------------------------
# This file is part of the rogue software platform. It is subject to
# the license terms in the LICENSE.txt file found in the top-level directory
# of this distribution and at:
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
# No part of the rogue software platform, including this file, may be
# copied, modified, propagated, or distributed except according to the terms
# contained in the LICENSE.txt file.
#-----------------------------------------------------------------------------

import datetime
import parse
import pyrogue as pr
import rogue
import rogue.hardware.axi
import numpy as np

class AxiVersion(pr.Device):

    # Last comment added by rherbst for demonstration.
    def __init__(
            self,
            name             = 'AxiVersion',
            description      = 'AXI-Lite Version Module',
            numUserConstants = 0,
            **kwargs):

        super().__init__(
            name        = name,
            description = description,
            **kwargs)

        ##############################
        # Variables
        ##############################

        self.add(pr.RemoteVariable(
            name         = 'FpgaVersion',
            description  = 'FPGA Firmware Version Number',
            offset       = 0x00,
            bitSize      = 32,
            bitOffset    = 0x00,
            base         = pr.UInt,
            mode         = 'RO',
            disp         = '{:#08x}',
        ))

        self.add(pr.RemoteVariable(
            name         = 'ScratchPad',
            description  = 'Register to test reads and writes',
            offset       = 0x04,
            bitSize      = 32,
            bitOffset    = 0x00,
            base         = pr.UInt,
            mode         = 'RW',
            units        = 'Test',
            disp         = '{:#08x}'
        ))

        self.add(pr.RemoteVariable(
            name         = 'UpTimeCnt',
            description  = 'Number of seconds since last reset',
            hidden       = True,
            offset       = 0x08,
            bitSize      = 32,
            bitOffset    = 0x00,
            base         = pr.UInt,
            mode         = 'RO',
            disp         = '{:d}',
            units        = 'seconds',
            pollInterval = 1
        ))

        self.add(pr.LinkVariable(
            name = 'UpTime',
            mode = 'RO',
            dependencies = [self.UpTimeCnt],
            linkedGet = lambda: str(datetime.timedelta(seconds=self.UpTimeCnt.value()))
        ))

        self.add(pr.RemoteVariable(
            name         = 'FpgaReloadHalt',
            description  = 'Used to halt automatic reloads via AxiVersion',
            offset       = 0x100,
            bitSize      = 1,
            bitOffset    = 0x00,
            base         = pr.UInt,
            mode         = 'RW',
        ))


        self.add(pr.RemoteCommand(
            name         = 'FpgaReload',
            description  = 'Optional Reload the FPGA from the attached PROM',
            offset       = 0x104,
            bitSize      = 1,
            bitOffset    = 0x00,
            base         = pr.UInt,
            function     = lambda cmd: cmd.post(1)
        ))

        self.add(pr.RemoteVariable(
            name         = 'FpgaReloadAddress',
            description  = 'Reload start address',
            offset       = 0x108,
            bitSize      = 32,
            bitOffset    = 0x00,
            base         = pr.UInt,
            mode         = 'RW',
        ))

        @self.command(hidden=True)
        def FpgaReloadAtAddress(arg):
            self.FpgaReloadAddress.set(arg)
            self.FpgaReload()

        self.add(pr.RemoteVariable(
            name         = 'UserReset',
            description  = 'Optional User Reset',
            offset       = 0x10C,
            bitSize      = 1,
            bitOffset    = 0x00,
            base         = pr.UInt,
            mode         = 'RW',
        ))

        self.add(pr.RemoteVariable(
            name         = 'FdSerial',
            description  = 'Board ID value read from DS2411 chip',
            offset       = 0x300,
            bitSize      = 64,
            bitOffset    = 0x00,
            base         = pr.UInt,
            mode         = 'RO',
        ))

        self.addRemoteVariables(
            name         = 'UserConstants',
            description  = 'Optional user input values',
            offset       = 0x400,
            bitSize      = 32,
            bitOffset    = 0x00,
            base         = pr.UInt,
            mode         = 'RO',
            number       = numUserConstants,
            stride       = 4,
            hidden       = True,
        )


        self.add(pr.RemoteVariable(
            name         = 'DeviceId',
            description  = 'Device Identification  (configured by generic)',
            offset       = 0x500,
            bitSize      = 32,
            bitOffset    = 0x00,
            base         = pr.UInt,
            mode         = 'RO',
        ))

        self.add(pr.RemoteVariable(
            name         = 'GitHash',
            description  = 'GIT SHA-1 Hash',
            offset       = 0x600,
            bitSize      = 160,
            bitOffset    = 0x00,
            base         = pr.UInt,
            mode         = 'RO',
            hidden       = True,
        ))

        self.add(pr.LinkVariable(
            name = 'GitHashShort',
            dependencies = [self.GitHash],
            disp = '{:07x}',
            linkedGet = lambda: self.GitHash.value() >> 132
        ))


        self.add(pr.RemoteVariable(
            name         = 'DeviceDna',
            description  = 'Xilinx Device DNA value burned into FPGA',
            offset       = 0x700,
            bitSize      = 128,
            bitOffset    = 0x00,
            base         = pr.UInt,
            mode         = 'RO',
        ))

        self.add(pr.RemoteVariable(
            name         = 'BuildStamp',
            description  = 'Firmware Build String',
            offset       = 0x800,
            bitSize      = 8*256,
            bitOffset    = 0x00,
            base         = pr.String,
            mode         = 'RO',
            hidden       = True,
        ))

        self.add(pr.RemoteVariable(
            name         = 'TestEnum',
            description  = 'ENUM Test Field',
            offset       = 0x900,
            bitSize      = 3,
            bitOffset    = 0x00,
            enum         = {0: 'Test0',
                            1: 'Test1',
                            2: 'Test2',
                            3: 'Test3',
                            4: 'Test4'},
            base         = pr.UInt,
            mode         = 'RW',
            hidden       = True,
        ))


        def parseBuildStamp(var, val):
            p = parse.parse("{ImageName}: {BuildEnv}, {BuildServer}, Built {BuildDate} by {Builder}", val.value.strip())
            if p is not None:
                for k,v in p.named.items():
                    self.node(k).set(v)

        self.add(pr.LocalVariable(
            name = 'ImageName',
            mode = 'RO',
            value = ''))

        self.add(pr.LocalVariable(
            name = 'BuildEnv',
            mode = 'RO',
            value = ''))

        self.add(pr.LocalVariable(
            name = 'BuildServer',
            mode = 'RO',
            value = ''))

        self.add(pr.LocalVariable(
            name = 'BuildDate',
            mode = 'RO',
            value = ''))

        self.add(pr.LocalVariable(
            name = 'Builder',
            mode = 'RO',
            value = ''))

        self.BuildStamp.addListener(parseBuildStamp)

        #self.add(pr.LocalVariable(name = 'TestArray[2]',value=0))

        for i in range(4):
            for j in range(4):
                for k in range(4):
                    self.add(pr.LocalVariable(name = f'TestArray[{i}][{j}][{k}]',
                                              guiGroup='TestArray',
                                              value=0))

        self.add(pr.LocalVariable(name = 'TestArray[4][5]',
                                  guiGroup='TestArray',
                                  value=0))
        self.add(pr.LocalVariable(name = 'TestArray[6]',
                                  guiGroup='TestArray',
                                  value=0))

        #self.add(pr.LocalVariable(name = 'TestArray[2]',value=0))

        for i in range(2):
            self.add(pr.LocalVariable(name = f'TestArray2[{i}]',
                                      guiGroup='TestArray',
                                      value=0))

        self.add(pr.RemoteVariable(
            name         = 'TestSpareArray[5][5]',
            description  = 'Array Test Field',
            offset       = 0x2000,
            bitSize      = 32,
            bitOffset    = 0,
            base         = pr.UInt,
            mode         = 'RW',
        ))

        self.add(pr.RemoteVariable(
            name         = 'TestSpareArray[8][8]',
            description  = 'Array Test Field',
            offset       = 0x2004,
            bitSize      = 32,
            bitOffset    = 0,
            base         = pr.UInt,
            mode         = 'RW',
        ))

        self.add(pr.RemoteVariable(
            name         = 'Test10Bit',
            description  = 'Test 10 bits',
            offset       = 0x2008,
            bitSize      = 10,
            bitOffset    = 0,
            base         = pr.UInt,
            mode         = 'RW',
        ))

        self.add(pr.RemoteVariable(
            name         = 'AlarmTest'.format(i),
            description  = 'Alarm Test Field',
            offset       = 0x8000,
            bitSize      = 32,
            bitOffset    = 0,
            base         = pr.UInt,
            mode         = 'RW',
            minimum      = 100,
            maximum      = 1000,
            lowAlarm     = 200,
            lowWarning   = 300,
            highWarning  = 800,
            highAlarm    = 900,
            value        = 100,
            disp         = '{}',
            hidden       = False,
            groups       = ['NoConfig','NoAlarm'],
        ))

        self.add(pr.LocalVariable(
            name = 'TestRealArray',
            mode = 'RW',
            value = np.array([1,2,3,4])))

        self.add(pr.LocalVariable(
            name = 'TestListA',
            mode = 'RW',
            value = [1,2,3,4,5,6,7,8,9,10]))

        self.add(pr.LocalVariable(
            name = 'TestListB',
            mode = 'RW',
            value = [11,12,13,14,15,16,17,18,19,20]))

        self.add(pr.LocalVariable(
            name = 'TestBool',
            mode = 'RW',
            value = False))

        self.add(pr.LocalVariable(
            name = 'TestBadArray[x]',
            mode = 'RW',
            value = ''))

        @self.command(hidden=False,value='',retValue='')
        def TestCommand(arg):
            print('Got {}'.format(arg))
            return('Got {}'.format(arg))

        @self.command(hidden=False,value='',retValue='')
        def TestMemoryException(arg):
            raise pr.MemoryError(name='blah',address=0)

        @self.command(hidden=False,value='',retValue='')
        def TestErrorLog(arg):
            self._log.error("Test error message")

        @self.command(hidden=False,value='',retValue='')
        def TestOtherLog(arg):
            self._log.log(93,"Test log level 39 message")

        @self.command(hidden=False,value='',retValue='')
        def TestGeneralException(arg):
            a = rogue.hardware.axi.AxiStreamDma('/dev/not_a_device',0,True)

        @self.command(hidden=False,value='',retValue='')
        def TestOtherError(arg):
            a = rogue.hardware.axi.AxiStreamDma('/dev/not_a_device',0)

        @self.command(hidden=False,value='blah blah',retValue='')
        def TestCmdString(arg):
            print("Send command string: {}".format(arg))

        @self.command(hidden=False, value=1, retValue='', enum={1:'One',2:'Two',3:'Three'})
        def TestCmdEnum(arg):
            print("Send command Enum: {}".format(arg))

    def hardReset(self):
        print('AxiVersion hard reset called')

    def softReset(self):
        print('AxiVersion soft reset called')

    def countReset(self):
        print('AxiVersion count reset called')
