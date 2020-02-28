/**
 *-----------------------------------------------------------------------------
 * Title      : Rogue Version
 * ----------------------------------------------------------------------------
 * File       : Version.h
 * Created    : 2017-05-17
 * ----------------------------------------------------------------------------
 * Description:
 * Version helpers for Rogue
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
#ifndef __ROGUE_VERSION_H__
#define __ROGUE_VERSION_H__
#include <stdint.h>
#include <string>

namespace rogue {

   //! Version
   class Version {

         static void init   ();
         static void extract(std::string compare, uint32_t *major, uint32_t *minor, uint32_t *maint);

         static const char _version[];

         static uint32_t _major;
         static uint32_t _minor;
         static uint32_t _maint;
         static uint32_t _devel;

      public:

         Version() {}

         static std::string current();

         static bool greaterThanEqual(std::string compare);

         static bool greaterThan(std::string compare);

         static bool lessThanEqual(std::string compare);

         static bool lessThan(std::string compare);

         static void minVersion(std::string compare);

         static void maxVersion(std::string compare);

         static void exactVersion(std::string compare);

         static void setup_python();

         static uint32_t getMajor ();
         static uint32_t getMinor ();
         static uint32_t getMaint ();
         static uint32_t getDevel ();

         // For debugging
         static void sleep(uint32_t seconds);
         static void usleep(uint32_t useconds);

         static std::string pythonVersion();
   };
}

#endif

