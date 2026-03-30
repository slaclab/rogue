#!/usr/bin/env python3
#-----------------------------------------------------------------------------
# This file is part of the rogue software platform. It is subject to
# the license terms in the LICENSE.txt file found in the top-level directory
# of this distribution and at:
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
# No part of the rogue software platform, including this file, may be
# copied, modified, propagated, or distributed except according to the terms
# contained in the LICENSE.txt file.
#-----------------------------------------------------------------------------

import re

from pyrogue.protocols.epicsV7 import _make_epics_suffix, _EPICS_MAX_NAME_LEN


def test_short_name_unchanged():
    base = "TestBase"
    suffix = "Short"
    assert len(f"{base}:{suffix}") < 60
    assert _make_epics_suffix(base, suffix) == "Short"


def test_exact_60_unchanged():
    # 10 + 1 + 49 = 60
    base = "B" * 10
    suffix = "S" * 49
    assert len(base + ":" + suffix) == 60
    assert _make_epics_suffix(base, suffix) == suffix


def test_61_chars_triggers_hash():
    # 10 + 1 + 50 = 61
    base = "B" * 10
    suffix = "S" * 50
    result = _make_epics_suffix(base, suffix)
    assert result != suffix
    assert result.startswith("tail_")
    assert len(result) == 15  # 5 prefix + 10 hex chars


def test_hash_format():
    base = "TestBase"
    suffix = "A" * 60
    result = _make_epics_suffix(base, suffix)
    assert re.match(r"^tail_[0-9a-f]{10}$", result)


def test_hash_deterministic():
    base = "TestBase"
    suffix = "LongSuffix" + "A" * 50
    result1 = _make_epics_suffix(base, suffix)
    result2 = _make_epics_suffix(base, suffix)
    result3 = _make_epics_suffix(base, suffix)
    assert result1 == result2 == result3


def test_different_inputs_different_hashes():
    base = "TestBase"
    suffix1 = "LongSuffix" + "A" * 50
    suffix2 = "LongSuffix" + "B" * 50
    assert _make_epics_suffix(base, suffix1) != _make_epics_suffix(base, suffix2)


def test_hash_uses_full_name():
    # Same suffix but different base strings — both exceed 60 chars
    base1 = "Base1" + "X" * 20
    base2 = "Base2" + "X" * 20
    suffix = "SameSuffix" + "Z" * 50
    assert _make_epics_suffix(base1, suffix) != _make_epics_suffix(base2, suffix)


def test_constant_value():
    assert _EPICS_MAX_NAME_LEN == 60
