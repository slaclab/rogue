# 
# ----------------------------------------------------------------------------
# Title      : PGP applications makefile
# ----------------------------------------------------------------------------
# File       : Makefile
# Author     : Ryan Herbst, rherbst@slac.stanford.edu
# Created    : 2016-08-08
# Last update: 2016-08-08
# ----------------------------------------------------------------------------
# Description:
# PGP applications makefile
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

# Variables
CC       := g++
DEF      :=
BLD      := $(PWD)/build
#CFLAGS   := -Wall `$(PYTHON_CFG) --cflags` -I$(PWD)/include -std=c++0x -fPIC
LFLAGS   := `$(PYTHON_CFG) --ldflags` -lboost_thread-mt -lboost_python -lboost_system
LFLAGS   := `$(PYTHON_CFG) --ldflags` -lboost_thread -lboost_python -lboost_system
SHNAME   := rogue
SHLIB    := rogue.so

# Rogue Library Sources
LIB_HDR := $(PWD)/include/rogue
LIB_SRC := $(PWD)/src/rogue
LIB_CPP := $(foreach dir,$(shell find $(LIB_SRC) -type d),$(wildcard $(dir)/*.cpp))
LIB_OBJ := $(patsubst %.cpp,%.o,$(LIB_CPP))
LIB_SHO := $(BLD)/$(SHLIB)

# Application Sources
APP_SRC := $(PWD)/src/app
APP_CPP := $(wildcard $(APP_SRC)/*.cpp)
APP_BIN := $(patsubst $(APP_SRC)/%.cpp,$(BLD)/%,$(APP_CPP))

# Targets
all: $(LIB_OBJ) $(LIB_SHO) $(APP_BIN)
#all: $(LIB_OBJ) $(LIB_SHO)

# Clean
clean:
	@rm -f $(BLD)/*
	@rm -f $(LIB_OBJ)

# Compile sources with headers
%.o: %.cpp %.h
	@echo "Compiling $@"; $(CC) -c $(CFLAGS) $(DEF) -o $@ $<

# Compile sources without headers
%.o: %.cpp
	@echo "Compiling $@"; $(CC) -c $(CFLAGS) $(DEF) -o $@ $<

# Compile Shared Library
$(LIB_SHO): $(LIB_OBJ)
	@test -d $(BLD) || mkdir $(BLD)
	@echo "Creating $@"; $(CC) -shared -Wl,-soname,$(SHNAME) $(LIB_OBJ) $(LFLAGS) -o $@

# Application sources
$(BLD)/%: $(APP_SRC)/%.cpp $(LIB_SHO)
	@test -d $(BLD) || mkdir $(BLD)
	@echo "Compiling $@"; $(CC) $(CFLAGS) $(DEF) $(LIB_OBJ) $(LFLAGS) -o $@ $<

# Compile from shared does not work....
#@echo "Compiling $@"; $(CC) $(CFLAGS) $(DEF) -l:$(SHLIB) -L$(BLD) $(LFLAGS) -o $@ $<
