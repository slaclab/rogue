"""Shared Boost.Python binding parser and RST renderer for Rogue docs."""

from __future__ import annotations

import dataclasses
import pathlib
import re
from functools import lru_cache
from typing import Iterable


REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]
SRC_ROOT = REPO_ROOT / "src" / "rogue"


@dataclasses.dataclass
class MethodDoc:
    name: str
    args: list[str]
    brief: str
    details: str
    params: dict[str, str]
    returns: str
    cpp_target: str
    cpp_role: str = "func"

    @property
    def is_internal(self) -> bool:
        return self.name.startswith("_") and not self.name.startswith("__")

    @property
    def is_dunder(self) -> bool:
        return self.name.startswith("__") and self.name.endswith("__")

    @property
    def signature(self) -> str:
        if self.name in {"__lshift__", "__rshift__", "__eq__"}:
            display = {
                "__lshift__": "__lshift__(other)",
                "__rshift__": "__rshift__(other)",
                "__eq__": "__eq__(other)",
            }
            return display[self.name]
        if self.args:
            return f"{self.name}({', '.join(self.args)})"
        return f"{self.name}()"

    @property
    def description(self) -> str:
        text = "\n\n".join(part for part in [self.brief, self.details] if part)
        text = normalize_doc_block(text)
        if not text:
            return "No binding docstring provided."
        return text


@dataclasses.dataclass
class ClassDoc:
    python_name: str
    class_name: str
    cpp_name: str
    cpp_target: str
    source_path: pathlib.Path
    bases_cpp: list[str]
    class_doc: str
    ctor_doc: str
    ctor_args: list[str]
    ctor_params: dict[str, str]
    ctor_cpp_target: str
    ctor_cpp_role: str
    methods: list[MethodDoc]


@dataclasses.dataclass
class HeaderDoc:
    class_docs: dict[str, MethodDoc]
    method_docs: dict[str, MethodDoc]


@dataclasses.dataclass
class ParsedComment:
    brief: str
    details: str
    params: dict[str, str]
    returns: str


def normalize_doc(text: str) -> str:
    text = text.strip()
    if not text:
        return ""
    text = re.sub(r"[ \t]+", " ", text.replace("\\n", " ")).strip()
    # Doxygen comments in this tree commonly use Markdown-style single backticks
    # for inline code. Convert them to reST inline literals for Sphinx.
    text = re.sub(r"(?<!`)`([^`\n]+)`(?!`)", r"``\1``", text)
    return text


def normalize_doc_block(text: str) -> str:
    paragraphs = [part.strip() for part in re.split(r"\n\s*\n", text) if part.strip()]
    rendered: list[str] = []
    for paragraph in paragraphs:
        lines = [line.strip() for line in paragraph.splitlines() if line.strip()]
        if not lines:
            continue

        chunk: list[str] = []
        bullet_lines: list[str] = []
        for line in lines:
            if line.startswith(("- ", "* ")):
                if chunk:
                    rendered.append(normalize_doc(" ".join(chunk)))
                    chunk = []
                bullet_lines.append(normalize_doc(line))
            else:
                if bullet_lines:
                    bullet_lines[-1] = normalize_doc(f"{bullet_lines[-1]} {line}")
                else:
                    chunk.append(line)
        if chunk:
            rendered.append(normalize_doc(" ".join(chunk)))
        if bullet_lines:
            rendered.append("\n".join(bullet_lines))

    return "\n\n".join(part for part in rendered if part)


def extract_string_literals(text: str) -> list[str]:
    parts: list[str] = []
    i = 0
    while i < len(text):
        if text[i] != '"':
            i += 1
            continue
        i += 1
        buf: list[str] = []
        while i < len(text):
            char = text[i]
            if char == "\\" and i + 1 < len(text):
                esc = text[i + 1]
                if esc == "n":
                    buf.append("\\n")
                else:
                    buf.append(esc)
                i += 2
                continue
            if char == '"':
                i += 1
                break
            buf.append(char)
            i += 1
        parts.append("".join(buf))
    return parts


def split_top_level(text: str, delimiter: str = ",") -> list[str]:
    parts: list[str] = []
    start = 0
    depth_paren = 0
    depth_angle = 0
    depth_brace = 0
    in_string = False
    escape = False

    for i, char in enumerate(text):
        if in_string:
            if escape:
                escape = False
            elif char == "\\":
                escape = True
            elif char == '"':
                in_string = False
            continue

        if char == '"':
            in_string = True
        elif char == "(":
            depth_paren += 1
        elif char == ")":
            depth_paren -= 1
        elif char == "<":
            depth_angle += 1
        elif char == ">":
            depth_angle -= 1
        elif char == "{":
            depth_brace += 1
        elif char == "}":
            depth_brace -= 1
        elif char == delimiter and depth_paren == 0 and depth_angle == 0 and depth_brace == 0:
            parts.append(text[start:i].strip())
            start = i + 1

    parts.append(text[start:].strip())
    return [part for part in parts if part]


def find_matching(text: str, start: int, opening: str, closing: str) -> int:
    depth = 0
    in_string = False
    escape = False
    for i in range(start, len(text)):
        char = text[i]
        if in_string:
            if escape:
                escape = False
            elif char == "\\":
                escape = True
            elif char == '"':
                in_string = False
            continue

        if char == '"':
            in_string = True
            continue

        if char == opening:
            depth += 1
        elif char == closing:
            depth -= 1
            if depth == 0:
                return i
    raise ValueError(f"Unmatched {opening}{closing} in text segment")


def resolve_name(name: str, aliases: dict[str, str]) -> str:
    name = name.strip()
    if not name:
        return name
    if "::" not in name:
        return aliases.get(name, name)
    head, tail = name.split("::", 1)
    return f"{aliases.get(head, head)}::{tail}"


def load_module_paths() -> dict[pathlib.Path, str]:
    mapping: dict[pathlib.Path, str] = {}
    for module_cpp in SRC_ROOT.rglob("module.cpp"):
        text = module_cpp.read_text()
        match = re.search(r'PyImport_AddModule\("([^"]+)"\)', text)
        if match:
            mapping[module_cpp.parent] = match.group(1)
    return mapping


def resolve_header_path(source_path: pathlib.Path) -> pathlib.Path | None:
    relative = source_path.relative_to(SRC_ROOT)
    header_path = REPO_ROOT / "include" / "rogue" / relative.with_suffix(".h")
    if header_path.exists():
        return header_path
    return None


def resolve_header_for_cpp_name(cpp_name: str) -> pathlib.Path | None:
    if not cpp_name.startswith("rogue::"):
        return None
    parts = cpp_name.split("::")
    header_path = REPO_ROOT / "include" / "/".join(parts).replace("rogue/", "rogue", 1)
    header_path = REPO_ROOT / "include" / pathlib.Path(*parts).with_suffix(".h")
    if header_path.exists():
        return header_path
    return None


def nearest_module_path(source_path: pathlib.Path, module_paths: dict[pathlib.Path, str]) -> str:
    parent = source_path.parent
    while parent != SRC_ROOT.parent:
        if parent in module_paths:
            return module_paths[parent]
        parent = parent.parent
    return "rogue"


def extract_setup_python_body(text: str) -> tuple[str, str]:
    match = re.search(r"void\s+([^\s(]+)::setup_python\(\)\s*\{", text)
    if not match:
        raise ValueError("Could not locate setup_python()")
    qualifier = match.group(1)
    brace_start = text.find("{", match.end() - 1)
    brace_end = find_matching(text, brace_start, "{", "}")
    return qualifier, text[brace_start + 1 : brace_end]


def parse_doxygen_comment(raw_comment: str) -> ParsedComment:
    lines: list[str] = []
    for line in raw_comment.splitlines():
        line = re.sub(r"^\s*/?\**\s?", "", line).strip()
        if line:
            lines.append(line)

    brief: list[str] = []
    details: list[str] = []
    params: dict[str, list[str]] = {}
    returns: list[str] = []
    current_param: str | None = None
    mode = "body"
    for line in lines:
        if line.startswith("@brief"):
            brief.append(line[len("@brief") :].strip())
            mode = "brief"
            current_param = None
            continue
        if line.startswith("@details"):
            details.append(line[len("@details") :].strip())
            mode = "details"
            current_param = None
            continue
        if line.startswith("@param"):
            match = re.match(r"@param(?:\s*\[[^\]]+\])?\s+(\w+)\s*(.*)", line)
            if match:
                current_param = match.group(1)
                params.setdefault(current_param, [])
                if match.group(2):
                    params[current_param].append(match.group(2).strip())
            mode = "param"
            continue
        if line.startswith("@return"):
            returns.append(line[len("@return") :].strip())
            mode = "return"
            current_param = None
            continue
        if line.startswith("@tparam"):
            mode = "tags"
            current_param = None
            continue
        if line.startswith("@"):
            mode = "tags"
            current_param = None
            continue

        if mode == "details":
            details.append(line)
        elif mode == "param" and current_param:
            params.setdefault(current_param, []).append(line)
        elif mode == "return":
            returns.append(line)
        elif mode in {"brief", "body"}:
            brief.append(line)

    return ParsedComment(
        brief=normalize_doc_block("\n".join(brief)),
        details=normalize_doc_block("\n".join(details)),
        params={key: normalize_doc(" ".join(value)) for key, value in params.items() if normalize_doc(" ".join(value))},
        returns=normalize_doc(" ".join(returns)),
    )


def declaration_name(declaration: str) -> str | None:
    class_match = re.search(r"\bclass\s+([A-Za-z_]\w*)\b", declaration)
    if class_match:
        return class_match.group(1)

    prefix = declaration.split("(", 1)[0]
    names = re.findall(r"(operator[^\s(]+|~?[A-Za-z_]\w*)", prefix)
    return names[-1] if names else None


@lru_cache(maxsize=None)
def parse_header_docs(header_path: pathlib.Path) -> HeaderDoc:
    text = header_path.read_text()
    class_docs: dict[str, MethodDoc] = {}
    method_docs: dict[str, MethodDoc] = {}
    pattern = re.compile(r"/\*\*(.*?)\*/\s*([^;{]+[;{])", re.DOTALL)
    for comment, declaration in pattern.findall(text):
        parsed = parse_doxygen_comment(comment)
        if not any([parsed.brief, parsed.details, parsed.params, parsed.returns]):
            continue
        name = declaration_name(declaration)
        if not name:
            continue
        doc = MethodDoc(
            name=name,
            args=[],
            brief=parsed.brief,
            details=parsed.details,
            params=parsed.params,
            returns=parsed.returns,
            cpp_target="",
        )
        if declaration.lstrip().startswith("class "):
            class_docs[name] = doc
        else:
            method_docs[name] = doc
    return HeaderDoc(class_docs=class_docs, method_docs=method_docs)


def lookup_method_doc(cpp_target: str, python_name: str = "") -> MethodDoc | None:
    header_path = resolve_header_for_cpp_name(cpp_target.rsplit("::", 1)[0])
    if not header_path:
        return None
    header_docs = parse_header_docs(header_path)
    target_name = cpp_target.rsplit("::", 1)[-1]
    return header_docs.method_docs.get(python_name) or header_docs.method_docs.get(target_name)


def extract_class_expression(body: str) -> str:
    start = body.find("bp::class_<")
    if start < 0:
        raise ValueError("Could not locate bp::class_<...>")

    template_end = find_matching(body, body.find("<", start), "<", ">")
    in_string = False
    escape = False
    depth_paren = 0
    depth_angle = 0
    depth_brace = 0
    for i in range(start, len(body)):
        char = body[i]
        if in_string:
            if escape:
                escape = False
            elif char == "\\":
                escape = True
            elif char == '"':
                in_string = False
            continue
        if char == '"':
            in_string = True
        elif char == "(":
            depth_paren += 1
        elif char == ")":
            depth_paren -= 1
        elif char == "<":
            depth_angle += 1
        elif char == ">":
            depth_angle -= 1
        elif char == "{":
            depth_brace += 1
        elif char == "}":
            depth_brace -= 1
        elif char == ";" and depth_paren == 0 and depth_angle == 0 and depth_brace == 0:
            return body[start:i]
    raise ValueError("Could not find end of bp::class_ expression")


def parse_method(def_text: str, cpp_class: str, aliases: dict[str, str]) -> MethodDoc | None:
    args = split_top_level(def_text)
    if not args:
        return None
    name_literals = extract_string_literals(args[0])
    if not name_literals:
        return None
    name = name_literals[0]

    bp_args_match = re.search(r"bp::args\((.*?)\)", def_text, re.DOTALL)
    if bp_args_match:
        arg_names = [normalize_doc(value) for value in extract_string_literals(bp_args_match.group(1))]
    else:
        arg_names = [normalize_doc(value) for value in re.findall(r'bp::arg\("([^"]+)"\)', def_text)]

    actual_target = None
    if len(args) > 1:
        func_match = re.search(r"&\s*([A-Za-z_:]\w*(?:::\w+)*)", args[1])
        if func_match:
            actual_target = resolve_name(func_match.group(1), aliases)
            if "::" not in actual_target:
                actual_target = f"{cpp_class}::{actual_target}"
            elif not actual_target.startswith("rogue::"):
                class_short = cpp_class.rsplit("::", 1)[-1]
                if actual_target.startswith(f"{class_short}::"):
                    actual_target = f"{cpp_class.rsplit('::', 1)[0]}::{actual_target}"
            if actual_target.endswith("Py") and not name.startswith("__"):
                actual_target = f"{cpp_class}::{name}"

    literals = extract_string_literals(def_text)
    doc = literals[-1] if len(literals) > 1 else ""
    cpp_target = actual_target or f"{cpp_class}::{name}"
    return MethodDoc(
        name=name,
        args=arg_names,
        brief=normalize_doc(doc),
        details="",
        params={},
        returns="",
        cpp_target=cpp_target,
    )


def parse_binding(source_path: pathlib.Path, module_paths: dict[pathlib.Path, str]) -> ClassDoc | None:
    text = source_path.read_text()
    if "setup_python()" not in text or "bp::class_<" not in text:
        return None

    aliases = {name: target for name, target in re.findall(r"namespace\s+(\w+)\s*=\s*([^;]+);", text)}
    qualifier, body = extract_setup_python_body(text)
    cpp_name = resolve_name(qualifier, aliases)
    class_expr = extract_class_expression(body)

    tmpl_start = class_expr.find("<")
    tmpl_end = find_matching(class_expr, tmpl_start, "<", ">")
    template_parts = split_top_level(class_expr[tmpl_start + 1 : tmpl_end])

    bases_cpp: list[str] = []
    for part in template_parts[1:]:
        bases_match = re.search(r"bp::bases<(.*)>", part, re.DOTALL)
        if bases_match:
            bases_cpp.extend(resolve_name(base, aliases) for base in split_top_level(bases_match.group(1)))

    call_start = class_expr.find("(", tmpl_end)
    call_end = find_matching(class_expr, call_start, "(", ")")
    call_args = split_top_level(class_expr[call_start + 1 : call_end])
    class_name_literals = extract_string_literals(call_args[0]) if call_args else []
    if not class_name_literals:
        return None
    class_name = class_name_literals[0]

    class_doc = ""
    ctor_doc = ""
    ctor_args: list[str] = []
    ctor_params: dict[str, str] = {}
    ctor_cpp_target = cpp_name
    ctor_cpp_role = "class"
    for arg in call_args[1:]:
        if "bp::init" in arg:
            literals = extract_string_literals(arg)
            if literals:
                ctor_doc = literals[-1]
        elif '"' in arg:
            literals = extract_string_literals(arg)
            if literals:
                class_doc = " ".join(literals)

    methods: list[MethodDoc] = []
    pos = 0
    while True:
        def_start = class_expr.find(".def(", pos)
        if def_start < 0:
            break
        open_paren = class_expr.find("(", def_start)
        close_paren = find_matching(class_expr, open_paren, "(", ")")
        method = parse_method(class_expr[open_paren + 1 : close_paren], cpp_name, aliases)
        if method:
            methods.append(method)
        pos = close_paren + 1

    header_path = resolve_header_path(source_path)
    header_docs = parse_header_docs(header_path) if header_path else HeaderDoc({}, {})
    if header_docs.class_docs.get(class_name):
        class_doc = header_docs.class_docs[class_name].description
    if header_docs.method_docs.get(class_name):
        ctor_header_doc = header_docs.method_docs[class_name]
        ctor_doc = ctor_header_doc.description
        ctor_args = list(ctor_header_doc.params.keys()) or ctor_args
        ctor_params = ctor_header_doc.params
    elif header_docs.method_docs.get("create"):
        create_doc = header_docs.method_docs["create"]
        ctor_doc = create_doc.description
        ctor_args = list(create_doc.params.keys()) or ctor_args
        ctor_params = create_doc.params
        ctor_cpp_target = f"{cpp_name}::create"
        ctor_cpp_role = "func"
    resolved_methods: list[MethodDoc] = []
    for method in methods:
        header_method = (
            header_docs.method_docs.get(method.name)
            or header_docs.method_docs.get(method.cpp_target.rsplit("::", 1)[-1])
            or lookup_method_doc(method.cpp_target, method.name)
        )
        if header_method:
            resolved_methods.append(
                dataclasses.replace(
                    method,
                    args=method.args or list(header_method.params.keys()),
                    brief=header_method.brief,
                    details=header_method.details,
                    params=header_method.params,
                    returns=header_method.returns,
                )
            )
        else:
            resolved_methods.append(method)
    methods = resolved_methods

    python_module = nearest_module_path(source_path, module_paths)
    python_name = f"{python_module}.{class_name}"
    return ClassDoc(
        python_name=python_name,
        class_name=class_name,
        cpp_name=cpp_name,
        cpp_target=cpp_name,
        source_path=source_path,
        bases_cpp=bases_cpp,
        class_doc=class_doc,
        ctor_doc=ctor_doc,
        ctor_args=ctor_args,
        ctor_params=ctor_params,
        ctor_cpp_target=ctor_cpp_target,
        ctor_cpp_role=ctor_cpp_role,
        methods=methods,
    )


@lru_cache(maxsize=1)
def scan_bindings() -> dict[str, ClassDoc]:
    module_paths = load_module_paths()
    bindings: dict[str, ClassDoc] = {}
    for source_path in SRC_ROOT.rglob("*.cpp"):
        if source_path.name == "module.cpp":
            continue
        try:
            parsed = parse_binding(source_path, module_paths)
        except ValueError:
            continue
        if parsed:
            bindings[parsed.python_name] = parsed
    return bindings


def render_method_entry(
    method: MethodDoc,
    indent: str = "",
    *,
    no_index: bool = False,
) -> list[str]:
    role = "class" if method.cpp_role == "class" else "func"
    directive = "py:method"
    lines = [f"{indent}.. {directive}:: {method.signature}"]
    if no_index:
        lines.append(f"{indent}   :no-index:")
    lines.append("")
    lines.append(f"{indent}   C++: :cpp:{role}:`{method.cpp_target}`")
    for paragraph in normalize_doc_block(method.description).split("\n\n"):
        if paragraph:
            lines.append("")
            if "\n" in paragraph and all(line.startswith(("- ", "* ")) for line in paragraph.splitlines()):
                for bullet in paragraph.splitlines():
                    lines.append(f"{indent}   {bullet}")
            else:
                lines.append(f"{indent}   {paragraph}")
    for arg in method.args:
        if arg in method.params:
            lines.append("")
            lines.append(f"{indent}   :param {arg}: {method.params[arg]}")
    if method.returns:
        lines.append("")
        lines.append(f"{indent}   :returns: {method.returns}")
    return lines


def render_method_entries(methods: Iterable[MethodDoc], indent: str = "") -> list[str]:
    methods = list(methods)
    if not methods:
        return []
    lines: list[str] = []
    for method in methods:
        lines.extend(render_method_entry(method, indent=indent))
        lines.append("")
    lines.pop()
    return lines


def render_inherited_section(
    binding: ClassDoc,
    bindings_by_cpp: dict[str, ClassDoc],
    *,
    indent: str = "",
) -> list[str]:
    bases = [bindings_by_cpp[base] for base in binding.bases_cpp if base in bindings_by_cpp]
    if not bases:
        return []

    lines: list[str] = []
    for base in bases:
        for method in base.methods:
            if method.name == "__eq__":
                continue
            lines.extend(render_method_entry(method, indent=indent, no_index=True))
            lines.append("")
    if lines:
        lines.pop()
    return lines


def render_class_section(
    binding: ClassDoc,
    include_init: bool,
    include_internal: bool,
    bindings_by_cpp: dict[str, ClassDoc],
) -> list[str]:
    module_name = binding.python_name.rsplit(".", 1)[0]
    show_constructor = include_init or bool(binding.ctor_args or binding.ctor_doc)
    if show_constructor:
        arglist = ", ".join(binding.ctor_args)
        class_signature = f"{binding.class_name}({arglist})"
    else:
        class_signature = binding.class_name
    lines = [f".. py:class:: {class_signature}", f"   :module: {module_name}", ""]
    lines.append(f"   C++: :cpp:class:`{binding.cpp_target}`")

    class_description = normalize_doc_block(binding.class_doc)
    if class_description:
        for paragraph in class_description.split("\n\n"):
            lines.append("")
            if "\n" in paragraph and all(line.startswith(("- ", "* ")) for line in paragraph.splitlines()):
                for bullet in paragraph.splitlines():
                    lines.append(f"   {bullet}")
            else:
                lines.append(f"   {paragraph}")

    if show_constructor and (binding.ctor_args or binding.ctor_doc):
        ctor_method = MethodDoc(
            name="__init__",
            args=binding.ctor_args,
            brief=binding.ctor_doc,
            details="",
            params=binding.ctor_params,
            returns="",
            cpp_target=binding.ctor_cpp_target,
            cpp_role=binding.ctor_cpp_role,
        )
        lines.extend(["", ""])
        lines.extend(render_method_entry(ctor_method, indent="   ", no_index=True))

    if include_internal:
        exported = [method for method in binding.methods if method.name != "__eq__"]
    else:
        exported = [method for method in binding.methods if not method.is_internal and not method.is_dunder]

    methods_block = render_method_entries(exported, indent="   ")
    if methods_block:
        lines.extend(["", ""])
        lines.extend(methods_block)

    inherited_block = render_inherited_section(binding, bindings_by_cpp, indent="   ")
    if inherited_block:
        lines.extend(["", ""])
        lines.extend(inherited_block)

    return lines


def render_embedded_api(
    python_name: str,
    include_init: bool = False,
    include_internal: bool = False,
) -> str:
    bindings = scan_bindings()
    if python_name not in bindings:
        raise KeyError(f"No Boost.Python binding found for {python_name}")

    binding = bindings[python_name]
    bindings_by_cpp = {item.cpp_name: item for item in bindings.values()}

    lines: list[str] = []
    lines.extend(["Generated API", "-------------", ""])
    lines.extend(render_class_section(binding, include_init, include_internal, bindings_by_cpp))
    lines.extend(["", ""])

    return "\n".join(lines)
