/**
 * ----------------------------------------------------------------------------
 * Company    : SLAC National Accelerator Laboratory
 * ----------------------------------------------------------------------------
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
#include "rogue/Directives.h"

#include <stdint.h>

#include <atomic>
#include <condition_variable>
#include <map>
#include <memory>
#include <mutex>
#include <string>
#include <thread>

#include "rogue/interfaces/stream/Master.h"

namespace rogue {
namespace utilities {
namespace fileio {

/**
 * @brief Reads Rogue stream data files and emits frames on stream master interface.
 *
 * @details
 * `StreamReader` opens a file (or indexed file sequence) created by Rogue file
 * writer utilities, parses frame headers/metadata, reconstructs stream frames,
 * and forwards them downstream via `sendFrame()`.
 *
 * File sequence behavior:
 * - If opened on a filename ending in `.1`, the reader attempts `.2`, `.3`, ...
 *   automatically as each file completes.
 * - Otherwise only the specified file is read.
 *
 * Read activity runs in a background thread while `isActive()` is true.
 */
class StreamReader : public rogue::interfaces::stream::Master {
    // Base file name for indexed-file mode.
    std::string baseName_;

    int32_t fd_ = -1;

    // Current file index in indexed-file mode.
    uint32_t fdIdx_ = 0;

    // True while read thread is actively processing file data.
    bool active_ = false;

    //! \cond INTERNAL
  protected:
    std::thread* readThread_ = nullptr;
    std::atomic<bool> threadEn_{false};
    //! \endcond

  private:
    // Worker thread entry point.
    void runThread();

    // Open next indexed file in sequence.
    bool nextFile();

    // Internal close helper.
    void intClose();

    // Condition signaled when activity state changes.
    std::condition_variable cond_;

    // Mutex for file/thread/activity state.
    std::mutex mtx_;

  public:
    /**
     * @brief Creates a stream reader instance.
     *
     * @details
     * This static factory is the preferred construction path when the object
     * is shared across Rogue graph connections or exposed to Python.
     * It returns `std::shared_ptr` ownership compatible with Rogue pointer typedefs.
     *
     * @return Shared pointer to the created reader.
     */
    static std::shared_ptr<rogue::utilities::fileio::StreamReader> create();

    /** @brief Registers Python bindings for this class. */
    static void setup_python();

    /**
     * @brief Constructs a stream reader instance.
     *
     * @details
     * This constructor is a low-level C++ allocation path.
     * Prefer `create()` when shared ownership or Python exposure is required.
     */
    StreamReader();

    /** @brief Destroys stream reader and closes active file/thread. */
    ~StreamReader();

    /**
     * @brief Opens a file and starts background read processing.
     *
     * @param file Input data filename.
     */
    void open(std::string file);

    /**
     * @brief Stops read thread and closes active file immediately.
     */
    void close();

    /**
     * @brief Returns whether a file descriptor is currently open.
     *
     * @return `true` if file is open; otherwise `false`.
     */
    bool isOpen();

    /**
     * @brief Waits for read activity to complete, then closes file/thread.
     */
    void closeWait();

    /**
     * @brief Returns read activity state.
     *
     * @return `true` while background reader is active.
     */
    bool isActive();
};

// Convenience
typedef std::shared_ptr<rogue::utilities::fileio::StreamReader> StreamReaderPtr;
}  // namespace fileio
}  // namespace utilities
}  // namespace rogue
#endif
