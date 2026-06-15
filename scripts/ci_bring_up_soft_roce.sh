#!/bin/bash
# ----------------------------------------------------------------------------
# Brings up a Soft-RoCE (rxe0) device for CI coverage of the RoCEv2 protocol
# module. Invoked by .github/workflows/rogue_ci.yml with
# `continue-on-error: true` because GHA-hosted runners ship an azure-tuned
# kernel that strips rdma_rxe from linux-modules-extra (confirmed on
# 24.04 / 6.17.0-*-azure and 22.04 / 6.8.0-*-azure). Real ibverbs coverage on
# rxe0 requires a self-hosted runner or larger runner with a generic kernel.
# ----------------------------------------------------------------------------

set -euo pipefail

if ! sudo modprobe rdma_rxe 2>/dev/null; then
    echo "rdma_rxe not in /lib/modules/$(uname -r) — trying linux-modules-extra fallback"
    sudo apt-get update
    sudo apt-get install -y "linux-modules-extra-$(uname -r)"
    sudo modprobe rdma_rxe
fi
IFACE=$(ip -o route get 1.1.1.1 | awk '{print $5; exit}')
echo "Using netdev: ${IFACE}"
sudo rdma link add rxe0 type rxe netdev "${IFACE}"

# Verify device exists; fail-fast if not
ibv_devices | tee /dev/stderr | grep -q rxe0

# Close GID race: poll up to 15 s (30 * 0.5 s) for non-zero GID
for i in $(seq 1 30); do
    if ibv_devinfo -v -d rxe0 2>/dev/null \
         | awk '/GID\[/ {print $NF}' \
         | grep -vE '^(0000:){7}0000$' \
         | grep -q .; then
        echo "rxe0 GID ready after ${i} polls"
        ibv_devinfo -v -d rxe0 | grep -E 'state|GID\['
        exit 0
    fi
    sleep 0.5
done
echo "ERROR: rxe0 GID still all-zero after 15s"
ibv_devinfo -v -d rxe0 || true
exit 1
