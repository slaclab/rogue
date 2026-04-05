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


def test_float8_model_metadata():
    model = pr.Float8(8)
    assert model.name == 'Float8'
    assert model.ndType == np.dtype(np.float32)
    assert model.modelId == rim.Float8
    assert model.minValue() == -448.0
    assert model.maxValue() == 448.0


def test_float8_model_rejects_wrong_bitsize():
    with pytest.raises(AssertionError):
        pr.Float8(16)


def test_float8_model_cache_returns_same_instance():
    assert pr.Float8(8) is pr.Float8(8)
    assert pr.Float8BE(8) is pr.Float8BE(8)
    assert pr.Float8(8) is not pr.Float8BE(8)


@pytest.mark.parametrize(("value", "description"), [
    (0.0, "positive zero"),
    (-0.0, "negative zero"),
    (448.0, "max positive"),
    (-448.0, "max negative"),
    (1.953125e-3, "smallest subnormal"),
    (0.015625, "smallest normal"),
    (1.0, "one"),
    (0.5, "one half"),
])
def test_float8_model_boundary_values_round_trip(value, description):
    model = pr.Float8(8)
    ba = model.toBytes(value)
    result = model.fromBytes(ba)
    if value == 0.0:
        assert result == 0.0, f"Failed for {description}"
    else:
        assert math.isclose(result, value, rel_tol=0.05), f"Failed for {description}: got {result}"


def test_float8_model_nan_encodes_as_0x7f():
    model = pr.Float8(8)
    ba = model.toBytes(float('nan'))
    assert ba == bytearray([0x7F])
    assert math.isnan(model.fromBytes(ba))


def test_float8_model_negative_nan_decodes():
    model = pr.Float8(8)
    assert math.isnan(model.fromBytes(bytes([0xFF])))


def test_float8_model_no_infinity():
    model = pr.Float8(8)
    # E4M3 has no infinity -- positive infinity clamps to max (0x7E = 448)
    ba = model.toBytes(float('inf'))
    assert ba == bytearray([0x7E])
    result = model.fromBytes(ba)
    assert math.isclose(result, 448.0, rel_tol=0.01)

    # Negative infinity clamps to -max (0xFE = -448)
    ba = model.toBytes(float('-inf'))
    assert ba == bytearray([0xFE])
    result = model.fromBytes(ba)
    assert math.isclose(result, -448.0, rel_tol=0.01)


def test_float8_model_fromstring():
    model = pr.Float8(8)
    assert model.fromString("1.5") == 1.5
    assert model.fromString("-448.0") == -448.0


def test_float8_model_known_bit_patterns():
    """Verify specific float values map to known E4M3 bit patterns."""
    model = pr.Float8(8)
    # 0.0 -> 0x00
    assert model.toBytes(0.0) == bytearray([0x00])
    # 1.0 -> 0x38 (sign=0, exp=0111, mant=000)
    assert model.toBytes(1.0) == bytearray([0x38])
    # 448.0 -> 0x7E (sign=0, exp=1111, mant=110)
    assert model.toBytes(448.0) == bytearray([0x7E])


class Float8VariableDevice(pr.Device):
    def __init__(self, mem_base, **kwargs):
        super().__init__(memBase=mem_base, **kwargs)
        self.add(pr.RemoteVariable(
            name="Float8Var",
            offset=0x00,
            bitSize=8,
            base=pr.Float8,
            mode="RW",
        ))


class Float8VariableRoot(pr.Root):
    def __init__(self):
        super().__init__(name="root", pollEn=False)
        mem = rim.Emulate(4, 0x4000)
        self.addInterface(mem)
        self.add(Float8VariableDevice(name="Dev", mem_base=mem))


def test_float8_remote_variable_round_trip():
    with Float8VariableRoot() as root:
        root.Dev.Float8Var.set(1.25)
        result = root.Dev.Float8Var.get()
        assert math.isclose(result, 1.25, rel_tol=0.1)
        assert root.Dev.Float8Var.typeStr == "Float8"


def test_float8_remote_variable_boundary_values():
    with Float8VariableRoot() as root:
        # Zero
        root.Dev.Float8Var.set(0.0)
        assert root.Dev.Float8Var.get() == 0.0

        # Max representable E4M3 value
        root.Dev.Float8Var.set(448.0)
        assert math.isclose(root.Dev.Float8Var.get(), 448.0, rel_tol=0.0, abs_tol=1.0)

        # Negative max
        root.Dev.Float8Var.set(-448.0)
        assert math.isclose(root.Dev.Float8Var.get(), -448.0, rel_tol=0.0, abs_tol=1.0)

        # Small value (tests subnormal handling through C++ path)
        root.Dev.Float8Var.set(0.015625)
        result = root.Dev.Float8Var.get()
        assert math.isclose(result, 0.015625, rel_tol=0.1)
