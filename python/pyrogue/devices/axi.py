#!/usr/bin/env python
#-----------------------------------------------------------------------------
# Title      : PyRogue AXI Module
#-----------------------------------------------------------------------------
# File       : pyrogue/devices/axi.py
# Author     : Ryan Herbst, rherbst@slac.stanford.edu
# Created    : 2016-09-29
# Last update: 2016-09-29
#-----------------------------------------------------------------------------
# Description:
# PyRogue AXI Module
#-----------------------------------------------------------------------------
# This file is part of the rogue software platform. It is subject to 
# the license terms in the LICENSE.txt file found in the top-level directory 
# of this distribution and at: 
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html. 
# No part of the rogue software platform, including this file, may be 
# copied, modified, propagated, or distributed except according to the terms 
# contained in the LICENSE.txt file.
#-----------------------------------------------------------------------------
import pyrogue
import collections

class AxiVersion(pyrogue.Device):
    """AXI Lite Version Class"""

    # Declaration. parent is the owner of this object which can be another Device or the root node.
    # memBase is either the register bus server (srp, rce mapped memory, etc) or the device which
    # contains this object. In most cases the parent and memBase are the same but they can be 
    # different in more complex bus structures. They will also be different for the top most node.
    # The setMemBase call can be used to update the memBase for this Device. All sub-devices and local
    # blocks will be updated.
    def __init__(self, parent, name, index=None, memBase=None, offset=0):

        pyrogue.Device.__init__(self, parent=parent, name=name, description='AXI-Lite Version Module', 
                                size=0x1000, memBase=memBase, offset=offset)

        #############################################
        # Create block / variable combinations
        #############################################

        # First define a block of memory we will be accessing. offset and size are in bytes
        pyrogue.Block(parent=self, offset=0x0, size=4, variables = [

            # Next create a list of variables associated with this block.
            # base has two functions. If base = 'string' then the block is treated as a string (see BuildStamp)
            # otherwise the value is retrieved or set using:
            # setUInt(self.bitOffset,self.bitSize,value) or getUInt(self.bitOffset,self.bitSize)
            # otherwise base is used by a higher level interface (GUI, etc) to determine display mode
            # Allowed modes are RO, WO, RW or CMD. Command indicates registers can be written but only
            # when executing commands (not accessed during writeAll and writeStale calls
            pyrogue.Variable(parent=self, name='fpgaVersion', description='FPGA Firmware Version Number',
                             bitSize=32, bitOffset=0, base='hex', mode='RO') ])

        pyrogue.Block(parent=self, offset=0x4, size=4, variables = [

            # Example of using setFunction and getFunction. setFunction and getFunctions are defined in the class
            # at the bottom. getFunction is defined as a series of python calls. When using the defined
            # function the scope is relative to the location of the function defintion. A pointer to the variable
            # and passed value are provided as args. See UserConstants below for an alernative method.
            pyrogue.Variable(parent=self, name='scratchPad', description='Register to test read and writes',
                             bitSize=32, bitOffset=0, base='hex', mode='RW', setFunction=self.setVariableExample,
                             getFunction=self.getVariableExample) ])

        pyrogue.Block(parent=self, offset=0x8, size=8, variables = [

            pyrogue.Variable(parent=self, name='deviceDna', description='Xilinx Device DNA value burned into FPGA',
                             bitSize=64, bitOffset=0, base='hex', mode='RO') ])

        pyrogue.Block(parent=self, offset=0x10, size=8, variables = [

            pyrogue.Variable(parent=self, name='fdSerial', description='Board ID value read from DS2411 chip',
                             bitSize=64, bitOffset=0, base='hex', mode='RO') ])

        pyrogue.Block(parent=self, offset=0x18, size=4, variables = [

            # Here we define MasterReset as mode 'CMD' this will ensure it does not get written during
            # writeAll and writeStale commands
            pyrogue.Variable(parent=self, name='masterResetVar', description='Optional User Reset',
                             bitSize=1, bitOffset=0, base='bool', mode='CMD', hidden=True) ])

        pyrogue.Block(parent=self, offset=0x1C, size=4, variables = [

            pyrogue.Variable(parent=self, name='fpgaReloadVar', description='Optional reload the FPGA from the attached PROM',
                             bitSize=1, bitOffset=0, base='bool', mode='CMD', hidden=True) ])

        pyrogue.Block(parent=self, offset=0x20, size=4, variables = [

            pyrogue.Variable(parent=self, name='fpgaReloadAddress', description='Reload start address',
                             bitSize=32, bitOffset=0, base='hex', mode='RW') ])

        pyrogue.Block(parent=self, offset=0x24, size=4, pollEn=True, variables = [

            pyrogue.Variable(parent=self, name='counter', description='Free running counter',
                             bitSize=32, bitOffset=0, base='hex', mode='RO') ])

        pyrogue.Block(parent=self, offset=0x28, size=4, variables = [

            # Bool is not used locally. Access will occur just as a uint or hex. The GUI will know how to display it.
            pyrogue.Variable(parent=self, name='fpgaReloadHalt', description='Used to halt automatic reloads via AxiVersion',
                             bitSize=1, bitOffset=0, base='bool', mode='RW') ])

        pyrogue.Block(parent=self, offset=0x2C, size=4, pollEn=True, variables = [

            pyrogue.Variable(parent=self, name='upTimeCnt', description='Number of seconds since reset',
                             bitSize=32, bitOffset=0, base='hex', mode='RO') ])

        pyrogue.Block(parent=self, offset=0x30, size=4, variables = [

            pyrogue.Variable(parent=self, name='deviceId', description='Device identification',
                             bitSize=32, bitOffset=0, base='hex', mode='RO') ])
#
#        for i in range(0,64):
#            pyrogue.Block(parent=self, offset=0x400+(i*4), size=4, variables = [
#
#                # Example of using setFunction and getFunction passed as strings. The scope is local to 
#                # the variable object with the passed value available as 'value' in the scope.
#                # The get function must set the 'value' variable as a result of the function.
#                pyrogue.Variable(parent=self, name='userConstant_%02i'%(i), description='Optional user input values',
#                                 bitSize=32, bitOffset=0, base='hex', mode='RW',
#                                 getFunction="""\
#                                             value = self._block.getUInt(self.bitOffset,self.bitSize)
#                                             """,
#                                 setFunction="""\
#                                             self._block.setUInt(self.bitOffset,self.bitSize,value)
#                                             """
#                )])

        pyrogue.Block(parent=self, offset=0x800, size=256, variables = [

            pyrogue.Variable(parent=self, name='buildStamp', description='Firmware build string',
                             bitSize=256*8, bitOffset=0, base='string', mode='RO') ])

        #####################################
        # Create commands
        #####################################

        # A command has an associated function. The function can be a series of
        # python commands in a string. Function calls are executed in the command scope
        # the passed arg is available as 'arg'. Use self._parent to get to device scope.
        pyrogue.Command(parent=self, name='masterReset',description='Master Reset',
           function='self._parent.masterResetVar.write(1)')
       
        # A command can also be a call to a local function with local scope.
        # The command object and the arg are passed
        pyrogue.Command(parent=self, name='fpgaReload',description='Reload FPGA',
           function=self.cmdFpgaReload)

        pyrogue.Command(parent=self, name='counterReset',description='Counter Reset',
           function='self._parent.counter.write(1)')

        # Example printing the arg and showing a larger block. The indentation will be adjusted.
        pyrogue.Command(parent=self, name='testCommand',description='Test Command',
           function="""\
                    print("Someone executed the %s command" % (self.name))
                    print("The passed arg was %s" % (arg))
                    print("My device is %s" % (self._parent.name))
                    """)

        # Alternative function for CPSW compatability
        # Pass a dictionary of numbered variable, value pairs to generate a CPSW sequence
        pyrogue.Command(parent=self, name='testCpsw',description='Test CPSW',
              function=collections.OrderedDict({ 'masterResetVar': 1,
                                                 'usleep': 100,
                                                 'counter': 1 }))

    # Example command function
    def cmdFpgaReload(self,cmd,arg):
        self.fpgaReload.write(1)

    # Example variable set function
    def setVariableExample(self,var,value):
        var._block.setUInt(var.bitOffset,var.bitSize,value)

    # Example variable get function
    def getVariableExample(self,var):
        return(var._block.getUInt(var.bitOffset,var.bitSize))

    # Soft reset. Called from top level. Add calls to generate a device specific 'softReset'
    def _softReset(self):
      self.counter.write(1)

    # Hard reset. Called from top level. Add calls to generate a device specific 'hardReset'
    def _hardReset(self):
      self.masterResetVar.write(1)

    # Count reset. Called from top level. Add calls to generate a device specific 'countReset'
    def _countReset(self):
      self.counter.write(1)


class AxiPrbsTx(pyrogue.Device):
    """PRBS Tx"""

    def __init__(self, parent, name, index=None, memBase=None, offset=0):

        pyrogue.Device.__init__(self, parent=parent, name=name, description='HW PRBS Transmitter', 
                                size=0x100, memBase=memBase, offset=offset)

        pyrogue.Block(parent=self, offset=0x0, size=4, variables = [

            pyrogue.Variable(parent=self, name='axiEn', description='AXI Bus enable',
                             bitSize=1, bitOffset=0, base='bool', mode='RW'),
            
            pyrogue.Variable(parent=self, name='txEn', description='Transmit enable',
                             bitSize=1, bitOffset=1, base='bool', mode='RW'), 

            pyrogue.Variable(parent=self, name='busy', description='Busy Flag',
                             bitSize=1, bitOffset=2, base='bool', mode='RO'), 

            pyrogue.Variable(parent=self, name='overflow', description='Overflow Flag',
                             bitSize=1, bitOffset=3, base='bool', mode='RO'), 

            pyrogue.Variable(parent=self, name='oneShotCmd', hidden=True, description='Oneshot frame generate',
                             bitSize=1, bitOffset=4, base='bool', mode='CMD'), 

            pyrogue.Variable(parent=self, name='fwCnt', description='????',
                             bitSize=1, bitOffset=5, base='bool', mode='RW') ])

        pyrogue.Block(parent=self, offset=0x4, size=4, variables = [

            pyrogue.Variable(parent=self, name='packetLength', description='Packet Length Control',
                             bitSize=32, bitOffset=0, base='uint', mode='RW') ])

        pyrogue.Block(parent=self, offset=0x8, size=4, variables = [

            pyrogue.Variable(parent=self, name='tDest', description='TDEST value for frame',
                             bitSize=8, bitOffset=0, base='hex', mode='RW'),

            pyrogue.Variable(parent=self, name='tId', description='TID value for frame',
                             bitSize=8, bitOffset=8, base='hex', mode='RW') ])

        pyrogue.Block(parent=self, offset=0xC, size=4, pollEn=True, variables = [

            pyrogue.Variable(parent=self, name='dataCount', description='Data counter',
                             bitSize=32, bitOffset=0, base='uint', mode='RO') ])

        pyrogue.Block(parent=self, offset=0x10, size=4, pollEn=True, variables = [

            pyrogue.Variable(parent=self, name='eventCount', description='Event counter',
                             bitSize=32, bitOffset=0, base='uint', mode='RO') ])

        pyrogue.Block(parent=self, offset=0x14, size=4, pollEn=True, variables = [

            pyrogue.Variable(parent=self, name='randomData', description='Random data',
                             bitSize=32, bitOffset=0, base='uint', mode='RO') ])

        pyrogue.Command(parent=self, name='oneShot',description='Generate a single frame',
              function={ 1: { 'oneShotCmd': 1 } })

