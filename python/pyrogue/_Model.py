import pyrogue as pr

def wordCount(bits, wordSize):
    ret = bits // wordSize
    if (bits % wordSize != 0 or bits == 0):
        ret += 1
    return ret

def byteCount(bits):
    return wordCount(bits, 8)

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

class Model(metaclass=ModelMeta):
    pass

class IntModel(Model):
    """Variable holding an unsigned integer"""
    def __init__(self, numBits=1, signed=False, endianness='little'):
        self.numBits = numBits
        self.numBytes = byteCount(numBits)
        self.defaultdisp = '{:x}'
        self.signed = signed
        self.endianness = endianness

    def _toBlock(self, value):
        return value.to_bytes(self.numBytes, self.endianness, signed=self.signed)

    def _fromBlock(self, ba):
        return int.from_bytes(ba, self.endianness, signed=self.signed)

    def _fromString(self, string):
        i = int(string, 0)
        # perform twos complement if necessary
        if self.signed and i>0 and ((i >> self.numBits) & 0x1 == 1):
            i = i - (1 << self.numBits)
        return i            

    def __str__(self):
        if self.signed is True:
            return 'Int{}'.format(self.numBits)
        else:
            return 'UInt{}'.format(self.numBits)

class BoolModel(Model):

    def __init__(self):
        self.defaultdisp = {False: 'False', True: 'True'}

    def _toBlock(self, value):
        return value.to_bytes(1, 'little', signed=False)

    def _fromBlock(self, ba):
        return bool(int.from_bytes(ba, 'little', signed=False))

    def _fromString(self, string):
        return str.lower(string) == "true"

    def __str__(self):
        return 'Bool'
        
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

    def _fromString(self, string):
        return string

    def __str__(self):
        return 'String'

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

    def _fromString(self, string):
        return float(string)

    def __str__(self):
        return 'Float32'

class DoubleModel(FloatModel):
    def __init__(self, endianness='little'):
        super().__init__(self, endianness)
        if endianness == 'little':
            self.format = 'd'
        if endianness == 'big':
            self.format = '!d'

    def __str__(self):
        return 'Float64'


