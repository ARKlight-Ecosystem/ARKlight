"""
`arklight search --retrieve-doc` -- doc-tree retrieval mode for the
existing `arklight search` subcommand (`arklight/cli/search.py`,
wired in `arklight/cli/main.py`).

Staged in `docs/Implementation/SEARCH-RETRIEVE-DOC-ADDENDUM.md` for
`v0.064`, from `docs/Proposals/SEARCH-RETRIEVE-DOC-PROPOSAL.md`. Read
this module alongside that proposal -- section numbers referenced
below (`SS3`, `SS4.3`, ...) point back to it.

This is a dev-time CLI convenience, not a compiler feature: it prints
exact, unmodified bytes from files already in the repo's `docs/` tree
(root index -> folder index -> one named file), nothing invented or
summarized. Because of that "files already in the repo" framing
(proposal SS1), `--retrieve-doc` only works from an ARKlight source
checkout -- `docs/` isn't packaged into the installed wheel
(`pyproject.toml`'s `[tool.setuptools.packages.find]` only includes
`arklight*`), so `_docs_root()` fails loudly rather than pretending to
have something to show.

Two additions on top of the staged proposal, both additive:

`--section QUERY`, paired with `--file NAME` and a folder flag, prints
one `##`-level heading's own text instead of a whole file. `QUERY` is
a section number (that heading's own `## N. Title` numbering if the
file uses one, else its plain 1-based position among that file's
`##` headings), a heading-text fragment (matched the same
case/punctuation-insensitive way `--file` already matches filenames,
with a `difflib` "did you mean" on a miss), or both together, e.g.
`--section '3 terminology'`. `_extract_section`'s job stops at slicing
lines out of the file byte-for-byte, same "nothing invented or
summarized" framing as everything else here -- it never touches the
Markdown content it returns.

Terminal rendering (`arklight.cli.mdrender.render_markdown`) is
deliberately *not* applied anywhere in this module: `run_retrieve_doc`
keeps returning plain Markdown so its own tests keep asserting on
plain text, and coloring only happens once, at the CLI's actual print
site (`arklight/cli/main.py::_cmd_search`), driven by a `--color`
flag this module knows nothing about.
"""

from __future__ import annotations

import argparse
import difflib
import re
from dataclasses import dataclass
from pathlib import Path


class DocRetrievalError(Exception):
    """Raised for a `--retrieve-doc` invocation that can't be satisfied.
    Caught by `_cmd_search` in `arklight/cli/main.py` and reported on
    stderr with exit code 1 -- the same shape `SearchEngineError`
    already gets for component lookups."""


@dataclass(frozen=True)
class DocFolder:
    """One of the seven `docs/` lifecycle folders from
    `docs/README.md`'s own Folder Guide, one-for-one (proposal SS2)."""

    flag: str  # argparse flag spelling, e.g. "--foundational"
    attr: str  # argparse dest / Namespace attribute, e.g. "foundational"
    path: str  # folder name relative to docs/, e.g. "Foundational"
    blurb: str  # one-line description for the root-retrieval footer


# Order matches docs/README.md's Folder Guide table.
DOC_FOLDERS: tuple[DocFolder, ...] = (
    DocFolder(
        "--foundational",
        "foundational",
        "Foundational",
        "permanent design record (architecture, design notes, ...)",
    ),
    DocFolder(
        "--backends",
        "backends",
        "Backends",
        "per-backend staging docs (desktop, android, neutralino, ...)",
    ),
    DocFolder(
        "--proposals",
        "proposals",
        "Proposals",
        "unsettled proposals awaiting a decision",
    ),
    DocFolder(
        "--implementation",
        "implementation",
        "Implementation",
        "staged implementation ladders for accepted proposals",
    ),
    DocFolder(
        "--js-backend",
        "js_backend",
        "new js backend proposal",
        "competing new-JS-backend architecture proposals",
    ),
    DocFolder(
        "--far-future",
        "far_future",
        "Far Future Concern",
        "speculative/backlog backend material",
    ),
    DocFolder(
        "--version-history",
        "version_history",
        "version history",
        "per-milestone shipped-feature summaries",
    ),
)

_RULE = "=" * 80

_ROOT_FOOTER = "\n".join(
    ["---", "Go deeper with a folder flag:"]
    + [f"  {folder.flag:<20}{folder.blurb}" for folder in DOC_FOLDERS]
    + [
        "",
        "Then add --file NAME to print one file from that folder in full.",
        "Example: arklight search --retrieve-doc --foundational --file architecture",
    ]
)

# Matches one markdown table row of the shape
# "| [`NAME.md`](path) | description |" -- every folder README's own
# "File"/"Covers" (or "Version"/"Covers") index table uses this shape,
# per docs/README.md's "Adding a new doc" section. Header/separator
# rows ("| File | Covers |", "| --- | --- |") don't start with `[`
# right after the leading pipe, so they never match -- no separate
# header-skipping logic needed.
_TABLE_ROW = re.compile(r"^\|\s*\[`?([^`\]]+)`?\]\([^)]*\)\s*\|\s*(.+?)\s*\|\s*$")

# `--section` addressing. A "section" is a `##`-level (not `#`, not
# `###`+) heading -- the universal one-per-topic unit every docs/ file
# uses (document title is `#`, `##` divides it into sections, `###`+
# are that section's own internal subheadings and stay part of it).
_SECTION_HEADING = re.compile(r"^##\s+(.*?)\s*$")
# A heading's own declared numbering, e.g. "1. Summary" -> (1,
# "Summary"), "10) Versioning" -> (10, "Versioning"). Requires *some*
# text after the number -- a heading that's just "10" and nothing else
# is too strange a case to guess is numbering rather than a title.
_SECTION_NUMBER_PREFIX = re.compile(r"^(\d+)[.)]?\s+(.+)$")

# A `--section` query itself: an optional leading number (punctuation
# after it optional, e.g. "3", "3.", "3)") followed by an optional
# heading-text fragment. One pass covers "3", "3 Terminology",
# "3. Terminology", and bare "Terminology" (the number group simply
# doesn't match, `.*` still matches the whole string as `text`).
_SECTION_QUERY = re.compile(r"^(?:(\d+)[.)]?\s*)?(.*)$")
_INLINE_MARKUP = re.compile(r"[`*_]")


@dataclass(frozen=True)
class _Section:
    """One `##` heading in a file, resolved and ready to slice out."""

    index: int  # 1-based position among this file's `##` headings
    number: int | None  # that heading's own "N." prefix, if it has one
    title: str  # heading text with any "N." prefix stripped
    start_line: int  # 0-based index into the file's line list
    end_line: int  # exclusive -- the line before the next `##`, or EOF


def _normalize_heading_text(text: str) -> str:
    """Same job as `_normalize_stem`, for heading text instead of a
    filename: strips Markdown inline markup (`` ` ``/`*`/`_`, so
    `` `Provider` `` and `Provider` compare equal) before folding case
    and punctuation the same way `--file` matching already does."""
    return _normalize_stem(_INLINE_MARKUP.sub("", text))


def _parse_sections(file_text: str) -> list[_Section]:
    """Every `##` heading in `file_text`, in document order, each
    paired with the line range it owns (its own heading line up to,
    but not including, the next `##` heading, or end of file)."""
    lines = file_text.split("\n")
    headings = [
        (lineno, match.group(1))
        for lineno, line in enumerate(lines)
        if (match := _SECTION_HEADING.match(line)) is not None
    ]

    sections = []
    for position, (lineno, raw_heading) in enumerate(headings, start=1):
        end_line = headings[position][0] if position < len(headings) else len(lines)
        number_match = _SECTION_NUMBER_PREFIX.match(raw_heading)
        number = int(number_match.group(1)) if number_match else None
        title = number_match.group(2) if number_match else raw_heading
        sections.append(
            _Section(index=position, number=number, title=title, start_line=lineno, end_line=end_line)
        )
    return sections


def _section_listing(sections: list[_Section]) -> str:
    return "; ".join(f"{section.index}. {section.title}" for section in sections)


def _resolve_section(sections: list[_Section], query: str) -> _Section:
    """Case/punctuation-insensitive `--section` lookup against
    `sections` (proposal-style match, same shape as `_resolve_file`):
    a heading-text fragment wins first if one is given and matches
    exactly (normalized); a number -- the heading's own declared
    numbering if any file heading has one, else plain 1-based position
    -- is tried next; a `difflib` "did you mean" covers a near-miss
    text fragment; anything else raises `DocRetrievalError` naming
    every section this file actually has, so the fix is one look
    away."""
    if not sections:
        raise DocRetrievalError("This file has no `##` headings to select a --section from.")

    stripped = query.strip()
    if not stripped:
        raise DocRetrievalError("--section needs a value: a number, a heading fragment, or both.")

    match = _SECTION_QUERY.match(stripped)
    number = int(match.group(1)) if match.group(1) else None
    text = match.group(2).strip()

    by_normalized = {_normalize_heading_text(section.title): section for section in sections}
    if text:
        exact = by_normalized.get(_normalize_heading_text(text))
        if exact is not None:
            return exact

    if number is not None:
        by_number = {section.number: section for section in sections if section.number is not None}
        if number in by_number:
            return by_number[number]
        if not text and 1 <= number <= len(sections):
            return sections[number - 1]

    if text:
        close = difflib.get_close_matches(
            _normalize_heading_text(text), by_normalized.keys(), n=5, cutoff=0.4
        )
        if close:
            suggestion_list = ", ".join(by_normalized[name].title for name in close)
            raise DocRetrievalError(f"No section matching {query!r}. Did you mean: {suggestion_list}?")
        raise DocRetrievalError(
            f"No section matching {query!r}, and nothing close enough to suggest. "
            f"Sections: {_section_listing(sections)}."
        )

    raise DocRetrievalError(
        f"No section numbered {number} (this file has {len(sections)} section(s)). "
        f"Sections: {_section_listing(sections)}."
    )


def _extract_section(file_text: str, query: str) -> tuple[_Section, str]:
    """Resolve `query` against `file_text`'s own `##` headings and
    return `(section, body)`, `body` being that section's exact lines
    -- heading included, nothing else invented or summarized, same
    contract as every other read in this module."""
    lines = file_text.split("\n")
    section = _resolve_section(_parse_sections(file_text), query)
    return section, "\n".join(lines[section.start_line : section.end_line]).rstrip()


def _repo_root() -> Path:
    # arklight/cli/doc_retrieval.py -> arklight/cli -> arklight -> repo root.
    return Path(__file__).resolve().parents[2]


def _docs_root() -> Path:
    root = _repo_root() / "docs"
    if not root.is_dir():
        raise DocRetrievalError(
            "docs/ not found. --retrieve-doc reads files already in the "
            "repo (see docs/Proposals/SEARCH-RETRIEVE-DOC-PROPOSAL.md "
            "section 1), so it only works from an ARKlight source "
            "checkout, not an installed package."
        )
    return root


def _read_text(path: Path, *, what: str) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise DocRetrievalError(f"{what} not found on disk: {path}") from exc


def _normalize_stem(value: str) -> str:
    """Case-fold and collapse runs of whitespace/hyphen/underscore to a
    single hyphen, so `architecture`, `Architecture`, and `ARCHITECTURE`
    (or `user-defined-components` / `user_defined_components` / `user
    defined components`) all compare equal (proposal SS4)."""
    return re.sub(r"[\s_-]+", "-", value.strip().lower())


def _display_stem(filename: str) -> str:
    stem = filename[:-3] if filename.lower().endswith(".md") else filename
    return _normalize_stem(stem)


def _parse_index_table(readme_text: str) -> list[tuple[str, str]]:
    """Extract (filename, description) pairs from a folder README's own
    index table -- the same "Covers" column text is reused verbatim for
    the `--file`-available footer rather than re-authored, so there's
    exactly one place that text has to stay accurate (proposal SS4.1)."""
    entries = []
    for line in readme_text.splitlines():
        match = _TABLE_ROW.match(line.strip())
        if match:
            entries.append((match.group(1), match.group(2)))
    return entries


def _folder_by_attr(attr: str) -> DocFolder | None:
    for folder in DOC_FOLDERS:
        if folder.attr == attr:
            return folder
    return None


def _selected_folder(args: argparse.Namespace) -> DocFolder | None:
    for folder in DOC_FOLDERS:
        if getattr(args, folder.attr, False):
            return folder
    return None


def _folder_entries(folder: DocFolder) -> tuple[str, list[tuple[str, str]]]:
    """Returns (that folder's own README.md text, its parsed index
    entries)."""
    readme_path = _docs_root() / folder.path / "README.md"
    readme_text = _read_text(readme_path, what=f"docs/{folder.path}/README.md")
    return readme_text, _parse_index_table(readme_text)


def _folder_footer(folder: DocFolder, entries: list[tuple[str, str]]) -> str:
    lines = ["---", f"Files in docs/{folder.path}/ (use --file NAME):"]
    if not entries:
        lines.append("  (none)")
        return "\n".join(lines)

    stems = [_display_stem(filename) for filename, _ in entries]
    width = max(len(stem) for stem in stems) + 2
    for (_, description), stem in zip(entries, stems):
        lines.append(f"  {stem:<{width}}{description}")
    return "\n".join(lines)


def _resolve_file(folder: DocFolder, entries: list[tuple[str, str]], query: str) -> str:
    """Case-insensitive, punctuation-normalized stem match against
    `entries` (proposal SS4.3). Raises `DocRetrievalError` with a
    `difflib`-based "did you mean" on a miss (proposal SS5)."""
    normalized_query = _normalize_stem(query)
    stems_to_filenames = {_display_stem(filename): filename for filename, _ in entries}

    exact = stems_to_filenames.get(normalized_query)
    if exact is not None:
        return exact

    close = difflib.get_close_matches(normalized_query, stems_to_filenames.keys(), n=5, cutoff=0.4)
    if close:
        suggestion_list = ", ".join(close)
        raise DocRetrievalError(
            f"No file matching {query!r} in docs/{folder.path}/. "
            f"Did you mean: {suggestion_list}?"
        )
    raise DocRetrievalError(
        f"No file matching {query!r} in docs/{folder.path}/, and nothing "
        f"close enough to suggest."
    )


def _file_without_folder_error(query: str) -> DocRetrievalError:
    """Builds the SS4.4 error for `--file` given without a preceding
    directory flag, naming the folder(s) a match for `query` was
    actually found in when one exists, so the fix is one copy-paste
    away."""
    normalized_query = _normalize_stem(query)
    hint = "--file requires a folder flag (--foundational, --proposals, ...)."

    hits = []
    for folder in DOC_FOLDERS:
        readme_path = _docs_root() / folder.path / "README.md"
        if not readme_path.is_file():
            continue
        entries = _parse_index_table(_read_text(readme_path, what=f"docs/{folder.path}/README.md"))
        for filename, _ in entries:
            if _display_stem(filename) == normalized_query:
                hits.append((folder, filename))
                break

    if not hits:
        return DocRetrievalError(hint)

    pointers = "; ".join(
        f"{filename} lives in docs/{folder.path}/ -- try {folder.flag} --file {_display_stem(filename)}"
        for folder, filename in hits
    )
    return DocRetrievalError(f"{hint} {pointers}.")


def _root_output() -> str:
    readme_path = _docs_root() / "README.md"
    readme_text = _read_text(readme_path, what="docs/README.md")
    return f"{readme_text.rstrip()}\n\n{_ROOT_FOOTER}"


def _folder_output(folder: DocFolder, file_query: str | None, section_query: str | None = None) -> str:
    if section_query is not None and file_query is None:
        raise DocRetrievalError(
            "--section requires --file NAME too -- a section belongs to one "
            "file, not a whole folder index."
        )

    readme_text, entries = _folder_entries(folder)

    if file_query is None:
        return f"{readme_text.rstrip()}\n\n{_folder_footer(folder, entries)}"

    filename = _resolve_file(folder, entries, file_query)
    file_path = _docs_root() / folder.path / filename
    file_text = _read_text(file_path, what=f"docs/{folder.path}/{filename}")

    if section_query is not None:
        section, body = _extract_section(file_text, section_query)
        shown_number = section.number if section.number is not None else section.index
        header = f"docs/{folder.path}/{filename} -- section {shown_number}: {section.title}"
        return f"{_RULE}\n{header}\n{_RULE}\n\n{body}\n"

    header = f"docs/{folder.path}/{filename}"
    return (
        f"{readme_text.rstrip()}\n\n"
        f"{_RULE}\n{header}\n{_RULE}\n\n"
        f"{file_text.rstrip()}\n"
    )


def ignored_flag_notices(args: argparse.Namespace) -> list[str]:
    """`--limit`/`--near`/`--accept` are component-lookup-only flags
    (proposal SS2) -- when passed alongside `--retrieve-doc`, this
    returns the short "ignored" notices `_cmd_search` prints to stderr
    instead of silently dropping them. (`--limit`'s default is 5, so a
    `--limit 5` typed explicitly alongside `--retrieve-doc` is
    indistinguishable from not passing it at all and isn't flagged --
    the same ambiguity `argparse` defaults always carry.)"""
    notices = []
    if args.limit != 5:
        notices.append("--limit is component-lookup-only and is ignored with --retrieve-doc.")
    if args.near is not None:
        notices.append("--near is component-lookup-only and is ignored with --retrieve-doc.")
    if args.accept:
        notices.append("--accept is component-lookup-only and is ignored with --retrieve-doc.")
    return notices


def run_retrieve_doc(args: argparse.Namespace) -> str:
    """Top-level entry point for `_cmd_search` once `args.retrieve_doc`
    is set. Returns the full string to print; raises `DocRetrievalError`
    (caught by the caller) on any failure."""
    if args.name not in (None, "index"):
        raise DocRetrievalError(
            f"--retrieve-doc doesn't look up a name ({args.name!r}) -- the "
            "only positional value it accepts is the literal 'index' "
            "(same as the bare form). Use a folder flag (--foundational, "
            "--proposals, ...) to navigate, and --file NAME to select a "
            "file inside it."
        )

    folder = _selected_folder(args)
    file_query = getattr(args, "file", None)
    section_query = getattr(args, "section", None)

    if folder is None:
        if section_query is not None:
            raise DocRetrievalError(
                "--section requires a folder flag and --file NAME too -- a "
                "section belongs to one file."
            )
        if file_query is not None:
            raise _file_without_folder_error(file_query)
        return _root_output()

    return _folder_output(folder, file_query, section_query)
