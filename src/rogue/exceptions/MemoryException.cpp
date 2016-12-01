/**
 *-----------------------------------------------------------------------------
 * Title      : Memory Exception
 * ----------------------------------------------------------------------------
 * File       : MemoryException.cpp
 * Author     : Ryan Herbst, rherbst@slac.stanford.edu
 * Created    : 2017-09-17
 * Last update: 2017-09-17
 * ----------------------------------------------------------------------------
 * Description:
 * Memory denied exception for Rogue
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
#include <rogue/exceptions/MemoryException.h>
namespace re = rogue::exceptions;
namespace bp = boost::python;

PyObject * re::memoryExceptionObj = 0;

re::MemoryException::MemoryException(std::string src, uint32_t error, uint64_t address, uint32_t size) {

   switch ( error & 0xFF000000 ) {

      case TimeoutError:
         sprintf(text_,"%s: Memory access timeout. Address: 0x%lx, Size: %i",src.c_str(),address,size);
         break;

      case VerifyError:
         sprintf(text_,"%s: Memory verify error. Address: 0x%lx, Size: %i",src.c_str(),address,size);
         break;

      case AddressError:
         sprintf(text_,"%s: Memory address error. Address: 0x%lx, Size: %i",src.c_str(),address,size);
         break;

      case AxiTimeout:
         sprintf(text_,"%s: Memory AXI timeout. Address: 0x%lx, Size: %i",src.c_str(),address,size);
         break;

      case AxiFail:
         sprintf(text_,"%s: Memory AXI fail. Address: 0x%lx, Size: %i",src.c_str(),address,size);
         break;

      default:
         sprintf(text_,"%s: Memory error detected: 0x%x. Address: 0x%lx, Size: %i",src.c_str(),error,address,size);
         break;
   }
}

char const * re::MemoryException::what() const throw() {
   return(text_);
}

void re::MemoryException::setup_python() {
   bp::class_<re::MemoryException>("MemoryException",bp::init<std::string,uint32_t,uint64_t,uint32_t>());

   PyObject * typeObj = PyErr_NewException((char *)"rogue.exceptions.MemoryException", PyExc_Exception, 0);
   bp::scope().attr("MemoryException") = bp::handle<>(bp::borrowed(typeObj));

   re::memoryExceptionObj = typeObj;

   bp::register_exception_translator<re::MemoryException>(&re::MemoryException::translate);
}

void re::MemoryException::translate(MemoryException const &e) {
   bp::object exc(e); // wrap the C++ exception

   bp::object exc_t(bp::handle<>(bp::borrowed(re::memoryExceptionObj)));
   exc_t.attr("cause") = exc; // add the wrapped exception to the Python exception

   PyErr_SetString(re::memoryExceptionObj, e.what());
}
