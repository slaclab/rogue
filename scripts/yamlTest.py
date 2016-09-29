#!/usr/bin/env python

import rogue.hardware.pgp
import rogue.utilities 
import rogue.interfaces.stream
import pyrogue
import time
import yaml

pgpVc0 = rogue.hardware.pgp.PgpCard("/dev/pgpcard_0",0,0)
pgpVc1 = rogue.hardware.pgp.PgpCard("/dev/pgpcard_0",0,1)
pgpVc3 = rogue.hardware.pgp.PgpCard("/dev/pgpcard_0",0,3)

print("PGP Card Version: %x" % (pgpVc0.getInfo().version))

# Create and Connect SRP
srp = rogue.protocols.srp.SrpV0()
srp.setSlave(pgpVc0)
pgpVc0.setSlave(srp)

dev = None

with open('AxiVersion.yaml', 'r') as f:
   doc = yaml.load(f)

   for br in doc:
      if br == 'Device':
         dev = pyrogue.Device(doc[br])

dev.addAt(srp)
dev.readAll()

lst = dev.getFields()

for field in lst:
    print("%s = %s" % (field,str(dev.get(field))))

