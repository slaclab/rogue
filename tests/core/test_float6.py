#-----------------------------------------------------------------------------
# This file is part of the rogue software platform. It is subject to
# the license terms in the LICENSE.txt file found in the top-level directory
# of this distribution and at:
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
# No part of the rogue software platform, including this file, may be
# copied, modified, propagated, or distributed except according to the terms
# contained in the LICENSE.txt file.
#-----------------------------------------------------------------------------

import math

import numpy as np
import pytest
import pyrogue as pr
import rogue.interfaces.memory as rim


def test_float6_model_metadata():
    model = pr.Float6(8)
    assert model.name == 'Float6'
    assert model.ndType == np.dtype(np.float32)
    assert model.modelId == rim.Float6
    assert model.minValue() == -28.0
    assert model.maxValue() == 28.0


def test_float6_model_rejects_wrong_bitsize():
    with pytest.raises(AssertionError):
        pr.Float6(16)


def test_float6_model_cache_returns_same_instance():
    assert pr.Float6(8) is pr.Float6(8)
    assert pr.Float6BE(8) is pr.Float6BE(8)
    assert pr.Float6(8) is not pr.Float6BE(8)


@pytest.mark.parametrize(("value", "description"), [
    (0.0, "positive zero"),
    (-0.0, "negative zero"),
    (28.0, "max positive"),
    (-28.0, "max negative"),
    (0.0625, "smallest subnormal"),
    (0.125, "second subnormal"),
    (0.1875, "third subnormal"),
    (0.25, "smallest normal"),
    (1.0, "one"),
    (0.5, "one half"),
])
def test_float6_model_boundary_values_round_trip(value, description):
    model = pr.Float6(8)
    ba = model.toBytes(value)
    result = model.fromBytes(ba)
    if value == 0.0:
        assert result == 0.0, f"Failed for {description}"
    else:
        assert math.isclose(result, value, rel_tol=0.01), f"Failed for {description}: got {result}"


def test_float6_model_known_bit_patterns():
    """Verify specific float values map to known E3M2 bit patterns from the spec."""
    model = pr.Float6(8)
    # 0.0 -> 0x00
    assert model.toBytes(0.0) == bytearray([0x00])
    # 1.0 -> 0x0C (sign=0, exp=011, mant=00: 2^(3-3) * 1.0 = 1.0)
    assert model.toBytes(1.0) == bytearray([0x0C])
    # 28.0 -> 0x1F (sign=0, exp=111, mant=11: 2^(7-3) * 1.75 = 28.0)
    assert model.toBytes(28.0) == bytearray([0x1F])
    # -28.0 -> 0x3F (sign=1, exp=111, mant=11)
    assert model.toBytes(-28.0) == bytearray([0x3F])
    # 0.5 -> 0x08 (sign=0, exp=010, mant=00: 2^(2-3) * 1.0 = 0.5)
    assert model.toBytes(0.5) == bytearray([0x08])
    # Smallest subnormal 0.0625 -> 0x01 (exp=000, mant=01: 1/4 * 2^(-2) = 0.0625)
    assert model.toBytes(0.0625) == bytearray([0x01])
    # Smallest normal 0.25 -> 0x04 (exp=001, mant=00: 2^(1-3) * 1.0 = 0.25)
    assert model.toBytes(0.25) == bytearray([0x04])
    # 2.0 -> 0x10 (sign=0, exp=100, mant=00: 2^(4-3) * 1.0 = 2.0)
    assert model.toBytes(2.0) == bytearray([0x10])


def test_float6_model_nan_clamps_to_max():
    """E3M2 has no NaN encoding -- NaN input clamps to max positive (28.0)."""
    model = pr.Float6(8)
    ba = model.toBytes(float('nan'))
    assert ba == bytearray([0x1F])  # max positive = 28.0
    result = model.fromBytes(ba)
    assert result == 28.0  # decodes as finite value, NOT NaN


def test_float6_model_inf_clamps_to_max():
    """E3M2 has no infinity encoding -- Inf clamps to max finite."""
    model = pr.Float6(8)
    # +Inf -> max positive (0x1F = 28.0)
    ba = model.toBytes(float('inf'))
    assert ba == bytearray([0x1F])
    assert model.fromBytes(ba) == 28.0

    # -Inf -> max negative (0x3F = -28.0)
    ba = model.toBytes(float('-inf'))
    assert ba == bytearray([0x3F])
    assert model.fromBytes(ba) == -28.0


def test_float6_model_no_nan_on_decode():
    """All 64 bit patterns in E3M2 decode to finite values (no NaN/Inf)."""
    model = pr.Float6(8)
    for i in range(64):
        result = model.fromBytes(bytes([i]))
        assert math.isfinite(result), f"Pattern 0x{i:02X} decoded to non-finite: {result}"


def test_float6_model_fromstring():
    model = pr.Float6(8)
    assert model.fromString("1.5") == 1.5
    assert model.fromString("-28.0") == -28.0


class Float6VariableDevice(pr.Device):
    def __init__(self, mem_base, **kwargs):
        super().__init__(memBase=mem_base, **kwargs)
        self.add(pr.RemoteVariable(
            name="Float6Var",
            offset=0x00,
            bitSize=8,
            base=pr.Float6,
            mode="RW",
        ))


class Float6VariableRoot(pr.Root):
    def __init__(self):
        super().__init__(name="root", pollEn=False)
        mem = rim.Emulate(4, 0x4000)
        self.addInterface(mem)
        self.add(Float6VariableDevice(name="Dev", mem_base=mem))


def test_float6_remote_variable_round_trip():
    with Float6VariableRoot() as root:
        root.Dev.Float6Var.set(1.0)
        result = root.Dev.Float6Var.get()
        assert math.isclose(result, 1.0, rel_tol=0.01)
        assert root.Dev.Float6Var.typeStr == "Float6"


def test_float6_remote_variable_boundary_values():
    with Float6VariableRoot() as root:
        # Zero
        root.Dev.Float6Var.set(0.0)
        assert root.Dev.Float6Var.get() == 0.0

        # Max representable E3M2 value
        root.Dev.Float6Var.set(28.0)
        assert math.isclose(root.Dev.Float6Var.get(), 28.0, rel_tol=0.01)

        # Negative max
        root.Dev.Float6Var.set(-28.0)
        assert math.isclose(root.Dev.Float6Var.get(), -28.0, rel_tol=0.01)

        # Smallest subnormal
        root.Dev.Float6Var.set(0.0625)
        result = root.Dev.Float6Var.get()
        assert math.isclose(result, 0.0625, rel_tol=0.01)
