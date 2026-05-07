# Regression tests for hardware bridge candidates (plan 02-03).

rogue_add_cpp_test(rogue-cpp-hardware-memmap-raw-thread-audit-repro
   SOURCES
      test_memmap_raw_thread_audit_repro.cpp
   LABELS
      cpp-core
      no-python
)
target_compile_definitions(rogue-cpp-hardware-memmap-raw-thread-audit-repro
   PRIVATE ROGUE_SRC_DIR="${CMAKE_SOURCE_DIR}")

rogue_add_cpp_test(rogue-cpp-hardware-axi-memmap-raw-thread-audit-repro
   SOURCES
      test_axi_memmap_raw_thread_audit_repro.cpp
   LABELS
      cpp-core
      no-python
)
target_compile_definitions(rogue-cpp-hardware-axi-memmap-raw-thread-audit-repro
   PRIVATE ROGUE_SRC_DIR="${CMAKE_SOURCE_DIR}")

rogue_add_cpp_test(rogue-cpp-hardware-axi-stream-dma-raw-thread-audit-repro
   SOURCES
      test_axi_stream_dma_raw_thread_audit_repro.cpp
   LABELS
      cpp-core
      no-python
)
target_compile_definitions(rogue-cpp-hardware-axi-stream-dma-raw-thread-audit-repro
   PRIVATE ROGUE_SRC_DIR="${CMAKE_SOURCE_DIR}")

rogue_add_cpp_test(rogue-cpp-hardware-axi-stream-dma-fd-setsize-audit-repro
   SOURCES
      test_axi_stream_dma_fd_setsize_audit_repro.cpp
   LABELS
      cpp-core
      no-python
)
target_compile_definitions(rogue-cpp-hardware-axi-stream-dma-fd-setsize-audit-repro
   PRIVATE ROGUE_SRC_DIR="${CMAKE_SOURCE_DIR}")

rogue_add_cpp_test(rogue-cpp-hardware-axi-stream-dma-shared-static-race-audit-repro
   SOURCES
      test_axi_stream_dma_shared_static_race_audit_repro.cpp
   LABELS
      cpp-core
      no-python
)
target_compile_definitions(rogue-cpp-hardware-axi-stream-dma-shared-static-race-audit-repro
   PRIVATE ROGUE_SRC_DIR="${CMAKE_SOURCE_DIR}")

rogue_add_cpp_test(rogue-cpp-hardware-axi-stream-dma-disabled-block-audit-repro
   SOURCES
      test_axi_stream_dma_disabled_block_audit_repro.cpp
   LABELS
      cpp-core
      no-python
)
target_compile_definitions(rogue-cpp-hardware-axi-stream-dma-disabled-block-audit-repro
   PRIVATE ROGUE_SRC_DIR="${CMAKE_SOURCE_DIR}")

rogue_add_cpp_test(rogue-cpp-hardware-axi-stream-dma-open-count-audit-repro
   SOURCES
      test_axi_stream_dma_open_count_audit_repro.cpp
   LABELS
      cpp-core
      no-python
)
target_compile_definitions(rogue-cpp-hardware-axi-stream-dma-open-count-audit-repro
   PRIVATE ROGUE_SRC_DIR="${CMAKE_SOURCE_DIR}")

rogue_add_cpp_test(rogue-cpp-hardware-axi-stream-dma-stop-joinable-audit-repro
   SOURCES
      test_axi_stream_dma_stop_joinable_audit_repro.cpp
   LABELS
      cpp-core
      no-python
)
target_compile_definitions(rogue-cpp-hardware-axi-stream-dma-stop-joinable-audit-repro
   PRIVATE ROGUE_SRC_DIR="${CMAKE_SOURCE_DIR}")

rogue_add_cpp_test(rogue-cpp-hardware-axi-stream-dma-open-shared-stale-fd-audit-repro
   SOURCES
      test_axi_stream_dma_open_shared_stale_fd_audit_repro.cpp
   LABELS
      cpp-core
      no-python
)
target_compile_definitions(rogue-cpp-hardware-axi-stream-dma-open-shared-stale-fd-audit-repro
   PRIVATE ROGUE_SRC_DIR="${CMAKE_SOURCE_DIR}")

rogue_add_cpp_test(rogue-cpp-hardware-axi-stream-dma-use-after-stop-audit-repro
   SOURCES
      test_axi_stream_dma_use_after_stop_audit_repro.cpp
   LABELS
      cpp-core
      no-python
)
target_compile_definitions(rogue-cpp-hardware-axi-stream-dma-use-after-stop-audit-repro
   PRIVATE ROGUE_SRC_DIR="${CMAKE_SOURCE_DIR}")

