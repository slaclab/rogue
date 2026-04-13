/*
 * Derived from the upstream doctest project:
 *   https://github.com/doctest/doctest
 *
 * This file is a Rogue-local reduced compatibility shim for the native C++
 * test suite. It is not the full upstream doctest single-header distribution.
 *
 * Upstream doctest license:
 *
 * The MIT License (MIT)
 *
 * Copyright (c) 2016-2023 Viktor Kirilov
 *
 * Permission is hereby granted, free of charge, to any person obtaining a copy
 * of this software and associated documentation files (the "Software"), to deal
 * in the Software without restriction, including without limitation the rights
 * to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
 * copies of the Software, and to permit persons to whom the Software is
 * furnished to do so, subject to the following conditions:
 *
 * The above copyright notice and this permission notice shall be included in
 * all copies or substantial portions of the Software.
 *
 * THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
 * IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
 * FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
 * AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
 * LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
 * OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
 * THE SOFTWARE.
 */

#ifndef ROGUE_MINI_DOCTEST_H
#define ROGUE_MINI_DOCTEST_H

#include <exception>
#include <functional>
#include <iostream>
#include <sstream>
#include <stdexcept>
#include <string>
#include <type_traits>
#include <vector>

namespace doctest {

using TestFunction = void (*)();

struct TestCaseData {
    const char* name;
    const char* file;
    int line;
    TestFunction function;
};

inline std::vector<TestCaseData>& registry() {
    static std::vector<TestCaseData> tests;
    return tests;
}

class Registrator {
  public:
    Registrator(const char* name, const char* file, int line, TestFunction function) {
        registry().push_back({name, file, line, function});
    }
};

class AssertionFailure : public std::runtime_error {
  public:
    explicit AssertionFailure(const std::string& message) : std::runtime_error(message) {}
};

struct TestRunState {
    int assertions = 0;
    int failures   = 0;
};

inline TestRunState*& activeState() {
    static TestRunState* state = nullptr;
    return state;
}

inline std::string makeLocation(const char* file, int line) {
    std::ostringstream oss;
    oss << file << ":" << line;
    return oss.str();
}

template <typename T>
inline std::string stringify(const T& value) {
    std::ostringstream oss;
    oss << value;
    return oss.str();
}

template <typename T>
inline std::string stringify(const std::vector<T>& values) {
    std::ostringstream oss;
    oss << "[";
    for (size_t idx = 0; idx < values.size(); ++idx) {
        if (idx != 0) oss << ", ";
        oss << stringify(values[idx]);
    }
    oss << "]";
    return oss.str();
}

inline std::string stringify(const std::string& value) {
    return "\"" + value + "\"";
}

inline std::string stringify(const char* value) {
    return value == nullptr ? "nullptr" : "\"" + std::string(value) + "\"";
}

inline void failCheck(const char* file,
                      int line,
                      const std::string& expression,
                      bool fatal,
                      const std::string& message = std::string()) {
    TestRunState* state = activeState();
    if (state != nullptr) {
        state->assertions += 1;
        state->failures += 1;
    }

    std::ostringstream oss;
    oss << makeLocation(file, line) << ": assertion failed: " << expression;
    if (!message.empty()) oss << " - " << message;
    if (fatal) throw AssertionFailure(oss.str());
    std::cerr << oss.str() << std::endl;
}

template <typename Lhs, typename Rhs>
inline void checkBinary(const Lhs& lhs,
                        const Rhs& rhs,
                        const char* lhsExpr,
                        const char* rhsExpr,
                        const char* op,
                        bool result,
                        const char* file,
                        int line,
                        bool fatal) {
    TestRunState* state = activeState();
    if (state != nullptr) state->assertions += 1;
    if (result) return;

    if (state != nullptr) state->failures += 1;

    std::ostringstream oss;
    oss << makeLocation(file, line) << ": assertion failed: (" << lhsExpr << " " << op << " " << rhsExpr << ")";
    oss << " with " << stringify(lhs) << " vs " << stringify(rhs);

    if (fatal) throw AssertionFailure(oss.str());
    std::cerr << oss.str() << std::endl;
}

class Context {
  public:
    explicit Context(int argc = 0, char** argv = nullptr) : argc_(argc), argv_(argv) {}

    int run() {
        bool listTests = false;
        bool help      = false;

        for (int i = 1; i < argc_; ++i) {
            std::string arg = argv_[i];
            if (arg == "--list-test-cases" || arg == "--ltc") listTests = true;
            if (arg == "--help" || arg == "-h" || arg == "-?") help = true;
        }

        if (help) {
            std::cout << "Usage: " << (argc_ > 0 ? argv_[0] : "test") << " [--list-test-cases]" << std::endl;
            return 0;
        }

        if (listTests) {
            for (const auto& test : registry()) std::cout << test.name << std::endl;
            return 0;
        }

        int failedTests = 0;
        int totalTests  = 0;

        for (const auto& test : registry()) {
            totalTests += 1;
            TestRunState state;
            activeState() = &state;

            try {
                test.function();
            } catch (const AssertionFailure& error) {
                std::cerr << error.what() << std::endl;
            } catch (const std::exception& error) {
                state.failures += 1;
                std::cerr << makeLocation(test.file, test.line) << ": unexpected exception: " << error.what() << std::endl;
            } catch (...) {
                state.failures += 1;
                std::cerr << makeLocation(test.file, test.line) << ": unexpected non-standard exception" << std::endl;
            }

            activeState() = nullptr;

            if (state.failures != 0) {
                failedTests += 1;
                std::cerr << "[failed] " << test.name << " (" << state.failures << " failure";
                if (state.failures != 1) std::cerr << "s";
                std::cerr << ")" << std::endl;
            }
        }

        if (failedTests == 0) {
            std::cout << "[pass] " << totalTests << " test case";
            if (totalTests != 1) std::cout << "s";
            std::cout << std::endl;
        }
        return failedTests == 0 ? 0 : 1;
    }

  private:
    int argc_;
    char** argv_;
};

}  // namespace doctest

#define DOCTEST_DETAIL_CAT_IMPL(lhs, rhs) lhs##rhs
#define DOCTEST_DETAIL_CAT(lhs, rhs) DOCTEST_DETAIL_CAT_IMPL(lhs, rhs)
#define DOCTEST_DETAIL_MAKE_MESSAGE(msg)                                                           \
    ([&]() {                                                                                        \
        std::ostringstream doctest_oss;                                                            \
        doctest_oss << msg;                                                                        \
        return doctest_oss.str();                                                                  \
    }())

#define TEST_CASE(name)                                                                            \
    static void DOCTEST_DETAIL_CAT(doctest_case_, __LINE__)();                                     \
    static ::doctest::Registrator DOCTEST_DETAIL_CAT(doctest_registrar_, __LINE__)(               \
        name, __FILE__, __LINE__, &DOCTEST_DETAIL_CAT(doctest_case_, __LINE__));                  \
    static void DOCTEST_DETAIL_CAT(doctest_case_, __LINE__)()

#define CHECK(expr)                                                                                \
    do {                                                                                            \
        if (!(expr)) ::doctest::failCheck(__FILE__, __LINE__, #expr, false);                       \
        else if (::doctest::activeState() != nullptr) ::doctest::activeState()->assertions += 1;   \
    } while (0)

#define REQUIRE(expr)                                                                              \
    do {                                                                                            \
        if (!(expr)) ::doctest::failCheck(__FILE__, __LINE__, #expr, true);                        \
        else if (::doctest::activeState() != nullptr) ::doctest::activeState()->assertions += 1;   \
    } while (0)

#define CHECK_MESSAGE(expr, msg)                                                                   \
    do {                                                                                            \
        if (!(expr)) ::doctest::failCheck(__FILE__, __LINE__, #expr, false, DOCTEST_DETAIL_MAKE_MESSAGE(msg)); \
        else if (::doctest::activeState() != nullptr) ::doctest::activeState()->assertions += 1;   \
    } while (0)

#define REQUIRE_MESSAGE(expr, msg)                                                                 \
    do {                                                                                            \
        if (!(expr)) ::doctest::failCheck(__FILE__, __LINE__, #expr, true, DOCTEST_DETAIL_MAKE_MESSAGE(msg));  \
        else if (::doctest::activeState() != nullptr) ::doctest::activeState()->assertions += 1;   \
    } while (0)

#define FAIL(msg)                                                                                  \
    do {                                                                                            \
        ::doctest::failCheck(__FILE__, __LINE__, "FAIL", true, DOCTEST_DETAIL_MAKE_MESSAGE(msg));  \
    } while (0)

#define CHECK_FALSE(expr) CHECK(!(expr))
#define REQUIRE_FALSE(expr) REQUIRE(!(expr))

#define CHECK_EQ(lhs, rhs)                                                                         \
    do {                                                                                            \
        const auto& doctest_lhs = (lhs);                                                            \
        const auto& doctest_rhs = (rhs);                                                            \
        ::doctest::checkBinary(                                                                     \
            doctest_lhs, doctest_rhs, #lhs, #rhs, "==", doctest_lhs == doctest_rhs, __FILE__, __LINE__, false); \
    } while (0)

#define REQUIRE_EQ(lhs, rhs)                                                                       \
    do {                                                                                            \
        const auto& doctest_lhs = (lhs);                                                            \
        const auto& doctest_rhs = (rhs);                                                            \
        ::doctest::checkBinary(                                                                     \
            doctest_lhs, doctest_rhs, #lhs, #rhs, "==", doctest_lhs == doctest_rhs, __FILE__, __LINE__, true); \
    } while (0)

#define CHECK_NE(lhs, rhs)                                                                         \
    do {                                                                                            \
        const auto& doctest_lhs = (lhs);                                                            \
        const auto& doctest_rhs = (rhs);                                                            \
        ::doctest::checkBinary(                                                                     \
            doctest_lhs, doctest_rhs, #lhs, #rhs, "!=", doctest_lhs != doctest_rhs, __FILE__, __LINE__, false); \
    } while (0)

#define REQUIRE_NE(lhs, rhs)                                                                       \
    do {                                                                                            \
        const auto& doctest_lhs = (lhs);                                                            \
        const auto& doctest_rhs = (rhs);                                                            \
        ::doctest::checkBinary(                                                                     \
            doctest_lhs, doctest_rhs, #lhs, #rhs, "!=", doctest_lhs != doctest_rhs, __FILE__, __LINE__, true); \
    } while (0)

#define CHECK_GE(lhs, rhs)                                                                         \
    do {                                                                                            \
        const auto& doctest_lhs = (lhs);                                                            \
        const auto& doctest_rhs = (rhs);                                                            \
        ::doctest::checkBinary(                                                                     \
            doctest_lhs, doctest_rhs, #lhs, #rhs, ">=", doctest_lhs >= doctest_rhs, __FILE__, __LINE__, false); \
    } while (0)

#define CHECK_GT(lhs, rhs)                                                                         \
    do {                                                                                            \
        const auto& doctest_lhs = (lhs);                                                            \
        const auto& doctest_rhs = (rhs);                                                            \
        ::doctest::checkBinary(                                                                     \
            doctest_lhs, doctest_rhs, #lhs, #rhs, ">", doctest_lhs > doctest_rhs, __FILE__, __LINE__, false); \
    } while (0)

#define CHECK_LE(lhs, rhs)                                                                         \
    do {                                                                                            \
        const auto& doctest_lhs = (lhs);                                                            \
        const auto& doctest_rhs = (rhs);                                                            \
        ::doctest::checkBinary(                                                                     \
            doctest_lhs, doctest_rhs, #lhs, #rhs, "<=", doctest_lhs <= doctest_rhs, __FILE__, __LINE__, false); \
    } while (0)

#define CHECK_LT(lhs, rhs)                                                                         \
    do {                                                                                            \
        const auto& doctest_lhs = (lhs);                                                            \
        const auto& doctest_rhs = (rhs);                                                            \
        ::doctest::checkBinary(                                                                     \
            doctest_lhs, doctest_rhs, #lhs, #rhs, "<", doctest_lhs < doctest_rhs, __FILE__, __LINE__, false); \
    } while (0)

#define DOCTEST_DETAIL_CHECK_THROWS_IMPL(expr, exception_type, fatal)                             \
    do {                                                                                            \
        bool doctest_threw_expected = false;                                                        \
        if (::doctest::activeState() != nullptr) ::doctest::activeState()->assertions += 1;        \
        try {                                                                                       \
            expr;                                                                                   \
        } catch (const exception_type&) {                                                           \
            doctest_threw_expected = true;                                                          \
        } catch (...) {                                                                             \
        }                                                                                           \
        if (!doctest_threw_expected) {                                                              \
            if (::doctest::activeState() != nullptr) ::doctest::activeState()->failures += 1;      \
            std::ostringstream doctest_oss;                                                         \
            doctest_oss << ::doctest::makeLocation(__FILE__, __LINE__)                              \
                        << ": expected exception " << #exception_type << " from " << #expr;        \
            if (fatal) throw ::doctest::AssertionFailure(doctest_oss.str());                        \
            std::cerr << doctest_oss.str() << std::endl;                                            \
        }                                                                                           \
    } while (0)

#define CHECK_THROWS_AS(expr, exception_type) DOCTEST_DETAIL_CHECK_THROWS_IMPL(expr, exception_type, false)
#define REQUIRE_THROWS_AS(expr, exception_type) DOCTEST_DETAIL_CHECK_THROWS_IMPL(expr, exception_type, true)

#endif
