#!/usr/bin/env python
#-----------------------------------------------------------------------------
# Title      : PyRogue CPSW Export Utilities
#-----------------------------------------------------------------------------
# File       : pyrogue/utilities/cpsw.py
# Author     : Ryan Herbst, rherbst@slac.stanford.edu
# Created    : 2019-08-28
#-----------------------------------------------------------------------------
# Description:
# Tools to export Rogue modules to CPSW
#-----------------------------------------------------------------------------
# This file is part of the rogue software platform. It is subject to 
# the license terms in the LICENSE.txt file found in the top-level directory 
# of this distribution and at: 
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html. 
# No part of the rogue software platform, including this file, may be 
# copied, modified, propagated, or distributed except according to the terms 
# contained in the LICENSE.txt file.
#-----------------------------------------------------------------------------
import rogue.utilities
import rogue.utilities.fileio
import pyrogue
import rogue

def exportRemoteVariable(variable,indent):

    if 'List' in variable.typeStr or not('Bool' in variable.typeStr or 'String' in variable.typeStr or 'Int' in variable.typeStr):
        print(f"Error: Found variable {variable.path} with unsupported type {variable.typeStr}, error exporting")
        return ""

    if len(variable.bitOffset) > 1:
        print(f"Error: Found variable {variable.path} with multiple bit offsets, error exporting")
        return ""

    offset    = variable.offset + int(variable.bitOffset[0] / 8)
    bitOffset = int(variable.bitOffset[0] % 8)

    dat  = " " * indent +  "#########################################################\n"
    dat += " " * indent + f"{variable.name}:\n"
    dat += " " * indent +  "at:\n"
    dat += " " * indent + f"  offset: {offset:#x}\n"
    dat += " " * indent +  "class: IntField\n"
    dat += " " * indent +  "name: {variable.name}\n"

    if "String" in variable.typeStr:
        dat += " " * indent +  "encoding: ASCII\n"
        dat += " " * indent +  "sizeBits: 8\n"
        dat += " " * indent +  "nelms: {}\n".format(int(variable.bitSize[0]/8))
    elif "Int" in variable.typeStr or 'Bool' in variable.typeStr:
        dat += " " * indent + f"sizeBits: {variable.bitSize[0]}\n"
        dat += " " * indent + f"lsBit: {bitOffset}\n"

        if variable.disp != '{}':
            dat += " " * indent + "encoding: 16\n"

    dat += " " * indent + f"mode: {variable.mode}\n"
    dat += " " * indent + f"description: {variable.description}\n"

    if variable.enum is not None:
        dat +=  " " * indent +  "enums:\n"

        for k,v in variable.enum.items():
            dat += " " * indent + f"  - name: {v}\n"
            dat += " " * indent +  "    class: Enum\n"
            dat += " " * indent +  "    value: {}\n".format(int(k))

    return dat

def exportLinkVariable(variable, indent):
    dat  = " " * indent +  "#########################################################\n"
    dat += " " * indent +  "#Unsupported Link Variable\n"
    dat += " " * indent + f"#{variable.name}\n"
    dat += " " * indent + f"#typeStr: {variable.typeStr}\n"
    dat += " " * indent +  "#dependencies: {}\n".format(str(variable.dependencies))
    dat += " " * indent + f"#description: {variable.description}\n"

    print(f"Warning: Found link variable {variable.path}")
    return dat

def exportLocalVariable(variable, indent):
    dat  = " " * indent +  "#########################################################\n"
    dat += " " * indent +  "#Unsupported Local Variable\n"
    dat += " " * indent + f"#{variable.name}\n"
    dat += " " * indent + f"#typeStr: {variable.typeStr}\n"
    dat += " " * indent + f"#description: {variable.description}\n"

    print(f"Warning: Found local variable {variable.path}")
    return dat

def exportCommand(command, indent):
    dat  = " " * indent +  "#########################################################\n"
    dat += " " * indent +  "#Unsupported Command\n"
    dat += " " * indent + f"#{command.name}\n"
    dat += " " * indent + f"#description: {command.description}\n"

    print(f"Warning: Found command {command.path}")
    return dat

def exportSubDevice(device, indent, deviceList, dataDir):
    index = exportDevice(device, deviceList, dataDir)
    dn = f"{device.__class__.__name__}_{index}"

    dat  = " " * indent +  "#########################################################\n"
    dat += " " * indent + f"{device.name}\n"
    dat += " " * indent + f"    <<: *{dn}\n"
    dat += " " * indent +  "    at:\n"
    dat += " " * indent + f"      offset: {device.offset}\n"
    return dat,dn

def exportDevice(device, deviceList, dataDir):
    imp = []

    dat  =  "  class: MMIODev\n"
    dat +=  "  configPrio: 1\n"
    dat += f"  description: {device.description}\n"
    dat += f"  size: {device.size:#x}\n"
    dat +=  "  children:\n"
    dat +=  dat

    for k,node in device.nodes.items():
        if node.isinstance(pyrogue.EnableVariable):
            pass
        elif node.isinstance(pyrogue.LocalVariable):
            dat += exportLocalVariable(node,4)
        elif node.isinstance(pyrogue.RemoteVariable):
            dat += exportRemoteVariable(node,4)
        elif node.isinstance(pyrogue.LinkVariable):
            dat += exportLinkVariable(node,4)
        elif node.isinstance(pyrogue.Command):
            dat += exportCommand(node,4)
        elif node.isinstance(pyrogue.Device):
            ld,dn = exportSubDevice(node,4,deviceList, dataDir)
            dat += ld
            imp.append(dn)
        else:
            print(f"Error: Unsupported node type {node.path}")

    prefix  = "##############################################################################\n"
    prefix += "#Auto Generated CPSW Yaml File From pyrogue.utilities.cpsw.py                #\n"
    prefix += "##############################################################################\n"
    prefix += "#schemaversion 3.0.0\n"

    for i in imp:
        prefix += f"#once {i}.yaml\n"

    prefix += "\n"

    if device.__class__.__name__ not in deviceList:
        deviceList[device.__class__.__name__] = []

    for i in range(len(deviceList[device.__class__.__name__]) + 1):
        tname = device.__class__.__name__ + f"_{i}"
        ddat  = prefix
        ddat +=  f"{tname}: &{tname}\n"
        ddat +=  dat

        if i >= len(deviceList[device.__class__.__name__]):
            deviceList[device.__class__.__name__].append(ddat)
        elif deviceList[device.__class__.__name__][i] == ddat:
            break

    with open(dataDir + "/" + tname + ".yaml","w") as f:
        f.write(ddat)

    return i

def exportRoot(root,dataDir):
    dlist = {}

    for k,node in root.nodes.items():
        if node.isinstance(pyrogue.Device):
            exportDevice(node,dlist,dataDir)

