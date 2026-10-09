# Hardware-class tests that run AxiStreamDma against an LD_PRELOAD shim for
# the aes-stream-driver device. ELF symbol interposition is Linux-only; other
# platforms skip this subtree while still building rogue-core.
if (NOT CMAKE_SYSTEM_NAME STREQUAL "Linux")
   return()
endif()

add_library(rogue-cpp-fake-dma-preload MODULE support/fake_dma_preload.c)
target_link_libraries(rogue-cpp-fake-dma-preload PRIVATE ${CMAKE_DL_LIBS} pthread)

set(_rogue_fake_dma_env
   "MPLCONFIGDIR=${CMAKE_BINARY_DIR}/tests/cpp/mplconfig;LD_PRELOAD=$<TARGET_FILE:rogue-cpp-fake-dma-preload>"
)

rogue_add_cpp_test(rogue-cpp-hardware-axi-stream-dma-zerocopy-lifetime
   SOURCES
      test_axi_stream_dma_zerocopy_lifetime.cpp
   LABELS
      cpp-hardware
      no-python
   LIBRARIES
      ${CMAKE_DL_LIBS}
)
add_dependencies(rogue-cpp-hardware-axi-stream-dma-zerocopy-lifetime rogue-cpp-fake-dma-preload)
set_tests_properties(rogue-cpp-hardware-axi-stream-dma-zerocopy-lifetime PROPERTIES
   ENVIRONMENT "${_rogue_fake_dma_env}"
   TIMEOUT 10
)

rogue_add_cpp_test(rogue-cpp-hardware-axi-stream-dma-lifecycle
   SOURCES
      test_axi_stream_dma_lifecycle.cpp
   LABELS
      cpp-hardware
      no-python
   LIBRARIES
      ${CMAKE_DL_LIBS}
)
add_dependencies(rogue-cpp-hardware-axi-stream-dma-lifecycle rogue-cpp-fake-dma-preload)
set_tests_properties(rogue-cpp-hardware-axi-stream-dma-lifecycle PROPERTIES
   ENVIRONMENT "${_rogue_fake_dma_env}"
   TIMEOUT 10
)
