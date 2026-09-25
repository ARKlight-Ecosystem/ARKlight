"""
Guards against the two ways retiring a proposal has gone wrong here.

`test_doc_links.py` only sees real Markdown links, `[text](target)`. Most of
this repo's cross-references are *backtick path citations* --
`docs/Proposals/X.md` in a docstring, a test comment, or prose -- which that
test cannot see. This module covers them:

1. Live citations must resolve. Any `docs/<Folder>/<file>.md` citation in
   the code, the tests, or the docs must name a file that exists. Exempt:
   `CHANGELOG.md` and `PROGRESS.md` (history describes what was true at the
   time; only `PROGRESS.md`'s Snapshot table rows, which start with `| v0`,
   are live); any line that says a doc is "retired" or was "removed"; the
   "Graduated from" notes in `docs/Foundational/DESIGN-NOTES.md`; a
   `vX.md`/`vX.Y.md`-style template placeholder (literal letters, not a
   version number -- see `docs/version history/README.md`'s own convention);
   a citation of a not-yet-written file gated behind "if accepted"; and a
   citation explicitly naming another repo/branch, e.g. "main's ...".

2. A proposal may only be *retired* after it was *graduated*. Any citation of
   a missing `docs/Proposals/<file>.md` -- even in history -- must be backed by
   a `Graduated from `docs/Proposals/<file>.md`` note in
   `docs/Foundational/DESIGN-NOTES.md`. That note only exists once the
   proposal's rationale, deliberate limits, and out-of-scope decisions were
   moved there, so deleting a proposal without graduating it fails here.

See "Moving, renaming, or retiring a doc" in `docs/README.md`.
"""

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
DESIGN_NOTES = DOCS / "Foundational" / "DESIGN-NOTES.md"

_FOLDERS = r"(?:Foundational|Proposals|Implementation|Backends|Far Future Concern|version history)"
_CITATION = re.compile(r"docs/(%s)/([A-Za-z0-9_.\- ]+?\.md)" % _FOLDERS)
_PLACEHOLDER = re.compile(r"^v[A-Z](\.[A-Z])*$")  # vX, vX.Y, ... -- literal letters, not a version
_PROPOSAL = re.compile(r"docs/Proposals/([A-Za-z0-9_.\-]+?\.md)")
_GRADUATED = re.compile(r"Graduated from `docs/Proposals/([A-Za-z0-9_.\-]+?\.md)`")
_HISTORY = {"CHANGELOG.md", "PROGRESS.md"}

pytestmark = pytest.mark.skipif(
    not DOCS.is_dir(), reason="docs/ not present (e.g. installed package)"
)


def _sources():
    files = list(ROOT.glob("*.md"))
    files += DOCS.rglob("*.md")
    files += (ROOT / "arklight").rglob("*.py")
    files += (ROOT / "tests").rglob("*.py")
    files += DOCS.rglob("*.py")
    return sorted(p for p in files if p.is_file() and p != Path(__file__).resolve())


def _lines(path):
    text = path.read_text(encoding="utf-8", errors="replace")
    raw = text.splitlines()
    # Pair each line with a little context, since a qualifier like "main's"
    # or "if accepted" sometimes sits one line above the wrapped citation.
    return [(i, raw[i - 1], " ".join(raw[max(0, i - 2):i])) for i in range(1, len(raw) + 1)]


def test_live_docs_citations_resolve():
    problems = []
    for path in _sources():
        for n, line, context in _lines(path):
            if path.name in _HISTORY and not line.startswith("| v0"):
                continue
            if path == DESIGN_NOTES and ("Graduated from" in context or "git show" in context):
                continue
            low = context.lower()
            if "retired" in low or "removed" in low or "if accepted" in low or "main`" in low:
                continue
            for m in _CITATION.finditer(line):
                if _PLACEHOLDER.match(Path(m.group(2)).stem):
                    continue
                if not (DOCS / m.group(1) / m.group(2)).exists():
                    problems.append(f"{path.relative_to(ROOT)}:{n}: docs/{m.group(1)}/{m.group(2)}")
    assert not problems, (
        "Citations of docs that no longer exist (repoint them to where the content "
        "graduated, or tag a deliberate historical mention 'retired'; see 'Moving, "
        "renaming, or retiring a doc' in docs/README.md):\n  " + "\n  ".join(problems)
    )


def test_retired_proposals_were_graduated_first():
    graduated = set(_GRADUATED.findall(DESIGN_NOTES.read_text(encoding="utf-8")))
    ungraduated = {}
    for path in _sources():
        for n, line, context in _lines(path):
            if path == DESIGN_NOTES and ("Graduated from" in context or "git show" in context):
                continue
            for m in _PROPOSAL.finditer(line):
                name = m.group(1)
                if (DOCS / "Proposals" / name).exists() or name in graduated:
                    continue
                ungraduated.setdefault(name, f"{path.relative_to(ROOT)}:{n}")
    assert not ungraduated, (
        "A proposal is cited but missing, and DESIGN-NOTES.md has no 'Graduated from' "
        "note for it -- its design record was deleted, not graduated. Recover it with "
        "`git show <commit>^:docs/Proposals/<file>` and move it into "
        "docs/Foundational/DESIGN-NOTES.md first:\n  "
        + "\n  ".join(f"{k} (first cited at {v})" for k, v in sorted(ungraduated.items()))
    )
