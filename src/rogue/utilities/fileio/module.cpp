/**
 * ----------------------------------------------------------------------------
 * Company    : SLAC National Accelerator Laboratory
 * ----------------------------------------------------------------------------
 * Description:
 * Python Module For Stream Interface
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

#include "rogue/utilities/fileio/module.h"

#include <boost/python.hpp>

#include "rogue/utilities/fileio/LegacyStreamReader.h"
#include "rogue/utilities/fileio/LegacyStreamWriter.h"
#include "rogue/utilities/fileio/StreamReader.h"
#include "rogue/utilities/fileio/StreamWriter.h"
#include "rogue/utilities/fileio/StreamWriterChannel.h"

namespace bp  = boost::python;
namespace ruf = rogue::utilities::fileio;

void ruf::setup_module() {
    // map the IO namespace to a sub-module
    bp::object module(bp::handle<>(bp::borrowed(PyImport_AddModule("rogue.utilities.fileio"))));

    // make "from mypackage import class1" work
    bp::scope().attr("fileio") = module;

    // set the current scope to the new sub-module
    bp::scope io_scope = module;

    ruf::StreamReader::setup_python();
    ruf::LegacyStreamReader::setup_python();
    ruf::StreamWriter::setup_python();
    ruf::LegacyStreamWriter::setup_python();
    ruf::StreamWriterChannel::setup_python();
}
