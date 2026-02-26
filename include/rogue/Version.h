/**
 * ----------------------------------------------------------------------------
 * Company    : SLAC National Accelerator Laboratory
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
#include "rogue/Directives.h"

#include <stdint.h>

#include <string>

namespace rogue {

/**
 * @brief Rogue version query and comparison helpers.
 *
 * @details
 * Provides access to the runtime Rogue version string/components and utilities
 * to compare against a requested version expression. Comparison helpers parse
 * the passed version string into major/minor/maintenance components.
 */
class Version {
    static void init();
    static void extract(const std::string& compare, uint32_t* major, uint32_t* minor, uint32_t* maint);

    static const char _version[];

    static uint32_t _major;
    static uint32_t _minor;
    static uint32_t _maint;
    static uint32_t _devel;

  public:
    /** @brief Default constructor. */
    Version() {}

    /**
     * @brief Returns current Rogue version string.
     * @return Version string.
     */
    static std::string current();

    /**
     * @brief Returns whether current version is greater than or equal to `compare`.
     * @param compare Version string to compare against.
     * @return `true` when current version is >= `compare`.
     */
    static bool greaterThanEqual(const std::string& compare);

    /**
     * @brief Returns whether current version is greater than `compare`.
     * @param compare Version string to compare against.
     * @return `true` when current version is > `compare`.
     */
    static bool greaterThan(const std::string& compare);

    /**
     * @brief Returns whether current version is less than or equal to `compare`.
     * @param compare Version string to compare against.
     * @return `true` when current version is <= `compare`.
     */
    static bool lessThanEqual(const std::string& compare);

    /**
     * @brief Returns whether current version is less than `compare`.
     * @param compare Version string to compare against.
     * @return `true` when current version is < `compare`.
     */
    static bool lessThan(const std::string& compare);

    /**
     * @brief Throws if current version is below required minimum.
     * @param compare Minimum required version string.
     */
    static void minVersion(const std::string& compare);

    /**
     * @brief Throws if current version is above allowed maximum.
     * @param compare Maximum allowed version string.
     */
    static void maxVersion(const std::string& compare);

    /**
     * @brief Throws unless current version exactly matches `compare`.
     * @param compare Required exact version string.
     */
    static void exactVersion(const std::string& compare);

    /** @brief Registers Python bindings for version helpers. */
    static void setup_python();

    /** @brief Returns major version component. */
    static uint32_t getMajor();
    /** @brief Returns minor version component. */
    static uint32_t getMinor();
    /** @brief Returns maintenance/patch version component. */
    static uint32_t getMaint();
    /** @brief Returns development/build component. */
    static uint32_t getDevel();

    /** @brief Sleep helper for testing/debug timing. */
    static void sleep(uint32_t seconds);
    /** @brief Microsecond sleep helper for testing/debug timing. */
    static void usleep(uint32_t useconds);

    /** @brief Returns Python runtime version string. */
    static std::string pythonVersion();
};
}  // namespace rogue

#endif
