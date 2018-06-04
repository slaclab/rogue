import pyrogue as pr
import rogue.interfaces.memory as rim
import threading
from collections import OrderedDict as odict


class MemoryDevice(pr.Device):
    def __init__(self, *,
                 name=None,
                 description='',
                 memBase=None,
                 offset=0,
                 size=0,
                 hidden=False,
                 expand=True,
                 enabled=True,
                 base=pr.UInt,
                 wordBitSize=32,
                 stride=4,
                 verify=True):
        
        super().__init__(
            name=name,
            description=description,
            memBase=memBase,
            offset=offset,
            size=size,
            hidden=hidden,
            expand=expand,
            enabled=enabled,
        )

        self._lockCnt = 0
        self._base = base
        self._wordBitSize = wordBitSize
        self._stride = stride
        self._verify = verify

        self._setValues = odict()
        self._wrValues = odict() # parsed from yaml
        self._verValues = odict()
        self._wrData = odict() # byte arrays written
        self._verData = odict() # verify data wread back


    def _buildBlocks(self):
        pass

    def _setDict(self, d, writeEach, modes):
        # Parse comma separated values at each offset (key) in d
        with self._memLock:
            for offset, values in d.items():
                self._setValues[offset] = [self._base.fromString(s, self._wordBitSize) for s in values.split(',')]

    def _getDict(self,modes):
        return None

    def writeBlocks(self, force=False, recurse=True, variable=None, checkEach=False):
        if not self.enable.get(): return

        with self._memLock:
            self._wrValues = self._setValues
            
            for offset, values in self._setValues.items():
                wdata = self._rawTxnChunker(offset, values, self._base, self._stride, self._wordBitSize, rim.Write)
                if self._verify:
                    self._wrData[offset] = wdata

            # clear out wrValues when done
            self._setValues = odict()
        

    def verifyBlocks(self, recurse=True, variable=None, checkEach=False):
        if not self.enable.get(): return

        with self._memLock:
            for offset, ba in self._wrData.items():
                self._verData[offset] = bytearray(len(ba))
                self._rawTxnChunker(offset, self._verData[offset], txnType=rim.Verify)

            self._wrData = odict()
            self._verValues = self._wrValues

    def checkBlocks(self, recurse=True, variable=None):
        with self._memLock:
            # Wait for all txns to complete
            self._waitTransaction(0)

            # Error check?
            error = self._getError()
            self._setError(0)

            # Convert the read verfiy data back to the natic type
            checkValues = odict()
            #print(self._verData.items())
            for offset, ba in self._verData.items():
                checkValues[offset] = [self._base.mask(self._base.fromBytes(ba[i:i+self._stride]), self._wordBitSize)
                                       for i in range(0, len(ba), self._stride)]

            # Do verify if necessary
            if len(self._verValues) > 0:
                # Compare wrData with verData
                if self._verValues != checkValues:
                    msg = 'Verify error \n'
                    msg += f'Expected: \n {self._verValues} \n'
                    msg += f'Got: \n {checkValues}'
                    print(msg)
                    raise MemoryError(name=self.name, address=self.address, error=rim.VerifyError, msg=msg, size=self._size)


            # destroy the txn maps when done with verify
            self._verValues = odict()
            self._verData = odict()


    def readBlocks(self, recurse=True, variable=None, checkEach=False):
        pass

