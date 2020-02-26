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
#include <string>
#include <rogue/interfaces/stream/Master.h>
#include <rogue/interfaces/stream/Slave.h>
#include <rogue/interfaces/memory/Variable.h>

namespace rogue {

   //! LibraryBase
   class LibraryBase {

         //! Map of variables
         std::map< std::string, std::shared_ptr<rogue::interfaces::memory::Variable> > _variables;

         //! Map of master streams
         std::map< std::string, std::shared_ptr<rogue::interfaces::stream::Master> > _mastStreams;

         //! Map of slave streams
         std::map< std::string, std::shared_ptr<rogue::interfaces::stream::Slave> > _slaveStreams;

      protected:

         //! Add master stream
         void addMasterStream (std::string name, std::shared_ptr<rogue::interfaces::stream::Master> mast);

         //! Add slave stream
         void addSlaveStream (std::string name, std::shared_ptr<rogue::interfaces::stream::Slave> slave);

      public:

         static std::shared_ptr<rogue::LibraryBase> create();

         LibraryBase ();
         ~LibraryBase();

         //! Get master stream by name
         std::shared_ptr<rogue::interfaces::stream::Master> getMasterStream(std::string name);

         //! Get slave stream by name
         std::shared_ptr<rogue::interfaces::stream::Slave> getSlaveStream(std::string name);

         //! Get variable by name
         std::shared_ptr<rogue::interfaces::memory::Variable> getVariable(std::string name);
   };

   typedef std::shared_ptr<rogue::LibraryBase> LibraryBasePtr;
}

#endif

