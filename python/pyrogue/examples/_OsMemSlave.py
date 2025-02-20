#!/usr/bin/env python3
#-----------------------------------------------------------------------------
# Company    : SLAC National Accelerator Laboratory
#-----------------------------------------------------------------------------
#  Description:
#       Example OS Memory Slave
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
import pyrogue.interfaces
import subprocess

class OsMemSlave(pyrogue.interfaces.OsCommandMemorySlave):

    def __init__(self):
        super().__init__()

        @self.command(base=pyrogue.Float(32),addr=0x00)
        def uptime(self, arg):

            # Read, ignore write
            if arg is None:

                # This try block helps handle an issue with the CI test, don't include
                # this in production versions, instead let the error propogate
                try:
                    res = subprocess.run(['uptime','-r'], capture_output=True, text=True)
                    return float(res.stdout.split()[1])
                except Exception:
                    return 0

        @self.command(base=pyrogue.Float(32),addr=0x04)
        def load1min(self, arg):

            # Read, ignore write
            if arg is None:

                # This try block helps handle an issue with the CI test, don't include
                # this in production versions, instead let the error propogate
                try:
                    res = subprocess.run(['uptime','-r'], capture_output=True, text=True)
                    return float(res.stdout.split()[3])
                except Exception:
                    return 0

        @self.command(base=pyrogue.Float(32),addr=0x08)
        def load5min(self, arg):

            # Read, ignore write
            if arg is None:

                # This try block helps handle an issue with the CI test, don't include
                # this in production versions, instead let the error propogate
                try:
                    res = subprocess.run(['uptime','-r'], capture_output=True, text=True)
                    return float(res.stdout.split()[4])
                except Exception:
                    return 0

        @self.command(base=pyrogue.Float(32),addr=0x0C)
        def load15min(self, arg):

            # Read, ignore write
            if arg is None:

                # This try block helps handle an issue with the CI test, don't include
                # this in production versions, instead let the error propogate
                try:
                    res = subprocess.run(['uptime','-r'], capture_output=True, text=True)
                    return float(res.stdout.split()[5])
                except Exception:
                    return 0

        @self.command(base=pyrogue.UInt(32),addr=0x10)
        def echoFile(self, arg):

            # Write
            if arg is not None:
                subprocess.run(['bash','-c',f'echo {arg} >> /tmp/osCmdTest.txt'])

            # Read
            else:

                res = subprocess.run(['tail','-1', '/tmp/osCmdTest.txt'], capture_output=True, text=True)
                return int(res.stdout)
