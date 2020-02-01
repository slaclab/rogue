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
import struct
import math

import rogue.interfaces.memory as rim

def wordCount(bits, wordSize):
    ret = bits // wordSize
    if (bits % wordSize != 0 or bits == 0):
        ret += 1
    return ret

def byteCount(bits):
    return wordCount(bits, 8)

def reverseBits(value, bitSize):
    result = 0
    for i in range(bitSize):
        result <<= 1
        result |= value & 1
        value >>= 1
    return result

def twosComplement(value, bitSize):
    """compute the 2's complement of int value"""
    if (value & (1 << (bitSize - 1))) != 0: # if sign bit is set e.g., 8bit: 128-255
        value = value - (1 << bitSize)      # compute negative value
    return value                            # return positive value as is   

class ModelMeta(type):
    def __init__(cls, *args, **kwargs):
        super().__init__(*args, **kwargs)
        cls.subclasses = {}
 
    def __call__(cls, *args, **kwargs):
        key = cls.__name__ + str(args) + str(kwargs)

        if key not in cls.subclasses:
            #print(f'Key: {key}')
            inst = super().__call__(*args, **kwargs)
            cls.subclasses[key] = inst
        return cls.subclasses[key]


class Model(object, metaclass=ModelMeta):
    fstring     = None
    encoding    = None
    pytype      = None
    defaultdisp = '{}'    
    reverseBits = False
    signed      = False
    endianness  = 'little'
    blockFunc   = rim.PyFunc

    def __init__(self, bitSize, binPoint=0):
        self.binPoint = binPoint
        self.bitSize  = bitSize
        self.name     = self.__class__.__name__

    @property
    def isBigEndian(self):
        return self.endianness == 'big'

class UInt(Model):
    pytype      = int
    defaultdisp = '{:#x}'
    blockFunc   = rim.UInt

    def __init__(self, bitSize):
        super().__init__(bitSize)
        self.name = f'{self.__class__.__name__}{self.bitSize}'        

    def toBytes(self, value):
        if type(value) != self.pytype or self.bitSize < value.bit_length():
            raise Exception("Base type mismatch!")

        return value.to_bytes(byteCount(self.bitSize), self.endianness, signed=self.signed)

    def fromBytes(self, ba):
        return int.from_bytes(ba, self.endianness, signed=self.signed)

    def fromString(self, string):
        return int(string, 0)


class UIntReversed(UInt):
    """Converts Unsigned Integer to and from bytearray with reserved bit ordering"""
    reverseBits = True

    def toBytes(self, value):
        valueReverse = reverseBits(value, self.bitSize)
        return super().toBytes(valueReverse)

    def fromBytes(cls, ba):
        valueReverse = super().fromBytes(ba)
        return reverseBits(valueReverse, self.bitSize)

class Int(UInt):

    # Override these and inherit everything else from UInt
    defaultdisp = '{:d}'
    signed      = True

    def toBytes(self, value):
        if type(value) != self.pytype or self.bitSize < value.bit_length():
            raise Exception("Base type mismatch!")

        if (value < 0) and (self.bitSize < (byteCount(self.bitSize) * 8)):
            newValue = value & (2**(self.bitSize)-1) # Strip upper bits
            ba = newValue.to_bytes(byteCount(self.bitSize), self.endianness, signed=False)
        else:
            ba = value.to_bytes(byteCount(self.bitSize), self.endianness, signed=True)

        return ba

    def fromBytes(self,ba):
        if (self.bitSize < (byteCount(self.bitSize)*8)):
            value = int.from_bytes(ba, self.endianness, signed=False)

            if value >= 2**(self.bitSize-1):
                value -= 2**self.bitSize

        else:
            value = int.from_bytes(ba, self.endianness, signed=True)

        return value

    def fromString(self, string):
        i = int(string, 0)
        # perform twos complement if necessary
        if i>0 and ((i >> self.bitSize) & 0x1 == 1):
            i = i - (1 << self.bitSize)
        return i

class UIntBE(UInt):
    endianness = 'big'

class IntBE(Int):
    endianness = 'big'

class Bool(Model):
    pytype      = bool
    defaultdisp = {False: 'False', True: 'True'}

    def __init__(self, bitSize):
        super().__init__(bitSize)

    def toBytes(self, value):
        if type(value) != self.pytype:
            raise Exception("Base type error!")

        return value.to_bytes(1, 'little', signed=False)

    def fromBytes(self, ba):
        return bool(int.from_bytes(ba, 'little', signed=False))

    def fromString(self, string):
        return str.lower(string) == "true"

    
class String(Model):
    encoding    = 'utf-8'
    defaultdisp = '{}'
    pytype      = str
    blockFunc   = rim.String

    def __init__(self, bitSize):
        super().__init__(bitSize)
        self.name = f'{self.__class__.__name__}[{self.bitSize/8}]'      

    def toBytes(self, value):
        if type(val) != self.pytype or self.bitSize < (len(value) * 8):
            raise Exception("Base type mismatch!")

        ba = bytearray(value, self.encoding)
        ba.extend(bytearray(1))
        return ba

    def fromBytes(self, ba):
        s = ba.rstrip(bytearray(1))
        return s.decode(self.encoding)

    def fromString(self, string):
        return string


class Float(Model):
    """Converter for 32-bit float"""

    defaultdisp = '{:f}'
    pytype      = float
    fstring     = 'f'

    def __init__(self, bitSize):
        assert bitSize == 32, f"The bitSize param of Model {self.__class__.__name__} must be 32"
        super().__init__(bitSize)
        self.name = f'{self.__class__.__name__}{self.bitSize}'

    def toBytes(self, value):
        if type(value) != self.pytype:
            raise Exception("Base type error!")

        return bytearray(struct.pack(self.fstring, value))

    def fromBytes(self, ba):
        return struct.unpack(self.fstring, ba)

    def fromString(self, string):
        return float(string)


class Double(Float):
    fstring = 'd'

    def __init__(self, bitSize):
        assert bitSize == 64, f"The bitSize param of Model {self.__class__.__name__} must be 64"
        super().__init__(bitSize)
        self.name = f'{self.__class__.__name__}{self.bitSize}'

class FloatBE(Float):
    fstring = '!f'

class DoubleBE(Double):
    fstring = '!d'

class Fixed(Model):
    pytype = float
    signed = True

    def __init__(self, bitSize, binPoint):
        super().__init__(bitSize,binPoint)

        # Pre-compute max and min allowable values
        if signed:
            self.maxValue = math.pow(2, (bitSize-binPoint))/2-1
            self.minValue = -1.0 * self.maxValue + 1
            sign = 'S'
        else:
            self.maxValue = math.pow(2,(bitSize-binPoint))-1
            self.minValue = 0.0
            sign = 'U'
            
        self.name = f'Fixed_{self.sign}_{self.bitSize}_{self.binPoint}'

    def toBytes(self, value):
        if type(value) != self.pytype or value > self.maxValue or value < self.minValue:
            raise Exception("Base type error!")

        i = int(round(value * math.pow(2, self.binPoint)))
        return i.to_bytes(byteCount(self.bitSize), self.endianness, signed=self.signed)

    def fromBytes(self, ba):
        i = int.from_bytes(ba, self.endianness, signed=self.signed)
        return i * math.pow(2, -1*self.binPoint)

