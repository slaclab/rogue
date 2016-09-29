#!/usr/bin/env python

import rogue.hardware.pgp
import rogue.utilities 
import rogue.interfaces.stream
import pyrogue
import time

pgpVc0 = rogue.hardware.pgp.PgpCard("/dev/pgpcard_0",0,0)
pgpVc1 = rogue.hardware.pgp.PgpCard("/dev/pgpcard_0",0,1)
pgpVc3 = rogue.hardware.pgp.PgpCard("/dev/pgpcard_0",0,3)

print("PGP Card Version: %x" % (pgpVc0.getInfo().version))

# Create and Connect SRP
srp = rogue.protocols.srp.SrpV0()
srp.setSlave(pgpVc0)
pgpVc0.setSlave(srp)

# Setup device
dev = pyrogue.Device("AxiVersion","AXI-Lite Version Module",0x1000)
dev.setSlave(srp)

field = pyrogue.IntField()
field.offset = 0x00 
field.name = "FpgaVersion"
field.mode = "RO"
field.description = "FPGA Firmware Version Number "
dev.addField(field)

field = pyrogue.IntField()
offset = 0x04
field.name = "ScratchPad"
field.mode = "RW"
field.description = "Register to test reads and writes"
dev.addField(field)

field = pyrogue.IntField()
field.offset = 0x08
field.name = "DeviceDna"
field.sizeBits = 64
field.mode = "RO"
field.description = "Xilinx Device DNA value burned into FPGA"
dev.addField(field)

field = pyrogue.IntField()
field.offset = 0x10
field.name = "FdSerial"
field.sizeBits = 64
field.mode = "RO"
field.description = "Board ID value read from DS2411 chip"
dev.addField(field)

field = pyrogue.IntField()
field.offset = 0x18
field.name = "MasterReset"
field.mode = "WO"
field.sizeBits = 1
field.description = "Optional User Reset"
dev.addField(field)

field = pyrogue.IntField()
field.offset = 0x1C
field.name = "FpgaReload"
field.mode = "RW"
field.sizeBits = 1
field.description = "Optional Reload the FPGA from the attached PROM"
dev.addField(field)

field = pyrogue.IntField()
field.offset = 0x20
field.name = "FpgaReloadAddress"
field.mode = "RW"
field.description = "Reload start address"
dev.addField(field)

field = pyrogue.IntField()
field.offset = 0x24
field.name = "Counter"
field.mode = "RO"
field.description = "Free running counter"
dev.addField(field)

field = pyrogue.IntField()
field.offset = 0x28
field.name = "FpgaReloadHalt"
field.mode = "RW"
field.sizeBits = 1
field.description = "Used to halt automatic reloads via AxiVersion"
dev.addField(field)

field = pyrogue.IntField()
field.offset = 0x2C
field.name = "UpTimeCnt"
field.mode = "RO"
field.description = "Number of seconds since last reset"
dev.addField(field)

field = pyrogue.IntField()
field.offset = 0x30
field.name = "DeviceId"
field.mode = "RO"
field.description = "Device Identification"
dev.addField(field)

field = pyrogue.IntField()
field.offset = 0x400
field.name = "UserConstants"
field.nelms = 64
field.mode = "RO"
field.description = "Optional user input values"
dev.addField(field)

field = pyrogue.IntField()
field.offset = 0x800
field.name = "BuildStamp"
field.nelms = 64
field.sizeBits = 8
field.mode = "RO"
field.description = "Firmware Build String"
dev.addField(field)

dev.readAll()

lst = dev.getList()

for fields in lst:
    print("%s = %s" % (fields.name,str(dev.get(fields.name))))

