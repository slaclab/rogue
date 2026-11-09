rogue_add_cpp_test(rogue-cpp-utilities-stream-writer-buffer
   SOURCES
      test_stream_writer_buffer.cpp
   LABELS
      cpp-core
      no-python
)

# Isolated in its own binary because an unpatched library aborts the process.
rogue_add_cpp_test(rogue-cpp-utilities-prbs-set-width-while-enabled
   SOURCES
      test_prbs_set_width_while_enabled.cpp
   LABELS
      cpp-core
      no-python
)

set_tests_properties(rogue-cpp-utilities-prbs-set-width-while-enabled PROPERTIES TIMEOUT 30)

rogue_add_cpp_test(rogue-cpp-utilities-stream-reader-close
   SOURCES
      test_stream_reader_close.cpp
   LABELS
      cpp-core
      no-python
)

set_tests_properties(rogue-cpp-utilities-stream-reader-close PROPERTIES TIMEOUT 30)
