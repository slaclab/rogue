/**
 *-----------------------------------------------------------------------------
 * Title      : Shared memory functions
 * ----------------------------------------------------------------------------
 * File       : RogueSMemFunctions.h
 * Created    : 2017-06-07
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
#ifndef __ROGUE_SMEM_FUNCTIONS_H__
#define __ROGUE_SMEM_FUNCTIONS_H__

#include <sys/mman.h>
#include <sys/stat.h>
#include <fcntl.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <unistd.h>
#include <sys/types.h>

// Commands
#define ROGUE_CMD_GET   0x1
#define ROGUE_CMD_SET   0x2
#define ROGUE_CMD_EXEC  0x3
#define ROGUE_CMD_VALUE 0x4

// Sizes
#define ROGUE_PATH_STR_SIZE 1024
#define ROGUE_ARG_STR_SIZE  1024
#define ROGUE_NAME_SIZE     256

typedef struct {
   uint8_t cmdReqCount;
   uint8_t cmdAckCount;
   uint8_t cmdType;
   char    name[ROGUE_NAME_SIZE];
   char    path[ROGUE_PATH_STR_SIZE];
   char    arg[ROGUE_ARG_STR_SIZE];
   char    result[ROGUE_ARG_STR_SIZE];

} RogueControlMem;

// Open and map shared memory
inline int32_t rogueSMemControlOpenAndMap ( RogueControlMem **ptr, const char * group ) {
   int32_t  smemFd;
   char     shmName[ROGUE_NAME_SIZE];

   // Generate shared memory
   sprintf(shmName,"rogue_control.%s",group);

   // Attempt to open existing shared memory
   if ( (smemFd = shm_open(shmName, O_RDWR, (S_IRUSR | S_IWUSR | S_IRGRP | S_IWGRP | S_IROTH | S_IWOTH)) ) < 0 ) {

      // Otherwise open and create shared memory
      if ( (smemFd = shm_open(shmName, (O_CREAT | O_RDWR), (S_IRUSR | S_IWUSR | S_IRGRP | S_IWGRP | S_IROTH | S_IWOTH)) ) < 0 ) return(-1);

      // Force permissions regardless of umask
      fchmod(smemFd, (S_IRUSR | S_IWUSR | S_IRGRP | S_IWGRP | S_IROTH | S_IWOTH));
    
      // Set the size of the shared memory segment
      ftruncate(smemFd, sizeof(RogueControlMem));
   }

   // Map the shared memory
   if((*ptr = (RogueControlMem *)mmap(0, sizeof(RogueControlMem),
              (PROT_READ | PROT_WRITE), MAP_SHARED, smemFd, 0)) == MAP_FAILED) return(-2);

   // Store name
   strncpy((*ptr)->name,shmName,ROGUE_NAME_SIZE);
   (*ptr)->name[ROGUE_NAME_SIZE-1] = '\0';

   return(smemFd);
}

// Close shared memory
inline void rogueSMemControlClose ( RogueControlMem *ptr ) {
   char shmName[200];

   // Get shared name
   strcpy(shmName,ptr->name);

   // Unlink
   shm_unlink(shmName);
}

// Init data structure, called by rogue
inline void rogueSMemControlInit ( RogueControlMem *ptr ) {
   memset(ptr->path,0,ROGUE_PATH_STR_SIZE);
   memset(ptr->arg,0,ROGUE_ARG_STR_SIZE);
   memset(ptr->result,0,ROGUE_ARG_STR_SIZE);

   ptr->cmdType     = 0;
   ptr->cmdReqCount = 0;
   ptr->cmdAckCount = 0;
}

// Send command
inline void rogueSMemControlReq ( RogueControlMem *ptr, uint8_t cmdType, const char *path, const char *arg ) {
   if ( path != NULL ) {
      strncpy(ptr->path,path,ROGUE_PATH_STR_SIZE);
      ptr->path[ROGUE_PATH_STR_SIZE-1] = '\0';
   }
   if ( arg != NULL ) {
      strncpy(ptr->arg,arg,ROGUE_ARG_STR_SIZE);
      ptr->path[ROGUE_ARG_STR_SIZE-1] = '\0';
   }
   memset(ptr->result,0,ROGUE_ARG_STR_SIZE);
   ptr->cmdType = cmdType;
 
   ptr->cmdReqCount++;
}

// Check for pending command
inline int32_t rogueSMemControlReqCheck ( RogueControlMem *ptr, uint8_t *cmdType, char **path, char **arg ) {
   if ( ptr->cmdReqCount == ptr->cmdAckCount ) return(0);
   else {
      ptr->path[ROGUE_PATH_STR_SIZE-1] = '\0';
      ptr->arg[ROGUE_ARG_STR_SIZE-1] = '\0';

      *cmdType = ptr->cmdType;
      *path    = ptr->path;
      *arg     = ptr->arg;
      return(1);
   }
}

// Command ack
inline void rogueSMemControlAck ( RogueControlMem *ptr, const char *result ) {
   if ( result != NULL ) {
      strncpy(ptr->result,result,ROGUE_ARG_STR_SIZE);
      ptr->result[ROGUE_ARG_STR_SIZE-1] = '\0';
   }
   ptr->cmdAckCount = ptr->cmdReqCount;
}

// Wait for ack
inline int32_t rogueSMemControlAckCheck ( RogueControlMem *ptr, char *result ) {
   if ( ptr->cmdReqCount != ptr->cmdAckCount ) return(0);
   else { 
      if ( result != NULL ) {
         ptr->result[ROGUE_ARG_STR_SIZE-1] = '\0';
         strncpy(result,ptr->result,ROGUE_ARG_STR_SIZE);
      }
      return(1);
   }
}

#endif

