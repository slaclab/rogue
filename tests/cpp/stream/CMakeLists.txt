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

# Needs the Python runtime: the regression only reproduces when the queued frame
# carries a Boost.Python deleter, which a C++-allocated frame never does.
# Isolated in its own binary because an unpatched library aborts the interpreter.
if (NOT NO_PYTHON)
   rogue_add_cpp_test(rogue-cpp-stream-fifo-nocopy-python-frame-release
      SOURCES
         test_fifo_nocopy_python_frame_release.cpp
      LABELS
         cpp-core
         requires-python
   )

   set_tests_properties(rogue-cpp-stream-fifo-nocopy-python-frame-release
                        PROPERTIES TIMEOUT 30)
endif()
