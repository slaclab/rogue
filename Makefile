# 
# ----------------------------------------------------------------------------
# Title      : ROGUE makefile
# ----------------------------------------------------------------------------
# File       : Makefile
# Created    : 2016-08-08
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

# To enable verbose: make VER=1
VER      := 0
CC_0     := @g++
CC_1     := g++
CC       := $(CC_$(VER))

# Generate version
VER_T    := $(shell git describe --tags)
VER_D    := $(shell git status --short -uno | wc -l)
VERSION  := $(if $(filter $(VER_D),0),$(VER_T),$(VER_T)-dirty)

# Defines
DEF      := -DVERSION=\"$(VERSION)\"

# Standard directives
CFLAGS   := -Wall -fno-strict-aliasing -std=c++0x -fPIC
CFLAGS   += -I$(PWD)/include -I$(PWD)/drivers/include
LFLAGS   := -lbz2

# Python configuration
CFLAGS   += `python3-config --cflags | sed s/-Wstrict-prototypes//` 
LFLAGS   += `python3-config --ldflags` -L`python3-config --prefix`/lib/

# Boost configuration
LFLAGS   += -lboost_system -lboost_thread
LFLAGS   += $(shell ld -lboost_python3     2> /dev/null && echo '-lboost_python3')
LFLAGS   += $(shell ld -lboost_python-py35 2> /dev/null && echo '-lboost_python-py35')

# Sometimes boost is in a non standard location
ifdef BOOST_PATH
	CFLAGS += -I$(BOOST_PATH)/include
	LFLAGS += -L$(BOOST_PATH)/lib
endif

# EPICS 3 Support Is Optional
ifdef EPICS_BASE
	CFLAGS += -I$(EPICS_BASE)/include -I$(EPICS_BASE)/include/compiler/gcc -I$(EPICS_BASE)/include/os/Linux
	LFLAGS += -L$(EPICS_BASE)/lib/rhel6-x86_64/ -lcas -lca -lCom -lgdd
	DEF    += -DDO_EPICSV3
endif

# Rogue Library Sources
LIB_HDR  := $(PWD)/include/rogue
LIB_SRC  := $(PWD)/src/rogue
LIB_CPP  := $(foreach dir,$(shell find $(LIB_SRC) -type d),$(wildcard $(dir)/*.cpp))
LIB_OBJ  := $(patsubst %.cpp,%.o,$(LIB_CPP))

# Python library sources
PYL_SRC  := $(PWD)/src/package.cpp
PYL_OBJ  := $(PWD)/src/package.o

# Python library
PYLIB      := $(PWD)/python/rogue.so
PYLIB_NAME := rogue

# C++ Library
CPPDIR := $(PWD)/lib
CPPLIB := $(CPPDIR)/librogue.so

# Targets
all: $(CPPLIB) $(PYLIB)

# Clean
clean:
	@rm -f $(PYL_OBJ)
	@rm -f $(LIB_OBJ)
	@rm -f $(PYLIB)
	@rm -f $(CPPLIB)

# Compile sources with headers
%.o: %.cpp %.h 
	@echo "Compiling $@"
	$(CC) -c $(CFLAGS) $(DEF) -o $@ $<

# Compile sources without headers
%.o: %.cpp 
	@echo "Compiling $@";
	$(CC) -c $(CFLAGS) $(DEF) -o $@ $<

# Compile Shared Library
$(CPPLIB): $(LIB_OBJ)
	@mkdir -p $(PWD)/lib
	@echo "Creating Version $(VERSION) of $@"
	$(CC) -shared $(LIB_OBJ) $(LFLAGS) -o $@

# Compile Python Library
$(PYLIB): $(CPPLIB) $(PYL_OBJ)
	@echo "Creating Version $(VERSION) of $@"; 
	$(CC) -shared -Wl,-soname,$(PYLIB_NAME) $(PYL_OBJ) -L$(CPPDIR) -lrogue $(LFLAGS) -o $@

