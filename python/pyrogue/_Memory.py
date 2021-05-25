#-----------------------------------------------------------------------------
# This file is part of the rogue software platform. It is subject to
# the license terms in the LICENSE.txt file found in the top-level directory
# of this distribution and at:
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
# No part of the rogue software platform, including this file, may be
# copied, modified, propagated, or distributed except according to the terms
# contained in the LICENSE.txt file.
#-----------------------------------------------------------------------------
import pyrogue as pr
import rogue.interfaces.memory as rim
from collections import OrderedDict as odict
import collections
import threading


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
            hidden=hidden,
            groups=groups,
            expand=expand,
            enabled=enabled,
        )

        self._rawSize = size
        self._txnLock = threading.RLock()

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
        self._verData = odict() # verify the written data


    def _buildBlocks(self):
        pass

    @pr.expose
    def set(self, offset, values, write=False):
        with self._txnLock:
            self._setValues[offset] = values
            if write:
                self.writeBlocks()
                self.verifyBlocks()
                self.checkBlocks()

    @pr.expose
    def get(self, offset, numWords):
        with self._txnLock:
            #print(f'get() self._wordBitSize={self._wordBitSize}')
            data = self._txnChunker(offset=offset, data=None,
                                    base=self._base, stride=self._stride,
                                    wordBitSize=self._wordBitSize, txnType=rim.Read,
                                    numWords=numWords)
            self._waitTransaction(0)
            self._clearError()
            return [self._base.fromBytes(data[i:i+self._stride])
                    for i in range(0, len(data), self._stride)]


    def _setDict(self, d, writeEach, modes,incGroups,excGroups,keys):
        # Parse comma separated values at each offset (key) in d
        with self._txnLock:
            for offset, values in d.items():
                self._setValues[offset] = [self._base.fromString(s) for s in values.split(',')]

    def _getDict(self,modes,incGroups,excGroups):
        return None

    def writeBlocks(self, force=False, recurse=True, variable=None, checkEach=False):
        if self.enable.get() is not True:
            return

        with self._txnLock:
            self._wrValues = self._setValues
            for offset, values in self._setValues.items():
                self._txnChunker(offset, values, self._base, self._stride, self._wordBitSize, rim.Write, len(values))

            # clear out setValues when done
            self._setValues = odict()


    def verifyBlocks(self, recurse=True, variable=None, checkEach=False):
        if (not self._verify) or (self.enable.get() is not True):
            return

        with self._txnLock:
            for offset, ba in self._wrValues.items():
                # _verValues will not be filled until waitTransaction completes
                self._verValues[offset] = self._txnChunker(offset, None, self._base, self._stride, self._wordBitSize, txnType=rim.Verify, numWords=len(ba))

    def checkBlocks(self, recurse=True, variable=None):
        with self._txnLock:
            # Wait for all txns to complete
            self._waitTransaction(0)

            # Error check?
            self._clearError()

            # Convert the read verify data back to the native type
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
                    raise MemoryError(name=self.name, address=self.address, msg=msg, size=self._rawSize)


            # destroy the txn maps when done with verify
            self._verValues = odict()
            self._wrValues = odict()


    def readBlocks(self, recurse=True, variable=None, checkEach=False):
        pass

    @pr.expose
    @property
    def size(self):
        return self._rawSize

    def _txnChunker(self, offset, data, base=pr.UInt, stride=4, wordBitSize=32, txnType=rim.Write, numWords=1):

        if not isinstance(base, pr.Model):
            base = base(wordBitSize)

        if offset + (numWords * stride) > self._rawSize:
            raise pr.MemoryError(name=self.name, address=offset|self.address,
                                 msg='Raw transaction outside of device size')

        if base.bitSize > stride*8:
            raise pr.MemoryError(name=self.name, address=offset|self.address,
                                 msg='Called raw memory access with wordBitSize > stride')

        if txnType == rim.Write or txnType == rim.Post:
            if isinstance(data, bytearray):
                ldata = data
            elif isinstance(data, collections.abc.Iterable):
                ldata = b''.join(base.toBytes(word).ljust(stride, b'\0') for word in data)
            else:
                ldata = base.toBytes(data)

        else:
            if data is not None:
                ldata = data
            else:
                ldata = bytearray(numWords*stride)

        with self._txnLock:
            for i in range(offset, offset+len(ldata), self._reqMaxAccess()):
                sliceOffset = i | self.offset
                txnSize = min(self._reqMaxAccess(), len(ldata)-(i-offset))
                #print(f'sliceOffset: {sliceOffset:#x}, ldata: {ldata}, txnSize: {txnSize}, buffOffset: {i-offset}')
                self._reqTransaction(sliceOffset, ldata, txnSize, i-offset, txnType)

            return ldata
