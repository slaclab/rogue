# Hardware-class tests. The AxiStreamDma zero-copy lifetime test drives a real
# AxiStreamDma against an LD_PRELOAD shim that fakes the aes-stream-driver
# device, so it is Linux-only (ELF symbol interposition). Other platforms skip
# it; rogue-core still builds there.
if (NOT CMAKE_SYSTEM_NAME STREQUAL "Linux")
   return()
endif()

# Test-only fake-driver shim, injected via LD_PRELOAD (never linked into rogue).
add_library(rogue-cpp-fake-dma-preload MODULE support/fake_dma_preload.c)
target_link_libraries(rogue-cpp-fake-dma-preload PRIVATE ${CMAKE_DL_LIBS} pthread)

rogue_add_cpp_test(rogue-cpp-hardware-axi-stream-dma-zerocopy-lifetime
   SOURCES   test_axi_stream_dma_zerocopy_lifetime.cpp
   LABELS    cpp-hardware no-python
   LIBRARIES ${CMAKE_DL_LIBS})

# Ensure the shim is built whenever the test is built.
add_dependencies(rogue-cpp-hardware-axi-stream-dma-zerocopy-lifetime
                 rogue-cpp-fake-dma-preload)

# rogue_add_cpp_test() sets ENVIRONMENT=MPLCONFIGDIR; re-set it here to also
# inject the fake-driver shim. The generator expression resolves to the built
# shim's absolute path.
set_tests_properties(rogue-cpp-hardware-axi-stream-dma-zerocopy-lifetime PROPERTIES
   ENVIRONMENT "MPLCONFIGDIR=${CMAKE_BINARY_DIR}/tests/cpp/mplconfig;LD_PRELOAD=$<TARGET_FILE:rogue-cpp-fake-dma-preload>")
