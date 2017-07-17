import pyrogue as pr
import rogue.interfaces.memory as rim
import threading

class MemoryDevice(pr.Device):
    def __init__(self, base=pr.UInt, wordSize=4, stride=4, verify=True, **kwargs):
        super().__init__(hidden=True, **kwargs)

        self._base = base
        self._wordSize = wordSize
        self._bitSize = wordSize*8
        self._stride = stride
        self._bitStride = stride*8
        self._verify = verify
        self._txnSize = self._reqMaxAccess()        
        self._segments = {} # Data parsed from yaml
        self._wrTxns = {} # map of txnId and bytearrays
        self._verTxns = {}

        self._cond = threading.Condition()
        self._txnPending = False

    def _buildBlocks(self):
        pass

    def _setOrExec(self, d, writeEach, modes):
        # Parse comma separated values at each offset (key) in d
        with self._cond:
            self._segments = {k: [self._base.fromString(s) for s in v.split(',')] for k, v in d.items()}


    def writeBlocks(self, force=False, recurse=True, variable=None):
        if not self.enable.get(): return

        with self._cond:
            self._cond.wait_for(self._txnPending==False)
            self._txnPending = True

            # transform each segment into a bytearray
            arrays = {k: [b''.join(self._base.toBlock(v, self._bitStride))] for k, v in self._segments}            

            # Issue as many transactions as are needed to cover each bytearray            
            for offset, ba in arrays.items():
                for i in range(offset, offset+len(ba), self._txnSize):
                    baSlice = ba[i:min(i+self._txnSize, len(ba))]
                    sliceOffset = i|self.offset
                    self._reqTransaction(sliceOffset, baSlice, rim.Write)
                    self._wrTxns[sliceOffset] = baSlice
                    if self._verify:
                        self._verTxns[sliceOffset] = bytearray(len(baSlice))
        

    def verifyBlocks(self, recurse=True, variable=None):
        if not self.enable.get(): return
        
        with self._cond:
            for offset, ba in self._verTxns.items():
                self._reqTransaction(offset, ba, rim.Verify)

    def checkBlocks(self, varUpdate=True, recurse=True, variable=None):
        with self._cond:
            self._waitTransaction(0)

            # Error check?
            error = self._getError()
            self._setError(0)

            # Do verify if necessary
            if len(self._verTxns) > 0:
                # Compare wrData with verData
                if self._wrTxns != self._verTxns:
                    msg = 'Local - Verify \n'
                    msg += '\n'.join(f'{x:#02x} - {y:#02x}' for x,y in zip(self._wrTxns.values(), self._verTxns.values()))


                # destroy the txn maps when done with verify
                self._wrTxns = {}
                self._verTxns = {}
                self._txnPending = False
                self._cond.notify()
        

    def readBlocks(self, recurse=True, variable=None):
        pass

