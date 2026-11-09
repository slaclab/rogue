/**
 * ----------------------------------------------------------------------------
 * Company    : SLAC National Accelerator Laboratory
 * ----------------------------------------------------------------------------
 * Description:
 * Native C++ regression coverage for StreamWriter buffer lifetime. Toggling
 * setBufferSize() through a zero size used to leave buffer_ dangling and free
 * it a second time on the next non-zero call, and the destructor never
 * released the buffer that was live at teardown. The double free aborts the
 * process outright; the leak is reported when this binary runs under a leak
 * checker such as AddressSanitizer or Valgrind.
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
#include <stdint.h>

#include "doctest/doctest.h"
#include "rogue/utilities/fileio/StreamWriter.h"

namespace ruf = rogue::utilities::fileio;

TEST_CASE("StreamWriter setBufferSize survives enable, disable, re-enable") {
    ruf::StreamWriter writer;

    writer.setBufferSize(1024);
    writer.setBufferSize(0);
    writer.setBufferSize(2048);

    // Destructor runs with a live 2048-byte buffer and must release it.
}

TEST_CASE("StreamWriter setBufferSize tolerates repeated disable") {
    ruf::StreamWriter writer;

    writer.setBufferSize(512);
    writer.setBufferSize(0);
    writer.setBufferSize(0);
    writer.setBufferSize(512);
    writer.setBufferSize(0);

    // Destructor runs with buffering disabled and nothing to release.
}
