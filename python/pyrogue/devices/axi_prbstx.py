#!/usr/bin/env python
#-----------------------------------------------------------------------------
# Title      : PyRogue AXI Version Module
#-----------------------------------------------------------------------------
# File       : pyrogue/devices/axi_version.py
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

def create(name, offset, memBase=None, hidden=False):
    """Create the aixPrbsTx device"""

    dev = pyrogue.Device(name=name, memBase=memBase, offset=offset, hidden=hidden, size=0x100,
                         description='HW PRBS Transmitter')

    # Variables

    dev.add(pyrogue.Variable(name='axiEn', description='AXI Bus enable',
                             offset=0x0, bitSize=1, bitOffset=0, base='bool', mode='RW'))
    
    dev.add(pyrogue.Variable(name='txEn', description='Transmit enable',
                             offset=0x0, bitSize=1, bitOffset=1, base='bool', mode='RW')) 

    dev.add(pyrogue.Variable(name='busy', description='Busy Flag',
                             offset=0x0, bitSize=1, bitOffset=2, base='bool', mode='RO')) 

    dev.add(pyrogue.Variable(name='overflow', description='Overflow Flag',
                             offset=0x0, bitSize=1, bitOffset=3, base='bool', mode='RO')) 

    dev.add(pyrogue.Variable(name='oneShotCmd', hidden=True, description='Oneshot frame generate',
                             offset=0x0, bitSize=1, bitOffset=4, base='bool', mode='CMD')) 

    dev.add(pyrogue.Variable(name='fwCnt', description='????',
                             offset=0x0, bitSize=1, bitOffset=5, base='bool', mode='RW'))

    dev.add(pyrogue.Variable(name='packetLength', description='Packet Length Control',
                             offset=0x4,bitSize=32, bitOffset=0, base='uint', mode='RW'))

    dev.add(pyrogue.Variable(name='tDest', description='TDEST value for frame',
                             offset=0x8,bitSize=8, bitOffset=0, base='hex', mode='RW'))

    dev.add(pyrogue.Variable(name='tId', description='TID value for frame',
                             offset=0x8,bitSize=8, bitOffset=8, base='hex', mode='RW'))

    dev.add(pyrogue.Variable(name='dataCount', description='Data counter', pollEn=True,
                             offset=0xC, bitSize=32, bitOffset=0, base='uint', mode='RO'))

    dev.add(pyrogue.Variable(name='eventCount', description='Event counter', pollEn=True,
                             offset=0x10, bitSize=32, bitOffset=0, base='uint', mode='RO'))

    dev.add(pyrogue.Variable(name='randomData', description='Random data', pollEn=True,
                             offset=0x14, bitSize=32, bitOffset=0, base='uint', mode='RO'))

    # Commands

    dev.add(pyrogue.Command(name='oneShot',description='Generate a single frame',
                            function=collections.OrderedDict({'oneShotCmd': 1})))

    # Return device
    return dev

