#-----------------------------------------------------------------------------
# Company    : SLAC National Accelerator Laboratory
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
import math

import pyrogue


def exportRemoteVariable(variable: pyrogue.RemoteVariable, indent: int) -> tuple[str, int]:
    """Export a ``RemoteVariable`` into CPSW YAML text.

    Parameters
    ----------
    variable : pyrogue.RemoteVariable
        PyRogue remote variable instance.
    indent : int
        Number of leading spaces for generated YAML lines.

    Returns
    -------
    tuple[str, int]
        Generated YAML snippet and discovered byte size.
    """

    if variable.ndType is not None or not ('Bool' in variable.typeStr or 'String' in variable.typeStr or 'Int' in variable.typeStr):
        print(f"Error: Found variable {variable.path} with unsupported type {variable.typeStr}, error exporting")
        return "", 0

    #if len(variable.bitOffset) > 1:
    #    print(f"Warning: Splitting multiple bit offset variable {variable.path}")
    size = 0

    for i in range(len(variable.bitOffset)):

        offset    = variable.offset + int(variable.bitOffset[i] / 8)
        bitOffset = int(variable.bitOffset[i] % 8)

        if (offset + math.ceil(variable.bitSize[i]/8)) > size:
            size = offset + math.ceil(variable.bitSize[i]/8)

    if len(variable.bitOffset) > 1:
        name = f"{variable.name}[{i}]"
    else:
        name = f"{variable.name}"

    dat  = " " * indent +  "#########################################################\n"
    dat += " " * indent +  name + ":\n"
    dat += " " * indent +  "at:\n"
    dat += " " * indent + f"  offset: {offset:#x}\n"
    dat += " " * indent +  "class: IntField\n"
    dat += " " * indent +  "name: " + name + "\n"

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

    return dat, size


def exportLinkVariable(variable: pyrogue.LinkVariable, indent: int) -> str:
    """Export a placeholder block for an unsupported ``LinkVariable``.

    Parameters
    ----------
    variable : pyrogue.LinkVariable
        Link variable to describe in the generated placeholder comment block.
    indent : int
        Number of leading spaces for generated YAML lines.

    Returns
    -------
    str
        YAML comment block describing the unsupported link variable.
    """
    dat  = " " * indent +  "#########################################################\n"
    dat += " " * indent +  "#Unsupported Link Variable\n"
    dat += " " * indent + f"#{variable.name}\n"
    dat += " " * indent + f"#typeStr: {variable.typeStr}\n"
    dat += " " * indent +  "#dependencies: {}\n".format(str(variable.dependencies))
    dat += " " * indent + f"#description: {variable.description}\n"

    #print(f"Warning: Found link variable {variable.path}")
    return dat


def exportLocalVariable(variable: pyrogue.LocalVariable, indent: int) -> str:
    """Export a placeholder block for an unsupported ``LocalVariable``.

    Parameters
    ----------
    variable : pyrogue.LocalVariable
        Local variable to describe in the generated placeholder comment block.
    indent : int
        Number of leading spaces for generated YAML lines.

    Returns
    -------
    str
        YAML comment block describing the unsupported local variable.
    """
    dat  = " " * indent +  "#########################################################\n"
    dat += " " * indent +  "#Unsupported Local Variable\n"
    dat += " " * indent + f"#{variable.name}\n"
    dat += " " * indent + f"#typeStr: {variable.typeStr}\n"
    dat += " " * indent + f"#description: {variable.description}\n"

    #print(f"Warning: Found local variable {variable.path}")
    return dat


def exportCommand(command: pyrogue.LocalCommand, indent: int) -> str:
    """Export a placeholder block for an unsupported command node.

    Parameters
    ----------
    command : pyrogue.LocalCommand
        Command node to describe in the generated placeholder comment block.
    indent : int
        Number of leading spaces for generated YAML lines.

    Returns
    -------
    str
        YAML comment block describing the unsupported command node.
    """
    dat  = " " * indent +  "#########################################################\n"
    dat += " " * indent +  "#Unsupported Command\n"
    dat += " " * indent + f"#{command.name}\n"
    dat += " " * indent + f"#description: {command.description}\n"

    #print(f"Warning: Found command {command.path}")
    return dat


def exportSubDevice(device: pyrogue.Device, indent: int, deviceList: dict[str, list[str]], dataDir: str) -> tuple[str, str, int]:
    """Export a child device and its reference include block.

    Parameters
    ----------
    device : pyrogue.Device
        Child device to export.
    indent : int
        Number of leading spaces for generated YAML lines.
    deviceList : dict[str, list[str]]
        Cache of generated class YAML bodies keyed by class name.
    dataDir : str
        Output directory for generated YAML files.

    Returns
    -------
    tuple[str, str, int]
        Child include YAML block, generated anchor name, and computed size.
    """
    index, size = exportDevice(device, deviceList, dataDir)

    if index > 0:
        dn = f"{device.__class__.__name__}_{index}"
    else:
        dn = f"{device.__class__.__name__}"

    dat  = " " * indent +  "#########################################################\n"
    dat += " " * indent + f"{device.name}\n"
    dat += " " * indent + f"    <<: *{dn}\n"
    dat += " " * indent +  "    at:\n"
    dat += " " * indent + f"      offset: {device.offset:#x}\n"

    size += device.offset
    return dat, dn, size


def exportDevice(device: pyrogue.Device, deviceList: dict[str, list[str]], dataDir: str) -> tuple[int, int]:
    """Export a device tree into CPSW YAML files.

    Parameters
    ----------
    device : pyrogue.Device
        Root or child PyRogue device to export.
    deviceList : dict[str, list[str]]
        Cache of generated class YAML bodies keyed by class name.
    dataDir : str
        Output directory for generated YAML files.

    Returns
    -------
    tuple[int, int]
        Generated device-class index and discovered size.
    """
    imp: list[str] = []
    size = 0
    dat  = ""

    for k,node in device.nodes.items():
        if node.isinstance(pyrogue.EnableVariable):
            pass
        elif node.isinstance(pyrogue.LocalVariable):
            dat += exportLocalVariable(node,4)
        elif node.isinstance(pyrogue.RemoteVariable):
            d, s = exportRemoteVariable(node, 4)
            dat += d
            if s > size:
                size = s
        elif node.isinstance(pyrogue.LinkVariable):
            dat += exportLinkVariable(node,4)
        elif node.isinstance(pyrogue.Command):
            dat += exportCommand(node,4)
        elif node.isinstance(pyrogue.Device):
            ld, dn, s = exportSubDevice(node, 4, deviceList, dataDir)
            dat += ld
            if s > size:
                size = s
            imp.append(dn)
        else:
            print(f"Error: Unsupported node type {node.path}")

    prefix  = "##############################################################################\n"
    prefix += "#Auto Generated CPSW Yaml File From pyrogue.utilities.cpsw.py                #\n"
    prefix += "##############################################################################\n"
    prefix += "#schemaversion 3.0.0\n"
    include = ""

    for i in imp:
        include += f"#include {i}.yaml\n"

    if device.__class__.__name__ not in deviceList:
        deviceList[device.__class__.__name__] = []

    for i in range(len(deviceList[device.__class__.__name__]) + 1):
        if i > 0:
            tname = device.__class__.__name__ + f"_{i}"
        else:
            tname = device.__class__.__name__

        ddat  = prefix
        ddat +=  f"#once {tname}\n"
        ddat +=  include + "\n"
        ddat +=  f"{tname}: &{tname}\n"
        ddat  =  "  class: MMIODev\n"
        ddat +=  "  configPrio: 1\n"
        ddat += f"  description: {device.description}\n"
        ddat += f"  size: {size:#x}\n"
        ddat +=  "  children:\n"
        ddat +=  dat

        if i >= len(deviceList[device.__class__.__name__]):
            deviceList[device.__class__.__name__].append(ddat)
        elif deviceList[device.__class__.__name__][i] == ddat:
            break

    with open(dataDir + "/" + tname + ".yaml", "w") as f:
        f.write(ddat)

    return i, size


def exportRoot(root: pyrogue.Root, dataDir: str) -> None:
    """Export all top-level devices from a PyRogue root node.

    Parameters
    ----------
    root : pyrogue.Root
        Root node containing top-level device children to export.
    dataDir : str
        Output directory for generated YAML files.
    """
    dlist: dict[str, list[str]] = {}

    for _, node in root.nodes.items():
        if node.isinstance(pyrogue.Device):
            exportDevice(node, dlist, dataDir)
