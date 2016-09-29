/**
 *-----------------------------------------------------------------------------
 * Title         : Data file writer utility. Slave interface.
 * ----------------------------------------------------------------------------
 * File          : StreamWriterSlaveSlave.h
 * Author        : Ryan Herbst <rherbst@slac.stanford.edu>
 * Created       : 09/28/2016
 * Last update   : 09/28/2016
 *-----------------------------------------------------------------------------
 * Description :
 *    Class to act as a slave interface to the StreamWriterSlave. Each
 *    slave is associated with a tag. The tag is included in the bank header
 *    of each write.
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
#ifndef __ROGUE_UTILITIES_FILEIO_STREAM_WRITER_SLAVE_H__
#define __ROGUE_UTILITIES_FILEIO_STREAM_WRITER_SLAVE_H__
#include <stdint.h>
#include <boost/thread.hpp>
#include <rogue/interfaces/stream/Slave.h>

namespace rogue {
   namespace utilities {
      namespace fileio {

         class StreamWriter;

         //! Stream writer central class
         class StreamWriterSlave : public rogue::interfaces::stream::Slave {

               //! Associated Stream Writer class
               boost::shared_ptr<rogue::utilities::fileio::StreamWriter> writer_;

               //! Tag information
               uint16_t tag_;

               //! Type information
               uint8_t  type_;

            public:

               //! Class creation
               static boost::shared_ptr<rogue::utilities::fileio::StreamWriterSlave> 
                  create (boost::shared_ptr<rogue::utilities::fileio::StreamWriter> writer, uint16_t tag, uint8_t type);

               //! Setup class in python
               static void setup_python();

               //! Creator
               StreamWriterSlave(boost::shared_ptr<rogue::utilities::fileio::StreamWriter> writer, uint16_t tag, uint8_t type);

               //! Deconstructor
               ~StreamWriterSlave();

               //! Accept a frame from master
               void acceptFrame ( boost::shared_ptr<rogue::interfaces::stream::Frame> frame );
         };

         // Convienence
         typedef boost::shared_ptr<rogue::utilities::fileio::StreamWriterSlave> StreamWriterSlavePtr;
      }
   }
}

#endif

