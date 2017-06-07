/**
 *-----------------------------------------------------------------------------
 * Title      : Rogue Shared Memory Interface
 * ----------------------------------------------------------------------------
 * File       : RogueSMem.h
 * Created    : 2017-06-06
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
#ifndef __ROGUE_SMEM_H__
#define __ROGUE_SMEM_H__
#include <boost/python.hpp>

namespace rogue {

   //! Logging
   class RogueSMem {

         boost::python::object _root;
         boost::python::object _client;
         
      public:

         static boost::shared_ptr<rogue::RogueSMem> create(std::string module, std::string rootClass);

         RogueSMem (bool local, std::string arg1, std::string arg2);
         ~RogueSMem();

         void exec(std::string path, std::string arg = "");

         void exec(std::string path, uint64_t arg = 0);

         uint64_t get(std::string path);

         std::string getDisp(std::string path);

         uint64_t value(std::string path);

         std::string valueDisp(std::string path);

         void set(std::string path, uint64_t value);

         void setDisp(std::string path, std::string value);

   };


   //! Stream slave class, wrapper to enable pyton overload of virtual methods
   class RogueSmemWrap : 
      public rogue::RogueSMems::stream::Slave, 
      public boost::python::wrapper<rogue::interfaces::stream::Slave> {

      public:

         //! Accept frame
         void acceptFrame ( boost::shared_ptr<rogue::interfaces::stream::Frame> frame );

         //! Default accept frame call
         void defAcceptFrame ( boost::shared_ptr<rogue::interfaces::stream::Frame> frame );
   };



   typedef boost::shared_ptr<rogue::RogueSMem> RogueSMemPtr;
}

#endif

