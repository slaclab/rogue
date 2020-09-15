#-----------------------------------------------------------------------------
# Title      : PyRogue PyDM Package, Function to start default Rogue PyDM GUI
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

def runPyDM(serverList='localhost:9090', root=None, ui=None, title=None,sizeX=800,sizeY=1000,maxListExpand=5,maxListSize=100):

    if root is not None:

        if not root.running:
            raise Exception("Attempt to use pydm with root that has not started")

        os.environ['ROGUE_SERVERS'] = 'localhost:{}'.format(root.serverPort)
    else:
        os.environ['ROGUE_SERVERS'] = serverList

    if ui is None or ui == '':
        ui = os.path.dirname(os.path.abspath(__file__)) + '/pydmTop.py'

    if title is None:
        title = "Rogue Server: {}".format(os.getenv('ROGUE_SERVERS'))

    args = []
    args.append(f"sizeX={sizeX}")
    args.append(f"sizeY={sizeY}")
    args.append(f"title='{title}'")
    args.append(f"maxListExpand={maxListExpand}")
    args.append(f"maxListSize={maxListSize}")

    app = pydm.PyDMApplication(ui_file=ui,
                               command_line_args=args,
                               hide_nav_bar=True,
                               hide_menu_bar=True,
                               hide_status_bar=True)

    print(f"Running GUI. Close window, hit cntrl-c or send SIGTERM to {os.getpid()} to exit.")

    app.exec()

