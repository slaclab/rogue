/**
 *-----------------------------------------------------------------------------
 * Title      : Rogue as a library base class
 * ----------------------------------------------------------------------------
 * File       : LibraryBase.cpp
 * ----------------------------------------------------------------------------
 * Description:
 * Base class for creating a Rogue shared library
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

#include <rogue/LibraryBase.h>
#include <rogue/GeneralError.h>
#include <rogue/interfaces/memory/Constants.h>
#include <stdint.h>
#include <algorithm>
#include <vector>
#include <map>
#include <string>
#include <sstream>
#include <iostream>
#include <fstream>

namespace ris  = rogue::interfaces::stream;
namespace rim  = rogue::interfaces::memory;

rogue::LibraryBasePtr rogue::LibraryBase::create() {
   rogue::LibraryBasePtr ret = std::make_shared<rogue::LibraryBase>();
   return(ret);
}

rogue::LibraryBase::LibraryBase () {
   log_ = rogue::Logging::create("LibraryBase");
}

rogue::LibraryBase::~LibraryBase() { }

//! Add slave memory interface
void rogue::LibraryBase::addMemory (std::string name, rim::SlavePtr slave) {
   memSlaves_[name] = slave;
}

//! Get variable by name
rim::VariablePtr rogue::LibraryBase::getVariable(const std::string & name) {
   return variables_[name];
}

//! Get a map of variables
const std::map<std::string, rim::VariablePtr> & rogue::LibraryBase::getVariableList() {
   return variables_;
}

//! Get block by name
rim::BlockPtr rogue::LibraryBase::getBlock(const std::string & name) {
   return blocks_[name];
}

//! Get a map of blocks
const std::map< std::string, rim::BlockPtr> rogue::LibraryBase::getBlockList() {
   return blocks_;
}

// Parse memory map
void rogue::LibraryBase::parseMemMap (std::string map) {
   std::string line;
   std::string field;
   std::istringstream fStream(map);
   std::vector<std::string> key;

   std::map< std::string, std::vector<rim::VariablePtr> > blockVars;
   std::map< std::string, std::vector<rim::VariablePtr> >::iterator it;

   uint32_t x;
   bool doKey=true;
   char delim;

   // Determine which delimiter we are using
   std::size_t found = map.find("|");
   if (found!=std::string::npos) delim = '|';
   else delim = '\n';

   while(std::getline(fStream,line,delim)) {
      std::istringstream lStream(line);
      std::map<std::string, std::string> fields;
      x = 0;

      while(std::getline(lStream,field,'\t')) {
         if (doKey) key.push_back(field);
         else fields.insert(std::pair<std::string, std::string>(key[x],field));
         ++x;
      }

      if (!doKey) createVariable(fields,blockVars);
      doKey = false;
   }

   // Add variables to the blocks
   for (it=blockVars.begin(); it != blockVars.end(); ++it) {
      rim::BlockPtr blk = blocks_[it->first];
      blk->addVariables(it->second);
   }
}

//! Create a variable
// The fields used here are defined in saveAddressMap in _Root.py
void rogue::LibraryBase::createVariable(std::map<std::string, std::string> &data,
                                        std::map<std::string, std::vector<rim::VariablePtr> > &blockVars ) {

   // Extract fields
   std::string name    = getFieldString(data,"Path");
   std::string mode    = getFieldString(data,"Mode");
   std::string mbName  = getFieldString(data,"MemBaseName");
   std::string blkName = getFieldString(data,"BlockName");

   // Verify memory slave exists
   if ( memSlaves_.find(mbName) == memSlaves_.end() ) {
      if ( memSlavesMissing_.find(mbName) != memSlavesMissing_.end() ) {
         // Just return as we've already reported this.
         return;
      }
      memSlavesMissing_.insert(mbName);
      log_->info("LibraryBase::createVariable: '%s' memory interface '%s' not found!",name.c_str(),mbName.c_str());
      return;
   }

   bool overlapEn    = getFieldBool(data,"OverlapEn");
   bool verify       = getFieldBool(data,"Verify");
   bool bulkEn       = getFieldBool(data,"BulkEn");
   bool updateNotify = getFieldBool(data,"UpdateNotify");
   bool byteReverse  = getFieldBool(data,"ByteReverse");
   bool bitReverse   = getFieldBool(data,"BitReverse");

   uint64_t offset      = getFieldUInt64(data,"Address");
   uint32_t modelId     = getFieldUInt32(data,"ModelId");
   uint32_t binPoint    = getFieldUInt32(data,"BinPoint");
   uint32_t blockSize   = getFieldUInt32(data,"BlockSize");
   uint32_t numValues   = getFieldUInt32(data,"NumValues",true);
   uint32_t valueBits   = getFieldUInt32(data,"ValueBits",true);
   uint32_t valueStride = getFieldUInt32(data,"ValueStride",true);
   uint32_t retryCount  = getFieldUInt32(data,"RetryCount",true);

   double minimum = getFieldDouble(data,"Minimum");
   double maximum = getFieldDouble(data,"Maximum");

   std::vector<uint32_t> bitOffset = getFieldVectorUInt32(data,"BitOffset");
   std::vector<uint32_t> bitSize   = getFieldVectorUInt32(data,"BitSize");

   // Create the holding block if it does not already exist
   if ( blocks_.find(blkName) == blocks_.end() ) {
      rim::BlockPtr block = rim::Block::create(offset,blockSize);
      blocks_.insert(std::pair<std::string,rim::BlockPtr>(blkName,block));
      std::vector<rim::VariablePtr> vp;
      blockVars.insert(std::pair<std::string,std::vector<rim::VariablePtr>>(blkName,vp));

      // Connect to memory slave
      *block >> memSlaves_[mbName];

      // Enable the block
      block->setEnable(true);
   }

   // Create variable
   rim::VariablePtr var = rim::Variable::create(name,mode,minimum,maximum,offset,bitOffset,bitSize,
      overlapEn,verify,bulkEn,updateNotify,modelId,byteReverse,bitReverse,binPoint,numValues,
      valueBits,valueStride,retryCount);

   // Adjust min transaction size to match blocksize field
   var->shiftOffsetDown(0, blockSize);

   // Add to block list
   blockVars[blkName].push_back(var);
   variables_[name]=var;
}

// Read all variables
void rogue::LibraryBase::readAll() {
   std::map< std::string, rim::VariablePtr>::iterator it;
   for (it=variables_.begin(); it != variables_.end(); ++it) {
      it->second->read();
   }
}

//! Helper function to get string from fields
std::string rogue::LibraryBase::getFieldString(std::map<std::string, std::string> fields, std::string name) {
   if (fields.find(name) == fields.end())
      throw(rogue::GeneralError::create("LibraryBase::getFieldString","Failed to find field '%s' in exported address map",name.c_str()));

   return fields[name];
}

//! Helper function to get uint64_t from fields
uint64_t rogue::LibraryBase::getFieldUInt64(std::map<std::string, std::string> fields, std::string name) {
   uint64_t ret;

   if (fields.find(name) == fields.end())
      throw(rogue::GeneralError::create("LibraryBase::getFieldUInt64","Failed to find field '%s' in exported address map",name.c_str()));

   if (fields[name] == "None") return 0;

   try {
      ret = std::stol(fields[name],0,0);
   } catch(...) {
      throw(rogue::GeneralError::create("LibraryBase::getFieldUInt64","Failed to extract uint64_t from field '%s' in exported address map",name.c_str()));
   }
   return ret;
}

//! Helper function to get uint32_t from fields
uint32_t rogue::LibraryBase::getFieldUInt32(std::map<std::string, std::string> fields, std::string name, bool def) {
   uint32_t ret;

   if (fields.find(name) == fields.end()) {
      if ( def ) return 0;
      else throw(rogue::GeneralError::create("LibraryBase::getFieldUInt32","Failed to find field '%s' in exported address map",name.c_str()));
   }

   if (fields[name] == "None") return 0;

   try {
      ret = std::stoi(fields[name],0,0);
   } catch(...) {
      throw(rogue::GeneralError::create("LibraryBase::getFieldUInt32","Failed to extract uint32_t from field '%s' in exported address map",name.c_str()));
   }
   return ret;
}

//! Helper function to get bool from fields
bool rogue::LibraryBase::getFieldBool(std::map<std::string, std::string> fields, std::string name) {
   if (fields.find(name) == fields.end())
      throw(rogue::GeneralError::create("LibraryBase::getFieldBool","Failed to find field '%s' in exported address map",name.c_str()));

   return (fields[name] == "True");
}

//! Helper function to get double from fields
double rogue::LibraryBase::getFieldDouble(std::map<std::string, std::string> fields, std::string name) {
   double ret;

   if (fields.find(name) == fields.end())
      throw(rogue::GeneralError::create("LibraryBase::getFieldDouble","Failed to find field '%s' in exported address map",name.c_str()));

   if (fields[name] == "None") return 0.0;

   try {
      ret = std::stod(fields[name]);
   } catch(...) {
      throw(rogue::GeneralError::create("LibraryBase::getFieldDouble","Failed to extract double from field '%s' in exported address map",name.c_str()));
   }
   return ret;
}

//! Helper function to get uint32_t vector from fields
std::vector<uint32_t> rogue::LibraryBase::getFieldVectorUInt32(std::map<std::string, std::string> fields, std::string name) {
   std::vector<uint32_t> ret;
   std::string fld;
   std::string sub;
   uint32_t val;

   if (fields.find(name) == fields.end())
      throw(rogue::GeneralError::create("LibraryBase::getFieldVector32","Failed to find field '%s' in exported address map",name.c_str()));

   fld = fields[name];

   std::replace(fld.begin(),fld.end(),'[',' ');
   std::replace(fld.begin(),fld.end(),']',',');

   std::istringstream fStream(fld);

   while(std::getline(fStream,sub,',')) {

      try {
         val = std::stoi(sub);
      } catch(...) {
         throw(rogue::GeneralError::create("LibraryBase::getFieldVectorUInt32","Failed to extract uint32 from field '%s' in exported address map",name.c_str()));
      }
      ret.push_back(val);
   }
   return ret;
}


//! Dump the current state of the registers in the system
void rogue::LibraryBase::dumpRegisterStatus(std::string filename, bool read, bool includeStatus) {
   std::map< std::string, rim::VariablePtr>::iterator it;

   std::ofstream myfile;

   myfile.open(filename);

   for (it=variables_.begin(); it != variables_.end(); ++it) {
      if ( includeStatus || it->second->mode() != "RO" ) {
         myfile << it->second->getDumpValue(read);
      }
   }
   myfile.close();

}

