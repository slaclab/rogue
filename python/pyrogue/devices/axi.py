#!/usr/bin/env python

import pyrogue

class AxiVersion(pyrogue.Device):
    """AXI Lite Version Class"""

    # Declaration. parent is the owner of this object which can be another Device or the root node.
    # memBase is either the register bus server (srp, rce mapped memory, etc) or the device which
    # contains this object. In most cases the parent and memBase are the same but they can be 
    # different in more complex bus structures. They will also be different for the top most node.
    # The setMemBase call can be used to update the memBase for this Device. All sub-devices and local
    # blocks will be updated.
    def __init__(self, parent, memBase=None, offset=0):
        pyrogue.Device.__init__(self, parent=parent, name='AxiVersion', description='AXI-Lite Version Module', 
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
            pyrogue.Variable(parent=self, name='FpgaVersion', description='FPGA Firmware Version Number',
                             bitSize=32, bitOffset=0, base='hex', mode='RO') ])

        pyrogue.Block(parent=self, offset=0x4, size=4, variables = [

            # Example of using setFunction and getFunction. setFunction and getFunctions are defined in the class
            # at the bottom. getFunction is defined as a series of python calls. When using the defined
            # function the scope is relative to the location of the function defintion. A pointer to the variable
            # and passed value are provided as args. See UserConstants below for an alernative method.
            pyrogue.Variable(parent=self, name='ScratchPad', description='Register to test read and writes',
                             bitSize=32, bitOffset=0, base='hex', mode='RW', setFunction=self.setVariableExample,
                             getFunction=self.getVariableExample) ])

        pyrogue.Block(parent=self, offset=0x8, size=8, variables = [

            pyrogue.Variable(parent=self, name='DeviceDna', description='Xilinx Device DNA value burned into FPGA',
                             bitSize=64, bitOffset=0, base='hex', mode='RO') ])

        pyrogue.Block(parent=self, offset=0x10, size=8, variables = [

            pyrogue.Variable(parent=self, name='FdSerial', description='Board ID value read from DS2411 chip',
                             bitSize=64, bitOffset=0, base='hex', mode='RO') ])

        pyrogue.Block(parent=self, offset=0x18, size=4, variables = [

            # Here we define MasterReset as mode 'CMD' this will ensure it does not get written during
            # writeAll and writeStale commands
            pyrogue.Variable(parent=self, name='MasterReset', description='Optional User Reset',
                             bitSize=1, bitOffset=0, base='bool', mode='CMD', hidden=True) ])

        pyrogue.Block(parent=self, offset=0x1C, size=4, variables = [

            pyrogue.Variable(parent=self, name='FpgaReload', description='Optional reload the FPGA from the attached PROM',
                             bitSize=1, bitOffset=0, base='bool', mode='CMD', hidden=True) ])

        pyrogue.Block(parent=self, offset=0x20, size=4, variables = [

            pyrogue.Variable(parent=self, name='FpgaReloadAddress', description='Reload start address',
                             bitSize=32, bitOffset=0, base='hex', mode='RW') ])

        pyrogue.Block(parent=self, offset=0x24, size=4, pollEn=True, variables = [

            pyrogue.Variable(parent=self, name='Counter', description='Free running counter',
                             bitSize=32, bitOffset=0, base='hex', mode='RO') ])

        pyrogue.Block(parent=self, offset=0x28, size=4, variables = [

            # Bool is not used locally. Access will occur just as a uint or hex. The GUI will know how to display it.
            pyrogue.Variable(parent=self, name='FpgaReloadHalt', description='Used to halt automatic reloads via AxiVersion',
                             bitSize=1, bitOffset=0, base='bool', mode='RW') ])

        pyrogue.Block(parent=self, offset=0x2C, size=4, pollEn=True, variables = [

            pyrogue.Variable(parent=self, name='UpTimeCnt', description='Number of seconds since reset',
                             bitSize=32, bitOffset=0, base='hex', mode='RO') ])

        pyrogue.Block(parent=self, offset=0x30, size=4, variables = [

            pyrogue.Variable(parent=self, name='DeviceId', description='Device identification',
                             bitSize=32, bitOffset=0, base='hex', mode='RO') ])

        for i in range(0,64):
            pyrogue.Block(parent=self, offset=0x400+(i*4), size=4, variables = [

                # Example of using setFunction and getFunction passed as strings. The scope is local to 
                # the variable object with the passed value available as 'value' in the scope.
                # The get function must set the 'value' variable as a result of the function.
                pyrogue.Variable(parent=self, name='UserConstant_%02i'%(i), description='Optional user input values',
                                 bitSize=32, bitOffset=0, base='hex', mode='RW',
                                 getFunction="""
                                             value = self._block.getUInt(self.bitOffset,self.bitSize)
                                             """,
                                 setFunction="""
                                             self._block.setUInt(self.bitOffset,self.bitSize,value)
                                             """
                )])

        pyrogue.Block(parent=self, offset=0x800, size=256, variables = [

            pyrogue.Variable(parent=self, name='BuildStamp', description='Firmware build string',
                             bitSize=256*8, bitOffset=0, base='string', mode='RO') ])

        #####################################
        # Create commands
        #####################################

        # A command has an associated function. The function can be a series of
        # python commands in a string. Function calls are executed in the command scope
        # the passed arg is available as 'arg'. Use self._parent to get to device scope.
        pyrogue.Command(parent=self, name="MasterReset",description="Master Reset",
           function="self._parent.MasterReset.setAndWrite(1)")
       
        # A command can also be a call to a local function with local scope.
        # The command object and the arg are passed
        pyrogue.Command(parent=self, name="FpgaReload",description="Reload FPGA",
           function=self.fpgaReload)

        pyrogue.Command(parent=self, name="CounterReset",description="Counter Reset",
           function="self._parent.Counter.setAndWrite(1)")

        # Example printing the arg and showing a larger block. The indentation will be adjusted.
        pyrogue.Command(parent=self, name="TestCommand",description="Test Command",
           function="""\
                    print("Someone executed the %s command" % (self.name))
                    print("The passed arg was %s" % (arg))
                    print("My device is %s" % (self._parent.name))
                    """)

    # Example command function
    def fpgaReload(self,cmd,arg):
        self.FpgaReload.setAndWrite(1)

    # Example variable set function
    def setVariableExample(self,var,value):
        var._block.setUInt(var.bitOffset,var.bitSize,value)

    # Example variable get function
    def getVariableExample(self,var):
        return(var._block.getUInt(var.bitOffset,var.bitSize))

