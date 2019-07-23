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

class ModelMeta(type):
    def __init__(cls, *args, **kwargs):
        super().__init__(*args, **kwargs)
        cls.subclasses = {}

    def __call__(cls, *args, **kwargs):
        key = cls.__name__ + str(args) + str(kwargs)

        if key not in cls.subclasses:
            print(f'Key: {key}')
            inst = super().__call__(*args, **kwargs)
            cls.subclasses[key] = inst
        return cls.subclasses[key]


class Model(object, metaclass=ModelMeta):
    
    pytype = None
    defaultdisp = '{}'    

    def __init__(self, bitSize):
        self.bitSize = bitSize
        self.name = self.__class__.__name__        
        
    def check(self, value):
        return type(value) == self.pytype


class UInt(Model):
    
    defaultdisp = '{:#x}'
    pytype = int
    signed = False
    endianness = 'little'

    def __init__(self, bitSize):
        super().__init__(bitSize)
        self.name = f'{self.__class__.__name__}{self.bitSize}'        
    
    def check(self, value):
        return (type(value) == self.pytype and self.bitSize >= value.bit_length())

    def toBytes(self, value):
        return value.to_bytes(byteCount(self.bitSize), self.endianness, signed=self.signed)

    def fromBytes(self, ba):
        return int.from_bytes(ba, self.endianness, signed=self.signed)

    def fromString(self, string):
        return int(string, 0)


class UIntReversed(UInt):
    """Converts Unsigned Integer to and from bytearray with reserved bit ordering"""

    def toBytes(self, value):
        valueReverse = reverseBits(value, self.bitSize)
        return super().toBytes(valueReverse)

    def fromBytes(cls, ba):
        valueReverse = super().fromBytes(ba)
        return reverseBits(valueReverse, self.bitSize)

class Int(UInt):

    # Override these and inherit everything else from UInt
    defaultdisp = '{:d}'
    signed = True

    def toBytes(self, value):
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
    
    defaultdisp = {False: 'False', True: 'True'}
    pytype = bool

    def __init__(self, bitSize):
        super().__init__(bitSize)

    def toBytes(self, value):
        return value.to_bytes(1, 'little', signed=False)

    def fromBytes(self, ba):
        return bool(int.from_bytes(ba, 'little', signed=False))

    def fromString(self, string):
        return str.lower(string) == "true"
    
        
class String(Model):

    encoding = 'utf-8'
    defaultdisp = '{}'
    pytype = str

    def __init__(self, bitSize):
        super().__init__(bitSize)
        self.name = f'{self.__class__.__name__}[{self.bitSize/8}]'      

    def check(self, value):
        return (type(val) == self.pytype and self.bitSize >= (len(value) * 8))

    def toBytes(self, value):
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
    pytype = float
    fstring = 'f'
    bitSize = 32

    def __init__(self, bitSize):
        assert bitSize == self.__class__.bitSize, f"The bitSize param of Model {self.__class__.__name__} must be {self.__class__.bitSize}"
        self.name = f'{self.__class__.__name__}{self.bitSize}'

    def toBytes(self, value):
        return bytearray(struct.pack(self.fstring, value))

    def fromBytes(self, ba):
        return struct.unpack(self.fstring, ba)

    def fromString(self, string):
        return float(string)



class Double(Float):
    fstring = 'd'
    bitSize = 64

class FloatBE(Float):
    fstring = '!f'

class DoubleBE(Double):
    fstring = '!d'
                
class Fixed(Model):

    pytype = float

    def __init__(self, bitSize, binPoint, signed=False, endianness='little'):
        self.bitSize = bitSize
        self.binPoint = binPoint
        self.signed = signed
        self.endianness = endianness

        # Precompute max and min allowable values
        if signed:
            self.maxValue = math.pow(2, (bitSize-binPoint))/2-1
            self.minValue = -1.0 * self.maxValue + 1
            sign = 'S'
        else:
            self.maxValue = math.pow(2,(bitSize-binPoint))-1
            self.minValue = 0.0
            sign = 'U'
            
        self.name = f'Fixed_{self.sign}_{self.bitSize}_{self.binPoint}'


    def check(self, value):
        return value <= self.maxValue and value >= self.minValue

    def toBytes(self, value):
        i = int(round(value * math.pow(2, self.binPoint)))
        return i.to_bytes(byteCount(self.bitSize), self.endianness, signed=self.signed)

    def fromBytes(self, ba):
        i = int.from_bytes(ba, self.endianness, signed=self.signed)
        return i * math.pow(2, -1*self.binPoint)

