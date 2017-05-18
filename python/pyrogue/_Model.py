#!/usr/bin/env python
#-----------------------------------------------------------------------------
# Title      : PyRogue base module - Model Class
#-----------------------------------------------------------------------------
# File       : pyrogue/_Model.py
# Created    : 2016-09-29
#-----------------------------------------------------------------------------
# This file is part of the rogue software platform. It is subject to 
# the license terms in the LICENSE.txt file found in the top-level directory 
# of this distribution and at: 
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html. 
# No part of the rogue software platform, including this file, may be 
# copied, modified, propagated, or distributed except according to the terms 
# contained in the LICENSE.txt file.
#-----------------------------------------------------------------------------
import pyrogue as pr

def wordCount(bits, wordSize):
    ret = bits // wordSize
    if (bits % wordSize != 0 or bits == 0):
        ret += 1
    return ret

def byteCount(bits):
    return wordCount(bits, 8)

# class ModelMeta(type):
#     def __init__(cls, *args, **kwargs):
#         super().__init__(*args, **kwargs)
#         cls.cache = {}

#     def __call__(cls, *args, **kwargs):
#         key = str(args) + str(kwargs)
#         if key not in cls.cache:
#             inst = super().__call__(*args, **kwargs)
#             cls.cache[key] = inst
#         return cls.cache[key]

# # Python magic so that only one instance of each Model 
# # with a specific set of args is ever created
# class Model(metaclass=ModelMeta):
#     pass

class UInt(object):
    """Converts Unsigned Integer to and from bytearray"""
#     def __init__(self, numBits=1, signed=False, endianness='little'):
#         self.numBits = numBits
#         self.numBytes = byteCount(numBits)
#         self.defaultdisp = '{:x}'
#         self.signed = signed
#         self.endianness = endianness

#     def clone(self, numBits):
#         return IntModel(numBits, self.signed, self.endianness)
    defaultdisp = '{:x}'

    @staticmethod
    def toBlock(value, bitSize):
        return value.to_bytes(byteCount(bitSize), 'little', signed=False)

    @staticmethod
    def fromBlock(ba):
        return int.from_bytes(ba, 'little', signed=False)

    @staticmethod
    def fromString(string):
        i = int(string, 0)

class Int(object):

    defaultdisp = '{:x}'    

    @staticmethod
    def toBlock(value, bitSize):
        return value.to_bytes(byteCount(bitSize), 'little', signed=True)

    @staticmethod
    def fromBlock(ba):
        return int.from_bytes(ba, 'little', signed=True)

    @staticmethod
    def fromString(string):
        i = int(string, 0)
        # perform twos complement if necessary
        if i>0 and ((i >> self.numBits) & 0x1 == 1):
            i = i - (1 << self.numBits)
        return i            

class Bool(object):
    
    defaultdisp = {False: 'False', True: 'True'}    

    @staticmethod
    def toBlock(value, bitSize):
        return value.to_bytes(1, 'little', signed=False)

    @staticmethod
    def fromBlock(ba):
        return bool(int.from_bytes(ba, 'little', signed=False))

    @staticmethod
    def fromString(string):
        return str.lower(string) == "true"
        
class String(object):

    encoding = 'utf-8'
    defaultdisp = '{}'

    @staticmethod
    def toBlock(value, bitSize):
        ba = bytearray(value, String.encoding)
        ba.extend(bytearray(1))
        return ba

    @staticmethod
    def fromBlock(ba):
        s = ba.rstrip(bytearray(1))
        return s.decode(String.encoding)

    @staticmethod
    def fromString(string):
        return string

class Float(object):
    """Converter for 32-bit float"""

    defaultdisp = '{:f}'
#    endianness='little'
#    fstring = 'f' # use '!f' for big endian

    @staticmethod
    def toBlock(value, bitSize):
        if bitSize == 32:
            fstring = 'f'
        elif bitsize == 64:
            fstring = 'd'
        return bytearray(struct.pack(fstring, value))

    @staticmethod
    def fromBlock(ba):
        if len(ba) == 4:
            return struct.unpack('f', ba)
        elif len(ba) == 8:
            return struct.unpack('d', ba)

        # Need better error handling
        return struct.unpack('d', ba)        

    @staticmethod
    def fromString(string):
        return float(string)


