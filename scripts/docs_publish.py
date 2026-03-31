#!/usr/bin/env python3
# ----------------------------------------------------------------------------
# Title      : ROGUE Documentation Publisher
# ----------------------------------------------------------------------------
# This file is part of the rogue software package. It is subject to
# the license terms in the LICENSE.txt file found in the top-level directory
# of this distribution and at:
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
# No part of the rogue software package, including this file, may be
# copied, modified, propagated, or distributed except according to the terms
# contained in the LICENSE.txt file.
# ----------------------------------------------------------------------------
"""Publish built documentation into a gh-pages worktree."""

from __future__ import annotations

import argparse
import json
import re
import shutil
from pathlib import Path


RELEASE_DIR_RE = re.compile(r"^v(\d+)\.(\d+)\.(\d+)$")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--site-dir", required=True, help="Built HTML directory to publish")
    parser.add_argument("--output-root", required=True, help="Target root inside the gh-pages tree")
    parser.add_argument(
        "--site-root",
        required=True,
        help="Public URL root for the published docs, for example /rogue or /rogue/staging-docs",
    )
    parser.add_argument(
        "--mode",
        required=True,
        choices=("release", "pre-release"),
        help="Publishing mode",
    )
    parser.add_argument("--version", help="Release version label for release mode")
    parser.add_argument(
        "--write-root-redirect",
        action="store_true",
        help="Write index.html at the output root redirecting to latest/",
    )
    return parser.parse_args()


def normalize_site_root(site_root: str) -> str:
    site_root = site_root.strip()
    if not site_root or site_root == "/":
        return ""
    if not site_root.startswith("/"):
        site_root = f"/{site_root}"
    return site_root.rstrip("/")


def url_join(site_root: str, *parts: str) -> str:
    pieces = [site_root.strip("/")] if site_root else [""]
    pieces.extend(part.strip("/") for part in parts if part)
    path = "/".join(piece for piece in pieces if piece)
    return f"/{path}/" if path else "/"


def sync_tree(source: Path, destination: Path) -> None:
    if destination.exists():
        shutil.rmtree(destination)
    shutil.copytree(source, destination)


def ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def write_text(path: Path, content: str) -> None:
    ensure_parent(path)
    path.write_text(content, encoding="utf-8")


def release_sort_key(slug: str) -> tuple[int, int, int]:
    match = RELEASE_DIR_RE.match(slug)
    if not match:
        return (-1, -1, -1)
    return tuple(int(part) for part in match.groups())


def collect_versions(output_root: Path, site_root: str) -> dict[str, object]:
    versions: list[dict[str, str]] = []

    if (output_root / "latest").is_dir():
        versions.append(
            {
                "slug": "latest",
                "title": "Latest Release",
                "kind": "alias",
                "url": url_join(site_root, "latest"),
            }
        )

    if (output_root / "pre-release").is_dir():
        versions.append(
            {
                "slug": "pre-release",
                "title": "Pre-release",
                "kind": "branch",
                "url": url_join(site_root, "pre-release"),
            }
        )

    release_slugs = sorted(
        (
            path.name
            for path in output_root.iterdir()
            if path.is_dir() and RELEASE_DIR_RE.match(path.name)
        ),
        key=release_sort_key,
        reverse=True,
    )

    for slug in release_slugs:
        versions.append(
            {
                "slug": slug,
                "title": slug,
                "kind": "release",
                "url": url_join(site_root, slug),
            }
        )

    return {"default": "latest", "versions": versions}


def render_versions_page(metadata: dict[str, object], site_root: str) -> str:
    versions = metadata["versions"]
    latest = next((entry for entry in versions if entry["slug"] == "latest"), None)
    pre_release = next((entry for entry in versions if entry["slug"] == "pre-release"), None)
    releases = [entry for entry in versions if entry["kind"] == "release"]

    def render_entry(entry: dict[str, str]) -> str:
        return f'<li><a href="{entry["url"]}">{entry["title"]}</a></li>'

    latest_html = render_entry(latest) if latest else "<li>Not published yet.</li>"
    pre_release_html = render_entry(pre_release) if pre_release else "<li>Not published yet.</li>"
    release_html = "\n".join(render_entry(entry) for entry in releases) or "<li>No releases published yet.</li>"

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Rogue Documentation Versions</title>
  <style>
    :root {{
      color-scheme: light;
      --bg: #f6f8fb;
      --card: #ffffff;
      --border: #d8dee9;
      --text: #1c2533;
      --muted: #5c6b80;
      --link: #005a9c;
    }}
    * {{
      box-sizing: border-box;
    }}
    body {{
      margin: 0;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      background: var(--bg);
      color: var(--text);
      line-height: 1.6;
    }}
    main {{
      max-width: 56rem;
      margin: 0 auto;
      padding: 3rem 1.5rem 4rem;
    }}
    h1 {{
      margin-bottom: 0.25rem;
    }}
    p {{
      color: var(--muted);
      margin-top: 0;
    }}
    section {{
      background: var(--card);
      border: 1px solid var(--border);
      border-radius: 0.75rem;
      padding: 1.25rem 1.5rem;
      margin-top: 1rem;
    }}
    ul {{
      margin: 0;
      padding-left: 1.25rem;
    }}
    a {{
      color: var(--link);
    }}
    .home-link {{
      display: inline-block;
      margin-top: 1rem;
    }}
  </style>
</head>
<body>
  <main>
    <h1>Rogue Documentation Versions</h1>
    <p>Select released or development documentation.</p>
    <section>
      <h2>Latest Release</h2>
      <ul>
        {latest_html}
      </ul>
    </section>
    <section>
      <h2>Development Docs</h2>
      <ul>
        {pre_release_html}
      </ul>
    </section>
    <section>
      <h2>Release History</h2>
      <ul>
        {release_html}
      </ul>
    </section>
    <a class="home-link" href="{url_join(site_root, metadata['default'])}">Open default docs</a>
  </main>
</body>
</html>
"""


def render_redirect(target: str) -> str:
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta http-equiv="refresh" content="0; url={target}">
  <title>Redirecting...</title>
  <link rel="canonical" href="{target}">
</head>
<body>
  <p>Redirecting to <a href="{target}">{target}</a>.</p>
</body>
</html>
"""


def main() -> int:
    args = parse_args()

    site_dir = Path(args.site_dir).resolve()
    output_root = Path(args.output_root).resolve()
    site_root = normalize_site_root(args.site_root)

    if not site_dir.is_dir():
        raise FileNotFoundError(f"Built site directory not found: {site_dir}")

    output_root.mkdir(parents=True, exist_ok=True)

    if args.mode == "release":
        if not args.version:
            raise ValueError("--version is required in release mode")
        sync_tree(site_dir, output_root / args.version)
        sync_tree(site_dir, output_root / "latest")
    else:
        sync_tree(site_dir, output_root / "pre-release")

    metadata = collect_versions(output_root, site_root)
    write_text(output_root / "versions.json", json.dumps(metadata, indent=2, sort_keys=False) + "\n")
    write_text(output_root / "versions" / "index.html", render_versions_page(metadata, site_root))

    if args.write_root_redirect:
        write_text(output_root / "index.html", render_redirect("latest/"))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
