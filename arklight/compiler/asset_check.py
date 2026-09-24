"""
Pre-write asset gate.

Before `build()` writes anything, this module answers one question:
does every file the site *references* actually exist, under exactly
the name the site uses, in the `assets/` folder the build is about to
copy (or among the files the build itself generates)?

How it works, in the order it runs:

1. `collect_required_assets(ir)` walks the finished Website IR once and
   builds the working list -- an in-memory `{path: [where it's used]}`
   map of every asset path the site references. Nothing touches the
   disk here.
2. `check_required_assets(...)` compares that list against the real
   directory listings, one path component at a time. Matching is by
   *exact name*, never `Path.exists()`: on a case-insensitive
   filesystem (macOS, Windows) `exists()` says `Logo.png` is there
   when the site asks for `logo.png`, and the site then breaks on the
   first case-sensitive host (Linux, most CDNs). Listing the directory
   and comparing names is what makes the check the same everywhere.
3. `format_report(...)` renders the problems as a plain-text report.
   `build()` writes it straight to stderr -- not through `on_stage`, not
   through the `rei` narrator, not through `warnings` -- and then raises
   `CompileError`. There is no flag that turns this off.

What counts as a required asset -- the same classification the HTML
backend uses when it rewrites paths (see `backend/html/routing.py`):
a value is an asset unless it is external (`scheme:` or `//`), a bare
`#fragment`, or a registered page route. `src`/`poster`/`srcset` and
the page-level `favicon`/`og_image` are always treated this way, as
are `url(...)` references in a node's `style` and in `@font-face`
sources. `href` is only treated as an asset when it points into
`assets/` (a downloadable PDF, say) -- any other unknown `href` is a
routing question, not an asset question, and is left to the routing
code.

A required path is satisfied when either
  - the build generates it (a key of `output_files`, e.g. `styles.css`),
    or
  - it lives under `assets/` and that exact file exists in the
    `assets/` folder next to the entry file.
Anything else -- including a path outside `assets/` that nothing
generates, because the build has no way to supply it -- is a problem.

Not covered (values only known at runtime, so nothing to check here):
references built from state/derivations, and paths inside JavaScript.
"""

from __future__ import annotations

import os
import posixpath
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from arklight.ir.build import IRNode, WebsiteIR

_SCHEME = re.compile(r"^[a-z][a-z0-9+.\-]*:", re.I)
_CSS_URL = re.compile(r"""url\(\s*(['"]?)(.*?)\1\s*\)""", re.I)

# Props whose value is always a single asset path (or a route, for
# `src`, which the HTML backend checks against known routes first).
_SRC_LIKE = ("src", "poster")
# Page-level head props, read only from a Page root (see head_meta.py).
_PAGE_ASSET_PROPS = ("favicon", "og_image")

_LISTING_PREVIEW = 8


@dataclass(frozen=True)
class AssetProblem:
    path: str
    kind: str  # "missing" | "case" | "not-a-file" | "not-a-dir" | "outside-assets" | "escapes-root"
    detail: str
    used_by: tuple[str, ...]


def _split_srcset(value: str) -> list[str]:
    urls = []
    for part in value.split(","):
        token = part.strip().split()
        if token:
            urls.append(token[0])
    return urls


def _classify(raw: Any, *, routes: frozenset[str], is_href: bool = False) -> str | None:
    """Return the normalized output-root-relative asset path a raw prop
    value refers to, or None when it isn't a checkable asset reference."""
    if not isinstance(raw, str):
        return None
    value = raw.strip()
    if not value or value.startswith("#") or value.startswith("//") or _SCHEME.match(value):
        return None
    if value.partition("#")[0] in routes:
        return None
    bare = value.split("#", 1)[0].split("?", 1)[0]
    if not bare:
        return None
    normalized = posixpath.normpath(bare.lstrip("/"))
    if normalized in ("", "."):
        return None
    if is_href and not (normalized == "assets" or normalized.startswith("assets/")):
        return None
    return normalized


def collect_required_assets(ir: WebsiteIR) -> dict[str, list[str]]:
    """Walk every page once and return `{asset_path: [usage, ...]}` in
    first-seen order. Pure: reads the IR, touches no files."""
    routes = frozenset(page.route for page in ir.pages)
    required: dict[str, list[str]] = {}

    def add(path: str | None, where: str) -> None:
        if path is None:
            return
        uses = required.setdefault(path, [])
        if where not in uses:
            uses.append(where)

    def walk(node: Any, route: str, *, is_page_root: bool) -> None:
        if isinstance(node, IRNode):
            tag = node.type
            props = node.props
            for key in _SRC_LIKE:
                add(_classify(props.get(key), routes=routes), f"{route} <{tag} {key}>")
            srcset = props.get("srcset")
            if isinstance(srcset, str):
                for url in _split_srcset(srcset):
                    add(_classify(url, routes=routes), f"{route} <{tag} srcset>")
            add(_classify(props.get("href"), routes=routes, is_href=True), f"{route} <{tag} href>")
            style = props.get("style")
            if isinstance(style, dict):
                style_values = [v for v in style.values() if isinstance(v, str)]
            else:
                style_values = [style] if isinstance(style, str) else []
            for text in style_values:
                for match in _CSS_URL.finditer(text):
                    add(_classify(match.group(2), routes=routes), f"{route} <{tag} style url()>")
            if is_page_root:
                for key in _PAGE_ASSET_PROPS:
                    add(_classify(props.get(key), routes=routes), f"{route} page {key}")
            for value in props.values():
                walk(value, route, is_page_root=False)
            for child in node.children:
                walk(child, route, is_page_root=False)
        elif isinstance(node, dict):
            for value in node.values():
                walk(value, route, is_page_root=False)
        elif isinstance(node, (list, tuple)):
            for value in node:
                walk(value, route, is_page_root=False)

    for page in ir.pages:
        walk(page.root, page.route, is_page_root=True)

    for face in getattr(ir, "font_faces", None) or []:
        if isinstance(face, dict):
            for value in face.values():
                if isinstance(value, str):
                    for match in _CSS_URL.finditer(value):
                        add(_classify(match.group(2), routes=routes), "site.font_face src")
    return required


def _entries(directory: Path, cache: dict[Path, dict[str, os.DirEntry]]) -> dict[str, os.DirEntry]:
    if directory not in cache:
        with os.scandir(directory) as it:
            cache[directory] = {entry.name: entry for entry in it}
    return cache[directory]


def _preview(names: list[str]) -> str:
    shown = sorted(names)[:_LISTING_PREVIEW]
    extra = len(names) - len(shown)
    text = ", ".join(shown) if shown else "(empty)"
    return text + (f", ... +{extra} more" if extra > 0 else "")


def check_required_assets(
    required: dict[str, list[str]],
    *,
    assets_src: Path,
    generated: set[str],
    assets_dir_name: str = "assets",
) -> list[AssetProblem]:
    """Compare the working list against real directory listings, exact
    name by exact name. Returns every problem found (empty == all green)."""
    problems: list[AssetProblem] = []
    cache: dict[Path, dict[str, os.DirEntry]] = {}

    for path, uses in required.items():
        used_by = tuple(uses)
        if path in generated:
            continue
        parts = path.split("/")
        if parts[0] == "..":
            problems.append(AssetProblem(path, "escapes-root", "points outside the site's output folder", used_by))
            continue
        if parts[0] != assets_dir_name or len(parts) == 1:
            problems.append(
                AssetProblem(
                    path,
                    "outside-assets",
                    f"is not under {assets_dir_name}/ and nothing in the build generates it, "
                    f"so the build has no way to supply it",
                    used_by,
                )
            )
            continue

        current = assets_src
        walked = assets_dir_name
        failed = False
        for index, name in enumerate(parts[1:], start=1):
            last = index == len(parts) - 1
            if not current.is_dir():
                where = "next to the entry file" if index == 1 else f"under {walked}/"
                problems.append(AssetProblem(path, "missing", f"{walked}/ folder not found {where} ({current})", used_by))
                failed = True
                break
            entries = _entries(current, cache)
            entry = entries.get(name)
            if entry is None:
                lower = name.lower()
                near = [n for n in entries if n.lower() == lower]
                if near:
                    detail = (
                        f"names must match exactly: site says {name!r} but {walked}/ has {near[0]!r}"
                    )
                    problems.append(AssetProblem(path, "case", detail, used_by))
                else:
                    detail = f"{name!r} not found in {walked}/  (contents: {_preview(list(entries))})"
                    problems.append(AssetProblem(path, "missing", detail, used_by))
                failed = True
                break
            if last and not entry.is_file():
                problems.append(AssetProblem(path, "not-a-file", f"{walked}/{name} is a directory, expected a file", used_by))
                failed = True
                break
            if not last and not entry.is_dir():
                problems.append(AssetProblem(path, "not-a-dir", f"{walked}/{name} is a file, expected a directory", used_by))
                failed = True
                break
            current = current / name
            walked = f"{walked}/{name}"
        if failed:
            continue
    return problems


def format_report(
    problems: list[AssetProblem],
    *,
    total_required: int,
    entry_path: Path,
    assets_src: Path,
) -> str:
    bar = "=" * 72
    lines = [
        bar,
        "ARKlight ASSET CHECK FAILED -- build halted, nothing was written.",
        f"  site file: {entry_path}",
        f"  assets/:   {assets_src}" + ("" if assets_src.is_dir() else "  (folder does not exist)"),
        "",
        f"  {len(problems)} of {total_required} required asset(s) are missing or don't match exactly:",
        "",
    ]
    for problem in problems:
        lines.append(f"  [{problem.kind.upper()}] {problem.path}")
        lines.append(f"      {problem.detail}")
        lines.append(f"      used by: {'; '.join(problem.used_by)}")
        lines.append("")
    lines.append("Fix the names in the site file or the files in assets/, then rebuild.")
    lines.append(bar)
    return "\n".join(lines)
