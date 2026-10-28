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

# Exercises the key translation of the embedded terminal widget. keyToBytes is
# a pure function, so no QApplication and no display are needed; importing
# qtpy.QtCore for the key constants does not require an application instance.
# The pseudo-terminal and screen behaviour is covered by
# test_pydm_terminal_core.py, which needs no Qt at all.

import pytest

try:
    import pyte  # noqa: F401
    from qtpy.QtCore import Qt
    from pyrogue.pydm.widgets.terminal import keyToBytes
except Exception as exc:
    pytest.skip(
        f"PyDM/Qt test dependencies unavailable: {exc}",
        allow_module_level=True,
    )


@pytest.mark.parametrize("key,expected", [
    (Qt.Key_Return,    b'\r'),
    (Qt.Key_Enter,     b'\r'),
    (Qt.Key_Backspace, b'\x7f'),
    (Qt.Key_Tab,       b'\t'),
    (Qt.Key_Backtab,   b'\x1b[Z'),
    (Qt.Key_Escape,    b'\x1b'),
    (Qt.Key_Up,        b'\x1b[A'),
    (Qt.Key_Down,      b'\x1b[B'),
    (Qt.Key_Right,     b'\x1b[C'),
    (Qt.Key_Left,      b'\x1b[D'),
    (Qt.Key_Home,      b'\x1b[H'),
    (Qt.Key_End,       b'\x1b[F'),
    (Qt.Key_Insert,    b'\x1b[2~'),
    (Qt.Key_Delete,    b'\x1b[3~'),
    (Qt.Key_PageUp,    b'\x1b[5~'),
    (Qt.Key_PageDown,  b'\x1b[6~'),
    (Qt.Key_F1,        b'\x1bOP'),
    (Qt.Key_F4,        b'\x1bOS'),
    (Qt.Key_F5,        b'\x1b[15~'),
    (Qt.Key_F10,       b'\x1b[21~'),
    (Qt.Key_F12,       b'\x1b[24~'),
])
def test_special_keys(key, expected):
    assert keyToBytes(key, Qt.NoModifier, '') == expected


def test_backspace_sends_delete_not_backspace():
    # readline and the xterm terminfo entry expect DEL here. Sending BS instead
    # is the classic mistake and makes backspace stop working at the prompt.
    assert keyToBytes(Qt.Key_Backspace, Qt.NoModifier, '\x08') == b'\x7f'


def test_printable_text_passes_through():
    assert keyToBytes(Qt.Key_A, Qt.NoModifier, 'a') == b'a'
    assert keyToBytes(Qt.Key_Space, Qt.NoModifier, ' ') == b' '


def test_non_ascii_text_is_utf8_encoded():
    assert keyToBytes(Qt.Key_unknown, Qt.NoModifier, 'µ') == 'µ'.encode('utf-8')


@pytest.mark.parametrize("key,expected", [
    (Qt.Key_A, b'\x01'),
    (Qt.Key_C, b'\x03'),
    (Qt.Key_D, b'\x04'),
    (Qt.Key_U, b'\x15'),
    (Qt.Key_Z, b'\x1a'),
])
def test_control_letters_map_to_control_codes(key, expected):
    # Ctrl-C in particular must reach the shell as an interrupt rather than
    # being swallowed as a copy shortcut.
    assert keyToBytes(key, Qt.ControlModifier, '') == expected


def test_control_space_and_bracket_group():
    assert keyToBytes(Qt.Key_Space, Qt.ControlModifier, '') == b'\x00'
    assert keyToBytes(Qt.Key_BracketLeft, Qt.ControlModifier, '') == b'\x1b'
    assert keyToBytes(Qt.Key_Backslash, Qt.ControlModifier, '') == b'\x1c'
    assert keyToBytes(Qt.Key_BracketRight, Qt.ControlModifier, '') == b'\x1d'


def test_ctrl_shift_copy_paste_send_nothing():
    # These are handled as clipboard actions by the widget, so the translation
    # must not also forward them to the shell.
    mods = Qt.ControlModifier | Qt.ShiftModifier
    assert keyToBytes(Qt.Key_C, mods, '') == b''
    assert keyToBytes(Qt.Key_V, mods, '') == b''


def test_alt_prefixes_escape():
    assert keyToBytes(Qt.Key_B, Qt.AltModifier, 'b') == b'\x1bb'
    assert keyToBytes(Qt.Key_Left, Qt.AltModifier, '') == b'\x1b\x1b[D'


@pytest.mark.parametrize("key", [
    Qt.Key_Shift, Qt.Key_Control, Qt.Key_Alt, Qt.Key_Meta,
    Qt.Key_CapsLock, Qt.Key_NumLock, Qt.Key_ScrollLock,
])
def test_bare_modifier_keys_send_nothing(key):
    assert keyToBytes(key, Qt.NoModifier, '') == b''


def test_unmapped_key_without_text_sends_nothing():
    assert keyToBytes(Qt.Key_unknown, Qt.NoModifier, '') == b''


def test_every_result_is_bytes():
    # A str slipping into the table would only fail later at os.write().
    for key in (Qt.Key_Return, Qt.Key_Up, Qt.Key_F7, Qt.Key_A, Qt.Key_Shift):
        assert isinstance(keyToBytes(key, Qt.NoModifier, ''), bytes)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
