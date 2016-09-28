/**
 *-----------------------------------------------------------------------------
 * Title         : Register access peek and poke
 * ----------------------------------------------------------------------------
 * File          : PeekPoke.h
 * Author        : Ryan Herbst <rherbst@slac.stanford.edu>
 * Created       : 09/17/2016
 * Last update   : 09/17/2016
 *-----------------------------------------------------------------------------
 * Description :
 *    Interface to peek and poke arbitary registers.
 *-----------------------------------------------------------------------------
 * This file is part of the rogue software platform. It is subject to 
 * the license terms in the LICENSE.txt file found in the top-level directory 
 * of this distribution and at: 
    * https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html. 
 * No part of the rogue software platform, including this file, may be 
 * copied, modified, propagated, or distributed except according to the terms 
 * contained in the LICENSE.txt file.
 *-----------------------------------------------------------------------------
**/
#ifndef __ROGUE_UTILITIES_PEEK_POKE_H__
#define __ROGUE_UTILITIES_PEEK_POKE_H__
#include <stdint.h>
#include <boost/thread.hpp>
#include <rogue/interfaces/memory/Block.h>

namespace rogue {
   namespace utilities {

      //! Register access peek and poke
      class PeekPoke : public rogue::interfaces::memory::Block {
         public:

            //! Class creation
            static boost::shared_ptr<rogue::utilities::PeekPoke> create (uint32_t size);

            //! Setup class in python
            static void setup_python();

            //! Creator 
            PeekPoke(uint32_t size);

            //! Deconstructor
            ~PeekPoke();

            //! Poke. Write to an address
            void poke ( uint64_t address, uint32_t value );

            //! Peek. Read from an address
            uint32_t peek ( uint64_t address );
      };

      // Convienence
      typedef boost::shared_ptr<rogue::utilities::PeekPoke> PeekPokePtr;
   }
}
#endif

