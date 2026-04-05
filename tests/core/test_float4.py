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


def test_float4_model_metadata():
    model = pr.Float4(8)
    assert model.name == 'Float4'
    assert model.ndType == np.dtype(np.float32)
    assert model.modelId == rim.Float4
    assert model.minValue() == -6.0
    assert model.maxValue() == 6.0


def test_float4_model_rejects_wrong_bitsize():
    with pytest.raises(AssertionError):
        pr.Float4(16)


def test_float4_model_cache_returns_same_instance():
    assert pr.Float4(8) is pr.Float4(8)
    assert pr.Float4BE(8) is pr.Float4BE(8)
    assert pr.Float4(8) is not pr.Float4BE(8)


@pytest.mark.parametrize(("value", "description"), [
    (0.0, "positive zero"),
    (-0.0, "negative zero"),
    (0.5, "subnormal"),
    (-0.5, "negative subnormal"),
    (1.0, "smallest normal"),
    (1.5, "normal 1.5"),
    (2.0, "normal 2.0"),
    (3.0, "normal 3.0"),
    (4.0, "normal 4.0"),
    (6.0, "max positive"),
    (-6.0, "max negative"),
])
def test_float4_model_boundary_values_round_trip(value, description):
    model = pr.Float4(8)
    ba = model.toBytes(value)
    result = model.fromBytes(ba)
    if value == 0.0:
        assert result == 0.0, f"Failed for {description}"
    else:
        assert result == value, f"Failed for {description}: got {result}"


def test_float4_model_known_bit_patterns():
    """Verify all 16 E2M1 bit patterns against the specification."""
    model = pr.Float4(8)
    # All 8 positive values
    assert model.toBytes(0.0) == bytearray([0x00])    # 0 00 0 = +0.0
    assert model.toBytes(0.5) == bytearray([0x01])    # 0 00 1 = +0.5 (subnormal)
    assert model.toBytes(1.0) == bytearray([0x02])    # 0 01 0 = +1.0
    assert model.toBytes(1.5) == bytearray([0x03])    # 0 01 1 = +1.5
    assert model.toBytes(2.0) == bytearray([0x04])    # 0 10 0 = +2.0
    assert model.toBytes(3.0) == bytearray([0x05])    # 0 10 1 = +3.0
    assert model.toBytes(4.0) == bytearray([0x06])    # 0 11 0 = +4.0
    assert model.toBytes(6.0) == bytearray([0x07])    # 0 11 1 = +6.0

    # All 8 negative values
    assert model.toBytes(-0.5) == bytearray([0x09])   # 1 00 1 = -0.5
    assert model.toBytes(-1.0) == bytearray([0x0A])   # 1 01 0 = -1.0
    assert model.toBytes(-1.5) == bytearray([0x0B])   # 1 01 1 = -1.5
    assert model.toBytes(-2.0) == bytearray([0x0C])   # 1 10 0 = -2.0
    assert model.toBytes(-3.0) == bytearray([0x0D])   # 1 10 1 = -3.0
    assert model.toBytes(-4.0) == bytearray([0x0E])   # 1 11 0 = -4.0
    assert model.toBytes(-6.0) == bytearray([0x0F])   # 1 11 1 = -6.0

    # Verify decode of all 16 patterns
    expected = [0.0, 0.5, 1.0, 1.5, 2.0, 3.0, 4.0, 6.0,
                -0.0, -0.5, -1.0, -1.5, -2.0, -3.0, -4.0, -6.0]
    for i in range(16):
        result = model.fromBytes(bytes([i]))
        if i == 0 or i == 8:
            assert result == 0.0, f"Pattern 0x{i:02X}: expected 0.0, got {result}"
        else:
            assert result == expected[i], f"Pattern 0x{i:02X}: expected {expected[i]}, got {result}"


def test_float4_model_nan_clamps_to_max():
    """E2M1 has no NaN encoding -- NaN input clamps to max positive (6.0)."""
    model = pr.Float4(8)
    ba = model.toBytes(float('nan'))
    assert ba == bytearray([0x07])  # max positive = 6.0
    result = model.fromBytes(ba)
    assert result == 6.0  # decodes as finite value, NOT NaN


def test_float4_model_inf_clamps_to_max():
    """E2M1 has no infinity encoding -- Inf clamps to max finite."""
    model = pr.Float4(8)
    # +Inf -> max positive (0x07 = 6.0)
    ba = model.toBytes(float('inf'))
    assert ba == bytearray([0x07])
    assert model.fromBytes(ba) == 6.0

    # -Inf -> max negative (0x0F = -6.0)
    ba = model.toBytes(float('-inf'))
    assert ba == bytearray([0x0F])
    assert model.fromBytes(ba) == -6.0


def test_float4_model_no_nan_on_decode():
    """All 16 bit patterns in E2M1 decode to finite values (no NaN/Inf)."""
    model = pr.Float4(8)
    for i in range(16):
        result = model.fromBytes(bytes([i]))
        assert math.isfinite(result), f"Pattern 0x{i:02X} decoded to non-finite: {result}"


def test_float4_model_overflow_clamps():
    """Values above max representable clamp to +/-6.0."""
    model = pr.Float4(8)
    assert model.toBytes(100.0) == bytearray([0x07])   # clamp to +6.0
    assert model.toBytes(-100.0) == bytearray([0x0F])  # clamp to -6.0
    assert model.toBytes(7.0) == bytearray([0x07])     # just above max


def test_float4_model_underflow_flushes():
    """Values below smallest subnormal flush to zero."""
    model = pr.Float4(8)
    ba = model.toBytes(0.1)  # below 0.5 subnormal threshold
    result = model.fromBytes(ba)
    assert result == 0.0  # flushed to zero


def test_float4_model_fromstring():
    model = pr.Float4(8)
    assert model.fromString("1.5") == 1.5
    assert model.fromString("-6.0") == -6.0


class Float4VariableDevice(pr.Device):
    def __init__(self, mem_base, **kwargs):
        super().__init__(memBase=mem_base, **kwargs)
        self.add(pr.RemoteVariable(
            name="Float4Var",
            offset=0x00,
            bitSize=8,
            base=pr.Float4,
            mode="RW",
        ))


class Float4VariableRoot(pr.Root):
    def __init__(self):
        super().__init__(name="root", pollEn=False)
        mem = rim.Emulate(4, 0x4000)
        self.addInterface(mem)
        self.add(Float4VariableDevice(name="Dev", mem_base=mem))


def test_float4_remote_variable_round_trip():
    with Float4VariableRoot() as root:
        root.Dev.Float4Var.set(1.0)
        result = root.Dev.Float4Var.get()
        assert result == 1.0
        assert root.Dev.Float4Var.typeStr == "Float4"


def test_float4_remote_variable_boundary_values():
    with Float4VariableRoot() as root:
        # Zero
        root.Dev.Float4Var.set(0.0)
        assert root.Dev.Float4Var.get() == 0.0

        # Max representable E2M1 value
        root.Dev.Float4Var.set(6.0)
        assert root.Dev.Float4Var.get() == 6.0

        # Negative max
        root.Dev.Float4Var.set(-6.0)
        assert root.Dev.Float4Var.get() == -6.0

        # Subnormal
        root.Dev.Float4Var.set(0.5)
        assert root.Dev.Float4Var.get() == 0.5
