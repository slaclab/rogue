/**
 * ----------------------------------------------------------------------------
 * Company    : SLAC National Accelerator Laboratory
 * ----------------------------------------------------------------------------
 * Description:
 * Logging interface for pyrogue
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
#ifndef __ROGUE_LOGGING_H__
#define __ROGUE_LOGGING_H__
#include "rogue/Directives.h"

#include <stdint.h>

#include <exception>
#include <memory>
#include <mutex>
#include <string>
#include <thread>
#include <vector>

namespace rogue {

/** @brief Per-logger level override filter entry. */
class LogFilter {
  public:
    /** @brief Logger name prefix to match. */
    std::string name_;
    /** @brief Minimum enabled level for matching names. */
    uint32_t level_;

    /**
     * @brief Constructs a filter entry.
     * @param name Logger name prefix.
     * @param level Minimum enabled level.
     */
    LogFilter(std::string name, uint32_t level) {
        name_  = name;
        level_ = level;
    }
};

/**
 * @brief Structured Rogue logging helper.
 *
 * @details
 * Provides leveled logging with global level control and optional name-based
 * filters. Instances are typically created per class/module and reused.
 */
class Logging {
    // Global logging level
    static uint32_t gblLevel_;

    // Logging-level lock
    static std::mutex levelMtx_;

    // Name/level filters
    static std::vector<rogue::LogFilter*> filters_;

    void intLog(uint32_t level, const char* format, va_list args);

    // Local logger level
    uint32_t level_;

    // Logger name
    std::string name_;

  public:
    /** @brief Critical severity level constant. */
    static const uint32_t Critical = 50;
    /** @brief Error severity level constant. */
    static const uint32_t Error    = 40;
    /** @brief Thread-trace severity level constant. */
    static const uint32_t Thread   = 35;
    /** @brief Warning severity level constant. */
    static const uint32_t Warning  = 30;
    /** @brief Informational severity level constant. */
    static const uint32_t Info     = 20;
    /** @brief Debug severity level constant. */
    static const uint32_t Debug    = 10;

    /**
     * @brief Creates a logger instance.
     *
     * @details
     * Parameter semantics are identical to the constructor; see `Logging()`
     * for logger initialization details.
     * This static factory is the preferred construction path when the object
     * is shared across Rogue graph connections or exposed to Python.
     * It returns `std::shared_ptr` ownership compatible with Rogue pointer typedefs.
     *
     * @param name Logger name/category.
     * @param quiet When `true`, suppresses creation banner output.
     * @return Shared logger instance.
     */
    static std::shared_ptr<rogue::Logging> create(const std::string& name, bool quiet = false);

    /**
     * @brief Constructs a logger.
     *
     * @details
     * This constructor is a low-level C++ allocation path.
     * Prefer `create()` when shared ownership or Python exposure is required.
     *
     * @param name Logger name/category.
     * @param quiet When `true`, suppresses creation banner output.
     */
    explicit Logging(const std::string& name, bool quiet = false);
    /** @brief Destroys the logger instance. */
    ~Logging();

    /**
     * @brief Sets the global default logging level.
     * @param level New global level threshold.
     */
    static void setLevel(uint32_t level);

    /**
     * @brief Sets name-based filter level override.
     * @param filter Logger-name prefix to match.
     * @param level Level threshold for matching names.
     */
    static void setFilter(const std::string& filter, uint32_t level);

    /**
     * @brief Normalizes logger names to the emitted Rogue namespace.
     * @param name Logger name or prefix.
     * @return Name prefixed with ``pyrogue.`` when required.
     */
    static std::string normalizeName(const std::string& name);

    /**
     * @brief Emits a formatted log message at a specified level.
     * @param level Severity level.
     * @param fmt `printf`-style format string.
     */
    void log(uint32_t level, const char* fmt, ...);

    /** @brief Emits a formatted message at `Critical` level. */
    void critical(const char* fmt, ...);
    /** @brief Emits a formatted message at `Error` level. */
    void error(const char* fmt, ...);
    /** @brief Emits a formatted message at `Warning` level. */
    void warning(const char* fmt, ...);
    /** @brief Emits a formatted message at `Info` level. */
    void info(const char* fmt, ...);
    /** @brief Emits a formatted message at `Debug` level. */
    void debug(const char* fmt, ...);

    /** @brief Emits the current thread id through this logger. */
    void logThreadId();

    /** @brief Returns the fully-qualified emitted logger name. */
    const std::string& name() const;

    /** @brief Registers Python bindings for `Logging`. */
    static void setup_python();
};

/** @brief Shared pointer alias for `Logging`. */
typedef std::shared_ptr<rogue::Logging> LoggingPtr;
}  // namespace rogue

#endif
