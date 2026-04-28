#!/bin/bash
# ----------------------------------------------------------------------------
# System apt packages shared by full_build_test and small_build_test jobs in
# .github/workflows/rogue_ci.yml. perf_test uses a narrower package set and
# does not source this script.
# ----------------------------------------------------------------------------

set -e

sudo apt-get update
sudo apt-get install -y \
    libzmq3-dev \
    libboost-all-dev \
    bzip2 \
    libbz2-dev \
    libibverbs-dev \
    rdma-core
