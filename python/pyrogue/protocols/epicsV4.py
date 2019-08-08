#!/usr/bin/env python
#-----------------------------------------------------------------------------
# Title      : PyRogue epics support
#-----------------------------------------------------------------------------
# File       : pyrogue/protocols/epics.py
# Author     : Ryan Herbst, rherbst@slac.stanford.edu
# Created    : 2016-09-29
# Last update: 2016-09-29
#-----------------------------------------------------------------------------
# Description:
# Module containing epics support classes and routines
#-----------------------------------------------------------------------------
# This file is part of the rogue software platform. It is subject to 
# the license terms in the LICENSE.txt file found in the top-level directory 
# of this distribution and at: 
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html. 
# No part of the rogue software platform, including this file, may be 
# copied, modified, propagated, or distributed except according to the terms 
# contained in the LICENSE.txt file.
#-----------------------------------------------------------------------------
import pyrogue
import time
#from p4p.server import Server, StaticProvider
import p4p.server


class EpicsPvHandler:
    def __init__(self, var):
        self._var = var

    def put(self, op):
        pass

    def rpc(self, op):
        pass

    def onFirstConnect(self): # may be omitted
        pass

    def onLastDisconnect(self): # may be omitted
        pass


class EpicsPvServer(object):
    """
    Class to contain an epics PV server
    """
    def __init__(self,*,base,root,pvMap=None, syncRead=True, threadCount=0):
        self._root      = root
        self._base      = base 
        self._log       = pyrogue.logInit(cls=self)
        self._syncRead  = syncRead

        self._provider = p4p.server.StaticProvider(__name__)

        self._list = []

        #pvstats = PVStats(provider, lock, args.P, xpm)
        #pvctrls = PVCtrls(provider, lock, args.P, args.ip, xpm, pvstats._groups)
        #pvxtpg  = None
        #if 'xtpg' in xpm.AxiVersion.ImageName.get():
            #pvxtpg = PVXTpg(provider, lock, args.P, xpm, xpm.mmcmParms)

        if not root.running:
            raise Exception("Epics can not be setup on a tree which is not started")

        # Figure out mapping mode
        if pvMap is None:
            doAll = True
            self._pvMap = {}
        else:
            doAll = False
            self._pvMap = pvMap

        # Create PVs
        for v in self._root.variableList:
            eName = None

            if doAll:
                eName = self._base + ':' + node.path.replace('.',':')
                self._pvMap[node.path] = eName
            elif v.path in self._pvMap:
                eName = self._pvMap[v.path]

            if eName is not None:
                
                # Convert valType
                if 'UInt' in v.typeStr:
                    if   v.bitSize <= 8:  valType = 'B'
                    elif v.bitSize <= 16: valType = 'H'
                    elif v.bitSize <= 32: valType = 'I'
                    elif v.bitSize <= 64: valType = 'L'

                elif 'Int' in v.typeStr:
                    if   v.bitSize <= 8:  valType = 'b'
                    elif v.bitSize <= 16: valType = 'h'
                    elif v.bitSize <= 32: valType = 'i'
                    elif v.bitSize <= 64: valType = 'l'

                elif 'Float' in v.typeStr:
                    if v.bitSize   <= 32: valType = 'f'
                    elif v.bitSize <= 64: valType = 'd'

                elif v.typeStr == 'int':
                    valType = 'i'
                elif v.typeStr == 'float':
                    valType = 'd'
                elif v.typeStr == 'str':
                    valType = 's'
                else:
                    valType = 's'

                h = EpicsPvHandler(v)
                p4p.server.thread.SharedPV(queue=None, 
                                           handler= h,
                                           initial=NTScalar(valType).wrap(v.value()),
                                           nt=NTScalar(valType), 
                                           options={})

#?	bool
#s	unicode

#v	variant
#U	union
#S	struct



                


#
#
#
#                if isinstance(node, pyrogue.BaseCommand):
#                    self._srv.addValue(rogue.protocols.epicsV3.Command(eName,node))
#                    self._log.info("Adding command {} mapped to {}".format(node.path,eName))
#                else:
#
#                    # Add standard variable
#                    evar = rogue.protocols.epicsV3.Variable(eName,node,self._syncRead)
#                    node.addListener(evar.varUpdated)
#                    self._srv.addValue(evar)
#                    self._log.info("Adding variable {} mapped to {}".format(node.path,eName))


#   // Enum type
#   if ( isEnum ) {
#      epicsType_ = aitEnumEnum16;
#      log_->info("Detected enum for %s typeStr=%s", epicsName_.c_str(),typeStr.c_str());
#   }
#
#   // Unsigned Int types, > 32-bits treated as string
#   else if ( sscanf(typeStr.c_str(),"UInt%i",&bitSize) == 1 ) {
#      if ( bitSize <=  8 ) { fSize_ = 1; epicsType_ = aitEnumUint8; } 
#      else if ( bitSize <= 16 ) { fSize_ = 2; epicsType_ = aitEnumUint16; } 
#      else if ( bitSize <= 32) { fSize_ = 4; epicsType_ = aitEnumUint32; } 
#      else { epicsType_ = aitEnumString; } 
#
#      log_->info("Detected Rogue Uint with size %i for %s typeStr=%s",
#            bitSize, epicsName_.c_str(),typeStr.c_str());
#  }
#
#   // Signed Int types, > 32-bits treated as string
#   else if ( sscanf(typeStr.c_str(),"Int%i",&bitSize) == 1 ) {
#      if ( bitSize <=  8 ) { fSize_ = 1; epicsType_ = aitEnumInt8; } 
#      else if ( bitSize <= 16 ) { fSize_ = 2; epicsType_ = aitEnumInt16; } 
#      else if ( bitSize <= 32 ) { fSize_ = 4; epicsType_ = aitEnumInt32; } 
#      else { epicsType_ = aitEnumString; }
#
#      log_->info("Detected Rogue Int with size %i for %s typeStr=%s",
#            bitSize, epicsName_.c_str(),typeStr.c_str());
#   }
#
#   // Python int
#   else if ( typeStr == "int" ) {
#      fSize_ = 4; 
#      epicsType_ = aitEnumInt32;
#      log_->info("Detected python int with size %i for %s typeStr=%s",
#            bitSize, epicsName_.c_str(),typeStr.c_str());
#   }
# 
#   // 32-bit Float
#   else if ( typeStr == "float" or typeStr == "Float32" ) {
#      log_->info("Detected 32-bit float %s: typeStr=%s", epicsName_.c_str(),typeStr.c_str());
#      epicsType_ = aitEnumFloat32;
#      fSize_ = 4;
#   }
#
#   // 64-bit float
#   else if ( typeStr == "Float64" ) {
#      log_->info("Detected 64-bit float %s: typeStr=%s", epicsName_.c_str(),typeStr.c_str());
#      epicsType_ = aitEnumFloat64;
#      fSize_ = 8;
#   }
#
#   // Unknown type maps to string
#   if ( epicsType_ == aitEnumInvalid ) {
#      log_->info("Detected unknow type for %s typeStr=%s. I wil be map to string.", epicsName_.c_str(),typeStr.c_str());
#      epicsType_ = aitEnumString;
#   }
#
#   // String are limited to 40 chars, so let's use an array of char instead for strings
#   if (epicsType_ == aitEnumString)
#   {
#      if ( count != 0 ) {
#         log_->error("Vector of string not supported in EPICS. Ignoring %\n", epicsName_.c_str());
#      } else {
#         log_->info("Treating String as waveform of chars for %s typeStr=%s\n", epicsName_.c_str(),typeStr.c_str());
#         epicsType_ = aitEnumUint8;
#         count      = 300;
#         isString_  = true;
#      }
#   }
#
#   // Vector
#   if ( count != 0 ) {
#      log_->info("Create vector GDD for %s epicsType_=%i, size=%i",epicsName_.c_str(),epicsType_,count);
#      pValue_ = new gddAtomic (gddAppType_value, epicsType_, 1u, count);
#      size_   = count;
#      max_    = count;
#      array_  = true;
#   }
#
#   // Scalar
#   else {
#      log_->info("Create scalar GDD for %s epicsType_=%i",epicsName_.c_str(),epicsType_);
#      pValue_ = new gddScalar(gddAppType_value, epicsType_);
#   }

	
#handler – A object which will receive callbacks when eg. a Put operation is requested. May be omitted if the decorator syntax is used.
#initial (Value) – An initial Value for this PV. If omitted, open() s must be called before client access is possible.
#nt – An object with methods wrap() and unwrap(). eg p4p.nt.NTScalar.
#wrap (callable) – As an alternative to providing ‘nt=’, A callable to transform Values passed to open() and post().
#unwrap (callable) – As an alternative to providing ‘nt=’, A callable to transform Values returned Operations in Put/RPC handlers.
#queue (WorkQueue) – The threaded WorkQueue on which handlers will be run.
#options (dict) – A dictionary of configuration options.
#
#
#
#        # Start server
#        self._thread = threading.Thread(target=self._run)
#        self._thread.start()
#
#    def createSlave(self, name, maxSize, type):
#        slave = rogue.protocols.epicsV3.Slave(self._base + ':' + name,maxSize,type)
#        self._srv.addValue(slave)
#        return slave
#
#    def createMaster(self, name, maxSize, type):
#        mast = rogue.protocols.epicsV3.Master(self._base + ':' + name,maxSize,type)
#        self._srv.addValue(mast)
#        return mast
#
#    def stop(self):
#        self._srv.stop()
#
#    def start(self):
#        self._srv.start()
#
#    def list(self):
#        return self._pvMap
#
#    def dump(self):
#        for k,v in self._pvMap.items():
#            print("{} -> {}".format(v,k))
#
#    def _run(self):
#
#        # process PVA transactions
#        updatePeriod = 1.0
#        with p4p.server.Server(providers=[self._provider]):
#            if pvxtpg is not None:
#                pvxtpg .init()
#            pvstats.init()
#            while True:
#                prev = time.perf_counter()
#                if pvxtpg is not None:
#                    pvxtpg .update()
#                pvstats.update()
#                curr  = time.perf_counter()
#                delta = prev+updatePeriod-curr
##                print('Delta {:.2f}  Update {:.2f}  curr {:.2f}  prev {:.2f}'.format(delta,curr-prev,curr,prev))
#                if delta>0:
#                    time.sleep(delta)
#
