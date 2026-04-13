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


def test_tensorfloat32_model_metadata():
    model = pr.TensorFloat32(32)
    assert model.name == 'TensorFloat32'
    assert model.ndType == np.dtype(np.float32)
    assert model.modelId == rim.TensorFloat32
    assert math.isclose(model.minValue(), -3.40e38, rel_tol=0.01)
    assert math.isclose(model.maxValue(), 3.40e38, rel_tol=0.01)


def test_tensorfloat32_model_rejects_wrong_bitsize():
    with pytest.raises(AssertionError):
        pr.TensorFloat32(16)


def test_tensorfloat32_model_cache_returns_same_instance():
    assert pr.TensorFloat32(32) is pr.TensorFloat32(32)
    assert pr.TensorFloat32BE(32) is pr.TensorFloat32BE(32)
    assert pr.TensorFloat32(32) is not pr.TensorFloat32BE(32)


@pytest.mark.parametrize(("value", "description"), [
    (0.0, "positive zero"),
    (-0.0, "negative zero"),
    (3.40e38, "max positive"),
    (-3.40e38, "max negative"),
    (1.0, "one"),
    (float('inf'), "positive infinity"),
    (float('-inf'), "negative infinity"),
])
def test_tensorfloat32_model_boundary_values_round_trip(value, description):
    model = pr.TensorFloat32(32)
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


def test_tensorfloat32_model_nan_round_trip():
    model = pr.TensorFloat32(32)
    ba = model.toBytes(float('nan'))
    assert math.isnan(model.fromBytes(ba))


def test_tensorfloat32_model_has_infinity():
    """TensorFloat32 preserves infinity (same exponent range as float32)."""
    model = pr.TensorFloat32(32)
    # Positive infinity
    ba = model.toBytes(float('inf'))
    result = model.fromBytes(ba)
    assert math.isinf(result) and result > 0

    # Negative infinity
    ba = model.toBytes(float('-inf'))
    result = model.fromBytes(ba)
    assert math.isinf(result) and result < 0


def test_tensorfloat32_model_fromstring():
    model = pr.TensorFloat32(32)
    assert model.fromString("3.14") == 3.14
    assert model.fromString("-1.5") == -1.5
    assert model.fromString("0.0") == 0.0


def test_tensorfloat32_model_known_bit_patterns():
    """Verify specific float values map to known TF32 bit patterns."""
    model = pr.TensorFloat32(32)
    # 0.0 -> 0x00000000 (little-endian: [0x00, 0x00, 0x00, 0x00])
    assert model.toBytes(0.0) == bytearray([0x00, 0x00, 0x00, 0x00])
    # 1.0 -> 0x3F800000 (little-endian: [0x00, 0x00, 0x80, 0x3F])
    assert model.toBytes(1.0) == bytearray([0x00, 0x00, 0x80, 0x3F])
    # +Inf -> 0x7F800000 (little-endian: [0x00, 0x00, 0x80, 0x7F])
    assert model.toBytes(float('inf')) == bytearray([0x00, 0x00, 0x80, 0x7F])
    # -Inf -> 0xFF800000 (little-endian: [0x00, 0x00, 0x80, 0xFF])
    assert model.toBytes(float('-inf')) == bytearray([0x00, 0x00, 0x80, 0xFF])


def test_tensorfloat32_be_endianness():
    """TensorFloat32BE stores bytes in big-endian order."""
    model = pr.TensorFloat32BE(32)
    assert model.endianness == 'big'
    # 1.0 -> float32 0x3F800000, lower 13 bits already zero, big-endian: [0x3F, 0x80, 0x00, 0x00]
    expected = bytearray([0x3F, 0x80, 0x00, 0x00])
    assert model.toBytes(1.0) == expected
    assert model.fromBytes(expected) == 1.0


class TensorFloat32VariableDevice(pr.Device):
    def __init__(self, mem_base, **kwargs):
        super().__init__(memBase=mem_base, **kwargs)
        self.add(pr.RemoteVariable(
            name="TF32Var",
            offset=0x00,
            bitSize=32,
            base=pr.TensorFloat32,
            mode="RW",
        ))


class TensorFloat32VariableRoot(pr.Root):
    def __init__(self):
        super().__init__(name="root", pollEn=False)
        mem = rim.Emulate(4, 0x4000)
        self.addInterface(mem)
        self.add(TensorFloat32VariableDevice(name="Dev", mem_base=mem))


def test_tensorfloat32_remote_variable_round_trip():
    with TensorFloat32VariableRoot() as root:
        root.Dev.TF32Var.set(1.25)
        result = root.Dev.TF32Var.get()
        assert math.isclose(result, 1.25, rel_tol=0.01)
        assert root.Dev.TF32Var.typeStr == "TensorFloat32"


def test_tensorfloat32_remote_variable_boundary_values():
    with TensorFloat32VariableRoot() as root:
        # Zero
        root.Dev.TF32Var.set(0.0)
        assert root.Dev.TF32Var.get() == 0.0

        # Positive near-max TF32 value
        root.Dev.TF32Var.set(3.0e38)
        result = root.Dev.TF32Var.get()
        assert math.isclose(result, 3.0e38, rel_tol=0.01)

        # Negative near-max TF32 value
        root.Dev.TF32Var.set(-3.0e38)
        result = root.Dev.TF32Var.get()
        assert math.isclose(result, -3.0e38, rel_tol=0.01)

        # Small value (tests normal encoding through C++ path)
        root.Dev.TF32Var.set(1.0)
        result = root.Dev.TF32Var.get()
        assert math.isclose(result, 1.0, rel_tol=0.01)
