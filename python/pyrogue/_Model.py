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
import Pyro4

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
class Model(object):

    @staticmethod
    def getMask(bitSize):
        # For now all models are little endian so we can get away with this
        i = (2**bitSize-1)
        return i.to_bytes(byteCount(bitSize), 'little', signed=False)

    @classmethod
    def mask(cls, ba, bitSize):
        #m = cls.getMask(bitSize)
        #for i in range(len(ba)):
            #ba[i] = ba[i] & m[i]
        return ba

@Pyro4.expose
class UInt(Model):
    """Converts Unsigned Integer to and from bytearray"""
#     def __init__(self, numBits=1, signed=False, endianness='little'):
#         self.numBits = numBits
#         self.numBytes = byteCount(numBits)
#         self.defaultdisp = '{:x}'
#         self.signed = signed
#         self.endianness = endianness

#     def clone(self, numBits):
#         return IntModel(numBits, self.signed, self.endianness)
    defaultdisp = '{:#x}'
    pytype = int

    @staticmethod
    def check(value,bitSize):
        return (type(value) == UInt.pytype and bitSize >= value.bit_length())

    @classmethod
    def toBytes(cls, value, bitSize):
        return value.to_bytes(byteCount(bitSize), 'little', signed=False)

    @classmethod
    def fromBytes(cls, ba, bitSize):
        return int.from_bytes(ba, 'little', signed=False)


    @staticmethod
    def fromString(string, bitSize):
        return int(string, 0)


    @classmethod
    def name(cls, bitSize):
        return '{}{}'.format(cls.__name__, bitSize)


@Pyro4.expose
class Int(Model):

    defaultdisp = '{:d}'
    pytype = int

    @staticmethod
    def check(value,bitSize):
        return (type(value) == Int.pytype and bitSize >= value.bit_length())

    @classmethod
    def toBytes(cls, value, bitSize):
        if (value < 0) and (bitSize < (byteCount(bitSize) * 8)):
            newValue = value & (2**(bitSize)-1) # Strip upper bits
            ba = newValue.to_bytes(byteCount(bitSize), 'little', signed=False)
        else:
            ba = value.to_bytes(byteCount(bitSize), 'little', signed=True)

        return ba

    @classmethod
    def fromBytes(cls,ba,bitSize):
        if (bitSize < (byteCount(bitSize)*8)):
            value = int.from_bytes(ba, 'little', signed=False)

            if value >= 2**(bitSize-1):
                value -= 2**bitSize

        else:
            value = int.from_bytes(ba, 'little', signed=True)

        return value

    @staticmethod
    def fromString(string, bitSize):
        i = int(string, 0)
        # perform twos complement if necessary
        if i>0 and ((i >> bitSize) & 0x1 == 1):
            i = i - (1 << bitSize)
        return i

    @classmethod
    def name(cls, bitSize):
        return '{}{}'.format(cls.__name__, bitSize)

@Pyro4.expose
class Bool(Model):
    
    defaultdisp = {False: 'False', True: 'True'}
    pytype = bool

    @staticmethod
    def check(value,bitSize):
        return (type(value) == Bool.pytype and bitSize == 1)

    @classmethod
    def toBytes(cls, value, bitSize):
        return value.to_bytes(1, 'little', signed=False)

    @classmethod
    def fromBytes(cls, ba, bitSize):
        return bool(int.from_bytes(ba, 'little', signed=False))

    @staticmethod
    def fromString(string, bitSize):
        return str.lower(string) == "true"

    @classmethod
    def name(cls, bitSize):
        return '{}'.format(cls.__name__)
    
        
@Pyro4.expose
class String(Model):

    encoding = 'utf-8'
    defaultdisp = '{}'
    pytype = str

    @staticmethod
    def check(value,bitSize):
        return (type(val) == String.pytype and bitSize >= (len(value) * 8))

    @classmethod
    def toBytes(cls, value, bitSize):
        ba = bytearray(value, String.encoding)
        ba.extend(bytearray(1))
        return ba

    @classmethod
    def fromBytes(cls, ba, bitSize):
        s = ba.rstrip(bytearray(1))
        return s.decode(String.encoding)

    @staticmethod
    def fromString(string, bitSize):
        return string

    @classmethod
    def name(cls, bitSize):
        return '{}'.format(cls.__name__)


@Pyro4.expose
class Float(Model):
    """Converter for 32-bit float"""

    defaultdisp = '{:f}'
    pytype = float
#    endianness='little'
#    fstring = 'f' # use '!f' for big endian

    @staticmethod
    def check(value,bitSize):
        return (type(val) == Float.pytype and (bitSize == 32 or bitSize == 64))

    @classmethod
    def toBytes(cls, value, bitSize):
        if bitSize == 32:
            fstring = 'f'
        elif bitsize == 64:
            fstring = 'd'
        return bytearray(struct.pack(fstring, value))

    @classmethod
    def fromBytes(cls, ba, bitSize):
        if len(ba) == 4:
            return struct.unpack('f', ba)
        elif len(ba) == 8:
            return struct.unpack('d', ba)

        # Need better error handling
        return struct.unpack('d', ba)        

    @staticmethod
    def fromString(string, bitSize):
        return float(string)

    @classmethod
    def name(cls, bitSize):
        return '{}{}'.format(cls.__name__, bitSize)
