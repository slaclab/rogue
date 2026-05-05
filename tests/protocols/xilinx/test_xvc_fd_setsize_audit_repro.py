#-----------------------------------------------------------------------------
# Company    : SLAC National Accelerator Laboratory
#-----------------------------------------------------------------------------
# Description:
#   Regression tests.
#   Three Xvc constructors create file descriptors via syscalls that can
#   legally return fd >= FD_SETSIZE on a process with many open files,
#   yet were only validated by the defensive FD_SETSIZE check inside
#   XvcServer::run / XvcConnection::readTo.  That late check produces a
#   silent worker-thread exit (caught by Xvc::runThread) while the
#   caller sees Xvc::start() return success.  These source-text tests
#   assert each ctor performs the FD_SETSIZE check synchronously so
#   start() / accept fail fast with a clear error.
#-----------------------------------------------------------------------------
# This file is part of the rogue software platform. It is subject to
# the license terms in the LICENSE.txt file found in the top-level directory
# of this distribution and at:
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
# No part of the rogue software platform, including this file, may be
# copied, modified, propagated, or distributed except according to the terms
# contained in the LICENSE.txt file.
#-----------------------------------------------------------------------------

import pathlib
import re


_REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]
_XVC_CPP = _REPO_ROOT / "src" / "rogue" / "protocols" / "xilinx" / "Xvc.cpp"
_XVC_SERVER_CPP = _REPO_ROOT / "src" / "rogue" / "protocols" / "xilinx" / "XvcServer.cpp"
_XVC_CONN_CPP = _REPO_ROOT / "src" / "rogue" / "protocols" / "xilinx" / "XvcConnection.cpp"


def _ctor_body(path, qualified_name):
    """Return the body of ``qualified_name(...)`` defined in ``path``."""
    src = path.read_text()
    pattern = re.escape(qualified_name) + r"\([^{]*\{(?P<body>.*?)\n\}\s*\n"
    match = re.search(pattern, src, re.DOTALL)
    assert match is not None, (
        f"could not locate {qualified_name} ctor body in {path.name}"
    )
    return match.group("body")


def test_xvc_wakefd_fd_setsize_check_in_ctor():
    """Xvc::Xvc must reject wakeFd_ >= FD_SETSIZE synchronously after pipe()/pipe2().

    Without this, a high pipe fd would surface only as a deferred throw
    in XvcServer::run / XvcConnection::readTo, which Xvc::runThread
    catches and turns into a silent worker-thread exit while start()
    already returned success.
    """
    body = _ctor_body(_XVC_CPP, "rpx::Xvc::Xvc")

    # Both pipe creation and the FD_SETSIZE bounds check must appear in
    # the ctor body, with the bounds check after the pipe call.
    pipe_match = re.search(r"::pipe2?\(wakeFd_", body)
    assert pipe_match, "expected pipe()/pipe2() call in Xvc::Xvc"

    bounds_match = re.search(r"wakeFd_\[\s*\w+\s*\]\s*>=\s*FD_SETSIZE", body)
    assert bounds_match, (
        "Xvc::Xvc lacks an FD_SETSIZE bounds check on wakeFd_; high pipe "
        "fds would only surface as a silent worker-thread exit caught by "
        "Xvc::runThread, while the Python caller saw Xvc::start() return "
        "success"
    )
    assert bounds_match.start() > pipe_match.start(), (
        "FD_SETSIZE check must follow pipe()/pipe2() in Xvc::Xvc"
    )


def test_xvc_server_fd_setsize_check_in_ctor():
    """XvcServer::XvcServer must reject sd_ >= FD_SETSIZE after socket().

    The defensive FD_SETSIZE check in XvcServer::run runs on the worker
    thread and would only surface as a silent thread exit; the ctor
    check makes XvcServer construction fail fast so Xvc::start propagates
    the failure to the Python caller instead.
    """
    body = _ctor_body(_XVC_SERVER_CPP, "rpx::XvcServer::XvcServer")

    socket_match = re.search(r"sd_\s*=\s*::socket\(", body)
    assert socket_match, "expected ::socket() call in XvcServer::XvcServer"

    bounds_match = re.search(r"sd_\s*>=\s*FD_SETSIZE", body)
    assert bounds_match, (
        "XvcServer::XvcServer lacks an FD_SETSIZE bounds check on sd_; "
        "a high socket fd would only surface inside the worker thread's "
        "FD_SETSIZE check and be silently swallowed by Xvc::runThread"
    )
    assert bounds_match.start() > socket_match.start(), (
        "FD_SETSIZE check must follow ::socket() in XvcServer::XvcServer"
    )


def test_xvc_connection_fd_setsize_check_in_ctor():
    """XvcConnection::XvcConnection must reject sd_ >= FD_SETSIZE after accept().

    accept() can return a high fd on a process with many open files;
    readTo()'s defensive check would otherwise leave the bad fd open
    for the lifetime of the XvcConnection.  Throwing in the ctor lets
    XvcServer::run drop the bad connection cleanly via the existing
    ``catch (rogue::GeneralError&)`` arm and continue accepting.
    """
    body = _ctor_body(_XVC_CONN_CPP, "rpx::XvcConnection::XvcConnection")

    accept_match = re.search(r"sd_\s*=\s*::accept\(", body)
    assert accept_match, "expected ::accept() call in XvcConnection::XvcConnection"

    bounds_match = re.search(r"sd_\s*>=\s*FD_SETSIZE", body)
    assert bounds_match, (
        "XvcConnection::XvcConnection lacks an FD_SETSIZE bounds check on "
        "sd_; a high accept fd would leave a dead connection open until "
        "scope exit and every readTo() would silently return -2/EBADF"
    )
    assert bounds_match.start() > accept_match.start(), (
        "FD_SETSIZE check must follow ::accept() in XvcConnection::XvcConnection"
    )
