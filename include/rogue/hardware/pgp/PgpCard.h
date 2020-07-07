/**
 *-----------------------------------------------------------------------------
 * Title      : PGP Card Class
 * ----------------------------------------------------------------------------
 * Description:
 * PGP Card Class
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
#ifndef __ROGUE_HARDWARE_PGP_PGP_CARD_H__
#define __ROGUE_HARDWARE_PGP_PGP_CARD_H__
#include <rogue/interfaces/stream/Master.h>
#include <rogue/interfaces/stream/Slave.h>
#include <rogue/hardware/drivers/PgpDriver.h>
#include <thread>
#include <stdint.h>
#include <memory>


namespace rogue {
   namespace hardware {
      namespace pgp {

         class Info;
         class Status;
         class PciStatus;
         class EvrStatus;
         class EvrControl;

         //! PgpCard Class
         /** This class provides a bridge between the Rogue stream interface and
          * the pgpcard target of the AES Stream Drivers device drivers. This bridge
          * allows Rogue Frames to be sent and received to PGPCard boards. This interface
          * will allocate Frame and Buffer objects using memory mapped DMA buffers
          * or from a local memory pool when zero copy mode is disabled or a Frame
          * with is requested with the zero copy flag set to false.
          */
         class PgpCard : public rogue::interfaces::stream::Master,
                         public rogue::interfaces::stream::Slave {

               //! PgpCard file descriptor
               int32_t  fd_;

               //! Open lane
               uint32_t lane_;

               //! Open VC
               uint32_t vc_;

               //! Number of buffers available for zero copy
               uint32_t bCount_;

               //! Size of buffers in hardware
               uint32_t bSize_;

               //! Timeout for frame transmits
               struct timeval timeout_;

               //! Pointer to zero copy buffers
               void  ** rawBuff_;

               std::thread* thread_;
               bool threadEn_;

               //! Log
               std::shared_ptr<rogue::Logging> log_;

               //! Thread background
               void runThread();

               //! Enable zero copy
               bool zeroCopyEn_;

            public:

               //! Class factory which returns a PgpCardPtr to a newly created PgpCard object
               /** Exposed to Python as rogue.hardware.pgp.PgpCard()
                *
                * The lane and VC fields define the specific PGP lane and virtual channel
                * on that lane that this stream interface will be attached to.
                *
                * @param path Path to device. i.e /dev/pgpcard_0
                * @param lane PGP lane to attach to
                * @param vc   Lane virtual channel to attach to
                * @return PgpCard pointer (PgpCardPtr)
                */
               static std::shared_ptr<rogue::hardware::pgp::PgpCard>
                  create (std::string path, uint32_t lane, uint32_t vc);

               // Setup class in python
               static void setup_python();

               // Creator
               PgpCard(std::string path, uint32_t lane, uint32_t vc);

               // Destructor
               ~PgpCard();

               //! Stop the interface
               void stop();

               //! Set timeout for frame transmits in microseconds
               /** This setting defines how long to wait for the lower level
                * driver to be ready to send data.
                *
                * Exposed to python as SetTimeout()
                * @param timeout Timeout value in microseconds
                */
               void setTimeout(uint32_t timeout);

               //! Enable / disable zero copy
               /** By default the PgpCard class attempts to take advantage of
                * the zero copy mode of the lower level driver if supported. In zero
                * copy mode the Frame Buffer objects are mapped directly to the DMA
                * buffers allocated by the kernel. This allows for direct user space
                * access to the memory which the lower level DMA engines uses.
                * When zero copy mode is disabled a memory buffer will be allocated
                * using the Pool class and the DMA data will be coped to or from this
                * buffer.
                *
                * Exposed to python as setZeroCopyEn()
                * @param state Boolean indicating zero copy mode
                */
               void setZeroCopyEn(bool state);

               //! Get PGP card info.
               /** @return Info object pointer (InfoPtr) containing the PGPCard information
                */
               std::shared_ptr<rogue::hardware::pgp::Info> getInfo();

               //! Get pci status.
               /** @return PciStatus object pointer (PciStatusPtr) containing the PCI status
                */
               std::shared_ptr<rogue::hardware::pgp::PciStatus> getPciStatus();

               //! Get status of open lane.
               /** @return Status object pointer (StatusPtr) for current lane
                */
               std::shared_ptr<rogue::hardware::pgp::Status> getStatus();

               //! Get evr control for open lane.
               /** @return EvrControl object pointer (EvrControlPtr) for current lane
                */
               std::shared_ptr<rogue::hardware::pgp::EvrControl> getEvrControl();

               //! Set evr control for open lane.
               /** @param r EvrControl object pointer (EvrControlPtr) with new configuration
                */
               void setEvrControl(std::shared_ptr<rogue::hardware::pgp::EvrControl> r);

               //! Get evr status for open lane.
               /** @return EvrStatus object pointer (EvrStatusPtr) for current lane
                */
               std::shared_ptr<rogue::hardware::pgp::EvrStatus> getEvrStatus();

               //! Set loopback for open lane
               /** @param enable Enable flag for lane loopback
                */
               void setLoop(bool enable);

               //! Set lane data for open lane
               /** @param data Sideband data value lane
                */
               void setData(uint8_t data);

               //! Send an opcode
               /** @param code Opcode to send on lane
                */
               void sendOpCode(uint8_t code);

               // Generate a Frame. Called from master
               std::shared_ptr<rogue::interfaces::stream::Frame> acceptReq ( uint32_t size, bool zeroCopyEn);

               // Accept a frame from master
               void acceptFrame ( std::shared_ptr<rogue::interfaces::stream::Frame> frame );

               // Return a buffer
               void retBuffer(uint8_t * data, uint32_t meta, uint32_t rawSize);
         };

         //! Alias for using shared pointer as PgpCardPtr
         typedef std::shared_ptr<rogue::hardware::pgp::PgpCard> PgpCardPtr;

      }
   }
};

#endif

