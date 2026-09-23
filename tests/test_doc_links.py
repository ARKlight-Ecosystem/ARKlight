"""
Guards against docs drift: every relative Markdown link in the repo's
root `*.md` files and under `docs/` must resolve to a file or folder
that actually exists.

Most of the drift this catches came from a doc being moved, renamed, or
deleted while an index row or cross-reference still pointed at its old
name (see "Moving, renaming, or retiring a doc" in `docs/README.md`).

Deliberately narrow: it checks only real Markdown links, `[text](target)`,
not backtick path mentions or links inside fenced code blocks -- those
are frequently historical (`CHANGELOG.md`) or examples, and would make
this test noisy enough to get ignored. URLs and in-page `#anchors` are
skipped; only the file part of `path#anchor` is checked.
"""

import re
from pathlib import Path
from urllib.parse import unquote

import pytest

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"

_FENCE = re.compile(r"^(```|~~~).*?^\1", re.S | re.M)
_LINK = re.compile(r"\]\((<[^>]+>|[^)\s]+)\)")
_EXTERNAL = re.compile(r"^(?:[a-z][a-z0-9+.\-]*:|#)", re.I)


def _markdown_files():
    files = sorted(ROOT.glob("*.md"))
    if DOCS.is_dir():
        files += sorted(DOCS.rglob("*.md"))
    return files


def _broken_links(path):
    text = _FENCE.sub("", path.read_text(encoding="utf-8", errors="replace"))
    broken = []
    for match in _LINK.finditer(text):
        target = match.group(1).strip("<>")
        if _EXTERNAL.match(target):
            continue
        file_part = unquote(target.split("#", 1)[0])
        if not file_part:
            continue
        if not (path.parent / file_part).resolve().exists():
            broken.append(target)
    return broken


@pytest.mark.skipif(not DOCS.is_dir(), reason="docs/ not present (e.g. installed package)")
def test_no_broken_relative_links_in_markdown_docs():
    problems = {}
    for path in _markdown_files():
        broken = _broken_links(path)
        if broken:
            problems[str(path.relative_to(ROOT))] = broken
    assert not problems, (
        "Broken relative Markdown links (a doc was probably moved, renamed, or "
        "removed -- see 'Moving, renaming, or retiring a doc' in docs/README.md):\n"
        + "\n".join(f"  {f}: {', '.join(t)}" for f, t in problems.items())
    )
