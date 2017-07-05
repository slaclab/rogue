import pyrogue as pr

class PseudoVariable(object):
    def __init__(self, device, offset=0):
        self.device = device
        self.offset = offset

class MemoryDevice(pr.Device):
    def __init__(self, base=pr.UInt, wordSize=4, stride=4, **kwargs):
        super().__init__(hidden=True, **kwargs)

        self._base = base
        self._wordSize = wordSize
        self._bitSize = wordSize*8
        self._stride = stride
        
        self.add(pr.LocalVariable(name='Verify', value=True))

    def _buildBlocks(self):
        self._blocks = [pr.RawBlock(self)]

    def _setOrExec(self, d, writeEach, modes):
        """ Spin up a number of MemoryBlocks and set() them """
        for key, value in d.items():
            values = self._base.fromString(i) for i in value.split(',')

            block = pr.MemoryBlock(self, offset=key)
            self._blocks.append(block)
            block.set(values)

            
#             blockSize = self._reqMaxAccess()
#             numBytes = len(values) * self._stride
#             numBlocks = wordCount(len(values)*self._wordSize, blockSize)


    def verifyBlocks(self, recurse=True, variable=None):
        Device.verifyBlocks(self, recurse=recurse, variable=variable)
        # After verify is done, delete the Block objects
        self._blocks = []

    def readBlocks(self, recurse=True, variable=None):
        pass
