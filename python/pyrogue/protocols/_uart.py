#!/usr/bin/env python
#-----------------------------------------------------------------------------
# Title      : PyRogue protocols / UART register protocol
#-----------------------------------------------------------------------------
# File       : pyrogue/protocols/_uart.py
# Created    : 2017-01-15
#-----------------------------------------------------------------------------
# Description:
# Module containing protocol modules
#-----------------------------------------------------------------------------
# This file is part of the rogue software platform. It is subject to
# the license terms in the LICENSE.txt file found in the top-level directory
# of this distribution and at:
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
# No part of the rogue software platform, including this file, may be
# copied, modified, propagated, or distributed except according to the terms
# contained in the LICENSE.txt file.
#-----------------------------------------------------------------------------

import rogue.interfaces.memory
import pyrogue
import serial

class UartMemory(rogue.interfaces.memory.Slave):
    def __init__(self, device, timeout=1, **kwargs):
        super().__init__(4,4096) # Set min and max size to 4 bytes

        self._log = pyrogue.logInit(cls=self, name=f'{device}')
        self.serialPort = serial.Serial(device, timeout=timeout, **kwargs)

    def close(self):
        self.serialPort.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()


    def _doTransaction(self, transaction):
        with transaction.lock():
            address = transaction.address()

            # Write path
            if transaction.type() == rogue.interfaces.memory.Write:
                dataBa = bytearray(transaction.size())
                transaction.getData(data, 0)
                dataWords = [int.from_bytes(data[i:i+4], 'little', signed=False) for i in range(0, len(data), 4)]

                # Need to issue a UART command for each 32 bit word
                for i, (addr, data) in enumerate(zip(range(address, address+len(dataBa), 4), dataWords)):
                    sendString = f'w {addr:08x} {data:08x} \n'.encode('ASCII')
                    self._log.debug(f'Sending write transaction part {i}: {repr(sendString)}')
                    self.serialPort.write(sendString)
                    response = self.serialPort.readline().decode('ASCII')
                    
                    # If response is empty, a timeout occured
                    if len(response == 0):
                        transaction.done(rogue.interfaces.memory.TimeoutError)
                        self._log.error('Empty transaction response (likely timeout) for transaction part {i}: {repr(sendString)}')
                        return

                    # parse the response string
                    parts = response.split()
                    # Check for correct response
                    if (len(parts) != 2 or
                        parts[0].lower() != 'w' or
                        int(parts[1], 16) != transaction.address()):
                        transaction.done(rogue.interfaces.memory.ProtocolError)
                        self._log.error('Malformed response for part {i}: {repr(response)} to transaction: {repr(sendString)}')
                        return
                    else:
                        self._log.debug('Transaction part {i}: {repr(sendString)} completed successfully')
                        
                transaction.done(0)                        

            elif transaction.type() == rogue.interfaces.memory.Read:
                size = transaction.size()

                for i, addr in enumerate(range(address, address+size, 4)):
                    sendString = f'r {addr:08x} \n'.encode('ASCII')
                    self._log.debug(f'Sending read transaction part {i}: {repr(sendString)}')
                    self.serialPort.write(sendString)
                    response = self.serialPort.readline().decode('ASCII')

                    # If response is empty, a timeout occured
                    if len(response == 0):
                        transaction.done(rogue.interfaces.memory.TimeoutError)
                        self._log.error('Empty transaction response (likely timeout) for transaction part {i}: {repr(sendString)}')
                        return
                    
                    else: # if (transaction.type() == rogue.interfaces.memory.Read
                        if (len(parts) != 3 or
                            parts[0].lower() != 'r' or
                            int(parts[1], 16) != transaction.address()):
                            transaction.done(rogue.interfaces.memory.ProtocolError)
                            self._log.error('Malformed response part {i}: {repr(response)} to transaction: {repr(sendString)}')
                        else:
                            rdData = int(parts[2], 16)
                            transaction.setData(rdData.to_bytes(4, 'little', signed=False), i*4)
                            self._log.debug('Transaction part {i}: {repr(sendString)} with response data: {rdData:#08x} completed successfully')
                    
                transaction.done(0)
            else:
                # Posted writes not supported (for now)
                transaction.done(rogue.interfaces.memory.Unsupported)
                self._log.error(f'Unsupported transaction type: {transaction.type()}')
                return



  


