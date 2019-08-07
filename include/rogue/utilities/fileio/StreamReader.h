/**
 *-----------------------------------------------------------------------------
 * Title         : Data file reader utility.
 * ----------------------------------------------------------------------------
 * File          : StreamReader.h
 * Author        : Ryan Herbst <rherbst@slac.stanford.edu>
 * Created       : 09/28/2016
 * Last update   : 09/28/2016
 *-----------------------------------------------------------------------------
 * Description :
 *    Class to read data files.
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
#ifndef __ROGUE_UTILITIES_FILEIO_STREAM_READER_H__
#define __ROGUE_UTILITIES_FILEIO_STREAM_READER_H__
#include <rogue/interfaces/stream/Master.h>
#include <thread>
#include <stdint.h>
#include <mutex>
#include <condition_variable>
#include <map>

namespace rogue {
   namespace utilities {
      namespace fileio {

         //! Stream writer central class
         class StreamReader : public rogue::interfaces::stream::Master {

               //! Base file name
               std::string baseName_;

               //! File descriptor
               int32_t fd_;

               //! File index
               uint32_t fdIdx_;

               //! Active
               bool active_;
              
               //! Read thread
               std::thread* readThread_;
               bool threadEn_;

               //! Thread background
               void runThread();

               //! Open file
               bool nextFile();

               //! Internal close
               void intClose();

               //! Active condition
               std::condition_variable cond_;

               //! Active lock
               std::mutex mtx_;

            public:

               //! Class creation
               static std::shared_ptr<rogue::utilities::fileio::StreamReader> create ();

               //! Setup class in python
               static void setup_python();

               //! Creator
               StreamReader();

               //! Deconstructor
               ~StreamReader();

               //! Read from the data file
               void open(std::string file);

               //! Close and stop thread
               void close();

               //! Get open status
               bool isOpen();

               //! Close when done
               void closeWait();

               //! Return true while reading
               bool isActive();
         };

         // Convienence
         typedef std::shared_ptr<rogue::utilities::fileio::StreamReader> StreamReaderPtr;
      }
   }
}
#endif

