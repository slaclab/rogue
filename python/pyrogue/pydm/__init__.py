#-----------------------------------------------------------------------------
from __future__ import annotations

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
import inspect
from collections.abc import Callable
from types import FrameType
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pydm import Display


def _constructDisplay(
    *,
    display: type[Display] | None,
    display_factory: Callable[..., Display] | None,
    args: list[str],
) -> Display | None:
    """Construct a PyDM ``Display`` from a class or factory."""
    from pydm import Display

    target = display_factory if display_factory is not None else display
    if target is None:
        return None

    if display is not None:
        return display(parent=None, args=args, macros=None)

    sig = inspect.signature(target)
    kwargs = {}
    for name in sig.parameters:
        if name == 'parent':
            kwargs[name] = None
        elif name == 'args':
            kwargs[name] = args
        elif name == 'macros':
            kwargs[name] = None

    disp = target(**kwargs)

    if not isinstance(disp, Display):
        raise TypeError("display_factory must return a pydm.Display instance")

    return disp

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
    import pydm

    app = pydm.PyDMApplication.instance()
    if app is not None:
        app.closeAllWindows()

# Function to run the PyDM application with specified parameters
def runPyDM(
    serverList: str = 'localhost:9090',
    ui: str | None = None,
    display: type[Display] | None = None,
    display_factory: Callable[..., Display] | None = None,
    title: str | None = None,
    sizeX: int = 800,
    sizeY: int = 1000,
    maxListExpand: int = 5,
    maxListSize: int = 100,
) -> None:
    """Launch the default Rogue PyDM application.

    Parameters
    ----------
    serverList : str, optional
        Comma-separated list of ``host:port`` Rogue servers.
    ui : str | None, optional
        Optional UI file path. Defaults to ``pydmTop.py`` in this package if
        neither ``display`` nor ``display_factory`` is supplied.
    display : type[pydm.Display] | None, optional
        Optional top-level ``pydm.Display`` subclass to instantiate directly.
    display_factory : callable | None, optional
        Optional factory that returns a ``pydm.Display`` instance.
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

    Returns
    -------
    None
        This function runs the Qt event loop until the application exits.
    """
    import pydm
    import pydm.data_plugins
    from pydm.utilities import establish_widget_connections
    from pydm.widgets.rules import register_widget_rules

    from pyrogue.pydm.data_plugins.rogue_plugin import RoguePlugin

    if sum(v is not None for v in (ui, display, display_factory)) > 1:
        raise ValueError("ui, display, and display_factory are mutually exclusive")

    # Set the ROGUE_SERVERS environment variable
    os.environ['ROGUE_SERVERS'] = serverList

    # Set the UI file to a default value only for the file-based launch path
    if (ui is None or ui == '') and display is None and display_factory is None:
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

    custom_display = _constructDisplay(display=display, display_factory=display_factory, args=args)
    if custom_display is not None:
        establish_widget_connections(custom_display)
        register_widget_rules(custom_display)
        if app.main_window.home_widget is None:
            app.main_window.home_widget = custom_display
        app.main_window.set_display_widget(custom_display)

    # Setup signal handling for CTRL+C and SIGTERM for handling termination signal
    signal.signal(signal.SIGINT, pydmSignalHandler)
    signal.signal(signal.SIGTERM, pydmSignalHandler)

    # Print message indicating the GUI is running and how to exit
    print(f"Running GUI. Close window, hit cntrl-c or send SIGTERM to {os.getpid()} to exit.")

    # Run the PyDM application
    app.exec()
