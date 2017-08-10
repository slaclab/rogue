/**
 *-----------------------------------------------------------------------------
 * Title      : C++ API Wrapper
 * ----------------------------------------------------------------------------
 * File       : ApiWrapper.h
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
#ifndef __ROGUE_API_WRAPPER_H__
#define __ROGUE_API_WRAPPER_H__
#include <boost/python.hpp>
#include <vector>

namespace rogue {

   //! Structure for variable & command list
   class ApiEntry {
      public:
         std::string path;
         bool        cmd;
         bool        cmdArg;
         bool        hidden;
         std::string typeStr;
   };

   //! API Wrapper
   class ApiWrapper {

         boost::python::object _root;
         boost::python::object _client;
         
      public:

         static boost::shared_ptr<rogue::ApiWrapper> local(std::string module, std::string rootClass);
         static boost::shared_ptr<rogue::ApiWrapper> remote(std::string group, std::string root);

         ApiWrapper (bool local, std::string arg1, std::string arg2);
         ~ApiWrapper();

         std::vector<boost::shared_ptr<rogue::ApiEntry>> getEntries();

         void execUInt32 (std::string path, uint32_t arg = 0);
         void execUInt64 (std::string path, uint64_t arg = 0);
         void execDouble (std::string path, double   arg = 0.0);
         void execString (std::string path, std::string arg = "");

         uint32_t    getUInt32 (std::string path);
         uint64_t    getUInt64 (std::string path);
         double      getDouble (std::string path);
         std::string getString (std::string path);

         uint32_t    valueUInt32 (std::string path);
         uint64_t    valueUInt64 (std::string path);
         double      valueDouble (std::string path);
         std::string valueString (std::string path);

         void setUInt32  (std::string path, uint32_t value);
         void setUInt64  (std::string path, uint64_t value);
         void setDouble  (std::string path, double   value);
         void setString  (std::string path, std::string value);

         void stop();

         std::string getYaml();
         void setYaml(std::string);

         std::string getLog();
         void clrLog();
   };

   typedef boost::shared_ptr<rogue::ApiWrapper> ApiWrapperPtr;
   typedef boost::shared_ptr<rogue::ApiEntry>   ApiEntryPtr;
   typedef std::vector<rogue::ApiEntryPtr>      ApiEntryList;
}

#endif

