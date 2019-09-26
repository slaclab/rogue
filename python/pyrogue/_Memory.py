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
                 groups=None,
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
            groups=groups,
            expand=expand,
            enabled=enabled,
        )

        self._lockCnt = 0

        if isinstance(base, pr.Model):
        self._base = base
        else:
            self._base = base(wordBitSize)

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

    @pr.expose
    def set(self, offset, values, write=False):
        with self._memLock:
            self._setValues[offset] = values
            if write:
                self.writeBlocks()
                self.verifyBlocks()
                self.checkBlocks()

    @pr.expose
    def get(self, offset, numWords):
        with self._memLock:
            #print(f'get() self._wordBitSize={self._wordBitSize}')
            data = self._rawTxnChunker(offset=offset, data=None, base=self._base, stride=self._stride, wordBitSize=self._wordBitSize, txnType=rim.Read, numWords=numWords)
            self._waitTransaction(0)
            self._clearError()
            return [self._base.fromBytes(data[i:i+self._stride])
                    for i in range(0, len(data), self._stride)]


    def _setDict(self, d, writeEach, modes,incGroups,excGroups):
        # Parse comma separated values at each offset (key) in d
        with self._memLock:
            for offset, values in d.items():
                self._setValues[offset] = [self._base.fromString(s) for s in values.split(',')]

    def _getDict(self,modes,incGroups,excGroups):
        return None

    def writeBlocks(self, force=False, recurse=True, variable=None, checkEach=False):
        if not self.enable.get(): return

        with self._memLock:
            self._wrValues = self._setValues
            for offset, values in self._setValues.items():
                wdata = self._rawTxnChunker(offset, values, self._base, self._stride, self._wordBitSize, rim.Write)
                #print(f'wdata: {wdata}')
                #if self._verify:
                #    self._wrData[offset] = wdata

            # clear out setValues when done
            self._setValues = odict()
        

    def verifyBlocks(self, recurse=True, variable=None, checkEach=False):
        if not self.enable.get(): return

        with self._memLock:
            for offset, ba in self._wrValues.items():
                # _verValues will not be filled until waitTransaction completes
                self._verValues[offset] = self._rawTxnChunker(offset, None, self._base, self._stride, self._wordBitSize, txnType=rim.Verify, numWords=len(ba))
                

            #self._wrData = odict()
            #self._verValues = self._wrValues

    def checkBlocks(self, recurse=True, variable=None):
        with self._memLock:
            # Wait for all txns to complete
            self._waitTransaction(0)

            # Error check?
            error = self._getError()
            self._clearError()

            # Convert the read verfiy data back to the native type
            # Can't do this until waitTransaction is done
            checkValues = odict()
            for offset, ba in self._verValues.items():
                checkValues[offset] = [self._base.fromBytes(ba[i:i+self._stride])
                                       for i in range(0, len(ba), self._stride)]

            # Do verify if necessary
            if len(self._verValues) > 0:
                # Compare wrData with verData
                if checkValues != self._wrValues:
                    msg = 'Verify error \n'
                    msg += f'Expected: \n {self._wrValues} \n'
                    msg += f'Got: \n {checkValues}'
                    print(msg)
                    raise MemoryError(name=self.name, address=self.address, msg=msg, size=self._size)


            # destroy the txn maps when done with verify
            self._verValues = odict()
            self._wrValues = odict()


    def readBlocks(self, recurse=True, variable=None, checkEach=False):
        pass

