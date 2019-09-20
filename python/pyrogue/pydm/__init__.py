#!/usr/bin/env python
#-----------------------------------------------------------------------------
# Title      : PyRogue PyDM Package, Function to start default Rogue PyDM GUI
#-----------------------------------------------------------------------------
# File       : pyrogue/pydm/__init__.py
# Created    : 2019-09-18
#-----------------------------------------------------------------------------
# This file is part of the rogue software platform. It is subject to 
# the license terms in the LICENSE.txt file found in the top-level directory 
# of this distribution and at: 
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html. 
# No part of the rogue software platform, including this file, may be 
# copied, modified, propagated, or distributed except according to the terms 
# contained in the LICENSE.txt file.
#-----------------------------------------------------------------------------
import os
import sys
import pydm
import pyrogue.pydm.data_plugins.rogue_plugin

def runPyDM(addrList='localhost:9090', ui=None):

    os.environ['ROGUE_SERVERS'] = addrList

    if ui is None or ui == '':
        ui = os.path.dirname(os.path.abspath(__file__)) + '/pydmTop.py'

    app = pydm.PyDMApplication(ui_file=ui,
                               command_line_args=sys.argv, 
                               hide_nav_bar=True, 
                               hide_menu_bar=True, 
                               hide_status_bar=True)
    app.exec()

