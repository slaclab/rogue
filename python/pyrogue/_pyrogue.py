#!/usr/bin/env python
#-----------------------------------------------------------------------------
# Title      : PyRogue base module
#-----------------------------------------------------------------------------
# File       : pyrogue/__init__.py
# Created    : 2016-09-29
#-----------------------------------------------------------------------------
# Description:
# Module containing the top functions and classes within the pyrouge library
#-----------------------------------------------------------------------------
# This file is part of the rogue software platform. It is subject to 
# the license terms in the LICENSE.txt file found in the top-level directory 
# of this distribution and at: 
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html. 
# No part of the rogue software platform, including this file, may be 
# copied, modified, propagated, or distributed except according to the terms 
# contained in the LICENSE.txt file.
#-----------------------------------------------------------------------------
import sys
import rogue.interfaces.memory
import textwrap
import yaml
import threading
import time
import math
from collections import OrderedDict as odict
import collections
import datetime
import traceback
import re
import functools as ft
import itertools
import logging
import heapq
from inspect import signature









# class MultiDevice(Device):
#     def __init__(self, name, devices, **kwargs):
#         super(name=name, **kwargs)

#         # First check that all devices are of same type
#         if len(set((d.__class__ for d in devices))) != 1:
#             raise Exception("Devices must all be of same class")

#         for v in devices[0].variables.values():
#             if v.mode == 'RW':
#                 self.add(LocalVariable.clone(v))

#         for locVar in self.variables.values():
#             depVars = [v for d in devices for v in d.variables.items() if v.name == locVar.name]


#             # Create a new set method that mirrors the set value out to all the dependent variables
#             def locSet(self, value, write=True):
#                 self.value = value
#                 for v in depVars:
#                     v.set(locVar.value, write)

#             # Monkey patch the new set method in to the local variable
#             locVar.setSetFunc(locSet)
            
#             def locGet(self, read=True):
#                 values = {v: v.get(read) for v in depVars}

#                 self.value = list(values.values())[0]
#                 if len(set(values)) != 1:
#                     raise Exception("MultiDevice variables do not match: {}".format(values))

#                 return self.value

#             locVar.setGetFunc(locGet)
            







