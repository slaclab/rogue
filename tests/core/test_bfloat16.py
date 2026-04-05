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


def test_bfloat16_model_metadata():
    model = pr.BFloat16(16)
    assert model.name == 'BFloat16'
    assert model.ndType == np.dtype(np.float32)
    assert model.modelId == rim.BFloat16
    assert math.isclose(model.minValue(), -3.39e38, rel_tol=0.01)
    assert math.isclose(model.maxValue(), 3.39e38, rel_tol=0.01)


def test_bfloat16_model_rejects_wrong_bitsize():
    with pytest.raises(AssertionError):
        pr.BFloat16(8)


def test_bfloat16_model_cache_returns_same_instance():
    assert pr.BFloat16(16) is pr.BFloat16(16)
    assert pr.BFloat16BE(16) is pr.BFloat16BE(16)
    assert pr.BFloat16(16) is not pr.BFloat16BE(16)


@pytest.mark.parametrize(("value", "description"), [
    (0.0, "positive zero"),
    (-0.0, "negative zero"),
    (3.39e38, "max positive"),
    (-3.39e38, "max negative"),
    (1.0, "one"),
    (float('inf'), "positive infinity"),
    (float('-inf'), "negative infinity"),
])
def test_bfloat16_model_boundary_values_round_trip(value, description):
    model = pr.BFloat16(16)
    ba = model.toBytes(value)
    result = model.fromBytes(ba)
    if math.isinf(value):
        assert math.isinf(result) and math.copysign(1.0, result) == math.copysign(1.0, value), \
            f"Failed for {description}: got {result}"
    elif value == 0.0:
        assert result == 0.0, f"Failed for {description}"
    else:
        assert math.isclose(result, value, rel_tol=0.01), \
            f"Failed for {description}: got {result}"


def test_bfloat16_model_nan_round_trip():
    model = pr.BFloat16(16)
    ba = model.toBytes(float('nan'))
    assert math.isnan(model.fromBytes(ba))


def test_bfloat16_model_has_infinity():
    """BFloat16 preserves infinity (unlike Float8 which clamps to max finite)."""
    model = pr.BFloat16(16)
    # Positive infinity
    ba = model.toBytes(float('inf'))
    result = model.fromBytes(ba)
    assert math.isinf(result) and result > 0

    # Negative infinity
    ba = model.toBytes(float('-inf'))
    result = model.fromBytes(ba)
    assert math.isinf(result) and result < 0


def test_bfloat16_model_fromstring():
    model = pr.BFloat16(16)
    assert model.fromString("3.14") == 3.14
    assert model.fromString("-1.5") == -1.5
    assert model.fromString("0.0") == 0.0


def test_bfloat16_model_known_bit_patterns():
    """Verify specific float values map to known BFloat16 bit patterns."""
    model = pr.BFloat16(16)
    # 0.0 -> 0x0000 (little-endian: [0x00, 0x00])
    assert model.toBytes(0.0) == bytearray([0x00, 0x00])
    # 1.0 -> 0x3F80 (little-endian: [0x80, 0x3F])
    assert model.toBytes(1.0) == bytearray([0x80, 0x3F])
    # +Inf -> 0x7F80 (little-endian: [0x80, 0x7F])
    assert model.toBytes(float('inf')) == bytearray([0x80, 0x7F])
    # -Inf -> 0xFF80 (little-endian: [0x80, 0xFF])
    assert model.toBytes(float('-inf')) == bytearray([0x80, 0xFF])


def test_bfloat16_be_endianness():
    """BFloat16BE stores bytes in big-endian order."""
    model = pr.BFloat16BE(16)
    assert model.endianness == 'big'
    # 1.0 -> 0x3F80 (big-endian: [0x3F, 0x80])
    assert model.toBytes(1.0) == bytearray([0x3F, 0x80])
    assert model.fromBytes(bytearray([0x3F, 0x80])) == 1.0
    # +Inf -> 0x7F80 (big-endian: [0x7F, 0x80])
    assert model.toBytes(float('inf')) == bytearray([0x7F, 0x80])
    result = model.fromBytes(bytearray([0x7F, 0x80]))
    assert math.isinf(result) and result > 0
    # -Inf -> 0xFF80 (big-endian: [0xFF, 0x80])
    assert model.toBytes(float('-inf')) == bytearray([0xFF, 0x80])
    result = model.fromBytes(bytearray([0xFF, 0x80]))
    assert math.isinf(result) and result < 0


class BFloat16VariableDevice(pr.Device):
    def __init__(self, mem_base, **kwargs):
        super().__init__(memBase=mem_base, **kwargs)
        self.add(pr.RemoteVariable(
            name="BFloat16Var",
            offset=0x00,
            bitSize=16,
            base=pr.BFloat16,
            mode="RW",
        ))


class BFloat16VariableRoot(pr.Root):
    def __init__(self):
        super().__init__(name="root", pollEn=False)
        mem = rim.Emulate(4, 0x4000)
        self.addInterface(mem)
        self.add(BFloat16VariableDevice(name="Dev", mem_base=mem))


def test_bfloat16_remote_variable_round_trip():
    with BFloat16VariableRoot() as root:
        root.Dev.BFloat16Var.set(1.25)
        result = root.Dev.BFloat16Var.get()
        assert math.isclose(result, 1.25, rel_tol=0.01)
        assert root.Dev.BFloat16Var.typeStr == "BFloat16"


def test_bfloat16_remote_variable_boundary_values():
    with BFloat16VariableRoot() as root:
        # Zero
        root.Dev.BFloat16Var.set(0.0)
        assert root.Dev.BFloat16Var.get() == 0.0

        # Positive near-max BFloat16 value
        root.Dev.BFloat16Var.set(3.0e38)
        result = root.Dev.BFloat16Var.get()
        assert math.isclose(result, 3.0e38, rel_tol=0.01)

        # Negative near-max BFloat16 value
        root.Dev.BFloat16Var.set(-3.0e38)
        result = root.Dev.BFloat16Var.get()
        assert math.isclose(result, -3.0e38, rel_tol=0.01)

        # Small value (tests normal encoding through C++ path)
        root.Dev.BFloat16Var.set(1.0)
        result = root.Dev.BFloat16Var.get()
        assert math.isclose(result, 1.0, rel_tol=0.01)
