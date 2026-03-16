import numpy as np
import pyrogue as pr
import pyrogue._Block as block_mod
import rogue.interfaces.memory as rim
import pytest


class FakeBlock:
    def __init__(self):
        self.started = []
        self.checked = 0

    def _startTransaction(self, tx_type, force_wr, check, variable, index):
        self.started.append((tx_type, force_wr, check, variable, index))

    def _checkTransaction(self):
        self.checked += 1


class FakeVariable:
    def __init__(self, value, native_type=int, update_notify=True):
        self.path = "Root.Var"
        self.mode = "RW"
        self.parent = None
        self._nativeType = native_type
        self._updateNotify = update_notify
        self.queue_updates = 0
        self.path = "Root.Var"

    def _queueUpdate(self):
        self.queue_updates += 1


def test_block_transaction_helpers_forward_expected_arguments():
    first = FakeBlock()
    second = FakeBlock()
    variable = object()

    pr.startTransaction(first, type=rim.Write, forceWr=True, check=True, variable=variable, index=3)
    pr.checkTransaction(first)
    pr.writeBlocks([first, second], force=True, checkEach=True, index=7)
    pr.verifyBlocks([first, second], checkEach=True)
    pr.readBlocks([first, second], checkEach=True)
    pr.checkBlocks([first, second])
    pr.writeAndVerifyBlocks([first, second], force=True, checkEach=True, index=9)
    pr.readAndCheckBlocks([first, second], checkEach=True)

    assert first.started[0] == (rim.Write, True, True, variable, 3)
    assert first.started[1:] == [
        (rim.Write, True, True, None, 7),
        (rim.Verify, False, True, None, -1),
        (rim.Read, False, True, None, -1),
        (rim.Write, True, True, None, 9),
        (rim.Verify, False, True, None, -1),
        (rim.Read, False, True, None, -1),
    ]
    assert second.started == [
        (rim.Write, True, True, None, 7),
        (rim.Verify, False, True, None, -1),
        (rim.Read, False, True, None, -1),
        (rim.Write, True, True, None, 9),
        (rim.Verify, False, True, None, -1),
        (rim.Read, False, True, None, -1),
    ]
    assert first.checked == 4
    assert second.checked == 3


def test_memory_error_string_contains_context():
    err = block_mod.MemoryError(name="Device", address=0x24, msg="failed", size=4)
    assert str(err) == repr("Memory Error for Device at address 0x000024 failed")


def test_local_block_set_get_range_and_notifications():
    seen = []
    variable = FakeVariable(1)
    block = block_mod.LocalBlock(
        variable=variable,
        localSet=lambda dev=None, var=None, value=None, changed=None: seen.append((value, changed)),
        localGet=lambda dev=None, var=None: 11,
        minimum=0,
        maximum=20,
        value=1,
    )

    block.set(variable, 5)
    assert block.get(variable) == 11
    assert seen == [(5, True)]

    block._checkTransaction()
    assert variable.queue_updates == 1

    with pytest.raises(pr.VariableError, match="Value range error"):
        block.set(variable, 25)

    block.setEnable(False)
    block.set(variable, 6)
    assert seen == [(5, True)]


def test_local_block_array_numpy_and_inplace_helpers():
    array_var = FakeVariable([1, 2, 3], native_type=list)
    array_block = block_mod.LocalBlock(
        variable=array_var,
        localSet=None,
        localGet=None,
        minimum=None,
        maximum=None,
        value=[1, 2, 3],
    )

    array_block.set(array_var, 9, index=1)
    assert array_block.get(array_var, index=1) == 9

    numpy_var = FakeVariable(np.array([1, 2]), native_type=np.ndarray)
    numpy_block = block_mod.LocalBlock(
        variable=numpy_var,
        localSet=None,
        localGet=None,
        minimum=None,
        maximum=None,
        value=np.array([1, 2]),
    )
    numpy_block.set(numpy_var, np.array([1, 2]))
    assert np.array_equal(numpy_block.get(numpy_var), np.array([1, 2]))

    math_var = FakeVariable(8)
    math_block = block_mod.LocalBlock(
        variable=math_var,
        localSet=None,
        localGet=None,
        minimum=None,
        maximum=None,
        value=8,
    )

    # These in-place helpers are the convenience operators used by LocalVariable.
    math_block._iadd(2)
    math_block._imul(3)
    math_block._ifloordiv(2)
    math_block._imod(5)
    math_block._ipow(2)
    math_block._ilshift(1)
    math_block._irshift(2)
    math_block._iand(7)
    math_block._ixor(3)
    math_block._ior(8)

    assert math_block.get(math_var) == 11
    assert math_var.queue_updates == 10
