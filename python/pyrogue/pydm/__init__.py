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
import signal
import pydm
import pyrogue
import pyrogue.pydm.data_plugins.rogue_plugin

# Define a signal handler to ensure the application quits gracefully
def pydmSignalHandler(sig, frame):
    app = pydm.PyDMApplication.instance()
    if app is not None:
        app.closeAllWindows()

# Function to run the PyDM application with specified parameters
def runPyDM(serverList='localhost:9090', ui=None, title=None, sizeX=800, sizeY=1000, maxListExpand=5, maxListSize=100):

    # Set the ROGUE_SERVERS environment variable
    os.environ['ROGUE_SERVERS'] = serverList

    # Set the UI file to a default value if not provided
    if ui is None or ui == '':
        ui = os.path.dirname(os.path.abspath(__file__)) + '/pydmTop.py'

    # Set the title to a default value if not provided
    if title is None:
        title = "Rogue Server: {}".format(os.getenv('ROGUE_SERVERS'))

    # Prepare command line arguments
    args = []
    args.append(f"sizeX={sizeX}")
    args.append(f"sizeY={sizeY}")
    args.append(f"title='{title}'")
    args.append(f"maxListExpand={maxListExpand}")
    args.append(f"maxListSize={maxListSize}")

    # Initialize the PyDM application with specified parameters
    app = pydm.PyDMApplication(ui_file=ui,
                               command_line_args=args,
                               hide_nav_bar=True,
                               hide_menu_bar=True,
                               hide_status_bar=True)

    # Setup signal handling for CTRL+C and SIGTERM for handling termination signal
    signal.signal(signal.SIGINT, pydmSignalHandler)
    signal.signal(signal.SIGTERM, pydmSignalHandler)

    # Print message indicating the GUI is running and how to exit
    print(f"Running GUI. Close window, hit cntrl-c or send SIGTERM to {os.getpid()} to exit.")

    # Run the PyDM application
    app.exec()
