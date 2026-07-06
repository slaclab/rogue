/**
 * ----------------------------------------------------------------------------
 * Company    : SLAC National Accelerator Laboratory
 * ----------------------------------------------------------------------------
 * Description:
 * Test-only fake AxiStreamDma driver syscall interposer.
 * ----------------------------------------------------------------------------
 * This file is part of the rogue software platform. It is subject to
 * the license terms in the LICENSE.txt file found in the top-level directory
 * of this distribution and at:
 *    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
 * No part of the rogue software platform, including this file, may be
 * copied, modified, propagated, or distributed except according to the terms
 * contained in the LICENSE.txt file.
 * ----------------------------------------------------------------------------
 **/
#ifndef ROGUE_TEST_CPP_HARDWARE_FAKE_AXI_DMA_DRIVER_H
#define ROGUE_TEST_CPP_HARDWARE_FAKE_AXI_DMA_DRIVER_H

#include <stdint.h>

extern "C" {

enum RogueFakeAxiDmaBlockOp {
    ROGUE_FAKE_AXI_DMA_BLOCK_NONE              = 0,
    ROGUE_FAKE_AXI_DMA_BLOCK_IOCTL_GET_INDEX   = 1,
    ROGUE_FAKE_AXI_DMA_BLOCK_IOCTL_RET_INDEX   = 2,
    ROGUE_FAKE_AXI_DMA_BLOCK_IOCTL_BUFF_SIZE   = 3,
    ROGUE_FAKE_AXI_DMA_BLOCK_WRITE             = 4,
};

const char* rogue_fake_axi_dma_path_prefix();
void rogue_fake_axi_dma_reset();
void rogue_fake_axi_dma_block_next(RogueFakeAxiDmaBlockOp op);
bool rogue_fake_axi_dma_wait_blocked(uint32_t timeoutMs);
void rogue_fake_axi_dma_release_blocked();
uint32_t rogue_fake_axi_dma_close_count();
uint32_t rogue_fake_axi_dma_munmap_count();
uint32_t rogue_fake_axi_dma_ret_index_count();
bool rogue_fake_axi_dma_close_during_driver_call();

}  // extern "C"

#endif
