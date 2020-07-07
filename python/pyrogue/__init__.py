#-----------------------------------------------------------------------------
# This file is part of the rogue software platform. It is subject to
# the license terms in the LICENSE.txt file found in the top-level directory
# of this distribution and at:
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
# No part of the rogue software platform, including this file, may be
# copied, modified, propagated, or distributed except according to the terms
# contained in the LICENSE.txt file.
#-----------------------------------------------------------------------------
import sys

MIN_PYTHON = (3,6)
if sys.version_info < MIN_PYTHON:
    raise Exception("Python %s.%s or later is required.\n" % MIN_PYTHON)

from pyrogue._Node      import *
from pyrogue._Block     import *
from pyrogue._Model     import *
from pyrogue._Variable  import *
from pyrogue._Command   import *
from pyrogue._Device    import *
from pyrogue._Memory    import *
from pyrogue._Root      import *
from pyrogue._PollQueue import *
from pyrogue._Process   import *
from pyrogue._DataWriter   import *
from pyrogue._RunControl   import *
from pyrogue._DataReceiver import *
from pyrogue._HelperFunctions import *

# Add __version__ attribute with the module version number
__version__ = rogue.Version.pythonVersion()
