#-----------------------------------------------------------------------------
# Company    : SLAC National Accelerator Laboratory
#-----------------------------------------------------------------------------
#  Description:
#       PyRogue base module - Model Class
#-----------------------------------------------------------------------------
# This file is part of the rogue software platform. It is subject to
# the license terms in the LICENSE.txt file found in the top-level directory
# of this distribution and at:
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
# No part of the rogue software platform, including this file, may be
# copied, modified, propagated, or distributed except according to the terms
# contained in the LICENSE.txt file.
#-----------------------------------------------------------------------------

from __future__ import annotations

import struct
from typing import Any

import numpy as np
import rogue.interfaces.memory as rim

def wordCount(bits: int, wordSize: int) -> int:
    """Return the number of words needed to represent a bit width.

    Parameters
    ----------
    bits : int
        Number of bits to represent.
    wordSize : int
        Word size in bits.

    Returns
    -------
    int
        Number of words required.
    """
    ret = bits // wordSize
    if (bits % wordSize != 0 or bits == 0):
        ret += 1
    return ret


def byteCount(bits: int) -> int:
    """Return the number of bytes needed to represent a bit width.
    Equivalent to ``wordCount(bits, 8)``.

    Parameters
    ----------
    bits : int
        Number of bits to represent.

    Returns
    -------
    int
        Number of bytes required.
    """
    return wordCount(bits, 8)


def reverseBits(value: int, bitSize: int) -> int:
    """Return the bit-reversed value of an integer.
    For example, if ``value = 0b1010`` and ``bitSize = 4``, then the function will return ``0b0101``.

    Parameters
    ----------
    value : int
        Value to reverse.
    bitSize : int
        Number of bits to reverse.

    Returns
    -------
    int
        Bit-reversed value.
    """
    result = 0
    for i in range(bitSize):
        result <<= 1
        result |= value & 1
        value >>= 1
    return result


def twosComplement(value: int, bitSize: int) -> int:
    """Compute the two's complement of an integer value.
    For example, if ``value = 0b1010`` and ``bitSize = 4``, then the function will return ``0b0110``.

    Parameters
    ----------
    value : int
        Input value.
    bitSize : int
        Bit width of the value.

    Returns
    -------
    int
        Two's complement value.
    """
    if (value & (1 << (bitSize - 1))) != 0: # if sign bit is set e.g., 8bit: 128-255
        value = value - (1 << bitSize)      # compute negative value
    return value                            # return positive value as is


class ModelMeta(type):
    """Metaclass for the Model class.
    This metaclass is used to create a dictionary of subclasses of the Model class.
    """
    def __init__(cls, *args: Any, **kwargs: Any) -> None:
        """Initialize metaclass state for model-instance caching."""
        super().__init__(*args, **kwargs)
        cls.subclasses = {}

    def __call__(cls, *args: Any, **kwargs: Any) -> Any:
        """Return cached model instances for identical constructor arguments."""
        key = cls.__name__ + str(args) + str(kwargs)

        if key not in cls.subclasses:
            #print(f'Key: {key}')
            inst = super().__call__(*args, **kwargs)
            cls.subclasses[key] = inst
        return cls.subclasses[key]


class Model(object, metaclass=ModelMeta):
    """
    Extensible base class which describes how a data type is represented and accessed
    using the Rogue Variables and Blocks

    Parameters
    ----------
    bitSize : int
        Number of bits being represented.
    binPoint : int, optional (default = 0)
        Binary point position.
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

    ndType: np.dtype
        numpy type value (bool, int32, int64, uint32, uin64, float32, float64)
    """

    fstring     = None
    encoding    = None
    pytype      = None
    defaultdisp = '{}'
    signed      = False
    endianness  = 'little'
    bitReverse  = False
    modelId     = rim.PyFunc

    def __init__(self, bitSize: int, binPoint: int = 0) -> None:
        """Initialize base model metadata."""
        self.binPoint = binPoint
        self.bitSize  = bitSize
        self.name     = self.__class__.__name__
        self.ndType   = None

    @property
    def isBigEndian(self) -> bool:
        """Return True if the model is big endian."""
        return self.endianness == 'big'

    def toBytes(self, value: Any) -> Any:
        """
        Convert the python value to byte array.
        Implement this method in a subclass to define the conversion.

        Parameters
        ----------
        value : object
            Python value to convert.

        Returns
        -------


        """
        return None

    # Called by raw read/write and when bitsize > 64
    def fromBytes(self, ba: bytearray) -> Any:
        """
        Convert a byte array to a python value.
        Implement this method in a subclass to define the conversion.

        Parameters
        ----------
        ba : bytearray
            Byte array to extract value from.

        Returns
        -------
        Python value.

        """
        return None

    def fromString(self, string: str) -> Any:
        """
        Convert a string to a python value.
        Implement this method in a subclass to define the conversion.

        Parameters
        ----------
        string : str
            String representation of the value.

        Returns
        -------
        Python value.

        """
        return None

    def minValue(self) -> Any:
        """Return the minimum value for the Model type.
        Implement this method in a subclass to define the minimum value.
        """
        return None

    def maxValue(self) -> Any:
        """Return the maximum value for the Model type.
        Implement this method in a subclass to define the maximum value.
        """
        return None


class UInt(Model):
    """Model class for unsigned integers.

    Parameters
    ----------
    bitSize : int
        Number of bits being represented.
    """

    pytype      = int
    defaultdisp = '{:#x}'
    modelId     = rim.UInt

    def __init__(self, bitSize: int) -> None:
        """Initialize unsigned-integer model metadata."""
        super().__init__(bitSize)
        self.name = f'{self.__class__.__name__}{self.bitSize}'
        self.ndType = np.dtype(np.uint32) if bitSize <= 32 else np.dtype(np.uint64)

    # Called by raw read/write and when bitsize > 64
    def toBytes(self, value: int) -> bytes:
        """


        Parameters
        ----------
        value : int
            Python value to convert.


        Returns
        -------
        bytes
            Byte array representation of the value.
        """
        return value.to_bytes(byteCount(self.bitSize), self.endianness, signed=self.signed)

    # Called by raw read/write and when bitsize > 64
    def fromBytes(self, ba: bytes) -> int:
        """


        Parameters
        ----------
        ba : bytes
            Byte array to extract value from.


        Returns
        -------
        int
            Python value.
        """
        return int.from_bytes(ba, self.endianness, signed=self.signed)

    def fromString(self, string: str) -> int:
        """


        Parameters
        ----------
        string : str
            String representation of the value.


        Returns
        -------
        int
            Python value.
        """
        return int(string, 0)

    def minValue(self) -> int:
        """Return the minimum unisgned int (0). """
        return 0

    def maxValue(self) -> int:
        """Return the maximum unsigned int (2**bitSize-1). """
        return (2**self.bitSize)-1


class UIntReversed(UInt):
    """Model class for unsigned integers, stored in reverse bit order."""

    modelId    = rim.PyFunc # Not yet supported
    bitReverse = True

    def __init__(self, bitSize: int) -> None:
        """Initialize reversed-bit unsigned-integer model metadata."""
        super().__init__(bitSize)
        self.ndType = None

    def toBytes(self, value: int) -> bytes:
        """
        Convert a python int value to a byte array.

        Parameters
        ----------
        value : int
            Python int value to convert.


        Returns
        -------
        bytes
            Byte array representation of the value.
        """
        valueReverse = reverseBits(value, self.bitSize)
        return valueReverse.to_bytes(byteCount(self.bitSize), self.endianness, signed=self.signed)

    def fromBytes(self, ba: bytes) -> int:
        """
        Convert a byte array to a python int value.

        Parameters
        ----------
        ba : bytes
            Byte array to extract value from.


        Returns
        -------
        int
            Python value.
        """
        valueReverse = int.from_bytes(ba, self.endianness, signed=self.signed)
        return reverseBits(valueReverse, self.bitSize)


class Int(UInt):
    """Model class for signed integers.

    Parameters
    ----------
    bitSize : int
        Number of bits being represented.
    """

    # Override these and inherit everything else from UInt
    defaultdisp = '{:d}'
    signed      = True
    modelId     = rim.Int

    def __init__(self, bitSize: int) -> None:
        """Initialize signed-integer model metadata."""
        super().__init__(bitSize)
        self.ndType = np.dtype(np.int32) if bitSize <= 32 else np.dtype(np.int64)

    # Called by raw read/write and when bitsize > 64
    def toBytes(self, value: int) -> bytes:
        """
        Convert a python int value to a byte array.

        Parameters
        ----------
        value : int
            Python int value to convert.


        Returns
        -------
        bytes
            Byte array representation of the value.

        """
        if (value < 0) and (self.bitSize < (byteCount(self.bitSize) * 8)):
            newValue = value & (2**(self.bitSize)-1) # Strip upper bits
            ba = newValue.to_bytes(byteCount(self.bitSize), self.endianness, signed=False)
        else:
            ba = value.to_bytes(byteCount(self.bitSize), self.endianness, signed=True)

        return ba

    # Called by raw read/write and when bitsize > 64
    def fromBytes(self, ba: bytes) -> int:
        """
        Convert a byte array to a python int value.

        Parameters
        ----------
        ba : bytes
            Byte array to extract value from.

        Returns
        -------
        int
            Python value.

        """
        if (self.bitSize < (byteCount(self.bitSize)*8)):
            value = int.from_bytes(ba, self.endianness, signed=False)

            if value >= 2**(self.bitSize-1):
                value -= 2**self.bitSize

        else:
            value = int.from_bytes(ba, self.endianness, signed=True)

        return value

    def fromString(self, string: str) -> int:
        """
        Convert a string to a python int value.

        Parameters
        ----------
        string : str
            String representation of the value.

        Returns
        -------
        int
            Python value.


        """
        i = int(string, 0)
        # perform twos complement if necessary
        if i >= 2**(self.bitSize-1):
            i = i - (1 << self.bitSize)
        return i

    def minValue(self) -> int:
        """Return the minimum signed int (-2**(bitSize-1)). """
        return -1 * (2**(self.bitSize-1))

    def maxValue(self) -> int:
        """Return the maximum signed int (2**(bitSize-1)-1). """
        return (2**(self.bitSize-1))-1


class UIntBE(UInt):
    """Model class for big endian unsigned integers.
    Inherits from UInt.
    """

    endianness = 'big'


class IntBE(Int):
    """Model class for big endian integers.
    Inherits from Int.
    """

    endianness = 'big'


class Bool(Model):
    """Model class for booleans.

    Parameters
    ----------
    bitSize : int
        Number of bits being represented. Must be 1.
    """

    pytype      = bool
    defaultdisp = {False: 'False', True: 'True'}
    modelId     = rim.Bool

    def __init__(self, bitSize: int) -> None:
        """Initialize boolean model metadata."""
        assert bitSize == 1, f"The bitSize param of Model {self.__class__.__name__} must be 1"
        super().__init__(bitSize)
        self.ndType = np.dtype(bool)

    def toBytes(self, value: bool) -> bytes:
        """
        Convert a python bool value to a byte array.

        Parameters
        ----------
        value : bool
            Python bool value to convert.

        Returns
        -------
        bytes
            Byte array representation of the value.


        """
        return value.to_bytes(byteCount(self.bitSize), self.endianness, signed=self.signed)

    def fromBytes(self, ba: bytes) -> bool:
        """
        Convert a byte array to a python bool value.

        Parameters
        ----------
        ba : bytes
            Byte array to extract value from.

        Returns
        -------
        bool
            Python value.


        """
        return bool(int.from_bytes(ba, self.endianness, signed=self.signed))

    def fromString(self, string: str) -> bool:
        """Convert a string to a python bool value.

        Parameters
        ----------
        string : str
            String representation of the value.

        Returns
        -------
        bool
            Python value.
        Parameters
        ----------
        string :

        """
        return str.lower(string) == "true"

    def minValue(self) -> int:
        """Return the minimum bool (0). """
        return 0

    def maxValue(self) -> int:
        """Return the maximum bool (1). """
        return 1


class String(Model):
    """Model class for strings.

    Parameters
    ----------
    bitSize : int
        Number of bits being represented.
    """

    encoding    = 'utf-8'
    defaultdisp = '{}'
    pytype      = str
    modelId     = rim.String

    def __init__(self, bitSize: int) -> None:
        """Initialize string model metadata."""
        super().__init__(bitSize)
        self.name = f'{self.__class__.__name__}({self.bitSize//8})'


    def toBytes(self, value: str) -> bytearray:
        """
        Convert a python string value to a byte array.

        Parameters
        ----------
        value : str
            Python string value to convert.

        Returns
        -------
        bytearray
            Byte array representation of the value.
        """
        ba = bytearray(value, self.encoding)
        ba.extend(bytearray(1))
        return ba

    def fromBytes(self, ba: bytearray) -> str:
        """
        Convert a byte array to a python string value.

        Parameters
        ----------
        ba : bytearray
            Byte array to extract value from.

        Returns
        -------
        str
            Python value.
        """
        s = ba.rstrip(bytearray(1))
        return s.decode(self.encoding)

    def fromString(self, string: str) -> str:
        """
        Convert a string to a python string value.

        Parameters
        ----------
        string : str
            String representation of the value.

        Returns
        -------
        str
            Python string value.
        """
        return string


class Float(Model):
    """Model class for 32-bit floating point numbers.

    Parameters
    ----------
    bitSize : int
        Number of bits being represented. Must be 32.
    """

    defaultdisp = '{:f}'
    pytype      = float
    fstring     = 'f'
    modelId     = rim.Float

    def __init__(self, bitSize: int) -> None:
        """Initialize 32-bit float model metadata."""
        assert bitSize == 32, f"The bitSize param of Model {self.__class__.__name__} must be 32"
        super().__init__(bitSize)
        self.name = f'{self.__class__.__name__}{self.bitSize}'
        self.ndType = np.dtype(np.float32)

    def toBytes(self, value: float) -> bytearray:
        """
        Convert a python float value to a byte array.

        Parameters
        ----------
        value : float
            Python float value to convert.

        Returns
        -------
        bytearray
            Byte array representation of the value.

        """
        return bytearray(struct.pack(self.fstring, value))

    def fromBytes(self, ba: bytes) -> float:
        """
        Convert a byte array to a python float value.

        Parameters
        ----------
        ba : bytes
            Byte array to extract value from.

        Returns
        -------
        float
            Python value.

        """
        return struct.unpack(self.fstring, ba)[0]

    def fromString(self, string: str) -> float:
        """
        Convert a string to a python float value.

        Parameters
        ----------
        string : str
            String representation of the value.

        Returns
        -------
        float
            Python value.
        """
        return float(string)

    def minValue(self) -> float:
        """Return the minimum 32-bit float (-3.4e38). """
        return -3.4e38

    def maxValue(self) -> float:
        """Return the maximum 32-bit float (3.4e38). """
        return 3.4e38


class Double(Float):
    """Model class for 64-bit floats.

    Parameters
    ----------
    bitSize : int
        Number of bits being represented. Must be 64.
    """

    fstring = 'd'
    modelId = rim.Double

    def __init__(self, bitSize: int) -> None:
        """Initialize 64-bit float model metadata."""
        assert bitSize == 64, f"The bitSize param of Model {self.__class__.__name__} must be 64"
        Model.__init__(self,bitSize)
        self.name = f'{self.__class__.__name__}{self.bitSize}'
        self.ndType = np.dtype(np.float64)

    def minValue(self) -> float:
        """Return the minimum 64-bit float (-1.80e308). """
        return -1.80e308

    def maxValue(self) -> float:
        """Return the maximum 64-bit float (1.80e308). """
        return 1.80e308


class FloatBE(Float):
    """Model class for 32-bit floats stored as big endian"""

    endianness = 'big'
    fstring = '!f'


class DoubleBE(Double):
    """Model class for 64-bit floats stored as big endian"""

    endianness = 'big'
    fstring = '!d'


class Float16(Model):
    """Model class for 16-bit half-precision floating point numbers.

    Parameters
    ----------
    bitSize : int
        Number of bits being represented. Must be 16.
    """

    defaultdisp = '{:f}'
    pytype      = float
    fstring     = 'e'
    modelId     = rim.Float16

    def __init__(self, bitSize: int) -> None:
        """Initialize 16-bit float model metadata."""
        assert bitSize == 16, f"The bitSize param of Model {self.__class__.__name__} must be 16"
        super().__init__(bitSize)
        self.name = 'Float16'
        self.ndType = np.dtype(np.float16)

    def toBytes(self, value: float) -> bytearray:
        """
        Convert a python float value to a byte array.

        Parameters
        ----------
        value : float
            Python float value to convert.

        Returns
        -------
        bytearray
            Byte array representation of the value.

        """
        return bytearray(struct.pack(self.fstring, value))

    def fromBytes(self, ba: bytes) -> float:
        """
        Convert a byte array to a python float value.

        Parameters
        ----------
        ba : bytes
            Byte array to extract value from.

        Returns
        -------
        float
            Python value.

        """
        return struct.unpack(self.fstring, ba)[0]

    def fromString(self, string: str) -> float:
        """
        Convert a string to a python float value.

        Parameters
        ----------
        string : str
            String representation of the value.

        Returns
        -------
        float
            Python value.
        """
        return float(string)

    def minValue(self) -> float:
        """Return the minimum 16-bit float (-65504). """
        return -65504.0

    def maxValue(self) -> float:
        """Return the maximum 16-bit float (65504). """
        return 65504.0


class Float16BE(Float16):
    """Model class for 16-bit floats stored as big endian"""

    endianness = 'big'
    fstring = '!e'


class Float8(Model):
    """Model class for 8-bit E4M3 floating point numbers (NVIDIA FP8).

    Parameters
    ----------
    bitSize : int
        Number of bits being represented. Must be 8.

    Notes
    -----
    Format: 1 sign bit, 4 exponent bits, 3 mantissa bits (E4M3).
    Bias = 7. No infinity representation. NaN encoded as 0x7F.
    Maximum representable value is 448.0.
    Supported by NVIDIA Hopper (H100) and Blackwell GPUs.
    """

    defaultdisp = '{:f}'
    pytype      = float
    modelId     = rim.Float8

    def __init__(self, bitSize: int) -> None:
        """Initialize 8-bit E4M3 float model metadata."""
        assert bitSize == 8, f"The bitSize param of Model {self.__class__.__name__} must be 8"
        super().__init__(bitSize)
        self.name = 'Float8'
        self.ndType = np.dtype(np.float32)

    def toBytes(self, value: float) -> bytearray:
        """Convert float to 1-byte E4M3 encoding."""
        import math
        v = float(value)
        if math.isnan(v):
            return bytearray([0x7F])
        # Get float32 bit pattern
        bits = struct.unpack('I', struct.pack('f', v))[0]
        sign = (bits >> 24) & 0x80
        exp32 = (bits >> 23) & 0xFF
        mant32 = bits & 0x7FFFFF
        # Rebias exponent: float32 bias=127, E4M3 bias=7
        exp8 = exp32 - 127 + 7
        if exp32 == 0xFF:
            # float32 infinity -> clamp to max finite
            return bytearray([sign | 0x7E])
        if exp8 > 15:
            # Overflow -> clamp to max finite
            return bytearray([sign | 0x7E])
        if exp8 <= 0:
            # Subnormal or underflow
            if exp8 < -3:
                return bytearray([sign])  # flush to zero
            mant32 |= 0x800000
            shift = 1 - exp8
            mant32 >>= shift
            return bytearray([sign | ((mant32 >> 20) & 0x07)])
        return bytearray([sign | (exp8 << 3) | ((mant32 >> 20) & 0x07)])

    def fromBytes(self, ba: bytes) -> float:
        """Decode 1-byte E4M3 encoding to float."""
        f8 = ba[0]
        # Both 0x7F and 0xFF are NaN
        if (f8 & 0x7F) == 0x7F:
            return float('nan')
        sign = -1.0 if (f8 & 0x80) else 1.0
        exponent = (f8 >> 3) & 0x0F
        mantissa = f8 & 0x07
        if exponent == 0:
            if mantissa == 0:
                return 0.0 if sign > 0 else -0.0
            # Subnormal: value = sign * mantissa/8 * 2^(1-7) = sign * mantissa * 2^(-9)
            return sign * mantissa * (2.0 ** -9)
        # Normal: value = sign * (1 + mantissa/8) * 2^(exponent-7)
        return sign * (1.0 + mantissa / 8.0) * (2.0 ** (exponent - 7))

    def fromString(self, string: str) -> float:
        """Parse a string into a float value."""
        return float(string)

    def minValue(self) -> float:
        """Return the minimum representable value (-448.0)."""
        return -448.0

    def maxValue(self) -> float:
        """Return the maximum representable value (448.0)."""
        return 448.0


class Float8BE(Float8):
    """Model class for 8-bit E4M3 floats stored as big endian."""

    endianness = 'big'


class BFloat16(Model):
    """Model class for 16-bit Brain Float (BFloat16) numbers.

    Parameters
    ----------
    bitSize : int
        Number of bits being represented. Must be 16.

    Notes
    -----
    Format: 1 sign bit, 8 exponent bits, 7 mantissa bits (same exponent as float32).
    Bias = 127. Supports infinity and NaN. Maximum representable finite value
    is approximately 3.39e38 (same range as float32).
    Supported by NVIDIA Ampere (A100), Hopper (H100), and Blackwell GPUs.
    """

    defaultdisp = '{:f}'
    pytype      = float
    modelId     = rim.BFloat16

    def __init__(self, bitSize: int) -> None:
        """Initialize 16-bit BFloat16 model metadata."""
        assert bitSize == 16, f"The bitSize param of Model {self.__class__.__name__} must be 16"
        super().__init__(bitSize)
        self.name = 'BFloat16'
        self.ndType = np.dtype(np.float32)

    def toBytes(self, value: float) -> bytearray:
        """Convert float to 2-byte BFloat16 encoding.

        BFloat16 is the upper 16 bits of the float32 bit pattern.
        All special values (NaN, infinity, zero, subnormals) are preserved.
        """
        v = float(value)
        # Get float32 bit pattern as uint32, take upper 16 bits
        bits = struct.unpack('I', struct.pack('f', v))[0]
        bf16 = bits >> 16
        return bytearray(struct.pack('<H', bf16))

    def fromBytes(self, ba: bytes) -> float:
        """Decode 2-byte BFloat16 encoding to float.

        Reconstructs float32 by shifting the 16-bit pattern left by 16.
        """
        bf16 = struct.unpack('<H', ba[:2])[0]
        bits = bf16 << 16
        return struct.unpack('f', struct.pack('I', bits))[0]

    def fromString(self, string: str) -> float:
        """Parse a string into a float value."""
        return float(string)

    def minValue(self) -> float:
        """Return the minimum representable finite BFloat16 value (~-3.39e38)."""
        return -3.3895313892515355e+38

    def maxValue(self) -> float:
        """Return the maximum representable finite BFloat16 value (~3.39e38)."""
        return 3.3895313892515355e+38


class BFloat16BE(BFloat16):
    """Model class for BFloat16 floats stored as big endian."""

    endianness = 'big'


class TensorFloat32(Model):
    """Model class for 32-bit TensorFloat32 (NVIDIA TF32) numbers.

    Parameters
    ----------
    bitSize : int
        Number of bits being represented. Must be 32.

    Notes
    -----
    Format: 1 sign bit, 8 exponent bits, 10 mantissa bits (1s/8e/10m).
    Bias = 127. Same exponent range as float32. Stored in a 4-byte word
    with the lower 13 mantissa bits zeroed. Supports infinity and NaN.
    Maximum representable finite value is approximately 3.40e38.
    Supported by NVIDIA Ampere (A100), Hopper (H100), and Blackwell GPUs.
    """

    defaultdisp = '{:f}'
    pytype      = float
    modelId     = rim.TensorFloat32

    def __init__(self, bitSize: int) -> None:
        """Initialize 32-bit TensorFloat32 model metadata."""
        assert bitSize == 32, f"The bitSize param of Model {self.__class__.__name__} must be 32"
        super().__init__(bitSize)
        self.name = 'TensorFloat32'
        self.ndType = np.dtype(np.float32)

    def toBytes(self, value: float) -> bytearray:
        """Convert float to 4-byte TensorFloat32 encoding.

        TF32 zeros the lower 13 mantissa bits of the float32 bit pattern.
        All special values (NaN, infinity, zero, subnormals) are preserved.
        """
        v = float(value)
        bits = struct.unpack('I', struct.pack('f', v))[0]
        tf32 = bits & 0xFFFFE000
        return bytearray(struct.pack('<I', tf32))

    def fromBytes(self, ba: bytes) -> float:
        """Decode 4-byte TensorFloat32 encoding to float.

        TF32 bit pattern is a valid float32 with lower 13 mantissa bits
        zeroed. Direct reinterpretation as float32 is sufficient.
        """
        tf32 = struct.unpack('<I', ba[:4])[0]
        return struct.unpack('f', struct.pack('I', tf32))[0]

    def fromString(self, string: str) -> float:
        """Parse a string into a float value."""
        return float(string)

    def minValue(self) -> float:
        """Return the minimum representable finite TF32 value (~-3.40e38)."""
        return -3.4011621342146535e+38

    def maxValue(self) -> float:
        """Return the maximum representable finite TF32 value (~3.40e38)."""
        return 3.4011621342146535e+38


class TensorFloat32BE(TensorFloat32):
    """Model class for TensorFloat32 floats stored as big endian."""

    endianness = 'big'


class Float6(Model):
    """Model class for 6-bit E3M2 floating point numbers (NVIDIA Blackwell FP6).

    Parameters
    ----------
    bitSize : int
        Number of bits being represented. Must be 8 (stored in 1-byte word).

    Notes
    -----
    Format: 1 sign bit, 3 exponent bits, 2 mantissa bits (E3M2).
    Bias = 3. No infinity representation. No NaN representation.
    All 64 bit patterns are finite values or zero.
    Maximum representable value is 28.0.
    Stored in lower 6 bits of a uint8_t byte.
    Supported by NVIDIA Blackwell GPUs.
    """

    defaultdisp = '{:f}'
    pytype      = float
    modelId     = rim.Float6

    def __init__(self, bitSize: int) -> None:
        """Initialize 6-bit E3M2 float model metadata."""
        assert bitSize == 8, f"The bitSize param of Model {self.__class__.__name__} must be 8"
        super().__init__(bitSize)
        self.name = 'Float6'
        self.ndType = np.dtype(np.float32)

    def toBytes(self, value: float) -> bytearray:
        """Convert float to 1-byte E3M2 encoding (6 active bits in uint8).

        NaN and infinity inputs are clamped to max finite value (+/-28.0)
        since E3M2 has no NaN or infinity encodings.
        """
        import math
        v = float(value)
        if math.isnan(v) or math.isinf(v):
            # E3M2 has no NaN/Inf -- clamp to max finite
            sign = 0x20 if (math.isinf(v) and v < 0) else 0x00
            if math.isnan(v):
                sign = 0x00  # positive max for NaN
            return bytearray([sign | 0x1F])
        # Get float32 bit pattern
        bits = struct.unpack('I', struct.pack('f', v))[0]
        sign = (bits >> 26) & 0x20
        exp32 = (bits >> 23) & 0xFF
        mant32 = bits & 0x7FFFFF
        # Rebias exponent: float32 bias=127, E3M2 bias=3
        exp6 = exp32 - 127 + 3
        if exp32 == 0xFF:
            # float32 special values -- clamp to max finite
            return bytearray([sign | 0x1F])
        if exp6 > 7:
            # Overflow -- clamp to max finite
            return bytearray([sign | 0x1F])
        if exp6 <= 0:
            # Subnormal or underflow
            if exp6 < -2:
                return bytearray([sign])  # flush to zero
            mant32 |= 0x800000
            shift = 1 - exp6
            mant32 >>= shift
            return bytearray([sign | ((mant32 >> 21) & 0x03)])
        return bytearray([sign | (exp6 << 2) | ((mant32 >> 21) & 0x03)])

    def fromBytes(self, ba: bytes) -> float:
        """Decode 1-byte E3M2 encoding to float.

        All 64 bit patterns decode to finite values or zero (no NaN/Inf).
        """
        f6 = ba[0] & 0x3F  # mask to 6 bits
        sign = -1.0 if (f6 & 0x20) else 1.0
        exponent = (f6 >> 2) & 0x07
        mantissa = f6 & 0x03
        if exponent == 0:
            if mantissa == 0:
                return 0.0 if sign > 0 else -0.0
            # Subnormal: value = sign * mantissa/4 * 2^(1-3) = sign * mantissa * 2^(-4)
            return sign * mantissa * (2.0 ** -4)
        # Normal: value = sign * (1 + mantissa/4) * 2^(exponent-3)
        return sign * (1.0 + mantissa / 4.0) * (2.0 ** (exponent - 3))

    def fromString(self, string: str) -> float:
        """Parse a string into a float value."""
        return float(string)

    def minValue(self) -> float:
        """Return the minimum representable value (-28.0)."""
        return -28.0

    def maxValue(self) -> float:
        """Return the maximum representable value (28.0)."""
        return 28.0


class Float6BE(Float6):
    """Model class for 6-bit E3M2 floats stored as big endian."""

    endianness = 'big'


class Float4(Model):
    """Model class for 4-bit E2M1 floating point numbers (NVIDIA Blackwell FP4).

    Parameters
    ----------
    bitSize : int
        Number of bits being represented. Must be 8 (stored in 1-byte word).

    Notes
    -----
    Format: 1 sign bit, 2 exponent bits, 1 mantissa bit (E2M1).
    Bias = 1. No infinity representation. No NaN representation.
    All 16 bit patterns are finite values or zero.
    Only 8 distinct magnitudes: 0, 0.5, 1.0, 1.5, 2.0, 3.0, 4.0, 6.0.
    Maximum representable value is 6.0.
    Stored in lower 4 bits of a uint8_t byte.
    Supported by NVIDIA Blackwell GPUs.
    """

    defaultdisp = '{:f}'
    pytype      = float
    modelId     = rim.Float4

    def __init__(self, bitSize: int) -> None:
        """Initialize 4-bit E2M1 float model metadata."""
        assert bitSize == 8, f"The bitSize param of Model {self.__class__.__name__} must be 8"
        super().__init__(bitSize)
        self.name = 'Float4'
        self.ndType = np.dtype(np.float32)

    def toBytes(self, value: float) -> bytearray:
        """Convert float to 1-byte E2M1 encoding (4 active bits in uint8).

        NaN and infinity inputs are clamped to max finite value (+/-6.0)
        since E2M1 has no NaN or infinity encodings.
        """
        import math
        v = float(value)
        if math.isnan(v) or math.isinf(v):
            # E2M1 has no NaN/Inf -- clamp to max finite
            sign = 0x08 if (math.isinf(v) and v < 0) else 0x00
            if math.isnan(v):
                sign = 0x00  # positive max for NaN
            return bytearray([sign | 0x07])
        # Get float32 bit pattern
        bits = struct.unpack('I', struct.pack('f', v))[0]
        sign = (bits >> 28) & 0x08
        exp32 = (bits >> 23) & 0xFF
        mant32 = bits & 0x7FFFFF
        # Rebias exponent: float32 bias=127, E2M1 bias=1
        exp4 = exp32 - 127 + 1
        if exp32 == 0xFF:
            # float32 special values -- clamp to max finite
            return bytearray([sign | 0x07])
        if exp4 > 3:
            # Overflow -- clamp to max finite
            return bytearray([sign | 0x07])
        if exp4 <= 0:
            # Subnormal or underflow
            if exp4 < -1:
                return bytearray([sign])  # flush to zero
            mant32 |= 0x800000
            shift = 1 - exp4
            mant32 >>= shift
            return bytearray([sign | ((mant32 >> 22) & 0x01)])
        return bytearray([sign | (exp4 << 1) | ((mant32 >> 22) & 0x01)])

    def fromBytes(self, ba: bytes) -> float:
        """Decode 1-byte E2M1 encoding to float.

        All 16 bit patterns decode to finite values or zero (no NaN/Inf).
        """
        f4 = ba[0] & 0x0F  # mask to 4 bits
        sign = -1.0 if (f4 & 0x08) else 1.0
        exponent = (f4 >> 1) & 0x03
        mantissa = f4 & 0x01
        if exponent == 0:
            if mantissa == 0:
                return 0.0 if sign > 0 else -0.0
            # Subnormal: value = sign * mantissa * 0.5 (only one subnormal: +/-0.5)
            return sign * mantissa * 0.5
        # Normal: value = sign * (1 + mantissa/2) * 2^(exponent-1)
        return sign * (1.0 + mantissa / 2.0) * (2.0 ** (exponent - 1))

    def fromString(self, string: str) -> float:
        """Parse a string into a float value."""
        return float(string)

    def minValue(self) -> float:
        """Return the minimum representable value (-6.0)."""
        return -6.0

    def maxValue(self) -> float:
        """Return the maximum representable value (6.0)."""
        return 6.0


class Float4BE(Float4):
    """Model class for 4-bit E2M1 floats stored as big endian."""

    endianness = 'big'


class Fixed(Model):
    """
    Model class for fixed point signed integers

    Parameters
    ----------
    bitSize : int
        Specifies the total number of bits, including the binary point bit width.

    binPoint : int
        Specifies the bit location of the binary point, where bit zero is the least significant bit.
    """

    pytype  = float
    signed  = True
    modelId = rim.Fixed

    def __init__(self, bitSize: int, binPoint: int) -> None:
        """Initialize signed fixed-point model metadata."""
        super().__init__(bitSize,binPoint)
        self.name = f'Fixed_{self.bitSize}_{self.binPoint}'
        self.ndType = np.dtype(np.float64)

class UFixed(Model):
    """
    Model class for fixed point unsigned integers

    Parameters
    ----------
    bitSize : int
        Specifies the total number of bits, including the binary point bit width.

    binPoint : int
        Specifies the bit location of the binary point, where bit zero is the least significant bit.
    """

    pytype  = float
    signed  = False
    modelId = rim.Fixed

    def __init__(self, bitSize: int, binPoint: int) -> None:
        """Initialize unsigned fixed-point model metadata."""
        super().__init__(bitSize,binPoint)
        self.name = f'UFixed_{self.bitSize}_{self.binPoint}'
        self.ndType = np.dtype(np.float64)
