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

import pytest
import pyrogue as pr
import rogue.interfaces.memory


class ModelVariableDevice(pr.Device):
    def __init__(self, mem_base, **kwargs):
        super().__init__(memBase=mem_base, **kwargs)

        self.add(pr.RemoteVariable(
            name="UIntOdd",
            offset=0x00,
            bitSize=17,
            base=pr.UInt,
            mode="RW",
        ))

        self.add(pr.RemoteVariable(
            name="IntOdd",
            offset=0x04,
            bitSize=12,
            base=pr.Int,
            mode="RW",
        ))

        self.add(pr.RemoteVariable(
            name="BoolVar",
            offset=0x08,
            bitSize=1,
            base=pr.Bool,
            mode="RW",
        ))

        self.add(pr.RemoteVariable(
            name="StringVar",
            offset=0x0C,
            bitSize=32,
            base=pr.String,
            mode="RW",
        ))

        self.add(pr.RemoteVariable(
            name="FloatVar",
            offset=0x10,
            bitSize=32,
            base=pr.Float,
            mode="RW",
        ))

        self.add(pr.RemoteVariable(
            name="DoubleVar",
            offset=0x18,
            bitSize=64,
            base=pr.Double,
            mode="RW",
        ))

        self.add(pr.RemoteVariable(
            name="Float16Var",
            offset=0x28,
            bitSize=16,
            base=pr.Float16,
            mode="RW",
        ))

        self.add(pr.RemoteVariable(
            name="Float8Var",
            offset=0x30,
            bitSize=8,
            base=pr.Float8,
            mode="RW",
        ))

        self.add(pr.RemoteVariable(
            name="BFloat16Var",
            offset=0x32,
            bitSize=16,
            base=pr.BFloat16,
            mode="RW",
        ))

        self.add(pr.RemoteVariable(
            name="TF32Var",
            offset=0x34,
            bitSize=32,
            base=pr.TensorFloat32,
            mode="RW",
        ))

        self.add(pr.RemoteVariable(
            name="Float6Var",
            offset=0x38,
            bitSize=8,
            base=pr.Float6,
            mode="RW",
        ))

        self.add(pr.RemoteVariable(
            name="Float4Var",
            offset=0x39,
            bitSize=8,
            base=pr.Float4,
            mode="RW",
        ))

        # Keep the fixed-point cases on real RemoteVariables so the tests hit
        # the block/model conversion path that application code actually uses.
        self.add(pr.RemoteVariable(
            name="FixedVar",
            offset=0x20,
            bitSize=16,
            base=pr.Fixed(16, 4),
            mode="RW",
        ))

        self.add(pr.RemoteVariable(
            name="UFixedVar",
            offset=0x24,
            bitSize=16,
            base=pr.UFixed(16, 4),
            mode="RW",
        ))

        # Wide fixed-point variables exercise the sign-extension path in
        # Block::getFixed for valueBits_ >= 32. A plain `1 << valueBits_` in
        # that path is undefined behavior, so without correct 64-bit shifts
        # negative-value round-trips on these will fail.
        self.add(pr.RemoteVariable(
            name="Fixed32Var",
            offset=0x28,
            bitSize=32,
            base=pr.Fixed(32, 0),
            mode="RW",
        ))

        self.add(pr.RemoteVariable(
            name="Fixed40Var",
            offset=0x30,
            bitSize=40,
            base=pr.Fixed(40, 8),
            mode="RW",
        ))

        self.add(pr.RemoteVariable(
            name="Fixed64Var",
            offset=0x38,
            bitSize=64,
            base=pr.Fixed(64, 0),
            mode="RW",
        ))

        # Wide unsigned fixed-point variables exercise Block::setUFixed /
        # Block::getUFixed at valueBits_ >= 32, including the
        # `valueBits_ >= 64 ? UINT64_MAX` branch used to cap the max-range
        # computation at 64 bits.
        self.add(pr.RemoteVariable(
            name="UFixed32Var",
            offset=0x40,
            bitSize=32,
            base=pr.UFixed(32, 0),
            mode="RW",
        ))

        self.add(pr.RemoteVariable(
            name="UFixed40Var",
            offset=0x48,
            bitSize=40,
            base=pr.UFixed(40, 8),
            mode="RW",
        ))

        self.add(pr.RemoteVariable(
            name="UFixed64Var",
            offset=0x50,
            bitSize=64,
            base=pr.UFixed(64, 0),
            mode="RW",
        ))

        # List (numValues > 1) fixed-point variables exercise the numpy /
        # per-element paths in Block::setFixedPy / Block::getFixedPy, which
        # dispatch to the signed or unsigned scalar setter/getter via a
        # modelId check. Without list coverage, that dispatch is untested.
        self.add(pr.RemoteVariable(
            name="FixedListVar",
            offset=0x58,
            numValues=4,
            valueBits=16,
            valueStride=16,
            base=pr.Fixed(16, 4),
            mode="RW",
        ))

        self.add(pr.RemoteVariable(
            name="UFixedListVar",
            offset=0x60,
            numValues=4,
            valueBits=16,
            valueStride=16,
            base=pr.UFixed(16, 4),
            mode="RW",
        ))

        self.add(pr.LocalVariable(name="LocalInt", value=3))
        self.add(pr.LocalVariable(name="LocalBool", value=False))
        self.add(pr.LocalVariable(name="LocalString", value="start"))
        self.add(pr.LocalVariable(name="LocalFloat", value=1.25))


class ModelVariableRoot(pr.Root):
    def __init__(self):
        super().__init__(name="root", pollEn=False)
        mem = rogue.interfaces.memory.Emulate(4, 0x4000)
        self.addInterface(mem)
        self.add(ModelVariableDevice(name="Dev", mem_base=mem))


def test_local_variables_exercise_public_variable_api():
    with ModelVariableRoot() as root:
        root.Dev.LocalInt.set(12)
        root.Dev.LocalBool.set(True)
        root.Dev.LocalString.set("updated")
        root.Dev.LocalFloat.set(2.5)

        assert root.Dev.LocalInt.get() == 12
        assert root.Dev.LocalInt.typeStr == "int"
        assert root.Dev.LocalBool.get() is True
        assert root.Dev.LocalBool.typeStr == "bool"
        assert root.Dev.LocalString.get() == "updated"
        assert root.Dev.LocalString.typeStr == "str"
        assert root.Dev.LocalFloat.get() == 2.5
        assert root.Dev.LocalFloat.typeStr == "float"


def test_remote_variables_round_trip_model_backed_values():
    with ModelVariableRoot() as root:
        root.Dev.UIntOdd.set(0x1AAAA)
        root.Dev.IntOdd.set(-17)
        root.Dev.BoolVar.set(True)
        root.Dev.StringVar.set("abc")
        root.Dev.FloatVar.set(1.25)
        root.Dev.DoubleVar.set(2.5)
        root.Dev.Float16Var.set(1.25)
        root.Dev.Float8Var.set(1.0)
        root.Dev.BFloat16Var.set(1.0)
        root.Dev.TF32Var.set(1.25)
        root.Dev.Float6Var.set(1.0)
        root.Dev.Float4Var.set(1.0)
        root.Dev.FixedVar.set(1.5)
        root.Dev.UFixedVar.set(2.25)

        assert root.Dev.UIntOdd.get() == 0x1AAAA
        assert root.Dev.UIntOdd.typeStr == "UInt17"
        assert root.Dev.IntOdd.get() == -17
        assert root.Dev.IntOdd.typeStr == "Int12"
        assert root.Dev.BoolVar.get() is True
        assert root.Dev.BoolVar.typeStr == "Bool"
        assert root.Dev.StringVar.get() == "abc"
        assert root.Dev.StringVar.typeStr == "String(4)"
        assert math.isclose(root.Dev.FloatVar.get(), 1.25, rel_tol=0.0, abs_tol=1e-6)
        assert root.Dev.FloatVar.typeStr == "Float32"
        assert math.isclose(root.Dev.DoubleVar.get(), 2.5, rel_tol=0.0, abs_tol=1e-12)
        assert root.Dev.DoubleVar.typeStr == "Double64"
        assert math.isclose(root.Dev.Float16Var.get(), 1.25, rel_tol=0.0, abs_tol=1e-3)
        assert root.Dev.Float16Var.typeStr == "Float16"
        assert math.isclose(root.Dev.Float8Var.get(), 1.0, rel_tol=0.0, abs_tol=0.1)
        assert root.Dev.Float8Var.typeStr == "Float8"
        assert math.isclose(root.Dev.BFloat16Var.get(), 1.0, rel_tol=0.0, abs_tol=0.01)
        assert root.Dev.BFloat16Var.typeStr == "BFloat16"
        assert math.isclose(root.Dev.TF32Var.get(), 1.25, rel_tol=0.0, abs_tol=0.01)
        assert root.Dev.TF32Var.typeStr == "TensorFloat32"
        assert math.isclose(root.Dev.Float6Var.get(), 1.0, rel_tol=0.0, abs_tol=0.1)
        assert root.Dev.Float6Var.typeStr == "Float6"
        assert root.Dev.Float4Var.get() == 1.0
        assert root.Dev.Float4Var.typeStr == "Float4"
        assert math.isclose(root.Dev.FixedVar.get(), 1.5, rel_tol=0.0, abs_tol=1e-6)
        assert root.Dev.FixedVar.typeStr == "Fixed_16_4"
        assert math.isclose(root.Dev.UFixedVar.get(), 2.25, rel_tol=0.0, abs_tol=1e-6)
        assert root.Dev.UFixedVar.typeStr == "UFixed_16_4"


def test_remote_variable_metadata_exposes_model_constraints():
    with ModelVariableRoot() as root:
        assert root.Dev.UIntOdd.minimum == 0
        assert root.Dev.UIntOdd.maximum == (2 ** 17) - 1
        assert root.Dev.IntOdd.minimum == -(2 ** 11)
        assert root.Dev.IntOdd.maximum == (2 ** 11) - 1

        # Fixed-point variables should preserve the model metadata used by the
        # lower-level memory conversion logic.
        assert root.Dev.FixedVar._base.binPoint == 4
        assert root.Dev.FixedVar._base.signed is True
        assert root.Dev.UFixedVar._base.binPoint == 4
        assert root.Dev.UFixedVar._base.signed is False

        # Fixed-point models expose representable min/max
        assert root.Dev.FixedVar.minimum == -2048.0
        assert root.Dev.FixedVar.maximum == 2047.9375
        assert root.Dev.UFixedVar.minimum == 0.0
        assert root.Dev.UFixedVar.maximum == 4095.9375


def test_fixed_point_overflow_raises_error():
    with ModelVariableRoot() as root:
        # In-range values should round-trip correctly
        root.Dev.FixedVar.set(1.5)
        assert math.isclose(root.Dev.FixedVar.get(), 1.5, abs_tol=1e-6)

        root.Dev.UFixedVar.set(2.25)
        assert math.isclose(root.Dev.UFixedVar.get(), 2.25, abs_tol=1e-6)

        # Fixed(16, 4) range: -2048.0 to 2047.9375
        # Overflow must raise, not silently clip
        with pytest.raises(Exception, match="Value range error"):
            root.Dev.FixedVar.set(2048.0)

        with pytest.raises(Exception, match="Value range error"):
            root.Dev.FixedVar.set(-2049.0)

        # UFixed(16, 4) range: 0.0 to 4095.9375 (full unsigned range)
        with pytest.raises(Exception, match="Value range error"):
            root.Dev.UFixedVar.set(4096.0)

        with pytest.raises(Exception, match="Value range error"):
            root.Dev.UFixedVar.set(-1.0)

        # Boundary values should work
        root.Dev.FixedVar.set(2047.9375)
        assert math.isclose(root.Dev.FixedVar.get(), 2047.9375, abs_tol=1e-6)

        root.Dev.FixedVar.set(-2048.0)
        assert math.isclose(root.Dev.FixedVar.get(), -2048.0, abs_tol=1e-6)

        # UFixed must accept the full unsigned range (including values above
        # the signed-max boundary, which previously misbehaved)
        root.Dev.UFixedVar.set(0.0)
        assert math.isclose(root.Dev.UFixedVar.get(), 0.0, abs_tol=1e-6)

        root.Dev.UFixedVar.set(4095.9375)
        assert math.isclose(root.Dev.UFixedVar.get(), 4095.9375, abs_tol=1e-6)

        root.Dev.UFixedVar.set(3000.5)
        assert math.isclose(root.Dev.UFixedVar.get(), 3000.5, abs_tol=1e-6)


def test_wide_fixed_point_sign_extension_round_trip():
    # Regression test for Block::getFixed sign-extension on wide variables.
    # Historically the read path computed `1 << valueBits_` on a plain int,
    # which is undefined behavior for valueBits_ >= 31 and silently broke
    # negative-value round-trips for Fixed variables wider than 31 bits.
    with ModelVariableRoot() as root:
        # Fixed(32, 0): int32 range round-trips
        for v in (0.0, 1.0, -1.0, 2147483647.0, -2147483648.0):
            root.Dev.Fixed32Var.set(v)
            assert math.isclose(root.Dev.Fixed32Var.get(), v, abs_tol=0.0), (
                f"Fixed32Var round-trip failed for {v}"
            )

        # Fixed(40, 8): non-byte-aligned wide width with a fractional part
        for v in (0.0, 0.5, -0.5, 1023.75, -1024.0):
            root.Dev.Fixed40Var.set(v)
            assert math.isclose(
                root.Dev.Fixed40Var.get(), v, abs_tol=1.0 / (2**8)
            ), f"Fixed40Var round-trip failed for {v}"

        # Fixed(64, 0): values exactly representable as double. Avoid 2**63
        # boundaries because doubles cannot represent INT64_MIN/INT64_MAX
        # exactly — the stored integer would round.
        for v in (0.0, 1.0, -1.0, float(2**50), float(-(2**50))):
            root.Dev.Fixed64Var.set(v)
            assert math.isclose(root.Dev.Fixed64Var.get(), v, abs_tol=0.0), (
                f"Fixed64Var round-trip failed for {v}"
            )


def test_wide_ufixed_point_round_trip():
    # Regression test for Block::setUFixed / Block::getUFixed at wide widths.
    # Covers the `valueBits_ >= 64 ? UINT64_MAX : ((1ULL << valueBits_) - 1)`
    # branch in setUFixed's max-range computation and confirms reads do not
    # sign-extend (values above 2^(bitSize-1) must round-trip cleanly).
    with ModelVariableRoot() as root:
        # UFixed(32, 0): full unsigned 32-bit range, including values above
        # the signed-max boundary which previously misbehaved.
        for v in (0.0, 1.0, float(2**31), float(2**32 - 1)):
            root.Dev.UFixed32Var.set(v)
            assert math.isclose(root.Dev.UFixed32Var.get(), v, abs_tol=0.0), (
                f"UFixed32Var round-trip failed for {v}"
            )

        # UFixed(40, 8): non-byte-aligned wide width with fractional bits.
        for v in (0.0, 0.5, 1023.75, float(2**32) / (2**8)):
            root.Dev.UFixed40Var.set(v)
            assert math.isclose(
                root.Dev.UFixed40Var.get(), v, abs_tol=1.0 / (2**8)
            ), f"UFixed40Var round-trip failed for {v}"

        # UFixed(64, 0): exercises the UINT64_MAX cap branch. Use values that
        # are exactly representable as double (avoid 2**64 - 1 which rounds).
        for v in (0.0, 1.0, float(2**50), float(2**53)):
            root.Dev.UFixed64Var.set(v)
            assert math.isclose(root.Dev.UFixed64Var.get(), v, abs_tol=0.0), (
                f"UFixed64Var round-trip failed for {v}"
            )

        # Negative writes must still be rejected even at wide widths
        with pytest.raises(Exception):
            root.Dev.UFixed32Var.set(-1.0)
        with pytest.raises(Exception):
            root.Dev.UFixed64Var.set(-1.0)


def test_fixed_point_list_variables_round_trip():
    # Regression test for the list-variable (numValues > 1) path in
    # Block::setFixedPy / Block::getFixedPy, which dispatches to the signed
    # or unsigned scalar setter/getter via a modelId check. Covers both the
    # numpy-array write path and the per-element list write path.
    with ModelVariableRoot() as root:
        # Signed Fixed list: write a Python list, read back, check each element.
        fixed_values = [-128.0, -0.5, 0.0, 127.9375]
        root.Dev.FixedListVar.set(fixed_values)
        for i, v in enumerate(fixed_values):
            got = root.Dev.FixedListVar.get(index=i)
            assert math.isclose(got, v, abs_tol=1e-6), (
                f"FixedListVar[{i}] round-trip failed: expected {v}, got {got}"
            )

        # Unsigned UFixed list: must handle values above the signed-max
        # boundary (>= 2**(valueBits-1)) without sign-extending on read.
        ufixed_values = [0.0, 0.25, 2048.0, 4095.9375]
        root.Dev.UFixedListVar.set(ufixed_values)
        for i, v in enumerate(ufixed_values):
            got = root.Dev.UFixedListVar.get(index=i)
            assert math.isclose(got, v, abs_tol=1e-6), (
                f"UFixedListVar[{i}] round-trip failed: expected {v}, got {got}"
            )

        # Negative writes into the unsigned list must still be rejected.
        with pytest.raises(Exception):
            root.Dev.UFixedListVar.set([-1.0, 0.0, 0.0, 0.0])

def test_float16_remote_variable_boundary_values():
    with ModelVariableRoot() as root:
        # Zero
        root.Dev.Float16Var.set(0.0)
        assert root.Dev.Float16Var.get() == 0.0

        # Max representable half-precision value
        root.Dev.Float16Var.set(65504.0)
        assert math.isclose(root.Dev.Float16Var.get(), 65504.0, rel_tol=0.0, abs_tol=1.0)

        # Negative max
        root.Dev.Float16Var.set(-65504.0)
        assert math.isclose(root.Dev.Float16Var.get(), -65504.0, rel_tol=0.0, abs_tol=1.0)

        # Small normal value near the half-precision minimum normal range
        root.Dev.Float16Var.set(0.0001)
        result = root.Dev.Float16Var.get()
        assert math.isclose(result, 0.0001, rel_tol=0.1)

        # Smallest positive half-precision subnormal (2**-24) exercises the
        # floatToHalf/halfToFloat denormal conversion path in the C++ Block code.
        subnormal = 2 ** -24
        root.Dev.Float16Var.set(subnormal)
        result = root.Dev.Float16Var.get()
        assert result > 0.0
        assert math.isclose(result, subnormal, rel_tol=0.0, abs_tol=subnormal)
