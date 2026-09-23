# Needs the Python runtime: the regression only reproduces when the queued frame
# carries a Boost.Python deleter, which a C++-allocated frame never does.
# Isolated in its own binary because an unpatched library aborts the interpreter.
rogue_add_cpp_test(rogue-cpp-srp-python-frame-release
   SOURCES
      test_srpv3_python_frame_release.cpp
   LABELS
      cpp-core
      requires-python
)

set_tests_properties(rogue-cpp-srp-python-frame-release PROPERTIES TIMEOUT 30)
