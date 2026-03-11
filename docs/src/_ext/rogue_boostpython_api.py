"""Sphinx directive for rendering Rogue Boost.Python API details."""

from __future__ import annotations

from docutils import nodes
from docutils.parsers.rst import Directive
from sphinx.util.parsing import nested_parse_to_nodes

from rogue_boostpython_core import render_embedded_api


class RogueBoostPythonApiDirective(Directive):
    required_arguments = 1
    optional_arguments = 0
    final_argument_whitespace = False
    has_content = False
    option_spec = {
        "include-init": lambda arg: True,
        "include-internal": lambda arg: True,
    }

    def run(self) -> list[nodes.Node]:
        python_name = self.arguments[0].strip()
        include_init = "include-init" in self.options
        include_internal = "include-internal" in self.options
        generated = render_embedded_api(
            python_name,
            include_init=include_init,
            include_internal=include_internal,
        )

        return nested_parse_to_nodes(
            self.state,
            generated,
            allow_section_headings=True,
            keep_title_context=False,
        )


def setup(app):
    app.add_directive("rogue_boostpython_api", RogueBoostPythonApiDirective)
    return {
        "version": "0.1",
        "parallel_read_safe": True,
        "parallel_write_safe": True,
    }
