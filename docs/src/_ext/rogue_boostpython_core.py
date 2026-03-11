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
    doc: str
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
        text = normalize_doc_block(self.doc)
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
    methods: list[MethodDoc]


@dataclasses.dataclass
class HeaderDoc:
    class_docs: dict[str, str]
    method_docs: dict[str, str]


def normalize_doc(text: str) -> str:
    text = text.strip()
    if not text:
        return ""
    return re.sub(r"\s+", " ", text.replace("\\n", " ")).strip()


def normalize_doc_block(text: str) -> str:
    paragraphs = [normalize_doc(part) for part in re.split(r"\n\s*\n", text)]
    paragraphs = [part for part in paragraphs if part]
    return "\n\n".join(paragraphs)


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


def parse_doxygen_comment(raw_comment: str) -> str:
    lines: list[str] = []
    for line in raw_comment.splitlines():
        line = re.sub(r"^\s*/?\**\s?", "", line).strip()
        if line:
            lines.append(line)

    brief: list[str] = []
    details: list[str] = []
    mode = "body"
    for line in lines:
        if line.startswith("@brief"):
            brief.append(line[len("@brief") :].strip())
            mode = "brief"
            continue
        if line.startswith("@details"):
            details.append(line[len("@details") :].strip())
            mode = "details"
            continue
        if line.startswith("@param") or line.startswith("@return") or line.startswith("@tparam"):
            mode = "tags"
            continue
        if line.startswith("@"):
            mode = "tags"
            continue

        if mode == "details":
            details.append(line)
        elif mode in {"brief", "body"}:
            brief.append(line)

    brief_text = normalize_doc(" ".join(brief))
    details_text = normalize_doc(" ".join(details))
    return "\n\n".join(part for part in [brief_text, details_text] if part)


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
    class_docs: dict[str, str] = {}
    method_docs: dict[str, str] = {}
    pattern = re.compile(r"/\*\*(.*?)\*/\s*([^;{]+[;{])", re.DOTALL)
    for comment, declaration in pattern.findall(text):
        doc = parse_doxygen_comment(comment)
        if not doc:
            continue
        name = declaration_name(declaration)
        if not name:
            continue
        if declaration.lstrip().startswith("class "):
            class_docs[name] = doc
        else:
            method_docs[name] = doc
    return HeaderDoc(class_docs=class_docs, method_docs=method_docs)


def lookup_method_doc(cpp_target: str, python_name: str = "") -> str:
    header_path = resolve_header_for_cpp_name(cpp_target.rsplit("::", 1)[0])
    if not header_path:
        return ""
    header_docs = parse_header_docs(header_path)
    target_name = cpp_target.rsplit("::", 1)[-1]
    return header_docs.method_docs.get(python_name) or header_docs.method_docs.get(target_name) or ""


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
    return MethodDoc(name=name, args=arg_names, doc=doc, cpp_target=cpp_target)


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
        class_doc = header_docs.class_docs[class_name]
    if header_docs.method_docs.get(class_name):
        ctor_doc = header_docs.method_docs[class_name]
    methods = [
        dataclasses.replace(
            method,
            doc=header_docs.method_docs.get(method.name)
            or header_docs.method_docs.get(method.cpp_target.rsplit("::", 1)[-1])
            or lookup_method_doc(method.cpp_target, method.name)
            or method.doc,
        )
        for method in methods
    ]

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


def render_method_entry(method: MethodDoc) -> list[str]:
    role = "class" if method.cpp_role == "class" else "func"
    lines = [f"``{method.signature}`` -> :cpp:{role}:`{method.cpp_target}`"]
    paragraphs = normalize_doc_block(method.description).split("\n\n")
    for idx, paragraph in enumerate(paragraphs):
        if idx:
            lines.append("")
        lines.append(f"   {paragraph}")
    return lines


def render_methods_section(title: str, methods: Iterable[MethodDoc]) -> list[str]:
    methods = list(methods)
    if not methods:
        return []
    lines = [title, "-" * len(title), ""]
    for method in methods:
        lines.extend(render_method_entry(method))
        lines.append("")
    lines.pop()
    return lines


def render_inherited_section(binding: ClassDoc, bindings_by_cpp: dict[str, ClassDoc]) -> list[str]:
    bases = [bindings_by_cpp[base] for base in binding.bases_cpp if base in bindings_by_cpp]
    if not bases:
        return []

    lines = [
        "Inherited Methods",
        "-----------------",
        "",
        f"``{binding.class_name}`` also exposes methods inherited from its exported Python base classes.",
        "",
    ]
    for base in bases:
        heading = f"Inherited from :class:`{base.python_name}`"
        lines.append(heading)
        lines.append("~" * len(heading))
        lines.append("")
        lines.append(f"C++ base: :cpp:class:`{base.cpp_target}`")
        lines.append("")
        for method in base.methods:
            if method.name == "__eq__":
                continue
            lines.extend(render_method_entry(method))
            lines.append("")
        lines.pop()
        lines.append("")
    lines.pop()
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
    class_intro = normalize_doc_block(binding.class_doc)
    if class_intro:
        lines.extend(normalize_doc_block(class_intro).split("\n\n"))
        lines.append("")

    if include_init and binding.ctor_doc:
        lines.extend(["Construction", "------------", ""])
        ctor = MethodDoc(binding.class_name, [], binding.ctor_doc, binding.cpp_target, cpp_role="class")
        lines.extend(render_method_entry(ctor))
        lines.extend(["", ""])

    if include_internal:
        exported = [method for method in binding.methods if method.name != "__eq__"]
    else:
        exported = [method for method in binding.methods if not method.is_internal and not method.is_dunder]
    exported_block = render_methods_section("Exported Methods", exported)
    if exported_block:
        lines.extend(exported_block)
        lines.extend(["", ""])

    inherited_block = render_inherited_section(binding, bindings_by_cpp)
    if inherited_block:
        lines.extend(inherited_block)
        lines.extend(["", ""])

    return "\n".join(lines)
