#!/usr/bin/env python3
#-----------------------------------------------------------------------------
# Title      : EPICS Testing Script
#-----------------------------------------------------------------------------
# This file is part of the rogue_example software. It is subject to
# the license terms in the LICENSE.txt file found in the top-level directory
# of this distribution and at:
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
# No part of the rogue_example software, including this file, may be
# copied, modified, propagated, or distributed except according to the terms
# contained in the LICENSE.txt file.
#-----------------------------------------------------------------------------
import epics
import time
import pyrogue.interfaces

#class EpicsInterface(object):
#
#    def __init__(self):
#        self._epicsError = None
#        epics.ca.replace_printf_handler(self._printHandle)
#
#    def _printHandle(self, *argv, **kwargs):
#        print("Callback")
#        print(argv)
#        print(kwargs)
#        print("Done")
#        #print(f"Got {argv} {kwargs}")
#        #self._epicsError = msg
#
#    def caput(self, *argv, **kwargs):
#        ret = epics.caput(*argv,**kwargs)
#
#        if self._epicsError is not None:
#            raise Exception(self._epicsError)
#            self._epicsError = None
#
#        return ret
#
#    def caget(self, *argv, **kwargs):
#        ret = epics.caget(*argv,**kwargs)
#
#        if self._epicsError is not None:
#            raise Exception(self._epicsError)
#            self._epicsError = None
#
#        return ret
#
#
#ep = EpicsInterface()



#@withCA
#def replace_printf_handler(fcn=None):
#    """replace the normal printf() output handler
#    with the supplied function (defaults to :func:`sys.stderr.write`)"""
#    global error_message
#    if fcn is None:
#        fcn = sys.stderr.write
#    error_message = ctypes.CFUNCTYPE(None, ctypes.c_char_p)(fcn)
#    return libca.ca_replace_printf_handler(error_message)

#i = 0

#while True:
#    i += 1

#    caput('test:dummyTree:AxiVersion:ScratchPad',i % 1000)
#    caput('test:dummyTree:AxiVersion:AlarmTest',i % 50 + 100)
#    lst = [(i+j)%10 for j in range(10)]
#    caput('test:dummyTree:AxiVersion:TestListA', lst)
#    lst = [(i+j)%20 for j in range(10)]
#    caput('test:dummyTree:AxiVersion:TestListB', lst)

#    caget('test:dummyTree:AxiVersion:ScratchPad')
#    caget('test:dummyTree:AxiVersion:AlarmTest')
#    cur = caget('test:dummyTree:AxiVersion:TestListA')
#    cur = caget('test:dummyTree:AxiVersion:TestListB')
#    cur = caget('test:dummyTree:AxiVersion:TestString')


pv1 = epics.PV('test:dummyTree:AxiVersion:TestListA')
pv2 = epics.PV('test:dummyTree:AxiVersion:ScratchPad')

v = pyrogue.interfaces.VirtualClient()
test = v.dummyTree.AxiVersion.TestListA.get()
test = v.dummyTree.AxiVersion.ScratchPad.get()

c = 100000
s = time.time()
for i in range(c):
    cur = epics.caget('test:dummyTree:AxiVersion:TestListA')
e = time.time()

print(f"Epics list caget Rate = {c/(e-s)}")

c = 100000
s = time.time()
for i in range(c):
    cur[0]  = i
    cur[-1] = i
    epics.caput('test:dummyTree:AxiVersion:TestListA',cur,wait=True)
e = time.time()

print(f"Epics list caput Rate = {c/(e-s)}")

c = 100000
s = time.time()
for i in range(c):
    cur = pv1.get(use_monitor=False)
e = time.time()

print(f"Epics list pv.get Rate = {c/(e-s)}")

c = 100000
s = time.time()
for i in range(c):
    cur[0]  = i
    cur[-1] = i
    pv1.put(cur,wait=True)
e = time.time()

print(f"Epics list pv.put Rate = {c/(e-s)}")

c = 100000
s = time.time()
for i in range(c):
    cur = v.dummyTree.AxiVersion.TestListA.get()
e = time.time()

print(f"zmq list get Rate = {c/(e-s)}")

c = 100000
s = time.time()
for i in range(c):
    cur[0]  = i
    cur[-1] = i
    v.dummyTree.AxiVersion.TestListA.set(cur)
e = time.time()

print(f"zmq list set Rate = {c/(e-s)}")

c = 100000
s = time.time()
for i in range(c):
    cur = epics.caget('test:dummyTree:AxiVersion:ScratchPad')
e = time.time()

print(f"Epics caget Rate = {c/(e-s)}")

c = 100000
s = time.time()
for i in range(c):
    cur = i
    epics.caput('test:dummyTree:AxiVersion:ScratchPad',cur,wait=True)
e = time.time()

print(f"Epics caput Rate = {c/(e-s)}")

c = 100000
s = time.time()
for i in range(c):
    cur = pv2.get(use_monitor=False)
e = time.time()

print(f"Epics pv.get Rate = {c/(e-s)}")

c = 100000
s = time.time()
for i in range(c):
    cur = i
    pv2.put(cur,wait=True)
e = time.time()

print(f"Epics pv.put Rate = {c/(e-s)}")

c = 100000
s = time.time()
for i in range(c):
    cur = v.dummyTree.AxiVersion.ScratchPad.get()
e = time.time()

print(f"zmq get Rate = {c/(e-s)}")

c = 100000
s = time.time()
for i in range(c):
    cur = i
    v.dummyTree.AxiVersion.ScratchPad.set(cur)
e = time.time()

print(f"zmq set Rate = {c/(e-s)}")

v.stop()
