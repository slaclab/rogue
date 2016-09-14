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
# This file is part of the PGP card driver. It is subject to 
# the license terms in the LICENSE.txt file found in the top-level directory 
# of this distribution and at: 
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html. 
# No part of the PGP card driver, including this file, may be 
# copied, modified, propagated, or distributed except according to the terms 
# contained in the LICENSE.txt file.
# ----------------------------------------------------------------------------
# 

# Variables
CC       := g++
DEF      :=
BLD      := ./build
OBJ      := ./.obj
CFLAGS   := -Wall `$(PYTHON_CFG) --cflags`
LFLAGS   := -lpthread -lboost_python `$(PYTHON_CFG) --ldflags`
SHNAME   := rouge
SHLIB    := librouge.so

# Generic Sources
LIB_DIR := $(PWD)/hardware $(PWD)/interfaces $(PWD)/protocols $(PWD)/utilities
LIB_SUB := $(foreach dir,$(LIB_DIR),$(shell find $(dir) -type d))
LIB_SRC := $(foreach dir,$(LIB_SUB),$(wildcard $(dir)/*.cpp))
LIB_HDR := $(foreach dir,$(LIB_SUB),$(wildcard $(dir)/*.h))
LIB_OBJ := $(patsubst %.cpp,$(OBJ)/%.o,$(notdir $(LIB_SRC)))
LIB_SHO := $(BLD)/$(SHLIB)
CFLAGS  += $(foreach dir,$(LIB_SUB),-I$(dir))

# Python library sources
PYL_DIR := $(PWD)/py_modules
PYL_SRC := $(wildcard $(PYL_DIR)/*.cpp)
PYL_OBJ := $(patsubst $(PYL_DIR)/%.cpp,$(OBJ)/%.o,$(PYL_SRC))
PYL_SHO := $(patsubst $(PYL_DIR)/%.cpp,$(BLD)/%.so,$(PYL_SRC))

# Application Sources
APP_DIR := $(PWD)/test/src
APP_SRC := $(wildcard $(APP_DIR)/*.cpp)
APP_BIN := $(patsubst $(APP_DIR)/%.cpp,$(BLD)/%,$(APP_SRC))

# Targets
all: dir $(LIB_OBJ) $(LIB_SHO) $(PYL_OBJ) $(PYL_SHO) $(APP_BIN)

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

# Object directory
dir:
	@test -d $(OBJ) || mkdir $(OBJ)
	@test -d $(BLD) || mkdir $(BLD)

# Clean
clean:
	@rm -f $(BLD)/*
	@rm -f $(OBJ)/*

# Compile Generic Sources
define def_lib_rules
$(OBJ)/%.o: $(1)/%.cpp $(1)/%.h
	@echo "Compiling $$@ from $$<"; $(CC) -c $(CFLAGS) $(DEF) -o $$@ $$<
endef

$(foreach dir,$(LIB_SUB),$(eval $(call def_lib_rules,$(dir))))

# Compile Shared Library
$(LIB_SHO): $(LIB_OBJ)
	@echo "Creating $@"; $(CC) -shared -W1,-soname,$@ $(LIB_OBJ) $(LFLAGS) -o $@

# Compile Python Sources
$(OBJ)/%.o: $(PYL_DIR)/%.cpp 
	@echo "Compiling $@ from $<"; $(CC) -c $(CFLAGS) $(DEF) -o $@ $<

# Compile python shared libraries
$(BLD)/%.so: $(OBJ)/%.o $(LIB_SHO)
	@echo "Creating $@"; $(CC) -shared -W1,-soname,$@ $< -l$(SHNAME) -L$(BLD) -o $@

# Application sources
$(BLD)/%: $(APP_DIR)/%.cpp $(LIB_SHO)
	@echo "Compiling $@ from $<"; $(CC) $(CFLAGS) $(DEF) $(LFLAGS) -l$(SHNAME) -L$(BLD) -o $@ $<

