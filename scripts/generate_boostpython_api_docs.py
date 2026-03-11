#!/usr/bin/env python3
"""Generate Boost.Python-driven Python API RST content for one page."""

from __future__ import annotations

import argparse
import pathlib
import re
import sys


REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
EXT_ROOT = REPO_ROOT / "docs" / "src" / "_ext"
sys.path.insert(0, str(EXT_ROOT))

from rogue_boostpython_core import render_embedded_api


def extract_autoclass_target(text: str) -> str:
    directive_match = re.search(r"^\.\.\s+rogue_boostpython_api::\s+([^\s]+)\s*$", text, re.MULTILINE)
    if directive_match:
        return directive_match.group(1)
    match = re.search(r"^\.\.\s+autoclass::\s+([^\s]+)\s*$", text, re.MULTILINE)
    if not match:
        raise SystemExit("Could not locate '.. rogue_boostpython_api::' or '.. autoclass::' target in the RST page")
    return match.group(1)


def include_internal_methods(text: str) -> bool:
    return ":include-internal:" in text


def replace_directive_block(
    text: str,
    python_name: str,
    include_init: bool,
    include_internal: bool,
) -> str:
    directive = [f".. rogue_boostpython_api:: {python_name}"]
    if include_init:
        directive.append("   :include-init:")
    if include_internal:
        directive.append("   :include-internal:")
    block = "\n".join(directive)

    pattern = re.compile(
        r"^\.\.\s+rogue_boostpython_api::\s+[^\s]+\n(?:^[ \t]+:.*\n?)*",
        re.MULTILINE,
    )
    if pattern.search(text):
        return pattern.sub(block + "\n", text, count=1)
    autoclass_pattern = re.compile(
        r"^\.\.\s+autoclass::\s+[^\s]+\n(?:^[ \t]+:.*\n?)*",
        re.MULTILINE,
    )
    if autoclass_pattern.search(text):
        return autoclass_pattern.sub(block + "\n", text, count=1)
    return text.rstrip() + "\n\n" + block + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rst", type=pathlib.Path, required=True, help="RST page to inspect or update")
    parser.add_argument("--write", action="store_true", help="Replace/update the directive in-place")
    args = parser.parse_args()

    rst_path = args.rst.resolve()
    text = rst_path.read_text()
    python_name = extract_autoclass_target(text)
    include_init = ":special-members: __init__" in text or ":include-init:" in text
    include_internal = include_internal_methods(text)

    if args.write:
        rst_path.write_text(replace_directive_block(text, python_name, include_init, include_internal))
    else:
        sys.stdout.write(
            render_embedded_api(
                python_name,
                include_init=include_init,
                include_internal=include_internal,
            )
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
