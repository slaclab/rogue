# Each test finalizes the embedded interpreter, and an unpatched library faults
# on the ZMQ message that follows, so they cannot share a binary.
rogue_add_cpp_test(rogue-cpp-interfaces-zmq-client-after-finalize
   SOURCES
      test_zmq_client_after_finalize.cpp
   LABELS
      cpp-core
      requires-python
)
set_tests_properties(rogue-cpp-interfaces-zmq-client-after-finalize PROPERTIES TIMEOUT 30)

rogue_add_cpp_test(rogue-cpp-interfaces-zmq-server-after-finalize
   SOURCES
      test_zmq_server_after_finalize.cpp
   LABELS
      cpp-core
      requires-python
)
set_tests_properties(rogue-cpp-interfaces-zmq-server-after-finalize PROPERTIES TIMEOUT 30)
