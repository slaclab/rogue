#!/usr/bin/env python

import rogue.interfaces.memory
import math

class IntField(object):

    def __init__(self):
        self.offset      = 0
        self.name        = ""
        self.mode        = "RW"
        self.lsbit       = 0
        self.sizeBits    = 32
        self.nelms       = 1
        self.description = ""
        self.block       = None
        self.conversion  = None
        self.parameters  = []

class Command(object):
    def __init__(self):
        self.name        = ""
        self.description = ""
        self.sequence    = []  # Entry - value pairs

class Device(rogue.interfaces.memory.Master):
      
    def __init__(self, name ="", description = "", size = 0):
        rogue.interfaces.memory.Master.__init__(self,0) # Base address of zero 
        self.__description = description
        self.__name     = name
        self.__size     = size
        self.__mask     = size - 1
        self.__blocks   = []
        self.__fields   = {}
        self.__commands = {}

    def addAt(self,):
        pass

    def addIntField(self,field):

        # Insert into dictionary so we can map by name
        self.__fields[field.name] = field

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

    def addCommand(self, command):
        self.__commands[command.name] = command

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

