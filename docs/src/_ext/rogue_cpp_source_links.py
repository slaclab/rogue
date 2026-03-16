"""Add local source-code links to Breathe-rendered C++ API signatures."""

from __future__ import annotations

import shutil
import xml.etree.ElementTree as ET
from pathlib import Path
from posixpath import dirname, relpath
from typing import Dict, Optional

from docutils import nodes
from sphinx import addnodes
from sphinx.application import Sphinx


def _normalize_repo_path(file_name: str | None, repo_root: Path) -> Optional[str]:
    if not file_name:
        return None

    file_path = Path(file_name).resolve()
    try:
        relative = file_path.relative_to(repo_root)
    except ValueError:
        return None

    return relative.as_posix()


def _parse_line_number(value: str | None) -> int:
    if not value:
        return 1
    try:
        return max(int(value), 1)
    except ValueError:
        return 1


def _parse_location(location_elem: ET.Element, repo_root: Path) -> Optional[dict[str, object]]:
    decl_path = _normalize_repo_path(location_elem.get("file"), repo_root)
    def_path = _normalize_repo_path(location_elem.get("bodyfile"), repo_root)

    if not decl_path and not def_path:
        return None

    location: dict[str, object] = {}
    if decl_path:
        location["decl_path"] = decl_path
        location["decl_line"] = _parse_line_number(location_elem.get("line"))
    if def_path:
        location["def_path"] = def_path
        location["def_line"] = _parse_line_number(location_elem.get("bodystart"))
    return location


def _build_doxygen_index(app: Sphinx) -> tuple[Dict[str, dict[str, object]], Dict[str, str]]:
    xml_dir = Path(app.config.rogue_doxygen_xml_dir)
    repo_root = Path(app.config.rogue_source_repo_root).resolve()
    ref_map: Dict[str, dict[str, object]] = {}
    file_map: Dict[str, str] = {}

    if not xml_dir.exists():
        return ref_map, file_map

    for xml_path in xml_dir.glob("*.xml"):
        try:
            root = ET.parse(xml_path).getroot()
        except ET.ParseError:
            continue

        compound = root.find("compounddef")
        if compound is None:
            continue

        compound_id = compound.get("id")
        compound_kind = compound.get("kind")
        compound_location = compound.find("location")
        if compound_id and compound_location is not None:
            location = _parse_location(compound_location, repo_root)
            if location is not None:
                ref_map[compound_id] = location
                if compound_kind == "file" and "decl_path" in location:
                    file_map[str(location["decl_path"])] = compound_id

        for member in compound.findall(".//memberdef"):
            member_id = member.get("id")
            if not member_id:
                continue
            location_elem = member.find("location")
            if location_elem is None:
                continue
            location = _parse_location(location_elem, repo_root)
            if location is not None:
                ref_map[member_id] = location

    return ref_map, file_map


def _build_source_uri(app: Sphinx, docname: str, path: str, line: int) -> Optional[str]:
    file_map = getattr(app.env, "rogue_cpp_source_file_map", {})
    file_id = file_map.get(path)
    if not file_id:
        return None

    line_anchor = f"l{line:05d}"
    doxygen_subdir = app.config.rogue_doxygen_html_output.strip("/")
    current_uri = app.builder.get_target_uri(docname)
    target_path = f"{doxygen_subdir}/{file_id}_source.html"
    relative_path = relpath(target_path, start=dirname(current_uri) or ".")
    return f"{relative_path}#{line_anchor}"


def _source_links(app: Sphinx, docname: str, refid: str) -> list[tuple[str, str]]:
    ref_map = getattr(app.env, "rogue_cpp_source_ref_map", {})
    location = ref_map.get(refid)
    if location is None:
        return []

    links: list[tuple[str, str]] = []
    decl_path = location.get("decl_path")
    decl_line = location.get("decl_line")
    if isinstance(decl_path, str) and isinstance(decl_line, int):
        uri = _build_source_uri(app, docname, decl_path, decl_line)
        if uri:
            links.append(("header", uri))

    def_path = location.get("def_path")
    def_line = location.get("def_line")
    if isinstance(def_path, str) and isinstance(def_line, int):
        uri = _build_source_uri(app, docname, def_path, def_line)
        if uri and ("header", uri) not in links:
            label = "impl" if def_path.endswith((".cpp", ".cc", ".cxx")) else "source"
            links.append((label, uri))

    return links


def _candidate_refids(signature: addnodes.desc_signature) -> list[str]:
    candidates: list[str] = []

    for value in signature.get("ids", []):
        if isinstance(value, str) and value.startswith(
            ("class", "struct", "namespace", "union", "file", "dir", "group", "concept")
        ):
            candidates.append(value)

    for child in signature.findall(nodes.target):
        for value in child.get("ids", []):
            if isinstance(value, str) and value.startswith(
                ("class", "struct", "namespace", "union", "file", "dir", "group", "concept")
            ):
                candidates.append(value)

    return candidates


def _inject_source_links(app: Sphinx, doctree: nodes.document, docname: str) -> None:
    if app.builder.format != "html":
        return

    for desc in doctree.findall(addnodes.desc):
        if desc.get("domain") != "cpp":
            continue
        for signature in desc.findall(addnodes.desc_signature):
            if signature.get("rogue_source_link_added"):
                continue

            links: list[tuple[str, str]] = []
            for refid in _candidate_refids(signature):
                links = _source_links(app, docname, refid)
                if links:
                    break
            if not links:
                continue

            for label, uri in links:
                signature += nodes.Text(" ")
                signature += nodes.reference(
                    "",
                    f"[{label}]",
                    internal=False,
                    refuri=uri,
                    classes=["rogue-source-link"],
                )
            signature["rogue_source_link_added"] = True


def _copy_doxygen_html(app: Sphinx, exc: object) -> None:
    if exc is not None or app.builder.format != "html":
        return

    source_dir = Path(app.config.rogue_doxygen_html_dir)
    if not source_dir.exists():
        return

    target_dir = Path(app.outdir) / app.config.rogue_doxygen_html_output
    shutil.copytree(source_dir, target_dir, dirs_exist_ok=True)


def _on_builder_inited(app: Sphinx) -> None:
    ref_map, file_map = _build_doxygen_index(app)
    app.env.rogue_cpp_source_ref_map = ref_map
    app.env.rogue_cpp_source_file_map = file_map


def setup(app: Sphinx) -> dict[str, object]:
    repo_root = Path(__file__).resolve().parents[3]
    docs_root = repo_root / "docs"

    app.add_config_value("rogue_source_repo_root", str(repo_root), "env")
    app.add_config_value("rogue_doxygen_xml_dir", str(docs_root / "build" / "doxyxml"), "env")
    app.add_config_value("rogue_doxygen_html_dir", str(docs_root / "build" / "doxyhtml"), "env")
    app.add_config_value("rogue_doxygen_html_output", "_doxygen", "html")
    app.connect("builder-inited", _on_builder_inited)
    app.connect("doctree-resolved", _inject_source_links)
    app.connect("build-finished", _copy_doxygen_html)
    return {
        "version": "0.1",
        "parallel_read_safe": True,
        "parallel_write_safe": True,
    }
