file(MAKE_DIRECTORY ${CMAKE_BINARY_DIR}/tests/cpp/mplconfig)

set(ROGUE_CPP_TEST_OUTPUT_DIR ${CMAKE_BINARY_DIR}/tests/cpp)

add_library(rogue-cpp-test-support STATIC
   support/test_main.cpp
)

target_include_directories(rogue-cpp-test-support
   PUBLIC
      ${CMAKE_CURRENT_LIST_DIR}
      ${CMAKE_CURRENT_LIST_DIR}/vendor
)

if (NOT APPLE)
   target_link_libraries(rogue-cpp-test-support PUBLIC rt)
endif()

function(rogue_add_cpp_test target)
   set(options)
   set(oneValueArgs)
   set(multiValueArgs SOURCES LABELS LIBRARIES)
   cmake_parse_arguments(RCT "${options}" "${oneValueArgs}" "${multiValueArgs}" ${ARGN})

   set(rogue_cpp_test_extra_libs ${RCT_LIBRARIES})
   if (NOT NO_PYTHON)
      list(APPEND rogue_cpp_test_extra_libs ${Boost_LIBRARIES} ${Python3_LIBRARIES})
   endif()

   add_executable(${target} ${RCT_SOURCES})
   set_target_properties(${target} PROPERTIES
      RUNTIME_OUTPUT_DIRECTORY ${ROGUE_CPP_TEST_OUTPUT_DIR}
      BUILD_RPATH ${CMAKE_BINARY_DIR}
      SKIP_BUILD_RPATH FALSE
   )

   if ("no-python" IN_LIST RCT_LABELS)
      target_compile_definitions(${target} PRIVATE NO_PYTHON)
   endif()

   target_link_libraries(${target}
      PRIVATE
         rogue-cpp-test-support
         rogue-core-shared
         ${rogue_cpp_test_extra_libs}
   )

   add_test(NAME ${target} COMMAND ${target})
   set_tests_properties(${target} PROPERTIES
      LABELS "cpp;${RCT_LABELS}"
      ENVIRONMENT "MPLCONFIGDIR=${CMAKE_BINARY_DIR}/tests/cpp/mplconfig"
   )
endfunction()

add_subdirectory(core)
add_subdirectory(memory)
add_subdirectory(stream)
add_subdirectory(protocols)

if (NOT NO_PYTHON)
   add_subdirectory(smoke)
   add_subdirectory(protocols)
endif()
