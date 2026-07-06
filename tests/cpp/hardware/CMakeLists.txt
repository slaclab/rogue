add_library(rogue-cpp-axi-stream-dma-fake-driver SHARED
   fake_axi_dma_driver.cpp
)

target_include_directories(rogue-cpp-axi-stream-dma-fake-driver
   PRIVATE
      ${CMAKE_SOURCE_DIR}/include
      ${CMAKE_CURRENT_LIST_DIR}
)

target_link_libraries(rogue-cpp-axi-stream-dma-fake-driver
   PRIVATE
      ${CMAKE_DL_LIBS}
)

rogue_add_cpp_test(rogue-cpp-axi-stream-dma-lifecycle
   SOURCES
      test_axi_stream_dma_lifecycle.cpp
   LABELS
      cpp-core
      no-python
)

add_dependencies(rogue-cpp-axi-stream-dma-lifecycle rogue-cpp-axi-stream-dma-fake-driver)

set(_rogue_fake_axi_dma_env
   "MPLCONFIGDIR=${CMAKE_BINARY_DIR}/tests/cpp/mplconfig"
   "ROGUE_FAKE_AXI_DMA_DRIVER_LIB=$<TARGET_FILE:rogue-cpp-axi-stream-dma-fake-driver>"
)

if (APPLE)
   set_tests_properties(rogue-cpp-axi-stream-dma-lifecycle PROPERTIES
      DISABLED TRUE
   )
else()
   list(APPEND _rogue_fake_axi_dma_env
      "LD_PRELOAD=$<TARGET_FILE:rogue-cpp-axi-stream-dma-fake-driver>"
   )
endif()

set_tests_properties(rogue-cpp-axi-stream-dma-lifecycle PROPERTIES
   ENVIRONMENT "${_rogue_fake_axi_dma_env}"
   TIMEOUT 10
)
