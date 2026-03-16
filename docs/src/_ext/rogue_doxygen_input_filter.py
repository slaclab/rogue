#!/usr/bin/env python3
"""Normalize selected C++ alias spellings before Doxygen parses .cpp files."""

from __future__ import annotations

import pathlib
import re
import sys


NAMESPACE_ALIAS_RE = re.compile(r"^\s*namespace\s+([A-Za-z_]\w*)\s*=\s*([^;]+);", re.MULTILINE)
TYPE_ALIAS_MAP = {
    "rogue::interfaces::api::BspPtr": "std::shared_ptr<rogue::interfaces::api::Bsp>",
}


def expand_namespace_aliases(text: str) -> str:
    aliases = {match.group(1): match.group(2).strip() for match in NAMESPACE_ALIAS_RE.finditer(text)}
    for alias, target in sorted(aliases.items(), key=lambda item: len(item[0]), reverse=True):
        text = re.sub(rf"\b{re.escape(alias)}::", f"{target}::", text)
    return text


def expand_type_aliases(text: str) -> str:
    for alias, target in TYPE_ALIAS_MAP.items():
        text = re.sub(rf"\b{re.escape(alias)}\b", target, text)
    return text


def main() -> int:
    if len(sys.argv) != 2:
        return 1

    source_path = pathlib.Path(sys.argv[1])
    text = source_path.read_text()
    text = expand_namespace_aliases(text)
    text = expand_type_aliases(text)
    sys.stdout.write(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
