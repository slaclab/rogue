import pyrogue as pr
import rogue.interfaces.memory as rim
import threading
from collections import OrderedDict as odict


class MemoryDevice(pr.Device):
    def __init__(self, *, base=pr.UInt, wordBitSize=4, stride=4, verify=True, **kwargs):
        super().__init__(hidden=True, **kwargs)

        self._lockCnt = 0
        self._base = base
        self._wordBitSize = wordBitSize
        self._stride = stride
        self._verify = verify
        self._mask = base.blockMask(wordBitSize)

        self._setBlocks = odict()
        self._wrBlocks = odict() # parsed from yaml
        self._verBlocks = odict()
        self._wrData = odict() # byte arrays written
        self._verData = odict() # verify data wread back

    def __mask(self, ba):
        return bytearray(x&y for x,y in zip(self._mask, ba))

    def _buildBlocks(self):
        pass

    def _setOrExec(self, d, writeEach, modes):
        # Parse comma separated values at each offset (key) in d
        with self._memLock:
            self._setBlocks[0] = [i for i in range(2**14)]
            #for offset, values in d.items():
            #    self._setBlocks[offset] = [self._base.fromString(s) for s in values.split(',')]


    def writeBlocks(self, force=False, recurse=True, variable=None):
        if not self.enable.get(): return

        with self._memLock:
            self._wrBlocks = self._setBlocks
            
            for offset, values in self._setBlocks.items():
                wdata = self._rawTxnChunker(offset, values, self._base, self._stride, self._wordBitSize, rim.Write)
                if self._verify:
                    self._wrData[offset] = wdata

            # clear out wrBlocks when done
            self._setBlocks = odict()
        

    def verifyBlocks(self, recurse=True, variable=None):
        if not self.enable.get(): return

        with self._memLock:
            for offset, ba in self._wrData.items():
                self._verData[offset] = bytearray(len(ba))
                self._rawTxnChunker(offset, self._verData[offset], rim.Verify)

            self._wrData = odict()
            self._verBlocks = self._wrBlocks


    def checkBlocks(self, varUpdate=True, recurse=True, variable=None):
        with self._memLock:
            # Wait for all txns to complete
            self._waitTransaction(0)

            # Error check?
            error = self._getError()
            self._setError(0)

            # Convert the read verfiy data back to the natic type
            checkBlocks = {offset: [self._base.fromBlock(self.__mask(ba[i:i+self._stride]))
                                          for i in range(0, len(ba), self._stride)
                                          for offset, ba in self._verData.items()]}

            # Do verify if necessary
            if len(self._verBlocks) > 0:
                # Compare wrData with verData
                if self._verBlocks != checkBlocks:
                    msg = 'Local - Verify \n'
                    msg += '\n'.join(f'{x:#02x} - {y:#02x}'
                                     for x,y in zip(self._verBlocks.values(), self._checkBlocks.values()))


            # destroy the txn maps when done with verify
            self._verBlocks = odict()
            self._verData = odict()


    def readBlocks(self, recurse=True, variable=None):
        pass

