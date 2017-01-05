# 
# ----------------------------------------------------------------------------
# Title      : ROGUE makefile
# ----------------------------------------------------------------------------
# File       : Makefile
# Author     : Ryan Herbst, rherbst@slac.stanford.edu
# Created    : 2016-08-08
# Last update: 2016-08-08
# ----------------------------------------------------------------------------
# Description:
# ROGUE makefile
# ----------------------------------------------------------------------------
# This file is part of the rogue software package. It is subject to 
# the license terms in the LICENSE.txt file found in the top-level directory 
# of this distribution and at: 
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html. 
# No part of the rogue software package, including this file, may be 
# copied, modified, propagated, or distributed except according to the terms 
# contained in the LICENSE.txt file.
# ----------------------------------------------------------------------------
# 

# Python 3
PYCONF = python3-config
PYBOOST = -lboost_python3

# Python 2
#PYCONF = python2.7-config
#PYBOOST = -lboost_python

# Variables
C       := g++
DEF      :=
CFLAGS   := -Wall `$(PYCONF) --cflags` -I $(BOOST_PATH)/include -I$(PWD)/include -I$(PWD)/drivers/include -std=c++0x -fPIC
LFLAGS   := `$(PYCONF) --ldflags` -lboost_thread $(PYBOOST) -lboost_system
LFLAGS   += -L`$(PYCONF) --prefix`/lib/ -L$(BOOST_PATH)/lib 
SHNAME   := rogue
SHLIB    := rogue.so

# Rogue Library Sources
LIB_HDR := $(PWD)/include/rogue
LIB_SRC := $(PWD)/src/rogue
LIB_CPP := $(foreach dir,$(shell find $(LIB_SRC) -type d),$(wildcard $(dir)/*.cpp))
LIB_OBJ := $(patsubst %.cpp,%.o,$(LIB_CPP))
LIB_SHO := $(PWD)/python/$(SHLIB)

# Targets
all: $(LIB_OBJ) $(LIB_SHO)

# Doxygen
docs:
	cd doc; doxygen

# Clean
clean:
	@rm -f $(LIB_OBJ)
	@rm -f $(LIB_SHO)

# Compile sources with headers
%.o: %.cpp %.h
	@echo "Compiling $@"; $(CC) -c $(CFLAGS) $(DEF) -o $@ $<

# Compile sources without headers
%.o: %.cpp
	@echo "Compiling $@"; $(CC) -c $(CFLAGS) $(DEF) -o $@ $<

# Compile Shared Library
$(LIB_SHO): $(LIB_OBJ)
	@echo "Creating $@"; $(CC) -shared -Wl,-soname,$(SHNAME) $(LIB_OBJ) $(LFLAGS) -o $@

