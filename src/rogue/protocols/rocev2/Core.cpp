/**
 * ----------------------------------------------------------------------------
 * Company    : SLAC National Accelerator Laboratory
 * ----------------------------------------------------------------------------
 * Description:
 *   RoCEv2 Core
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

#include "rogue/protocols/rocev2/Core.h"

#include <infiniband/verbs.h>
#include <stdint.h>

#include <cstring>
#include <string>

#include "rogue/GeneralError.h"

namespace rpr = rogue::protocols::rocev2;

#ifndef NO_PYTHON
    #include <boost/python.hpp>
namespace bp = boost::python;
#endif

//! Creator
rpr::Core::Core(const std::string& deviceName,
                uint8_t            ibPort,
                uint8_t            gidIndex,
                uint32_t           maxPayload)
    : ctx_(nullptr),
      pd_(nullptr),
      deviceName_(deviceName),
      ibPort_(ibPort),
      gidIndex_(gidIndex),
      maxPayload_(maxPayload) {

    log_ = rogue::Logging::create("rocev2.Core");

    // -----------------------------------------------------------------------
    // 1. Find and open the requested ibverbs device
    //    devList is freed on every exit path (success and failure) so a
    //    partial-construction throw never leaks the device list.
    // -----------------------------------------------------------------------
    int numDevices = 0;
    struct ibv_device** devList = ibv_get_device_list(&numDevices);
    if (!devList || numDevices == 0) {
        if (devList) ibv_free_device_list(devList);
        throw(rogue::GeneralError::create("rocev2::Core::Core",
                                          "No RDMA devices found on this host"));
    }

    struct ibv_device* dev = nullptr;
    for (int i = 0; i < numDevices; ++i) {
        if (deviceName_ == ibv_get_device_name(devList[i])) {
            dev = devList[i];
            break;
        }
    }

    if (!dev) {
        ibv_free_device_list(devList);
        throw(rogue::GeneralError::create("rocev2::Core::Core",
                                          "RDMA device '%s' not found",
                                          deviceName_.c_str()));
    }

    ctx_ = ibv_open_device(dev);
    ibv_free_device_list(devList);

    if (!ctx_)
        throw(rogue::GeneralError::create("rocev2::Core::Core",
                                          "Failed to open RDMA device '%s'",
                                          deviceName_.c_str()));

    // -----------------------------------------------------------------------
    // 2. Allocate Protection Domain
    //    On failure we close ctx_ explicitly: the destructor does not run on
    //    a partially-constructed object, so without this the context would
    //    leak.
    // -----------------------------------------------------------------------
    pd_ = ibv_alloc_pd(ctx_);
    if (!pd_) {
        ibv_close_device(ctx_);
        ctx_ = nullptr;
        throw(rogue::GeneralError::create("rocev2::Core::Core",
                                          "Failed to allocate protection domain"));
    }

    log_->info("Opened RoCEv2 device '%s', port %u, GID index %u",
               deviceName_.c_str(), ibPort_, gidIndex_);
}

//! Destructor - releases the protection domain and closes the ibverbs context.
//
// CQ / QP / MR are owned by the derived Server class and are torn down in
// Server::stop() before the inherited Core destructor runs.
rpr::Core::~Core() {
    if (pd_)  ibv_dealloc_pd(pd_);
    if (ctx_) ibv_close_device(ctx_);
}

void rpr::Core::setup_python() {
#ifndef NO_PYTHON
    bp::class_<rpr::Core, rpr::CorePtr, boost::noncopyable>("Core", bp::no_init)
        .def("maxPayload", &rpr::Core::maxPayload);

    // Expose defaults as module-level attributes:
    //   rogue.protocols.rocev2.DefaultMaxPayload
    //   rogue.protocols.rocev2.DefaultRxQueueDepth
    bp::scope().attr("DefaultMaxPayload")   = rpr::DefaultMaxPayload;
    bp::scope().attr("DefaultRxQueueDepth") = rpr::DefaultRxQueueDepth;
#endif
}
