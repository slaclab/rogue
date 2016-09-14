/**
 *-----------------------------------------------------------------------------
 * Title      : PGP Card Class
 * ----------------------------------------------------------------------------
 * File       : PgpCard.h
 * Author     : Ryan Herbst, rherbst@slac.stanford.edu
 * Created    : 2016-08-08
 * Last update: 2016-08-08
 * ----------------------------------------------------------------------------
 * Description:
 * PGP Card Class
 * ----------------------------------------------------------------------------
 * This file is part of the rouge software platform. It is subject to 
 * the license terms in the LICENSE.txt file found in the top-level directory 
 * of this distribution and at: 
 *    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html. 
 * No part of the rouge software platform, including this file, may be 
 * copied, modified, propagated, or distributed except according to the terms 
 * contained in the LICENSE.txt file.
 * ----------------------------------------------------------------------------
**/
#include "PgpCard.h"
#include "PgpData.h"

PgpCard::PgpCard() {
   fd_      = -1;
   device_  = "";
   bCount_  = 0;
   bSize_   = 0;
   buffers_ = NULL;
   rawBuff_ = NULL;
}


PgpCard::~PgpCard() {
   this->close();
}


//! Open the device for a specific lane/vc mask with passed read/write permissions
bool PgpCard::openMask ( std::string path, uint32_t mask ) {
   uint32_t x;

   if ( fd_ > 0 ) return(false);

   device_ = path;

   if ( (fd_ = ::open(path.c_str(), O_RDWR)) < 0 ) return(false);

   if ( mask != 0 ) {
      if ( pgpSetMask(fd_,mask) < 0 ) {
         ::close(fd_);
         return(false);
      }
   }

   rawBuff_ = pgpMapDma(fd_,&bCount_,&bSize_);

   if ( rawBuff_ == NULL ) {
      ::close(fd_);
      bCount_  = 0;
      bSize_   = 0;
      fd_      = -1;
      device_  = "";
      buffers_ = NULL;
      rawBuff_ = NULL;
   }
    
   buffers_ = (PgpData **)malloc(sizeof(PgpData*)*bCount_);

   for (x=0; x < bCount_; x++) buffers_[x] = new PgpData(this,x,rawBuff_[x],bSize_);
   return(true);
}


//! Open the device with full read/write access
bool PgpCard::openWo ( std::string path ) {
   return(this->openMask(path,0));
}


//! Open the device for a specific lane/vc with passed read/write permissions
bool PgpCard::open ( std::string path, uint32_t lane, uint32_t vc) {
   if ( lane > MAX_PGP_LANE || vc > MAX_PGP_VC ) return(false);

   uint32_t mask;
   mask = (1 << ((lane*4) +vc));
   return(openMask(path,mask));
}


//! Close the device
void PgpCard::close() {
   uint32_t x;

   if ( fd_ < 0 ) return;

   if ( rawBuff_ != NULL ) pgpUnMapDma(fd_, rawBuff_);
   ::close(fd_);

   for ( x = 0; x < bCount_; x++ ) delete buffers_[x];
   free(buffers_);

   bCount_  = 0;
   bSize_   = 0;
   fd_      = -1;
   device_  = "";
   buffers_ = NULL;
   rawBuff_ = NULL;
}


//! Allocate a buffer for write, with optional timeout in micro seconds
PgpData * PgpCard::getWriteBuffer(uint32_t timeout) {
   int32_t          res;
   fd_set           fds;
   struct timeval   tout;
   struct timeval * tpr;

   if ( fd_ < 0 ) return(NULL);

   // Setup fds for select call
   FD_ZERO(&fds);
   FD_SET(fd_,&fds);

   // Setup select timeout
   if ( timeout > 0 ) {
      tout.tv_sec=timeout / 1000000;
      tout.tv_usec=timeout % 1000000;
      tpr = &tout;
   }
   else tpr = NULL;

   res = select(fd_+1,NULL,&fds,NULL,tpr);

   res = pgpGetIndex(fd_);

   if ( res >= 0 ) return(buffers_[res]); 
   else return(NULL);
}


//! Write
bool PgpCard::write(PgpData *buff) {
   if ( fd_ < 0 ) return(NULL);
   if ( pgpWriteIndex(fd_, buff->getIndex(), buff->size, buff->lane, buff->vc, buff->cont) > 0 ) return(true);
   else return(false);
}


//! Read with optional timeout in microseconds
PgpData * PgpCard::read(uint32_t timeout) {
   int32_t          res;
   fd_set           fds;
   struct timeval   tout;
   struct timeval * tpr;
   uint32_t         index;
   uint32_t         lane; 
   uint32_t         vc; 
   uint32_t         error;
   uint32_t         cont;
   PgpData *        buff;

   if ( fd_ < 0 ) return(NULL);

   // Setup fds for select call
   FD_ZERO(&fds);
   FD_SET(fd_,&fds);

   // Setup select timeout
   if ( timeout > 0 ) {
      tout.tv_sec=timeout / 1000000;
      tout.tv_usec=timeout % 1000000;
      tpr = &tout;
   }
   else tpr = NULL;

   select(fd_+1,&fds,NULL,NULL,tpr);

   res = pgpReadIndex(fd_, &index, &lane, &vc, &error, &cont);

   if ( res <= 0 ) return(NULL);

   buff = buffers_[index]; 

   buff->lane  = lane;
   buff->vc    = vc;
   buff->cont  = cont;
   buff->lane  = lane;
   buff->size  = res;
   buff->error = error;

   return(buff);
}


//! Return buffer
bool PgpCard::retBuffer(PgpData *buff) {
   if ( fd_ < 0 ) return(false);
   pgpRetIndex(fd_,buff->getIndex());
   return(true);
}


//! Get card info. Do not deallocate memory.
struct PgpInfo * PgpCard::getInfo() {
   if ( fd_ < 0 ) return(NULL);
   if ( pgpGetInfo(fd_,&pgpInfo_) == 0 ) return(&pgpInfo_);
   return(NULL);
}


//! Get pci status. Do not deallocate memory.
struct PciStatus * PgpCard::getPciStatus() {
   if ( fd_ < 0 ) return(NULL);
   if ( pgpGetPci(fd_,&pciStatus_) == 0 ) return(&pciStatus_);
   else return(NULL);
}


//! Get lane status. NULL for invalid lane. Do not deallocate memory.
struct PgpStatus * PgpCard::getLaneStatus(uint32_t lane) {
   if ( fd_ < 0 || lane > MAX_PGP_LANE ) return(NULL);
   if ( pgpGetStatus(fd_,lane,&(pgpStatus_[lane])) == 0 ) return(&(pgpStatus_[lane]));
   else return(NULL);
}


//! Get evr control for a lane. NULL for invalid lane. Do not deallocate memory.
struct PgpEvrControl * PgpCard::getEvrControl(uint32_t lane) {
   if ( fd_ < 0 || lane > MAX_PGP_LANE ) return(NULL);
   if ( pgpSetEvrControl(fd_,lane,&(evrControl_[lane])) == 0 ) return(&(evrControl_[lane]));
   else return(NULL);
}


//! Set evr control for a lane. Pass structure returned with getEvrControl.
bool PgpCard::setEvrControl(struct PgpEvrControl *evrControl) {
   if ( fd_ < 0 || evrControl == NULL || evrControl->lane > 8 ) return(false);
   if ( pgpSetEvrControl(fd_,evrControl->lane,&(evrControl_[evrControl->lane])) == 0 ) return(true);
   else return(false);
}


//! Get evr status for a lane. NULL for invalid lane. Do not deallocate memory.
struct PgpEvrStatus * PgpCard::getEvrStatus(uint32_t lane) {
   if ( fd_ < 0 || lane > MAX_PGP_LANE ) return(NULL);
   if ( pgpGetEvrStatus(fd_,lane,&(evrStatus_[lane])) == 0 ) return(&evrStatus_[lane]);
   else return(NULL);
}


//! Set loopback
bool PgpCard::setLoop(uint32_t lane, bool enable) {
   if ( fd_ < 0 ) return(false);
   return(pgpSetLoop(fd_,lane,enable) >= 0);
}


//! Set lane data
bool PgpCard::setData(uint32_t lane, uint8_t data) {
   if ( fd_ < 0 ) return(false);
   return(pgpSetData(fd_,lane,data) >= 0);
}


//! Send an opcode
bool PgpCard::sendOpCode(uint8_t code) {
   if ( fd_ < 0 ) return(false);
   return(pgpSendOpCode(fd_,code) >= 0);
}


