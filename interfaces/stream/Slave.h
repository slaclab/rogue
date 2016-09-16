/**
 *-----------------------------------------------------------------------------
 * Title      : Stream interface slave
 * ----------------------------------------------------------------------------
 * File       : Slave.h
 * Author     : Ryan Herbst, rherbst@slac.stanford.edu
 * Created    : 2016-08-08
 * Last update: 2016-08-08
 * ----------------------------------------------------------------------------
 * Description:
 * Stream interface slave
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
#ifndef __INTERFACES_STREAM_SLAVE_H__
#define __INTERFACES_STREAM_SLAVE_H__
#include <stdint.h>

#include <boost/python.hpp>
#include <boost/enable_shared_from_this.hpp>

namespace interfaces {
   namespace stream {

      class Frame;

      //! Stream slave class
      /*
       * The stream slave accepts stream data from a master. It also
       * can accept frame allocation requests.
       */
      class Slave : public boost::enable_shared_from_this<interfaces::stream::Slave> {
         public:

            //! Class creation
            static boost::shared_ptr<interfaces::stream::Slave> create ();

            //! Creator
            Slave();

            //! Destructor
            virtual ~Slave();

            //! Generate a buffer. Called from master
            /*
             * Pass total size required.
             * Pass flag indicating if zero copy buffers are acceptable
             */
            virtual boost::shared_ptr<interfaces::stream::Frame>
               acceptReq ( uint32_t size, bool zeroCopyEn);

            //! Accept a frame from master
            /* 
             * Returns true on success
             */
            virtual bool acceptFrame ( boost::shared_ptr<interfaces::stream::Frame> frame );

            //! Return a buffer
            /*
             * Called when this instance is marked as owner of a Buffer entity that is deleted.
             */
            virtual void retBuffer(uint8_t * data, uint32_t meta, uint32_t rawSize);

            //! Return instance as shared pointer
            boost::shared_ptr<interfaces::stream::Slave> getSlave();
      };

      //! Stream slave class, wrapper to enable pyton overload of virtual methods
      class SlaveWrap : 
         public interfaces::stream::Slave, 
         public boost::python::wrapper<interfaces::stream::Slave> {

         public:

            //! Accept frame
            bool acceptFrame ( boost::shared_ptr<interfaces::stream::Frame> frame );

            //! Default accept frame call
            bool defAcceptFrame ( boost::shared_ptr<interfaces::stream::Frame> frame );
      };

      // Convienence
      typedef boost::shared_ptr<interfaces::stream::Slave> SlavePtr;
      typedef boost::shared_ptr<interfaces::stream::SlaveWrap> SlaveWrapPtr;
   }
}

#endif

