#!/usr/bin/env python

import rogue.interfaces.memory
import math

class IntField(object):

    def __init__(self,branch):

        # Default YAML Fields
        self.offset      = 0
        self.name        = ""
        self.mode        = "RW"
        self.lsbit       = 0
        self.sizeBits    = 32
        self.nelms       = 1
        self.description = ""

        # Parse YAML
        for br in branch:
           setattr(self,br,branch[br])

        # Tracking fields
        self.block = None

class Command(object):
    def __init__(self):
        self.name        = ""
        self.description = ""
        self.sequence    = []  # Entry - value pairs

class Device(rogue.interfaces.memory.Master):
      
    #def __init__(self, name ="", description = "", size = 0):
    def __init__(self,branch):
        rogue.interfaces.memory.Master.__init__(self,0) # Base address of zero 

        # Tracking Fields
        self.__blocks   = []
        self.__fields   = {}
        self.__commands = {}

        # Default Yaml Fields
        self.description = ""
        self.offset   = 0
        self.name     = ""
        self.size     = 0

        # Parse YAML Branch
        for br in branch:

            # Process Each IntField Record
            if br == 'IntField':
                for f in branch[br]:
                    field = IntField(f)
                    self.__fields[field.name] = field

            # Otherwise set local variable
            setattr(self,br,branch[br])

        # Derived fields
        self.__mask = self.size - 1

        # Loop through and create blocks
        for fld in self.__fields:
            field = self.__fields[fld] 

            # First find matching block for address
            found = False
            for block in self.__blocks:
                if (block.getAddress() & self.__mask) == field.offset:
                    field.block = block
                    found = True
    
            # Block not found
            if found == False:
                minSize   = self.reqMinAccess()
                sizeBytes = minSize
                totBits   = (field.sizeBits + field.lsbit) * field.nelms
    
                # Required size is larger than min block size
                # Compute new size alinged to min size
                if totBits > (sizeBytes * 8): 
                    sizeBytes = int(math.ceil(totBits / (minSize * 8.0)) * minSize)
            
                block = rogue.interfaces.memory.Block((self.getAddress() & self.__mask) | field.offset,sizeBytes)
                block.setSlave(self.getSlave())
                field.block = block
                self.__blocks.append(block)

    def addAt(self,prev):
        self.setSlave(prev)
        for block in self.__blocks:
           block.setSlave(prev)

    def set(self,field,value):
        fld = self.__fields[field]
        if fld.mode == "RO":
            return None  # Exception

        # Determine Accessor
        if fld.nelms == 1:
            if fld.sizeBits == 8 and (fld.lsbit % 8) == 0:
                fld.block.setUInt8(fld.lsbit/8,value)
            elif fld.sizeBits == 16 and (fld.lsbit % 16) == 0:
                fld.block.setUInt16(fld.lsbit/8,value)
            elif fld.sizeBits == 32 and (fld.lsbit % 32) == 0:
                fld.block.setUInt32(fld.lsbit/8,value)
            elif fld.sizeBits == 64 and (fld.lsbit % 64) == 0:
                fld.block.setUInt64(fld.lsbit/8,value)
            else:
                return None  # Throw exception here
        elif fld.sizeBits == 8:
            return fld.block.setString(value)
        else:
            return None  # Throw exception here

    def get(self,field):
        fld = self.__fields[field]
        if fld.mode == "WO":
            return None  # Exception

        # Determine Accessor
        if fld.nelms == 1:
            if fld.sizeBits == 8 and (fld.lsbit % 8) == 0:
                return fld.block.getUInt8(fld.lsbit/8)
            elif fld.sizeBits == 16 and (fld.lsbit % 16) == 0:
                return fld.block.getUInt16(fld.lsbit/8)
            elif fld.sizeBits == 32 and (fld.lsbit % 32) == 0:
                return fld.block.getUInt32(fld.lsbit/8)
            elif fld.sizeBits == 64 and (fld.lsbit % 64) == 0:
                return fld.block.getUInt64(fld.lsbit/8)
            else:
                return None  # Throw exception here
        elif fld.sizeBits == 8:
            return fld.block.getString()
        else:
            return None  # Throw exception here

    def setAndWrite(self,field,value):
        self.set(field,value)
        self.__fields[field].block.blockingWrite()

    def readAndGet(self,field):
        self.__fields[field].block.blockingRead()
        return self.get(field)

    def writeStale(self):
        for block in self.__blocks:
            if block.getStale():
                block.backgroundWrite()

        for block in self.__blocks:
            if block.getError():
                return None # Throw exception here

    def writeAll(self):
        for block in self.__blocks:
            block.backgroundWrite()

        for block in self.__blocks:
            if block.getError():
                return None # Throw exception here

    def readAll(self):
        for block in self.__blocks:
            block.backgroundRead()

        for block in self.__blocks:
            if block.getError():
                return None # Throw exception here

    def getFields(self):
        return self.__fields

