#-----------------------------------------------------------------------------
# Title      : PyRogue base module - Model Class
#-----------------------------------------------------------------------------
# This file is part of the rogue software platform. It is subject to
# the license terms in the LICENSE.txt file found in the top-level directory
# of this distribution and at:
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
# No part of the rogue software platform, including this file, may be
# copied, modified, propagated, or distributed except according to the terms
# contained in the LICENSE.txt file.
#-----------------------------------------------------------------------------

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
    """
    Class which describes how a data type is represented and accessed
    using the Rogue Variables and Blocks

    Parameters
    ----------
    bitSize : int
        Number of bits being represented

    binPoint : int
        Huh?

    Attributes
    ----------
    name: str
        String representation of the Model type

    fstring: str
        Not sure what this is, Where is it used?

    encoding: str
        Encoding type for converting between string and byte arrays. i.e. UTF-8

    pytype: int
        Python type class.

    defaultdisp: str
        Default display formatting string. May be overriden by the Variable disp parameter.

    signed: bool
        Flag indicating if value is signed. Default=False

    endianness: str
        Endianness indicator. 'little' or 'big'. Default='little'

    bitReverse: bool
        Bit reversal flag.

    modelId: int
        Block processing ID. See :ref:`interfaces_memory_constants_ptype`

    isBigEndian: bool
        True if endianness = 'big'

    """

    fstring     = None
    encoding    = None
    pytype      = None
    defaultdisp = '{}'
    signed      = False
    endianness  = 'little'
    bitReverse  = False
    modelId     = rim.PyFunc

    def __init__(self, bitSize, binPoint=0):
        self.binPoint = binPoint
        self.bitSize  = bitSize
        self.name     = self.__class__.__name__

    @property
    def isBigEndian(self):
        return self.endianness == 'big'

    def toBytes(self, value):
        """
        Convert the python value to byte array.

        Parameters
        ----------
        value: obj
            Python value to convert

        Returns
        -------
        bytearray : Byte array representation of value
        """
        return None

    # Called by raw read/write and when bitsize > 64
    def fromBytes(self, ba):
        """
        Convert the python value to byte array.

        Parameters
        ----------
        ba: bytearray
            Byte array to extract value from

        Returns
        -------
        obj : Converted python value
        """
        return None

    def fromString(self, string):
        """
        Convert the string to a python value.

        Parameters
        ----------
        string: str
            String representation of the value

        Returns
        -------
        obj : Converted python value
        """
        return None

    def minValue(self):
        """
        Return the minimum value for the Model type

        Returns
        -------
        obj: Minimum value
        """
        return None

    def maxValue(self):
        """
        Return the maximum value for the Model type

        Returns
        -------
        obj: Maximum value
        """
        return None


class UInt(Model):
    """
    Model class for unsigned integers

    Parameters
    ----------
    bitSize : int
        Number of bits being represented
    """

    pytype      = int
    defaultdisp = '{:#x}'
    modelId     = rim.UInt

    def __init__(self, bitSize):
        super().__init__(bitSize)
        self.name = f'{self.__class__.__name__}{self.bitSize}'

    # Called by raw read/write and when bitsize > 64
    def toBytes(self, value):
        return value.to_bytes(byteCount(self.bitSize), self.endianness, signed=self.signed)

    # Called by raw read/write and when bitsize > 64
    def fromBytes(self, ba):
        return int.from_bytes(ba, self.endianness, signed=self.signed)

    def fromString(self, string):
        return int(string, 0)

    def minValue(self):
        return 0

    def maxValue(self):
        return (2**self.bitSize)-1


class UIntReversed(UInt):
    """
    Model class for unsigned integers, stored in reverse bit order
    """

    modelId   = rim.PyFunc # Not yet supported
    bitReverse = True

    def toBytes(self, value):
        valueReverse = reverseBits(value, self.bitSize)
        return valueReverse.to_bytes(byteCount(self.bitSize), self.endianness, signed=self.signed)

    def fromBytes(self, ba):
        valueReverse = int.from_bytes(ba, self.endianness, signed=self.signed)
        return reverseBits(valueReverse, self.bitSize)


class Int(UInt):
    """
    Model class for integers
    """

    # Override these and inherit everything else from UInt
    defaultdisp = '{:d}'
    signed      = True
    modelId     = rim.Int

    # Called by raw read/write and when bitsize > 64
    def toBytes(self, value):
        if (value < 0) and (self.bitSize < (byteCount(self.bitSize) * 8)):
            newValue = value & (2**(self.bitSize)-1) # Strip upper bits
            ba = newValue.to_bytes(byteCount(self.bitSize), self.endianness, signed=False)
        else:
            ba = value.to_bytes(byteCount(self.bitSize), self.endianness, signed=True)

        return ba

    # Called by raw read/write and when bitsize > 64
    def fromBytes(self,ba):
        if (self.bitSize < (byteCount(self.bitSize)*8)):
            value = int.from_bytes(ba, self.endianness, signed=False)

            if value >= 2**(self.bitSize-1):
                value -= 2**self.bitSize

        else:
            value = int.from_bytes(ba, self.endianness, signed=True)

        return

    def fromString(self, string):
        i = int(string, 0)
        # perform twos complement if necessary
        if i>0 and ((i >> self.bitSize) & 0x1 == 1):
            i = i - (1 << self.bitSize)
        return i

    def minValue(self):
        return -1 * ((2**(self.bitSize-1))-1)

    def maxValue(self):
        return (2**(self.bitSize-1))-1


class UIntBE(UInt):
    """
    Model class for big endian unsigned integers
    """

    endianness = 'big'


class IntBE(Int):
    """
    Model class for big endian integers
    """

    endianness = 'big'


class Bool(Model):
    """
    Model class for booleans

    Parameters
    ----------
    bitSize : int
        Number of bits being represented
    """

    pytype      = bool
    defaultdisp = {False: 'False', True: 'True'}
    modelId     = rim.Bool

    def __init__(self, bitSize):
        assert bitSize == 1, f"The bitSize param of Model {self.__class__.__name__} must be 1"
        super().__init__(bitSize)

    def fromString(self, string):
        return str.lower(string) == "true"

    def minValue(self):
        return 0

    def maxValue(self):
        return 1


class String(Model):
    """
    Model class for strings

    Parameters
    ----------
    bitSize : int
        Number of bits being represented
    """

    encoding    = 'utf-8'
    defaultdisp = '{}'
    pytype      = str
    modelId     = rim.String

    def __init__(self, bitSize):
        super().__init__(bitSize)
        self.name = f'{self.__class__.__name__}({self.bitSize//8})'

    def fromString(self, string):
        return string


class Float(Model):
    """
    Model class for 32-bit floats

    Parameters
    ----------
    bitSize : int
        Number of bits being represented, must be 32
    """

    defaultdisp = '{:f}'
    pytype      = float
    fstring     = 'f'
    modelId     = rim.Float

    def __init__(self, bitSize):
        assert bitSize == 32, f"The bitSize param of Model {self.__class__.__name__} must be 32"
        super().__init__(bitSize)
        self.name = f'{self.__class__.__name__}{self.bitSize}'

    def fromString(self, string):
        return float(string)

    def minValue(self):
        return -3.4e38

    def maxValue(self):
        return 3.4e38


class Double(Float):
    """
    Model class for 64-bit floats

    Parameters
    ----------
    bitSize : int
        Number of bits being represented, must be 64
    """

    fstring = 'd'
    modelId   = rim.Double

    def __init__(self, bitSize):
        assert bitSize == 64, f"The bitSize param of Model {self.__class__.__name__} must be 64"
        super().__init__(bitSize)
        self.name = f'{self.__class__.__name__}{self.bitSize}'

    def minValue(self):
        return -1.80e308

    def maxValue(self):
        return 1.80e308


class FloatBE(Float):
    """
    Model class for 32-bit floats stored as big endian
    """

    endianness = 'big'
    fstring = '!f'


class DoubleBE(Double):
    """
    Model class for 64-bit floats stored as big endian
    """

    endianness = 'big'
    fstring = '!d'


class Fixed(Model):
    """
    Model class for fixed point signed integers

    Parameters
    ----------
    bitSize : int
        Number of bits being represented

    binPoint : int
        Huh?
    """

    pytype = float
    signed = True
    modelId   = rim.Fixed

    def __init__(self, bitSize, binPoint):
        super().__init__(bitSize,binPoint)

        self.name = f'Fixed_{self.sign}_{self.bitSize}_{self.binPoint}'
