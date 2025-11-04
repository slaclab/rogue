#!/bin/bash

set -e

SCRIPT_DIR=$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")

cd ${SCRIPT_DIR}/..; python -m compileall -f ./python/
cd ${SCRIPT_DIR}/..; flake8 --count ./python/
cd ${SCRIPT_DIR}/..; python -m compileall -f ./tests
cd ${SCRIPT_DIR}/..; flake8 --count ./tests/

cd ${SCRIPT_DIR}/..; find . -name '*.h' -o -name '*.cpp' | grep -v build | xargs cpplint

