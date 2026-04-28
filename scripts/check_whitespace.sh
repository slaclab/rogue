#!/bin/bash
# ----------------------------------------------------------------------------
# Fails if any tracked *.cpp, *.h, or *.py file (except the vendored
# doctest.h) has trailing whitespace or tab indentation. Invoked by the
# full_build_test job in .github/workflows/rogue_ci.yml.
# ----------------------------------------------------------------------------

set -e

if git ls-files -z -- '*.cpp' '*.h' '*.py' ':(exclude)tests/cpp/vendor/doctest/doctest.h' \
    | xargs -0 -r grep -nI '[[:blank:]]$'; then
    echo "Error: Trailing whitespace found in the repository!"
    exit 1
fi

if git ls-files -z -- '*.cpp' '*.h' '*.py' ':(exclude)tests/cpp/vendor/doctest/doctest.h' \
    | xargs -0 -r grep -nI $'\t'; then
    echo "Error: Tab characters found in the repository! Please use spaces for indentation."
    exit 1
fi
