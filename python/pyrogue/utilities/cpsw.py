#!/usr/bin/env python
#-----------------------------------------------------------------------------
# Title      : PyRogue Utilities CPSW conversion
#-----------------------------------------------------------------------------
# File       : pyrogue/utilities/cpsw.py
# Author     : Ryan Herbst, rherbst@slac.stanford.edu
# Created    : 2016-09-29
# Last update: 2016-09-29
#-----------------------------------------------------------------------------
# Description:
# Module for converting CPSW yaml files to python device creation functions.
#-----------------------------------------------------------------------------
# This file is part of the rogue software platform. It is subject to 
# the license terms in the LICENSE.txt file found in the top-level directory 
# of this distribution and at: 
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html. 
# No part of the rogue software platform, including this file, may be 
# copied, modified, propagated, or distributed except according to the terms 
# contained in the LICENSE.txt file.
#-----------------------------------------------------------------------------
import yaml
import datetime
import os
import pyrogue

def findAndReadYamlFiles(path,base):
    """
    Search path for yaml files from which to generate python modules
    base is the base path for the location where the generated files are put.
    """
       
    failed = []
    for root,dirs,files in os.walk(path):
        for f in files:
            p = f.find('.yaml')
            if len(f) > 5 and p == (len(f)-5):
                path = '%s/%s' % (root,f)
                if not readYamlFile(path,base): 
                    failed.append(path)
          
    if failed:
        print('Failed to process the following:')
        for f in failed:
            print(f)


def readYamlFile(path,base):
    """
    Ready yaml file defined by path and generate a python module
    base is the base path for the location where the generated files are put.
    """
    with open(path,'r') as f:
        try:
            d = pyrogue.yamlToDict(f.read())
        except Exception as e:
            print(str(e))
            print('')
            print('Error processing %s' % (path))
            print('')
            return False

    # Process each device in the dictionary
    for key,v in d.iteritems():
    
        # We only know about MMIODev types
        if not ( isinstance(v,dict) and v.has_key('class')):
            print('Class not found in %s' % (path))
            return False

        if v['class'] == 'MMIODev':
            if not genMMIODev(path,base,key,v): 
                print('')
                print('Error processing %s' % (path))
                print('')
                return False
        else:
            print('Uknown device type %s' % (v['class']))
            print('')
            print('Error processing %s' % (path))
            print('')
            return False

    return True


def genMMIODev(path,base,name,fields):
    lines = []
    size  = 0
    desc  = ''

    for key,value in fields.iteritems():
        if key == 'children':
            if not genChildren(value,lines): return False
        elif key == 'class' or key == 'configPrio' or key == 'name' or key == 'metadata':
            pass
        elif key == 'size':
            size = value
        elif key == 'description':
            desc = value
        else:
            print('Uknown field \'%s\' in MMIODev' % (key))
            return False

    fname = '%s/%s.py' % (base,name)

    with open(fname,'w') as f:
        f.write(genHeader(path,name))
        f.write('def create(name, offset, memBase=None, hidden=False):\n\n')
        f.write('    dev = pyrogue.Device(name=name,memBase=memBase,offset=offset,\n')
        f.write('                         hidden=hidden,size=0x%x,\n' % (int(size)))
        f.write('                         description=\'%s\')\n' % (desc))
        f.write('\n')

        for l in lines:
            f.write(l)

    return True


def genChildren(fields,lines):

    for key,value in fields.iteritems():
        if value['class'] == 'IntField':
            if not genIntField(key,value,lines): return False
        elif value['class'] == 'SequenceCommand':
            if not genSequence(key,value,lines): return False
        else:
            print('Uknown class %s in MMIODev' % (value['class']))
            return False

    return True


def genIntField(name,fields,lines):
    desc      = ''
    mode      = 'RW'
    bitSize   = 32
    bitOffset = 0
    offset    = 0
    nelms     = 1
    base      = 'uint'
    stride    = 0
    hidden    = False
    enum      = None

    for key,value in fields.iteritems():
        if   key == 'description': desc      = value
        elif key == 'mode'       : mode      = value
        elif key == 'sizeBits'   : bitSize   = value
        elif key == 'lsBit'      : bitOffset = value
        elif key == 'hidden'     : hidden    = value
        elif key == 'at':
            for k,v in value.iteritems():
                if   k == 'offset': offset = v
                elif k == 'nelms':  nelms  = v
                elif k == 'stride': stride = v
                else:
                    print('Unknown field %s as \'at\' sub field in IntField' % (k))
                    return False
        elif key == 'enums':
            enum = {}
            for l in value:
                en = ''
                ev = 0
                for k,v in l.iteritems():
                    if   k == 'class': pass
                    elif k == 'name':  en = v
                    elif k == 'value': ev = v
                    else:
                        print('Unknown field %s as \'enum\' sub field in IntField' % (k))
                        return False
                enum[ev] = en

        elif key == 'class' or key == 'name':
            pass
        else:
            print('Unknown field %s in IntField' % (key))
            return False

    if (offset % 4) != 0:
        offset = offset / 4
        bitOffset += ((offset % 4) * 8)

    if nelms != 1 and stride == 0:
        bitSize = bitSize * nelms

    loc  = '    dev.add(pyrogue.Variable(name=\'%s\',\n'
    loc += '                             description=\'%s\',\n'
    loc += '                             hidden=%s, enum=%s, offset=0x%x, bitSize=%s, bitOffset=%s, base=\'%s\', mode=\'%s\'))\n\n'

    if stride == 0:
        lines.append(loc % (name,desc,hidden,str(enum),int(offset),bitSize,bitOffset,base,mode))
    else:

        if stride % 4 != 0:
            print('Bad stride %i' % (stride))
            return False
        
        for i in range(0,nelms):
            lname = '%s_%i' % (name,i)
            loffset = offset + (i * stride)
            lines.append(loc % (lname,desc,hidden,str(enum),int(loffset),bitSize,bitOffset,base,mode))

    return True


def genSequence(name,fields,lines):
    desc      = ''
    offset    = 0
    nelms     = 1

    for key,value in fields.iteritems():
        if   key == 'description': desc      = value
        elif key == 'at':
            for k,v in value.iteritems():
                if   k == 'offset': offset = v
                else:
                    print('Unknown field %s as \'at\' sub field in SequenceCommand' % (k))
                    return False
        elif key == 'sequence':
            cmds = []
            for l in value:
                cn = ''
                cv = 0
                for k,v in l.iteritems():
                    if   k == 'entry': cn = v
                    elif k == 'value': cv = v
                    else:
                        print('Unknown field %s as \'sequence\' sub field in SequenceCommand' % (k))
                        return False
                cmds.append('%s.set(%s)' % (cn,cv))

        elif key == 'nelms' or key == 'name' or key == 'class':
            pass
        else:
            print('Unknown field %s in SequenceCommand' % (key))
            return False

    loc  = '    dev.add(pyrogue.Command(name=\'%s\',\n' % (name)
    loc += '                            description=\'%s\',\n' % (desc)
    loc += '                            hidden=False, base=None,\n'
    loc += '                            function="""\\\n'

    for c in cmds:
        c = c.replace('[','_')
        c = c.replace(']','')
        loc += '                                     dev.%s\n' % (c)
    loc += '                                     """\n\n'

    lines.append(loc)
    return True


def genHeader(source,name):
    d = datetime.date.today()

    ret  = '#!/usr/bin/env python\n'
    ret += '#-----------------------------------------------------------------------------\n'
    ret += '# Title      : PyRogue Device %s\n' % (name)
    ret += '#-----------------------------------------------------------------------------\n'
    ret += '# File       : %s.py\n' % (name)
    ret += '# Author     : Ryan Herbst, rherbst@slac.stanford.edu\n'
    ret += '# Created    : %04i-%02i-%02i\n' % (d.year,d.month,d.day)
    ret += '# Last update: %04i-%02i-%02i\n' % (d.year,d.month,d.day)
    ret += '#-----------------------------------------------------------------------------\n'
    ret += '# Description:\n'
    ret += '# Device creator for %s\n' % (name)
    ret += '# Auto created from %s\n' % (source)
    ret += '#-----------------------------------------------------------------------------\n'
    ret += '# This file is part of the rogue software platform. It is subject to \n'
    ret += '# the license terms in the LICENSE.txt file found in the top-level directory \n'
    ret += '# of this distribution and at: \n'
    ret += '#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html. \n'
    ret += '# No part of the rogue software platform, including this file, may be \n'
    ret += '# copied, modified, propagated, or distributed except according to the terms \n'
    ret += '# contained in the LICENSE.txt file.\n'
    ret += '#-----------------------------------------------------------------------------\n'
    ret += '\n'
    ret += 'import pyrogue\n'
    ret += '\n'
    return ret

