/**
 *-----------------------------------------------------------------------------
 * Title      : RCE Memory Mapped Access
 * ----------------------------------------------------------------------------
 * File       : MapMemory.h
 * Author     : Ryan Herbst, rherbst@slac.stanford.edu
 * Created    : 2017-09-17
 * Last update: 2017-09-17
 * ----------------------------------------------------------------------------
 * Description:
 * Class for interfacing to RCE mapped memory space.
 * ----------------------------------------------------------------------------
 * This file is part of the rogue software platform. It is subject to 
 * the license terms in the LICENSE.txt file found in the top-level directory 
 * of this distribution and at: 
 *    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html. 
 * No part of the rogue software platform, including this file, may be 
 * copied, modified, propagated, or distributed except according to the terms 
 * contained in the LICENSE.txt file.
 * ----------------------------------------------------------------------------
**/
#include <rogue/hardware/rce/MapMemory.h>
#include <rogue/exceptions/OpenException.h>
#include <rogue/exceptions/MemoryException.h>
#include <rogue/interfaces/memory/Block.h>
#include <boost/make_shared.hpp>
#include <stdio.h>
#include <unistd.h>
#include <sys/types.h>
#include <sys/stat.h>
#include <sys/mman.h>
#include <fcntl.h>

namespace rhr = rogue::hardware::rce;
namespace rim = rogue::interfaces::memory;
namespace re  = rogue::exceptions;
namespace bp  = boost::python;

//! Class creation
rhr::MapMemoryPtr rhr::MapMemory::create () {
   rhr::MapMemoryPtr r = boost::make_shared<rhr::MapMemory>();
   return(r);
}

//! Creator
rhr::MapMemory::MapMemory() : rim::Slave(1,0xFFFFFFFF) {
   fd_ = ::open("/dev/mem", O_RDWR | O_SYNC);
   if ( fd_ < 0 ) throw(re::OpenException("MapMemory::MapMemory","/dev/mem",0));
}

//! Destructor
rhr::MapMemory::~MapMemory() {
   uint32_t x;

   for ( x=0; x < maps_.size(); x++ )
      munmap(maps_[x].ptr,maps_[x].size);

   maps_.clear();
   ::close(fd_);
}

//! Add a memory space
void rhr::MapMemory::addMap(uint32_t address, uint32_t size) {
   rhr::Map map;

   map.base = address;
   map.size = size;

   boost::lock_guard<boost::mutex> lock(mapMtx_);

   if ( fd_ >= 0 ) {
      map.ptr = (uint8_t *)mmap(NULL, map.size, PROT_READ | PROT_WRITE, MAP_SHARED, fd_, map.base);
      if ( map.ptr == NULL ) return;
      maps_.push_back(map);
   }
}

// Find matching address space
uint8_t * rhr::MapMemory::findSpace (uint32_t base, uint32_t size) {
   uint32_t x;

   boost::lock_guard<boost::mutex> lock(mapMtx_);

   for (x=0; x < maps_.size(); x++) {
      if ( (base >= maps_[x].base) && (((base - maps_[x].base) + size) < maps_[x].size) ) {
         return(maps_[x].ptr + (base-maps_[x].base));
      }
   }
   return(NULL);
}

//! Post a transaction
void rhr::MapMemory::doTransaction(uint32_t id, boost::shared_ptr<rogue::interfaces::memory::Master> master, 
                                   uint64_t address, uint32_t size, bool write, bool posted) {
   uint8_t * ptr;
   uint32_t count;

   if ((ptr = findSpace(address,size)) == NULL) {
      master->doneTransaction(id,re::MemoryException::AddressError);
   }
   else {
      count = 0;

      while ( count < size ) {
         if (write) master->getTransactionData(id,ptr+count,count,4);
         else master->setTransactionData(id,ptr+count,count,4);
         count += 4;
      }

      master->doneTransaction(id,0);
   }
}

void rhr::MapMemory::setup_python () {

   bp::class_<rhr::MapMemory, rhr::MapMemoryPtr, bp::bases<rim::Slave>, boost::noncopyable >("MapMemory",bp::init<>())
      .def("create",         &rhr::MapMemory::create)
      .staticmethod("create")
      .def("addMap",         &rhr::MapMemory::addMap)
   ;

   bp::implicitly_convertible<rhr::MapMemoryPtr, rim::SlavePtr>();
}

