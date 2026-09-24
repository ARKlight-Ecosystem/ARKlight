"""
Pre-write link gate -- the routing counterpart of `asset_check.py`.

`asset_check` answers "does every referenced *file* exist?". This module
answers the same question for internal *links*: does every `href` that
points inside the site land on a page (and an element) that exists?

It runs at the same point in `build()` -- after every backend has
produced the final file set, before anything touches disk -- and reports
the same way: one plain-text report straight to stderr, no flag to
silence it, then a `CompileError`.

What is checked, per `href` on any node:

- `#frag` (same page) -- a node with `id="frag"` must exist on this page.
  `#` and `#top` are always valid (the browser scrolls to the top).
- `/route`, `/route/`, `/route?q=1`, `/route#frag` -- must match a page
  this site registers (a trailing slash and a `?query` are accepted, the
  same way `backend/html/routing.py` resolves them). If a `#frag` is
  present, the *target* page must contain that id.
- `/anything-else` -- unknown internal route: not a registered page, not
  a file the build generates (`/styles.css`), and not under `assets/`
  (the asset gate owns those). Reported with a "did you mean" hint.

Not checked: external URLs (`https:`, `mailto:`, `tel:`, `//host`),
`href`s without a leading slash (authored as raw relative file links),
`action`/`formaction` (a form very often targets an external API), and
ids that only exist at runtime (built from state or a derivation) -- a
fragment aimed at one of those is reported, because nothing static can
vouch for it.

Route matching is exact and case-sensitive, like the asset gate: `/About`
is not `/about` on a case-sensitive host.
"""

from __future__ import annotations

import difflib
import posixpath
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import unquote

from arklight.backend.html.routing import _is_external_ref, _match_route
from arklight.ir.build import IRNode, WebsiteIR

_PREVIEW = 8


@dataclass(frozen=True)
class LinkProblem:
    href: str
    kind: str  # "unknown-route" | "dead-fragment"
    detail: str
    used_by: tuple[str, ...]


def _walk(node: Any, visit) -> None:
    if isinstance(node, IRNode):
        visit(node)
        for value in node.props.values():
            _walk(value, visit)
        for child in node.children:
            _walk(child, visit)
    elif isinstance(node, dict):
        for value in node.values():
            _walk(value, visit)
    elif isinstance(node, (list, tuple)):
        for value in node:
            _walk(value, visit)


def _ids_by_route(ir: WebsiteIR) -> dict[str, set[str]]:
    ids: dict[str, set[str]] = {}
    for page in ir.pages:
        found: set[str] = set()

        def visit(node: IRNode, found: set[str] = found) -> None:
            value = node.props.get("id")
            if isinstance(value, str) and value:
                found.add(value)

        _walk(page.root, visit)
        ids[page.route] = found
    return ids


def _preview(names) -> str:
    shown = sorted(names)[:_PREVIEW]
    extra = len(names) - len(shown)
    text = ", ".join(shown) if shown else "(none)"
    return text + (f", ... +{extra} more" if extra > 0 else "")


def _fragment_problem(fragment: str, target_route: str, ids: set[str]) -> str | None:
    frag = unquote(fragment)
    if frag in ("", "top") or frag in ids:
        return None
    near = [i for i in ids if i.lower() == frag.lower()] or difflib.get_close_matches(frag, ids, n=1)
    hint = f"  Did you mean #{near[0]}?" if near else ""
    return f"no element with id={frag!r} on {target_route}  (ids there: {_preview(ids)}).{hint}"


def check_links(ir: WebsiteIR, *, generated: set[str]) -> tuple[int, list[LinkProblem]]:
    """Return `(links_checked, problems)`. Pure: reads the IR only."""
    routes = {page.route: "" for page in ir.pages}  # dict shape `_match_route` expects
    ids = _ids_by_route(ir)
    problems: dict[tuple[str, str], list[str]] = {}
    details: dict[tuple[str, str], str] = {}
    checked = 0

    def record(href: str, kind: str, detail: str, where: str) -> None:
        key = (href, kind)
        details.setdefault(key, detail)
        uses = problems.setdefault(key, [])
        if where not in uses:
            uses.append(where)

    for page in ir.pages:
        route = page.route

        def visit(node: IRNode, route: str = route) -> None:
            nonlocal checked
            raw = node.props.get("href")
            if not isinstance(raw, str):
                return
            href = raw.strip()
            if not href or _is_external_ref(href):
                return
            where = f"{route} <{node.type} href>"

            if href.startswith("#"):
                checked += 1
                detail = _fragment_problem(href[1:], route, ids[route])
                if detail:
                    record(raw, "dead-fragment", detail, where)
                return

            if not href.startswith("/"):
                return  # raw relative file link -- not ours to judge

            path_and_query, _, fragment = href.partition("#")
            path, _, _query = path_and_query.partition("?")
            matched = _match_route(path, routes)
            if matched is not None:
                checked += 1
                detail = _fragment_problem(fragment, matched, ids[matched]) if fragment else None
                if detail:
                    record(raw, "dead-fragment", detail, where)
                return

            rel = posixpath.normpath(path.lstrip("/"))
            if rel in generated or rel == "assets" or rel.startswith("assets/"):
                return  # a generated file, or the asset gate's business
            checked += 1
            lower = path.lower().rstrip("/") or "/"
            near = [r for r in routes if r.lower() == lower] or difflib.get_close_matches(path, list(routes), n=1)
            hint = f"  Did you mean {near[0]!r}?" if near else ""
            record(
                raw,
                "unknown-route",
                f"not a page this site registers, not a generated file, not under assets/."
                f"{hint}  (registered routes: {_preview(list(routes))})",
                where,
            )

        _walk(page.root, visit)

    result = [
        LinkProblem(href, kind, details[(href, kind)], tuple(uses))
        for (href, kind), uses in problems.items()
    ]
    return checked, result


def format_report(problems: list[LinkProblem], *, total_checked: int, entry_path: Path) -> str:
    bar = "=" * 72
    lines = [
        bar,
        "ARKlight LINK CHECK FAILED -- build halted, nothing was written.",
        f"  site file: {entry_path}",
        "",
        f"  {len(problems)} internal link(s) don't resolve ({total_checked} internal link(s) checked):",
        "",
    ]
    for problem in problems:
        lines.append(f"  [{problem.kind.upper()}] {problem.href}")
        lines.append(f"      {problem.detail}")
        lines.append(f"      used by: {'; '.join(problem.used_by)}")
        lines.append("")
    lines.append("Fix the href in the site file (or add the missing page/id), then rebuild.")
    lines.append(bar)
    return "\n".join(lines)
