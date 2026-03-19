#-----------------------------------------------------------------------------
# Company    : SLAC National Accelerator Laboratory
#-----------------------------------------------------------------------------
#  Description:
#       PyRogue PyDM Package, Function to start default Rogue PyDM GUI
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
import signal
from types import FrameType

import pydm
import pydm.data_plugins
from pyrogue.interfaces import VirtualClient
from pyrogue.pydm.data_plugins.rogue_plugin import RoguePlugin

# Define a signal handler to ensure the application quits gracefully
def pydmSignalHandler(sig: int, frame: FrameType | None) -> None:
    """Handle process termination signals by closing all PyDM windows.

    Parameters
    ----------
    sig : int
        Received signal number.
    frame : types.FrameType | None
        Current stack frame provided by :mod:`signal`.
    """
    app = pydm.PyDMApplication.instance()
    if app is not None:
        app.closeAllWindows()


def _configureVirtualClients(
    serverList: str,
    *,
    linkTimeout: float,
    requestStallTimeout: float | None,
) -> None:
    """Preconfigure cached VirtualClient instances for each GUI server.

    The GUI shares one cached VirtualClient per ``host:port`` endpoint. This
    helper applies timeout settings before PyDM widgets create channels so the
    whole session uses consistent link-state behavior.
    """
    for server in serverList.split(","):
        server = server.strip()
        if server == "":
            continue

        host, port = server.rsplit(":", 1)
        VirtualClient(
            addr=host,
            port=int(port),
            linkTimeout=linkTimeout,
            requestStallTimeout=requestStallTimeout,
        )

# Function to run the PyDM application with specified parameters
def runPyDM(
    serverList: str = 'localhost:9090',
    ui: str | None = None,
    title: str | None = None,
    sizeX: int = 800,
    sizeY: int = 1000,
    maxListExpand: int = 5,
    maxListSize: int = 100,
    linkTimeout: float = 10.0,
    requestStallTimeout: float | None = None,
) -> None:
    """Launch the default Rogue PyDM application.

    Parameters
    ----------
    serverList : str, optional
        Comma-separated list of ``host:port`` Rogue servers.
    ui : str | None, optional
        Optional UI file path. Defaults to ``pydmTop.py`` in this package.
    title : str | None, optional
        Optional window title. Defaults to ``"Rogue Server: <servers>"``.
    sizeX : int, optional
        Initial window width in pixels.
    sizeY : int, optional
        Initial window height in pixels.
    maxListExpand : int, optional
        Debug-tree auto-expand depth argument forwarded to the UI.
    maxListSize : int, optional
        Debug-tree list-size cap argument forwarded to the UI.
    linkTimeout : float, optional
        Idle timeout in seconds for VirtualClient link-state detection. This is
        the normal tuning knob for long-running hardware or simulation
        transactions and defaults to 10 seconds.
    requestStallTimeout : float | None, optional
        In-flight request age in seconds before the VirtualClient declares the
        server stalled. ``None`` disables stalled-request detection, which is
        usually the right default unless the application has a strict upper
        bound for valid request duration.

    Returns
    -------
    None
        This function runs the Qt event loop until the application exits.
    """

    # Set the ROGUE_SERVERS environment variable
    os.environ['ROGUE_SERVERS'] = serverList

    _configureVirtualClients(
        serverList,
        linkTimeout=linkTimeout,
        requestStallTimeout=requestStallTimeout,
    )

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

    pydm.data_plugins.initialize_plugins_if_needed()

    # Add Rogue plugin manually, if it hasn't already been added based on $PYDM_DATA_PLUGINS_PATH
    if 'rogue' not in pydm.data_plugins.plugin_modules:
        pydm.data_plugins.add_plugin(RoguePlugin)

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
