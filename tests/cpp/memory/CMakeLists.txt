rogue_add_cpp_test(rogue-cpp-memory-bits
   SOURCES
      test_memory_bits.cpp
   LABELS
      cpp-core
      no-python
)

rogue_add_cpp_test(rogue-cpp-memory-transaction-block
   SOURCES
      test_transaction_block.cpp
   LABELS
      cpp-core
      no-python
)

rogue_add_cpp_test(rogue-cpp-memory-variable
   SOURCES
      test_variable.cpp
   LABELS
      cpp-core
      no-python
)

rogue_add_cpp_test(rogue-cpp-memory-tcpserver-send-failure-recovery
   SOURCES
      test_tcpserver_send_failure_recovery.cpp
   LABELS
      cpp-core
      no-python
)
set_tests_properties(rogue-cpp-memory-tcpserver-send-failure-recovery PROPERTIES
   TIMEOUT 10
)

# Finalizes the embedded interpreter, and an unpatched library faults on the
# transaction that follows, so it cannot share a binary.
if (NOT NO_PYTHON)
   rogue_add_cpp_test(rogue-cpp-memory-python-slave-after-finalize
      SOURCES
         test_python_slave_after_finalize.cpp
      LABELS
         cpp-core
         requires-python
   )
   set_tests_properties(rogue-cpp-memory-python-slave-after-finalize PROPERTIES
      TIMEOUT 30
   )
endif()
