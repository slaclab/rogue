/**
 *-----------------------------------------------------------------------------
 * Title      : Rogue as a library base class
 * ----------------------------------------------------------------------------
 * File       : LibraryBase.h
 * ----------------------------------------------------------------------------
 * Description:
 * Base class for creating a Rogue shared library
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
#ifndef __ROGUE_LIBRARY_BASE_H__
#define __ROGUE_LIBRARY_BASE_H__
#include <memory>
#include <stdint.h>
#include <vector>
#include <map>
#include <set>
#include <string>
#include <rogue/interfaces/stream/Master.h>
#include <rogue/interfaces/stream/Slave.h>
#include <rogue/interfaces/memory/Variable.h>
#include <rogue/interfaces/memory/Slave.h>
#include <rogue/interfaces/memory/Block.h>
#include <rogue/Logging.h>

namespace rogue {

   //! LibraryBase
   class LibraryBase {

         // Logger
         std::shared_ptr<rogue::Logging> log_;

         //! Map of variables
         std::map< std::string, std::shared_ptr<rogue::interfaces::memory::Variable> > variables_;

         //! Map of blocks by block name
         std::map< std::string, std::shared_ptr<rogue::interfaces::memory::Block> > blocks_;

         //! Map of memory interfaces
         std::map< std::string, std::shared_ptr<rogue::interfaces::memory::Slave> > memSlaves_;

         //! Map of missing memory interfaces
         std::set< std::string  > memSlavesMissing_;

      public:

         LibraryBase();
         ~LibraryBase();

         //! Add slave memory interface
         void addMemory (std::string name, std::shared_ptr<rogue::interfaces::memory::Slave> slave);

         // Parse memory map
         void parseMemMap (std::string map);

         static std::shared_ptr<rogue::LibraryBase> create();

         //! Read all variables
         void readAll();

         //! Get variable by name
         std::shared_ptr<rogue::interfaces::memory::Variable> getVariable(const std::string & name);

         //! Get a const reference to the map of variables
         const std::map<std::string, std::shared_ptr<rogue::interfaces::memory::Variable>> & getVariableList();

         //! Get block by name
         std::shared_ptr<rogue::interfaces::memory::Block> getBlock(const std::string & name);

         //! Get a map of blocks
         const std::map< std::string, std::shared_ptr<rogue::interfaces::memory::Block> > getBlockList();

      private:

         //! Create a variable
         void createVariable(std::map<std::string, std::string> &data,
                             std::map<std::string, std::vector< std::shared_ptr<rogue::interfaces::memory::Variable> > > &blockVars );

         //! Helper function to get string from fields
         std::string getFieldString(std::map<std::string, std::string> fields, std::string name);

         //! Helper function to get uint64_t from fields
         uint64_t getFieldUInt64(std::map<std::string, std::string> fields, std::string name);

         //! Helper function to get uint32_t from fields
         uint32_t getFieldUInt32(std::map<std::string, std::string> fields, std::string name, bool def=false);

         //! Helper function to get bool from fields
         bool getFieldBool(std::map<std::string, std::string> fields, std::string name);

         //! Helper function to get double from fields
         double getFieldDouble(std::map<std::string, std::string> fields, std::string name);

         //! Helper function to get uint32_t vector from fields
         std::vector<uint32_t> getFieldVectorUInt32(std::map<std::string, std::string> fields, std::string name);

         //! Dump the current state of the registers in the system
         void dumpRegisterStatus(std::string filename, bool read, bool includeStatus=false);

   };

   typedef std::shared_ptr<rogue::LibraryBase> LibraryBasePtr;
}

#endif

