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
#include "rogue/Directives.h"

#include "rogue/Logging.h"
#include "rogue/ScopedGil.h"

#include <inttypes.h>
#include <stdarg.h>
#include <sys/time.h>
#include <unistd.h>

#include <cstdio>
#include <cstring>
#include <memory>
#include <string>
#include <vector>

#if defined(__linux__)
    #include <sys/syscall.h>
#elif defined(__APPLE__) && defined(__MACH__)
    #include <pthread.h>
#endif

#ifndef NO_PYTHON
    #include <boost/python.hpp>
namespace bp = boost::python;
#endif

const uint32_t rogue::Logging::Critical;
const uint32_t rogue::Logging::Error;
const uint32_t rogue::Logging::Thread;
const uint32_t rogue::Logging::Warning;
const uint32_t rogue::Logging::Info;
const uint32_t rogue::Logging::Debug;

// Default Logging level Is Error
uint32_t rogue::Logging::gblLevel_ = rogue::Logging::Error;

// Logging level lock
std::mutex rogue::Logging::levelMtx_;

// Filter list
std::vector<rogue::LogFilter*> rogue::Logging::filters_;

// Active loggers
std::vector<rogue::Logging*> rogue::Logging::loggers_;

// Python forwarding enable
bool rogue::Logging::forwardPython_ = false;

// Crate logger
rogue::LoggingPtr rogue::Logging::create(const std::string& name, bool quiet) {
    rogue::LoggingPtr log = std::make_shared<rogue::Logging>(name, quiet);
    return log;
}

std::string rogue::Logging::normalizeName(const std::string& name) {
    if (name.rfind("pyrogue.", 0) == 0) return name;
    if (name == "pyrogue") return name;
    return "pyrogue." + name;
}

rogue::Logging::Logging(const std::string& name, bool quiet) {
    name_ = normalizeName(name);

    levelMtx_.lock();
    updateLevelLocked();
    loggers_.push_back(this);
    levelMtx_.unlock();

    if (!quiet) warning("Starting logger with level = %" PRIu32, level_.load());
}

rogue::Logging::~Logging() {
    std::vector<rogue::Logging*>::iterator it;

    levelMtx_.lock();
    for (it = loggers_.begin(); it < loggers_.end(); ++it) {
        if (*it == this) {
            loggers_.erase(it);
            break;
        }
    }
    levelMtx_.unlock();
}

void rogue::Logging::updateLevelLocked() {
    std::vector<rogue::LogFilter*>::iterator it;
    uint32_t level = gblLevel_;

    for (it = filters_.begin(); it < filters_.end(); ++it) {
        if (name_.find((*it)->name_) == 0) {
            if ((*it)->level_ < level) level = (*it)->level_;
        }
    }

    level_.store(level);
}

void rogue::Logging::setLevel(uint32_t level) {
    std::vector<rogue::Logging*>::iterator it;

    levelMtx_.lock();
    gblLevel_ = level;
    for (it = loggers_.begin(); it < loggers_.end(); ++it) (*it)->updateLevelLocked();
    levelMtx_.unlock();
}

void rogue::Logging::setFilter(const std::string& name, uint32_t level) {
    std::vector<rogue::Logging*>::iterator it;

    levelMtx_.lock();

    rogue::LogFilter* flt = new rogue::LogFilter(normalizeName(name), level);

    filters_.push_back(flt);

    for (it = loggers_.begin(); it < loggers_.end(); ++it) (*it)->updateLevelLocked();

    levelMtx_.unlock();
}

void rogue::Logging::setForwardPython(bool enable) {
    levelMtx_.lock();
    forwardPython_ = enable;
    levelMtx_.unlock();
}

bool rogue::Logging::forwardPython() {
    bool enable;
    levelMtx_.lock();
    enable = forwardPython_;
    levelMtx_.unlock();
    return enable;
}

void rogue::Logging::intLog(uint32_t level, const char* fmt, va_list args) {
    if (level < level_.load()) return;

    struct timeval tme;
    char buffer[1000];
    vsnprintf(buffer, sizeof(buffer), fmt, args);
    gettimeofday(&tme, NULL);
    printf("%" PRIi64 ".%06" PRIi64 ":%s: %s\n",
           static_cast<int64_t>(tme.tv_sec),
           static_cast<int64_t>(tme.tv_usec),
           name_.c_str(),
           buffer);

#ifndef NO_PYTHON
    if (forwardPython()) {
        rogue::ScopedGil gil;
        bp::object logging = bp::import("logging");
        bp::object logger  = logging.attr("getLogger")(name_);
        logger.attr("log")(level, buffer);
    }
#endif
}

void rogue::Logging::log(uint32_t level, const char* fmt, ...) {
    va_list arg;
    va_start(arg, fmt);
    intLog(level, fmt, arg);
    va_end(arg);
}

void rogue::Logging::critical(const char* fmt, ...) {
    va_list arg;
    va_start(arg, fmt);
    intLog(rogue::Logging::Critical, fmt, arg);
    va_end(arg);
}

void rogue::Logging::error(const char* fmt, ...) {
    va_list arg;
    va_start(arg, fmt);
    intLog(rogue::Logging::Error, fmt, arg);
    va_end(arg);
}

void rogue::Logging::warning(const char* fmt, ...) {
    va_list arg;
    va_start(arg, fmt);
    intLog(rogue::Logging::Warning, fmt, arg);
    va_end(arg);
}

void rogue::Logging::info(const char* fmt, ...) {
    va_list arg;
    va_start(arg, fmt);
    intLog(rogue::Logging::Info, fmt, arg);
    va_end(arg);
}

void rogue::Logging::debug(const char* fmt, ...) {
    va_list arg;
    va_start(arg, fmt);
    intLog(rogue::Logging::Debug, fmt, arg);
    va_end(arg);
}

void rogue::Logging::logThreadId() {
    uint32_t tid;

#if defined(__linux__)
    tid = syscall(SYS_gettid);
#elif defined(__APPLE__) && defined(__MACH__)
    uint64_t tid64;
    pthread_threadid_np(NULL, &tid64);
    tid = static_cast<uint32_t>(tid64);
#else
    tid = 0;
#endif

    this->log(Thread, "PID=%" PRIu32 ", TID=%" PRIu32, getpid(), tid);
}

const std::string& rogue::Logging::name() const {
    return name_;
}

void rogue::Logging::setup_python() {
#ifndef NO_PYTHON
    bp::class_<rogue::Logging, rogue::LoggingPtr, boost::noncopyable>("Logging", bp::no_init)
        .def("setLevel", &rogue::Logging::setLevel)
        .staticmethod("setLevel")
        .def("setFilter", &rogue::Logging::setFilter)
        .staticmethod("setFilter")
        .def("setForwardPython", &rogue::Logging::setForwardPython)
        .staticmethod("setForwardPython")
        .def("forwardPython", &rogue::Logging::forwardPython)
        .staticmethod("forwardPython")
        .def("normalizeName", &rogue::Logging::normalizeName)
        .staticmethod("normalizeName")
        .def_readonly("Critical", &rogue::Logging::Critical)
        .def_readonly("Error", &rogue::Logging::Error)
        .def_readonly("Thread", &rogue::Logging::Thread)
        .def_readonly("Warning", &rogue::Logging::Warning)
        .def_readonly("Info", &rogue::Logging::Info)
        .def_readonly("Debug", &rogue::Logging::Debug)
        .def("name", &rogue::Logging::name, bp::return_value_policy<bp::copy_const_reference>());
#endif
}
