import pyrogue as pr

class MemoryDevice(pr.Device):
    def __init__(self, base=pr.UInt, wordSize=4, stride=4, verify=True, **kwargs):
        super().__init__(hidden=True, **kwargs)

        self._base = base
        self._wordSize = wordSize
        self._bitSize = wordSize*8
        self._stride = stride
        self._bitStride = stride*8
        self._verify = verify

    def _buildBlocks(self):
        pass

    def _setOrExec(self, d, writeEach, modes):
        """ Spin up a number of MemoryBlocks and set() them """

        for offset, valueStr in d.items():
            values = self._base.fromString(i) for i in valueStr.split(',')
            size = len(values) * self._stride
            blockSize = self._reqMaxAccess()
            for i in range(offset, offset+size, blockSize):
                block = pr.MemoryBlock(self, offset=i)                
                self._blocks.append(block)
                block.set(values[offset-i:min(len(values), offset-i+blockSize)])
            

    def checkBlocks(self, varUpdate=True, recurse=True, variable=None):
        Device.checkBlocks(varUpdate=varUpdate, recurse=recurse, variable=variable)

        self._blocks = [b for b in self._blocks if b._verifyWr is False]

    def readBlocks(self, recurse=True, variable=None):
        pass

    def write(self, offset, values):
        pass

    def read(self, offset, size):
        pass
