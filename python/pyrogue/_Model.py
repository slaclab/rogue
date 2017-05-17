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
import pyrogue

class ModelMeta(type):
    def __init__(cls, *args, **kwargs):
        super().__init__(*args, **kwargs)
        cls.cache = {}

    def __call__(cls, *args, **kwargs):
        key = str(args) + str(kwargs)
        if key not in cls.cache:
            inst = super().__call__(*args, **kwargs)
            cls.cache[key] = inst
        return cls.cache[key]

# RTH: What is the purpose of this?
class Model(metaclass=ModelMeta):
    pass

class IntModel(Model):
    """Variable holding an unsigned integer"""
    def __init__(self, signed=False, endianness='little'):
        self.defaultdisp = '{:x}'
        self.signed = signed
        self.endianness = endianness

    def _toBlock(self, value):
        return value.to_bytes(numBytes(value.bit_length()), self.endianness, signed=self.signed)

    def _fromBlock(self, ba):
        return int.from_bytes(ba, self.endianness, signed=self.signed)


class BoolModel(IntModel):

    def __init__(self):
        super().__init__(self)
        self.defaultdisp = {False: 'False', True: 'True'}

    def _toBlock(self, value):
        return value.to_bytes(1, 'little', signed=False)

    def _fromBlock(self, ba):
        return bool(IntModel._fromBlock(self, ba))
        
class StringModel(Model):
    """Variable holding a string"""
    def __init__(self, encoding='utf-8', **kwargs):
        super().__init__(**kwargs)
        self.encoding = encoding
        self.defaultdisp = '{}'

    def _toBlock(self, value):
        ba = bytearray(value, self.encoding)
        ba.extend(bytearray(1))
        return ba

    def _fromBlock(self, ba):
        s = ba.rstrip(bytearray(1))
        return s.decode(self.encoding)

class FloatModel(Model):
    def __init__(self, endianness='little'):
        super().__init__(self)
        self.defaultdisp = '{:f}'
        if endianness == 'little':
            self.format = 'f'
        if endianness == 'big':
            self.format = '!f'

    def _toBlock(self, value):
        return bytearray(struct.pack(self.format, value))

    def _fromBlock(self, ba):
        return struct.unpack(self.format, ba)

class DoubleModel(FloatModel):
    def __init__(self, endianness='little'):
        super().__init__(self, endianness)
        if endianness == 'little':
            self.format = 'd'
        if endianness == 'big':
            self.format = '!d'

