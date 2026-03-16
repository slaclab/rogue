import struct

import numpy as np
import pytest
import pyrogue as pr
import rogue.interfaces.memory as rim


def test_model_helper_functions_and_instance_cache():
    assert pr.wordCount(0, 8) == 1
    assert pr.wordCount(9, 8) == 2
    assert pr.byteCount(9) == 2
    assert pr.reverseBits(0b1010, 4) == 0b0101
    assert pr.twosComplement(0b1111, 4) == -1

    # ModelMeta caches instances by constructor arguments so variables can
    # share immutable model metadata.
    assert pr.UInt(16) is pr.UInt(16)
    assert pr.UInt(16) is not pr.UInt(32)


def test_uint_and_reversed_models_round_trip():
    model = pr.UInt(12)
    assert model.name == "UInt12"
    assert model.ndType == np.dtype(np.uint32)
    assert model.toBytes(0xABC) == b"\xbc\x0a"
    assert model.fromBytes(b"\xbc\x0a") == 0xABC
    assert model.fromString("0x2a") == 42
    assert model.minValue() == 0
    assert model.maxValue() == 0xFFF

    reversed_model = pr.UIntReversed(4)
    # The reversed-bit model swaps bit order before serializing.
    assert reversed_model.toBytes(0b1101) == b"\x0b"
    assert reversed_model.fromBytes(b"\x0b") == 0b1101


def test_int_models_handle_signed_values_and_endianness():
    model = pr.Int(12)
    assert model.name == "Int12"
    assert model.ndType == np.dtype(np.int32)
    assert model.toBytes(-1) == b"\xff\x0f"
    assert model.fromBytes(b"\xff\x0f") == -1
    assert model.fromString("0xfff") == -1
    assert model.minValue() == -(2 ** 11)
    assert model.maxValue() == (2 ** 11) - 1

    be_model = pr.IntBE(16)
    assert be_model.isBigEndian is True
    assert be_model.toBytes(-2) == b"\xff\xfe"
    assert be_model.fromBytes(b"\xff\xfe") == -2


def test_bool_and_string_models_convert_values():
    bool_model = pr.Bool(1)
    assert bool_model.ndType == np.dtype(bool)
    assert bool_model.toBytes(True) == b"\x01"
    assert bool_model.fromBytes(b"\x00") is False
    assert bool_model.fromString("TrUe") is True
    assert bool_model.minValue() == 0
    assert bool_model.maxValue() == 1

    string_model = pr.String(32)
    assert string_model.name == "String(4)"
    payload = string_model.toBytes("abc")
    assert payload == bytearray(b"abc\x00")
    assert string_model.fromBytes(payload) == "abc"
    assert string_model.fromString("value") == "value"


def test_float_double_and_fixed_models_report_metadata():
    float_model = pr.Float(32)
    assert float_model.name == "Float32"
    assert float_model.ndType == np.dtype(np.float32)
    assert float_model.toBytes(1.25) == bytearray(struct.pack("f", 1.25))
    assert float_model.fromBytes(struct.pack("f", 1.25)) == 1.25
    assert float_model.fromString("2.5") == 2.5
    assert float_model.minValue() == -3.4e38
    assert float_model.maxValue() == 3.4e38

    double_model = pr.DoubleBE(64)
    assert double_model.isBigEndian is True
    assert double_model.ndType == np.dtype(np.float64)
    assert double_model.toBytes(1.5) == bytearray(struct.pack("!d", 1.5))
    assert double_model.fromBytes(struct.pack("!d", 1.5)) == 1.5

    fixed = pr.Fixed(16, 4)
    ufixed = pr.UFixed(16, 4)
    assert fixed.name == "Fixed_16_4"
    assert ufixed.name == "UFixed_16_4"
    assert fixed.ndType == np.dtype(np.float64)
    assert ufixed.ndType == np.dtype(np.float64)


@pytest.mark.parametrize(
    ("factory", "bit_size", "bin_point", "expected_name", "signed"),
    [
        # Zero fractional bits is a common integer-like fixed-point encoding.
        (pr.Fixed, 1, 0, "Fixed_1_0", True),
        (pr.UFixed, 1, 0, "UFixed_1_0", False),
        # Bin point equal to the bit width stresses the "all fractional" case.
        (pr.Fixed, 16, 16, "Fixed_16_16", True),
        (pr.UFixed, 16, 16, "UFixed_16_16", False),
        # Non-byte-aligned widths are common in FPGA register maps.
        (pr.Fixed, 17, 5, "Fixed_17_5", True),
        (pr.UFixed, 17, 5, "UFixed_17_5", False),
        # Large widths should still preserve metadata cleanly.
        (pr.Fixed, 64, 32, "Fixed_64_32", True),
        (pr.UFixed, 64, 32, "UFixed_64_32", False),
    ],
)
def test_fixed_models_handle_multiple_sizes_and_corner_cases(factory, bit_size, bin_point, expected_name, signed):
    model = factory(bit_size, bin_point)

    assert model.name == expected_name
    assert model.bitSize == bit_size
    assert model.binPoint == bin_point
    assert model.signed is signed
    assert model.pytype is float
    assert model.ndType == np.dtype(np.float64)
    assert model.modelId == rim.Fixed


def test_fixed_model_cache_keys_include_bit_size_and_bin_point():
    # The cache key needs both values so distinct fixed-point encodings do not
    # alias to the same shared model object.
    assert pr.Fixed(16, 4) is pr.Fixed(16, 4)
    assert pr.Fixed(16, 4) is not pr.Fixed(16, 5)
    assert pr.Fixed(16, 4) is not pr.Fixed(24, 4)
    assert pr.UFixed(16, 4) is pr.UFixed(16, 4)
    assert pr.UFixed(16, 4) is not pr.UFixed(16, 5)
