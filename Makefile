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

# Generate version
VER_T    := $(shell git describe --tags)
VER_D    := $(shell git status --short -uno | wc -l)
VERSION  := $(if $(filter $(VER_D),0),$(VER_T),$(VER_T)-dirty)

# To enable verbose: make VER=1
VER      := 0
CC_0     := @g++
CC_1     := g++
CC       := $(CC_$(VER))

# Variables
DEF      := -DVERSION=\"$(VERSION)\"
CFLAGS   := -Wall `python3-config --cflags | sed s/-Wstrict-prototypes//` 
CFLAGS   += -fno-strict-aliasing -std=c++0x -fPIC
CFLAGS   += -I$(PWD)/include -I$(PWD)/drivers/include
LFLAGS   := `python3-config --ldflags` -lboost_thread -lboost_python3 -lboost_system
LFLAGS   += -L`python3-config --prefix`/lib/ -lbz2

# Sometimes boost is in a non standard location
ifdef BOOST_PATH
	CFLAGS += -I$(BOOST_PATH)/include
	LFLAGS += -L$(BOOST_PATH)/lib
endif

# EPICS Support Is Optional
ifdef EPICS_BASE
	CFLAGS += -I$(EPICS_BASE)/include -I$(EPICS_BASE)/include/compiler/gcc -I$(EPICS_BASE)/include/os/Linux
	LFLAGS += -L$(EPICS_BASE)/lib/rhel6-x86_64/ -lcas -lca -lCom -lgdd
	DEF    += -DDO_EPICS
endif

# Rogue Library Sources
LIB_HDR  := $(PWD)/include/rogue
LIB_SRC  := $(PWD)/src/rogue
LIB_CPP  := $(foreach dir,$(shell find $(LIB_SRC) -type d),$(wildcard $(dir)/*.cpp))
LIB_OBJ  := $(patsubst %.cpp,%.o,$(LIB_CPP))

# Python library
PYLIB      := $(PWD)/python/rogue.so
PYLIB_NAME := rogue

# C++ Library
CPPLIB := $(PWD)/lib/librogue.so

# Targets
all: $(LIB_OBJ) $(PYLIB) $(CPPLIB)

# Doxygen
docs:
	cd doc; doxygen

# Clean
clean:
	@rm -f $(PYLIB)
	@rm -f $(CPPLIB)
	@rm -f $(LIB_OBJ)

# Compile sources with headers
%.o: %.cpp %.h 
	@echo "Compiling $@"
	$(CC) -c $(CFLAGS) $(DEF) -o $@ $<

# Compile sources without headers
%.o: %.cpp 
	@echo "Compiling $@";
	$(CC) -c $(CFLAGS) $(DEF) -o $@ $<

# Compile Shared Library
$(PYLIB): $(LIB_OBJ)
	@echo "Creating Version $(VERSION) of $@"
	$(CC) -shared -Wl,-soname,$(PYLIB_NAME) $(LIB_OBJ) $(LFLAGS) -o $@

# Compile Shared Library
$(CPPLIB): $(LIB_OBJ)
	@mkdir -p $(PWD)/lib
	@echo "Creating Version $(VERSION) of $@"
	$(CC) -shared $(LIB_OBJ) $(LFLAGS) -o $@

