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
BLD      := ./build
OBJ      := .obj
CFLAGS   := -Wall `$(PYTHON_CFG) --cflags` -I. -std=c++0x -fPIC
LFLAGS   := -lboost_thread-mt -lboost_python `$(PYTHON_CFG) --ldflags`
#LFLAGS   := -lboost_thread -lboost_python `$(PYTHON_CFG) --ldflags`
SHNAME   := rogue
SHLIB    := librogue.so

# Generic Sources
LIB_DIR := $(PWD)/interfaces $(PWD)/hardware $(PWD)/protocols $(PWD)/utilities
LIB_SUB := $(foreach dir,$(LIB_DIR),$(shell find $(dir) -type d))
LIB_SRC := $(foreach dir,$(LIB_SUB),$(wildcard $(dir)/*.cpp))
LIB_HDR := $(foreach dir,$(LIB_SUB),$(wildcard $(dir)/*.h))
LIB_OBJ := $(patsubst %.cpp,%.o,$(LIB_SRC))
LIB_SHO := $(BLD)/$(SHLIB)

# Python library sources
PYL_DIR := $(PWD)/py_modules
PYL_SRC := $(wildcard $(PYL_DIR)/*.cpp)
PYL_OBJ := $(patsubst %.cpp,%.o,$(PYL_SRC))
PYL_SHO := $(patsubst $(PYL_DIR)/%.cpp,$(BLD)/%.so,$(PYL_SRC))

# Application Sources
APP_DIR := $(PWD)/test/src
APP_SRC := $(wildcard $(APP_DIR)/*.cpp)
APP_BIN := $(patsubst $(APP_DIR)/%.cpp,$(BLD)/%,$(APP_SRC))

# Targets
#all: $(LIB_OBJ) $(LIB_SHO) $(PYL_OBJ) $(PYL_SHO) $(APP_BIN)
all: $(LIB_OBJ) $(LIB_SHO) $(PYL_OBJ) $(PYL_SHO)

# Test
list:
	@echo Dir: $(LIB_DIR)
	@echo ""
	@echo Sub: $(LIB_SUB)
	@echo ""
	@echo Hdr: $(LIB_HDR)
	@echo ""
	@echo Src: $(LIB_SRC)
	@echo ""
	@echo Obj: $(LIB_OBJ)
	@echo ""
	@echo Flags: $(CFLAGS)
	@echo ""
	@echo "Filter: " $(filter PgpCard.cpp,$(LIB_SRC))

# Clean
clean:
	@rm -f $(BLD)/*
	@rm -f $(LIB_OBJ) $(PYL_OBJ)

# Compile sources with headers
%.o: %.cpp %.h
	@echo "Compiling $@"; $(CC) -c $(CFLAGS) $(DEF) -o $@ $<

# Compile sources without headers
%.o: %.cpp
	@echo "Compiling $@"; $(CC) -c $(CFLAGS) $(DEF) -o $@ $<

# Compile Shared Library
$(LIB_SHO): $(LIB_OBJ)
	@test -d $(BLD) || mkdir $(BLD)
	@echo "Creating $@"; $(CC) -shared -Wl,-soname,$@ $(LIB_OBJ) $(LFLAGS) -o $@

# Compile python shared libraries
$(BLD)/%.so: $(PYL_DIR)/%.o $(LIB_SHO)
	@test -d $(BLD) || mkdir $(BLD)
	@echo "Creating $@"; $(CC) -shared -Wl,-soname,$@ $< -l$(SHNAME) -L$(BLD) -o $@

# Application sources
$(BLD)/%: $(APP_DIR)/%.cpp $(LIB_SHO)
	@test -d $(BLD) || mkdir $(BLD)
	@echo "Compiling $@"; $(CC) $(CFLAGS) $(DEF) $(LFLAGS) -l$(SHNAME) -L$(BLD) -o $@ $<

