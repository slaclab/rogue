/**
 *-----------------------------------------------------------------------------
 * Title      : PGP Data Class
 * ----------------------------------------------------------------------------
 * File       : PgpData.h
 * Author     : Ryan Herbst, rherbst@slac.stanford.edu
 * Created    : 2016-08-08
 * Last update: 2016-08-08
 * ----------------------------------------------------------------------------
 * Description:
 * PGP Data Class
 * ----------------------------------------------------------------------------
 * This file is part of the rouge software platform. It is subject to 
 * the license terms in the LICENSE.txt file found in the top-level directory 
 * of this distribution and at: 
 *    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html. 
 * No part of the rouge software platform, including this file, may be 
 * copied, modified, propagated, or distributed except according to the terms 
 * contained in the LICENSE.txt file.
 * ----------------------------------------------------------------------------
**/
#ifndef __PGP_Data_H__
#define __PGP_Data_H__
#include <stdint.h>

#include <boost/python.hpp>

class PgpCard;

//! Data Holder For PGP
class PgpData {
      PgpCard * card_;
      void *    data_;
      int32_t   index_;
      uint32_t  maxSize_;
   public:

      //! Create a shared memory buffer
      PgpData(PgpCard *card, uint32_t index, void *buff, uint32_t size);
      ~PgpData();

      //! Return buffer
      bool retBuffer();

      //! Write
      bool write();

      //! Get data pointer
      uint8_t * getData();

      //! Get python buffer
      boost::python::object getDataPy();

      //! Get shared memory index
      uint32_t getIndex();

      //! Get buffer max size
      uint32_t getMaxSize();

      //! Lane for transmit / receive
      uint32_t  lane;

      //! Lane for transmit / receive
      uint32_t  vc;

      //! Continue flag. This buffer is part of a larger frame
      uint32_t  cont;

      //! Size for transmit / receive
      uint32_t  size;

      //! Error flags for receive
      uint32_t  error;
};

#endif

