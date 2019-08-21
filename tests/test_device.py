#!/usr/bin/env python
#-----------------------------------------------------------------------------
# Title      : PyRogue AXI-Lite Version Module Test
#-----------------------------------------------------------------------------
# File       : test_device.py
# Created    : 2017-04-12
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
            disp         = '{:#08x}'            
        ))

        self.add(pr.RemoteVariable(   
            name         = 'UpTimeCnt',
            description  = 'Number of seconds since last reset',
            visibility   = 0,
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

        @self.command(visibility=0)
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
            visibility   = 0,
        )


        self.add(pr.RemoteVariable(   
            name         = 'DeviceId',
            description  = 'Device Identification  (configued by generic)',
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
            visibility   = 0,
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
            visibility   = 0,
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
            visibility   = 0,
        ))

        
        def parseBuildStamp(var, value, disp):
            p = parse.parse("{ImageName}: {BuildEnv}, {BuildServer}, Built {BuildDate} by {Builder}", value.strip())
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
      
        for i in range(16):
            remap = divmod(i,32)

            self.add(pr.RemoteVariable(
                name         = 'TestArray[{:d}]'.format(i),
                description  = 'Array Test Field',
                offset       = 0x1000 + remap[0]<<2,
                bitSize      = 1,
                bitOffset    = remap[1],
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
        ))

    def hardReset(self):
        print('AxiVersion hard reset called')

    def softReset(self):
        print('AxiVersion soft reset called')

    def countReset(self):
        print('AxiVersion count reset called')
