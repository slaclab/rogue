#-----------------------------------------------------------------------------
# This file is part of the rogue library utilities. It is subject to
# the license terms in the LICENSE.txt file found in the top-level directory
# of this distribution and at:
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
# No part of rogue, including this file, may be
# copied, modified, propagated, or distributed except according to the terms
# contained in the LICENSE.txt file.
#-----------------------------------------------------------------------------

# Run this script as shown below:
# python -m pyrogue.utilities.hls._RegInterfParser --memoryDevice
# python -m pyrogue.utilities.hls._RegInterfParser --remoteVariable
# python -m pyrogue.utilities.hls._RegInterfParser --remoteCommand

import os
import argparse
from collections import namedtuple
from zipfile import ZipFile

##############################################################################
# Supported types of rogue devices and variables                             #
##############################################################################
# RemoteVariable type
RemoteVariable = namedtuple('RemoteVariable', ['name', 'description', 'offset', 'bitSize', 'bitOffset', 'base',
                                               'mode'], defaults=['VarName', 'description', 0x00000, 8, 0, 'pr.Int',
                                                                  'RW'])

# RemoteCommand type
RemoteCommand = namedtuple('RemoteCommand', ['name', 'description', 'offset', 'bitSize', 'bitOffset', 'base',
                                             'function'], defaults=['CmdName', 'description', 0x00000, 8, 0, 'pr.UInt',
                                                                    'lambda cmd: cmd.post(1)'])

# MemoryDevice type
MemoryDevice = namedtuple('MemoryDevice', ['name', 'offset', 'size', 'wordBitSize', 'stride', 'base'],
                          defaults=['DevName', 0x00000, 16, 8, 16, 'pr.Int'])
##############################################################################

vartype = ''

def parse():
    # Get the path to the zip file
    zname = input('Enter the path to the zipfile: ')
    fname = zname

    try:
        zhand = open(zname)
    except FileNotFoundError:
        print('Zip file cannot be opened:', zname)
        del zhand
        exit()

    # Extract all the contents of the zip file in the current directory
    with ZipFile(zname, 'r') as zipObj:
        zipObj.extractall()

    for root, dirs, files in os.walk("./"):
        for file in files:
            if file.endswith("_hw.h"):
                fname = os.path.join(root, file)

    try:
        fhand = open(fname)
    except FileNotFoundError:
        print('Register file cannot be opened:', fname)
        exit()

    macrolines = []

    # Parse the register interface file and extract macros
    for line in fhand:
        line = line.lstrip()
        line = line.rstrip()
        words = line.split()

        # Look for the #define lines and save them off
        if len(words) > 0 and words[0] == '#define':
            if len(words) == 3:
                words = words[1::]
                macrolines.append((words[0], words[1]))

    # Keep track of indices of processed macros
    matchedIndices = []

    # Group all macros for the same device or variable together by detecting name similarities
    devs = []
    for m1 in macrolines:
        dev = []
        for m2 in macrolines:
            # Check macros differences and extract device/variable/command info
            if macrolines.index(m2) not in matchedIndices and m1 != m2:
                terms = ['ADDR', 'BASE', 'HIGH', 'BITS', 'WIDTH', 'DEPTH']
                diffm1m2 = list((set(m1[0].split('_'))-set(m2[0].split('_'))))
                diffm2m1 = list((set(m2[0].split('_'))-set(m1[0].split('_'))))
                if len(diffm1m2) == 1 and len(diffm2m1) == 1 and diffm1m2[0] in terms and diffm2m1[0] in terms:
                    dev.append(m1)
                    dev.append(m2)
                    matchedIndices.append(macrolines.index(m1))
                    matchedIndices.append(macrolines.index(m2))

                if (len(diffm1m2) == 2 and len(diffm2m1) == 1 and diffm2m1[0] in terms and 'ADDR' in diffm1m2 and ('BASE' in diffm1m2 or 'HIGH' in diffm1m2)) or \
                   (len(diffm1m2) == 1 and len(diffm2m1) == 2 and diffm1m2[0] in terms and 'ADDR' in diffm2m1 and ('BASE' in diffm2m1 or 'HIGH' in diffm2m1)):
                    dev.append(m1)
                    dev.append(m2)
                    matchedIndices.append(macrolines.index(m1))
                    matchedIndices.append(macrolines.index(m2))

        # Remove duplicates
        dev = list(dict.fromkeys(dev))

        # Save device macro to device list
        if dev:
            devs.append(dev)
        else:
            if macrolines.index(m1) not in matchedIndices:
                dev.append(m1)
                devs.append(dev)

    # List to hold device names and parameters
    params = []

    # Extract device and variable parameters
    for dev in devs:
        # Identify parameters and save off in a list
        dname = 'DevName'
        addr = 0x00000
        width = depth = 8
        for macroline in dev:
            macroname = macroline[0].split('_')
            # Get word bit size
            if 'BITS' in list(macroname):
                width = macroline[1]
            elif 'WIDTH' in list(macroname):
                width = macroline[1]

            # Get bit depth
            if 'DEPTH' in list(macroname):
                depth = macroline[1]

            # Get address offset
            if 'ADDR' in list(macroname) and 'BASE' in list(macroname):
                addr = macroline[1]
            elif 'ADDR' in list(macroname) and 'HIGH' in list(macroname):
                pass
            elif 'ADDR' in list(macroname):
                addr = macroline[1]

            # Get device name
            if dname == 'DevName':
                dname = macroline[0]
            else:
                if len(dname) > len(macroline[0]):
                    dname = macroline[0]

        # Modify dev/var name to its shortest and simplest form
        terms = ['ADDR', 'BASE', 'HIGH', 'BITS', 'WIDTH', 'DEPTH']
        for t in terms:
            if t in dname.split('_'):
                dname = dname.split('_')
                dname.remove(t)
                dname = "_".join(dname)

        if vartype is RemoteVariable.__name__:
            var = RemoteVariable(name=dname, description='remote variable', offset=addr, bitSize=width)
            params.append(var)
        elif vartype is MemoryDevice.__name__:
            var = MemoryDevice(name=dname, offset=addr, size=depth, wordBitSize=width)
            params.append(var)
        elif vartype is RemoteCommand.__name__:
            var = RemoteCommand(name=dname, description='remote command', offset=addr, bitSize=width)
            params.append(var)

    return params

def write(parameters):
    with open('application.py', 'w+') as fhand:

        fhand.write('#-----------------------------------------------------------------------------\n')
        fhand.write('# This file is part of the utilities for the rogue library. It is subject to\n')
        fhand.write('# the license terms in the LICENSE.txt file found in the top-level directory\n')
        fhand.write('# of this distribution and at:\n')
        fhand.write('#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.\n')
        fhand.write('# No part of the rogue, including this file, may be copied, modified,\n')
        fhand.write('# propagated, or distributed except according to the terms\n')
        fhand.write('# contained in the LICENSE.txt file.\n')
        fhand.write('#-----------------------------------------------------------------------------\n')
        fhand.write('\n')
        fhand.write('import pyrogue as pr\n')
        fhand.write('\n')
        fhand.write('class Application(pr.Device):\n')
        fhand.write('    def __init__(self, **kwargs):\n')
        fhand.write('        super().__init__(**kwargs)\n')
        fhand.write('\n')

        for param in parameters:
            print(param)
            if vartype is RemoteVariable.__name__:
                fhand.write('        pr.RemoteVariable(\n')
                argline = \
                    '                        name=' + '\'' + param.name + '\'' + ',\n' + \
                    '                        description=' + '\'' + param.description + '\'' + ',\n' + \
                    '                        offset=' + str(param.offset) + ',\n' + \
                    '                        bitSize=' + str(param.bitSize) + ',\n' + \
                    '                        bitOffset=' + str(param.bitOffset) + ',\n' + \
                    '                        base=' + str(param.base) + ',\n' + \
                    '                        mode=' + '\'' + str(param.mode) + '\'' + ',\n'
                fhand.write(argline)
                fhand.write('                       )\n\n')
            elif vartype is MemoryDevice.__name__:
                fhand.write('        pr.MemoryDevice(\n')
                argline = \
                    '                        name=' + '\'' + param.name + '\'' + ',\n' + \
                    '                        offset=' + str(param.offset) + ',\n' + \
                    '                        size=' + str(param.size) + ',\n' + \
                    '                        wordBitSize=' + str(param.wordBitSize) + ',\n' + \
                    '                        stride=' + str(param.stride) + ',\n' + \
                    '                        base=' + str(param.base) + ',\n'
                fhand.write(argline)
                fhand.write('                       )\n\n')
            elif vartype is RemoteCommand.__name__:
                fhand.write('        self.add(pr.RemoteCommand(\n')
                argline = \
                    '                        name=' + '\'' + param.name + '\'' + ',\n' + \
                    '                        description=' + '\'' + param.description + '\'' + ',\n' + \
                    '                        offset=' + str(param.offset) + ',\n' + \
                    '                        bitSize=' + str(param.bitSize) + ',\n' + \
                    '                        bitOffset=' + str(param.bitOffset) + ',\n' + \
                    '                        base=' + str(param.base) + ',\n' + \
                    '                        function=' + str(param.function) + ',\n'
                fhand.write(argline)
                fhand.write('                       ))\n\n')

        fhand.write('    # This function call occurs after loading YAML configuration\n')
        fhand.write('    def initialize(self):\n')
        fhand.write('        super().initialize()\n')
        fhand.write('\n')
        fhand.write('        # Add and execute the relevant commands below\n')
        fhand.write('\n\n')

def run():
    # Read command line option (i.e. output type)
    parser = argparse.ArgumentParser(description='Specify type of output.')
    parser.add_argument('--remoteCommand', action='store_true', required=False, help='set up remote commands')
    parser.add_argument('--remoteVariable', action='store_true', required=False, help='connect remote variables to register interface')
    parser.add_argument('--memoryDevice', action='store_true', required=False, help='connect memory devices to register interface')
    args = parser.parse_args()

    global vartype

    if args.memoryDevice:
        vartype = 'MemoryDevice'
    elif args.remoteVariable:
        vartype = 'RemoteVariable'
    elif args.remoteCommand:
        vartype = 'RemoteCommand'
    else:
        print('Please provide type of output at the command line.  Run with --help for more info.')
        exit(0)

    dev_params = parse()
    write(dev_params)

# __main__ block
if __name__ == '__main__':
    run()
