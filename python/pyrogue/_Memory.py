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
            values = [self._base.fromString(i) for i in valueStr.split(',')]
            size = len(values) * self._stride
            blockSize = self._reqMaxAccess()
            for i in range(offset, offset+size, blockSize):
                print(f'Making MemoryBlock for {self.path} with offset {i}')
                block = pr.MemoryBlock(name=f'{self.name}{i}', mode='RW', device=self, offset=i)
                block.timeout = 10
                self._blocks.append(block)
                block.set(values[offset-i:min(len(values), offset-i+blockSize)])
            

    def checkBlocks(self, recurse=True, variable=None):
        print(f'Checking blocks in {self.path}, blocks: {self._blocks}')
        pr.Device.checkBlocks(self, recurse=recurse, variable=variable)

        self._blocks = [b for b in self._blocks if b._verifyWr is False]
        print(f'Checking blocks done {self.path}, blocks: {self._blocks}')        

    def readBlocks(self, recurse=True, variable=None):
        pass

