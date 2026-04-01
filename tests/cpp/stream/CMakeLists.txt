rogue_add_cpp_test(rogue-cpp-stream-frame-pool
   SOURCES
      test_frame_pool.cpp
   LABELS
      cpp-core
      no-python
)

rogue_add_cpp_test(rogue-cpp-stream-iterator
   SOURCES
      test_iterator.cpp
   LABELS
      cpp-core
      no-python
)

rogue_add_cpp_test(rogue-cpp-stream-flow-primitives
   SOURCES
      test_fifo_filter_rate_drop.cpp
   LABELS
      cpp-core
      no-python
)
