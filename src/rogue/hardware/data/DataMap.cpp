/**
 *-----------------------------------------------------------------------------
 * Title      : Data Card Memory Mapped Access
 * ----------------------------------------------------------------------------
 * File       : DataMap.h
 * Created    : 2017-03-21
 * ----------------------------------------------------------------------------
 * Description:
 * Class for interfacing to data card mapped memory space.
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
#include <rogue/hardware/data/DataMap.h>
#include <rogue/interfaces/memory/Constants.h>
#include <rogue/GeneralError.h>
#include <boost/make_shared.hpp>
#include <stdio.h>
#include <unistd.h>
#include <sys/types.h>
#include <sys/stat.h>
#include <sys/mman.h>
#include <fcntl.h>
#include <DataDriver.h>

namespace rhd = rogue::hardware::data;
namespace rim = rogue::interfaces::memory;
namespace bp  = boost::python;

//! Class creation
rhd::DataMapPtr rhd::DataMap::create (std::string path) {
   rhd::DataMapPtr r = boost::make_shared<rhd::DataMap>(path);
   return(r);
}

//! Creator
rhd::DataMap::DataMap(std::string path) : rim::Slave(4,0xFFFFFFFF) {
   fd_ = ::open(path.c_str(), O_RDWR);
   log_ = new rogue::Logging("data.DataMap");
   if ( fd_ < 0 ) throw(rogue::GeneralError::open("DataMap::DataMap",path));
}

//! Destructor
rhd::DataMap::~DataMap() {
   ::close(fd_);
}

//! Post a transaction
void rhd::DataMap::doTransaction(uint32_t id, boost::shared_ptr<rogue::interfaces::memory::Master> master, 
                                   uint64_t address, uint32_t size, uint32_t type) {
   uint32_t count;
   uint32_t data;
   int32_t  ret;

   count = 0;
   ret = 0;

   while ( (ret == 0 ) && (count < size) ) {
      if (type == rim::Write || type == rim::Post) {
         master->getTransactionData(id,&data,count,4);
         ret = dmaWriteRegister(fd_,address+count,data);
      }
      else {
         ret = dmaReadRegister(fd_,address+count,&data);
         master->setTransactionData(id,&data,count,4);
      }
      count += 4;
   }

   master->doneTransaction(id,(ret==0)?0:1);
}

void rhd::DataMap::setup_python () {

   bp::class_<rhd::DataMap, rhd::DataMapPtr, bp::bases<rim::Slave>, boost::noncopyable >("DataMap",bp::init<std::string>())
      .def("create",         &rhd::DataMap::create)
      .staticmethod("create")
   ;

   bp::implicitly_convertible<rhd::DataMapPtr, rim::SlavePtr>();
}

