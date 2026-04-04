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

        # Small value (tests subnormal handling through the C++ path)
        root.Dev.Float16Var.set(0.0001)
        result = root.Dev.Float16Var.get()
        assert math.isclose(result, 0.0001, rel_tol=0.1)
