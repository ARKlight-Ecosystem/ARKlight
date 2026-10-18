"""
Markdown-to-IR parser.

Stage M2 of the Markdown-as-first-class-content landing order
(`docs/Implementation/MARKDOWN-CONTENT-ADDENDUM.md`) -- the core of
`docs/Proposals/MARKDOWN-CONTENT-PROPOSAL.md`. `parse_markdown` turns a
Markdown document's body into a list of `ARKNode`s built from
`arklight.api`'s existing components -- the same component functions a
hand-written `site.py` already calls -- so the result is an ordinary
ARK AST subtree, not a second, parallel representation. From there it
goes through the exact same `normalize` -> `validate` -> `build` ->
`backend` stages every Python-authored page already goes through (see
`arklight/compiler/pipeline.py`); nothing downstream needs to know this
subtree came from Markdown rather than a `Page(...)`-returning
function. No new `arklight.ir.schema.SCHEMA` entries are added or
needed -- every construct below lands on a node type that already
exists.

Recognizers (headings, emphasis, fenced code, lists, links, tables,
rules) are extracted and adapted from `arklight/cli/mdrender.py` --
that module's own vendored, dependency-free Markdown reader, written
for `arklight search --retrieve-doc`'s ANSI terminal output. The
regular expressions for each construct's *shape* are reused close to
verbatim; what changes is the target: `mdrender.py` stitches styled
ANSI strings together, this module builds `ARKNode` trees. `mdrender.py`
itself is untouched -- it still wants terminal text, not IR, and stays
exactly as it is.

A fenced block's language info string (`` ```python ``) is read and
then deliberately discarded, not carried onto `Code` as an extra prop:
`arklight.ir.schema.SCHEMA` has no recognized slot for it today, so a
`lang=`/`class_name=`-style prop would just round-trip through the
HTML backend's generic "unknown prop" fallback
(`arklight/backend/html/attrs.py`) as a `data-*` attribute nobody asked
for -- noise, not a feature, and not anything the mapping table below
promises. A later stage can add a real, schema-backed slot for it if
that turns out to matter.

Construct mapping, exactly the table in the proposal:

| Markdown                  | IR node(s)                                |
| -------------------------- | ------------------------------------------ |
| `#` ... `######`           | `Heading(level=1..6)`                      |
| paragraph                  | `Text` (one run) / `Container` (several)   |
| `**bold**`, `*italic*`     | `Strong`, `Em`                             |
| `` `code` ``                 | `Code`                                     |
| `[text](url)`               | `Link`                                     |
| `- item` / `1. item`        | `List`/`Item`, `OrderedList`/`Item`        |
| `![alt](src)`                | `Image`                                    |
| fenced block                 | `Pre(Code(...))`                           |
| `> quote`                    | `Blockquote`                               |
| `\\| a \\| b \\|` tables        | `Table`/`TableHead`/`TableBody`/`TableRow`/`TableHeaderCell`/`TableCell` |
| `---`                        | `HorizontalRule`                           |

One constraint this module has to design around, not just restate:
several of the node types above are `text_only_children` in
`arklight.ir.schema.SCHEMA` -- `Heading`, `Item`, `Text`, `Strong`,
`Em`, `Code`, and `Link` may only hold a plain string (or `Bind(...)`,
irrelevant here), never a nested `ARKNode`
(`arklight.ir.validate.validate_node`'s `text_only_children` branch).
That is an existing, deliberate rule this module does not get to
relax -- extending it is exactly the "no new schema entries" ground
the proposal and the addendum both rule out for this stage. Two
different answers follow from it, by context:

- **Inside a real container** (a paragraph's own top level, a table
  cell, a blockquote): inline markup -- bold, italic, code spans,
  links -- becomes real sibling nodes. A paragraph with exactly one
  run collapses to that run directly (a plain-text-only paragraph is
  just `Text(...)`, matching the table above exactly; a paragraph that
  is *only* `**bold**` is just `Strong(...)`, not `Container(Strong(...))`);
  two or more runs are wrapped in `Container(...)`, which is not
  text-only and holds them as ordinary siblings. `TableCell`/
  `TableHeaderCell` aren't text-only either, so a cell gets the same
  run list directly as children, no `Container` wrapper needed.
- **Inside a text-only node** (a heading's title, a list item's body):
  inline markup is flattened to plain text instead -- `**bold**`'s
  emphasis is dropped and its inner text kept, the same way a
  `<h1><strong>bold</strong> title</h1>` would read once stripped to
  its `textContent`. A heading or list item that wants real inline
  `Strong`/`Link` nodes is outside what this stage's node types can
  express; that is a limitation of `text_only_children` on `Heading`/
  `Item` themselves, not something this parser can route around
  without the schema change this stage explicitly isn't making.

**Raw HTML (Q4), settled per the addendum: escaped to visible text.**
This module has no `<tag>`-recognizing block or inline rule at all --
deliberately. A line or span that happens to contain `<script>...`
matches none of the patterns below, so it falls straight through to
the paragraph/inline-text path and is carried as an ordinary string
inside a `Text(...)` node, exactly like any other prose. Nothing
downstream in this module treats it as markup. The actual *escaping*
to visible text happens one stage later, for free: the HTML backend's
own text-rendering path (`arklight/backend/html/page_render.py`) runs
every text child through `html.escape` already, for every text node in
the system, Markdown-sourced or not -- so a raw `<script>` in a
Markdown file reaches the compiled page as `&lt;script&gt;...`, never
as a live element, with no Markdown-specific escaping logic needed
here. This module's own job is just to never *mistake* that text for
markup in the first place.

**Local references (Stage M4).** When `parse_markdown` is told which
content file it is parsing (`content_path=`), every `Image` `src` and
`Link` `href` that names a local file is rewritten into the form the
rest of the pipeline already understands, *before* the tree is handed
off -- so `arklight.compiler.asset_check` / `link_check` see a
Markdown-sourced reference exactly as they would a Python-authored one,
and need no Markdown-specific code. Without `content_path=` nothing is
rewritten (the Stage M2 behavior, which is what a bare `parse_markdown`
call gets). The rules, in order:

1. An external reference (`https:`, `mailto:`, `data:`, `//host`), a
   bare `#fragment`, or a root-relative path (`/guide`,
   `/assets/x.png`) is left exactly as written. Root-relative paths
   name the output root on purpose, and are checked downstream.
2. A relative link to a Markdown file (`Link`, path ending `.md`) is
   resolved against the *linking file's own directory* inside
   `content/` and replaced with that page's route (`?query`/`#fragment`
   kept) -- so `[setup](./setup.md#install)` written in
   `content/docs/index.md` becomes `/docs/setup#install`, honoring a
   front matter `route` override. A target that is not a (non-draft)
   page is a `MarkdownReferenceError`, never a silent dead link.
3. Every other relative path -- every `Image`, and a `Link` to a file
   such as a PDF -- is resolved against `assets/`: `./diagram.png` and
   `diagram.png` both become `assets/diagram.png`. A path already
   written as `assets/...` is left anchored (the spelling Python pages
   use), and `..` is allowed only while the result stays under
   `assets/` (so `../assets/logo.png`, the on-disk spelling from a
   top-level content file, works). A path that climbs out of `assets/`
   is a `MarkdownReferenceError`.

Whether the resulting `assets/...` file actually exists is *not*
decided here: that is `asset_check`'s job, and it reports a missing
one with its usual report.

Multi-paragraph list items, nested lists, and inline images (an
`![alt](src)` embedded mid-paragraph rather than standing alone as a
whole line) are not handled by this stage -- they are not part of the
mapping table above, and are left for a later stage if real projects
need them. A standalone line containing nothing but one `![alt](src)`
becomes a block-level `Image(...)`.
"""

from __future__ import annotations

import posixpath
import re
from typing import Mapping

from arklight.api import (
    Blockquote,
    Code,
    Container,
    Em,
    Heading,
    HorizontalRule,
    Image,
    Item,
    Link,
    List,
    OrderedList,
    Pre,
    Strong,
    Table,
    TableBody,
    TableCell,
    TableHead,
    TableHeaderCell,
    TableRow,
    Text,
)
from arklight.ast.nodes import ARKNode

# ---------------------------------------------------------------------------
# Block-level recognizers -- shapes adapted from arklight/cli/mdrender.py's
# `_ATX_HEADING`/`_FENCE`/`_HRULE`/`_BLOCKQUOTE`/`_BULLET`/`_NUMBERED`/
# `_TABLE_SEP_CELL`. mdrender.py itself is untouched; these are
# independent copies, free to diverge once a later stage needs to (a
# `lang=` fence info string, kept below, is already one such case --
# mdrender.py never needed it for ANSI output).
# ---------------------------------------------------------------------------

_ATX_HEADING = re.compile(r"^(#{1,6})\s+(.*?)\s*#*\s*$")
_FENCE = re.compile(r"^(\s*)(```|~~~)(.*)$")
_HRULE = re.compile(r"^\s*([-*_])(?:\s*\1){2,}\s*$")
_BLOCKQUOTE = re.compile(r"^\s*>\s?(.*)$")
_BULLET = re.compile(r"^(\s*)([-*+])\s+(.*)$")
_NUMBERED = re.compile(r"^(\s*)(\d+)[.)]\s+(.*)$")
_IMAGE_ONLY = re.compile(r"^!\[([^\]]*)\]\(([^)]+)\)$")
_TABLE_SEP_CELL = re.compile(r"^:?-{1,}:?$")

# ---------------------------------------------------------------------------
# Inline recognizers. One combined, alternation-based pattern rather
# than mdrender.py's sequence of independent `.sub(...)` passes: this
# module needs to walk the matches *in source order*, building a
# separate node per match and a plain-text run for every gap between
# them, not rewrite the string in place the way ANSI styling does.
# Code spans are tried first in the alternation so `` `**not bold**` ``
# can never have its backtick-protected `**`/`_` mistaken for emphasis
# -- the same ordering mdrender.py's `_stash_code`-before-styling two-pass
# approach achieves by a different mechanism. Bold is tried before
# italic so `**x**` commits to `Strong`, not `Em(Em(...))`-shaped
# nonsense from two single `*`s either side of `*x*`.
# ---------------------------------------------------------------------------

_INLINE_TOKEN = re.compile(
    r"`(?P<code>[^`]+)`"
    r"|\[(?P<link_text>[^\]]*)\]\((?P<link_url>[^)]+)\)"
    r"|(?P<bold_marker>\*\*|__)(?!\s)(?P<bold>.+?)(?<!\s)(?P=bold_marker)"
    r"|(?<!\*)\*(?!\*)(?!\s)(?P<italic_star>[^*]+?)(?<!\s)\*(?!\*)"
    r"|(?<!_)_(?!_)(?!\s)(?P<italic_under>[^_]+?)(?<!\s)_(?!_)"
)


class MarkdownSyntaxError(ValueError):
    """Raised for a Markdown construct that opens but never closes --
    currently only an unterminated fenced code block. Names the file
    and, where meaningful, the line the construct opened on, the same
    "fails loudly instead of resolving silently" posture
    `arklight.content.frontmatter.FrontMatterError` already takes for
    a malformed front matter block."""


class MarkdownReferenceError(MarkdownSyntaxError):
    """Raised (Stage M4) for a local reference that cannot be resolved
    at all: a link to a Markdown file that is not a page, or a path
    that climbs out of `assets/`/`content/`. A subclass of
    `MarkdownSyntaxError` so every caller already reporting that one
    (the compiler pipeline) reports this the same way. A reference
    that resolves fine but names a file that doesn't exist is *not*
    this error -- `arklight.compiler.asset_check` owns that."""


# ---------------------------------------------------------------------------
# Inline run parsing
# ---------------------------------------------------------------------------


def _inline_node_from_match(match: re.Match[str]) -> ARKNode:
    if match.group("code") is not None:
        return Code(match.group("code"))
    if match.group("link_url") is not None:
        text = match.group("link_text") or match.group("link_url")
        return Link(text, href=match.group("link_url"))
    if match.group("bold") is not None:
        return Strong(match.group("bold"))
    if match.group("italic_star") is not None:
        return Em(match.group("italic_star"))
    if match.group("italic_under") is not None:
        return Em(match.group("italic_under"))
    raise AssertionError(f"unreachable: unrecognized inline token {match.group(0)!r}")


def _parse_inline(text: str) -> list[ARKNode]:
    """Split `text` into an ordered list of inline run nodes: a plain
    run becomes `Text(run)`, a recognized span becomes its matching
    `Code`/`Link`/`Strong`/`Em` node. Always returns at least one node
    (`Text("")` for empty input), so callers never have to special-case
    zero runs."""
    runs: list[ARKNode] = []
    pos = 0
    for match in _INLINE_TOKEN.finditer(text):
        if match.start() > pos:
            runs.append(Text(text[pos : match.start()]))
        runs.append(_inline_node_from_match(match))
        pos = match.end()
    if pos < len(text) or not runs:
        runs.append(Text(text[pos:]))
    return runs


def _inline_plain_text(text: str) -> str:
    """Flatten `text`'s inline markup to a plain string -- a span's
    *syntax* is removed and its inner text kept, with no node built at
    all. Used wherever the surrounding node is `text_only_children`
    (`Heading`, `Item`) and so cannot hold a nested `Strong`/`Em`/
    `Code`/`Link`, per this module's docstring."""

    def _replace(match: re.Match[str]) -> str:
        if match.group("code") is not None:
            return match.group("code")
        if match.group("link_url") is not None:
            return match.group("link_text") or match.group("link_url")
        if match.group("bold") is not None:
            return match.group("bold")
        if match.group("italic_star") is not None:
            return match.group("italic_star")
        if match.group("italic_under") is not None:
            return match.group("italic_under")
        raise AssertionError(f"unreachable: unrecognized inline token {match.group(0)!r}")

    return _INLINE_TOKEN.sub(_replace, text).strip()


def _paragraph_node(runs: list[ARKNode]) -> ARKNode:
    """One run collapses to that run directly (a plain-text-only
    paragraph is `Text(...)`, matching the proposal's mapping table
    exactly; an all-`**bold**` paragraph is `Strong(...)`, not a
    one-child `Container`); more than one is wrapped in `Container`,
    which (unlike `Text`) is a real container and can hold them as
    ordinary siblings. See this module's docstring."""
    if len(runs) == 1:
        return runs[0]
    return Container(*runs)


# ---------------------------------------------------------------------------
# Tables -- row splitting adapted from mdrender.py's `_split_table_row`/
# `_is_table_separator` (the alignment-detection half, `_column_alignment`,
# isn't needed: the mapping table above has no alignment prop for this
# stage).
# ---------------------------------------------------------------------------


def _split_table_row(line: str) -> list[str]:
    stripped = line.strip()
    if stripped.startswith("|"):
        stripped = stripped[1:]
    if stripped.endswith("|") and not stripped.endswith("\\|"):
        stripped = stripped[:-1]
    if not stripped:
        return []
    return [cell.strip().replace("\\|", "|") for cell in re.split(r"(?<!\\)\|", stripped)]


def _is_table_separator(line: str) -> bool:
    cells = _split_table_row(line)
    return bool(cells) and all(_TABLE_SEP_CELL.match(cell) for cell in cells)


def _build_table(table_lines: list[str]) -> ARKNode:
    header = _split_table_row(table_lines[0])
    data = [_split_table_row(line) for line in table_lines[2:]]
    n_cols = max([len(header)] + [len(row) for row in data], default=0)

    def pad(row: list[str]) -> list[str]:
        return row + [""] * (n_cols - len(row))

    header_row = TableRow(*[TableHeaderCell(*_parse_inline(cell)) for cell in pad(header)])
    body_rows = [
        TableRow(*[TableCell(*_parse_inline(cell)) for cell in pad(row)]) for row in data
    ]
    return Table(TableHead(header_row), TableBody(*body_rows))


# ---------------------------------------------------------------------------
# Block-level parsing
# ---------------------------------------------------------------------------


def _starts_new_block(line: str) -> bool:
    """True if `line` should end an in-progress paragraph rather than
    be swallowed into it as a soft-wrapped continuation line -- i.e.
    it opens one of the other block constructs this module recognizes."""
    stripped = line.strip()
    return bool(
        _ATX_HEADING.match(line)
        or _FENCE.match(line)
        or _HRULE.match(line)
        or line.lstrip().startswith(">")
        or _BULLET.match(line)
        or _NUMBERED.match(line)
        or _IMAGE_ONLY.match(stripped)
    )


# ---------------------------------------------------------------------------
# Local reference resolution (Stage M4)
# ---------------------------------------------------------------------------

_URL_SCHEME = re.compile(r"^[a-z][a-z0-9+.\-]*:", re.I)
_ASSETS_DIR = "assets"


def _split_suffix(value: str) -> tuple[str, str]:
    """`"a/b.png?x=1#f"` -> `("a/b.png", "?x=1#f")`."""
    cut = min((i for i in (value.find("?"), value.find("#")) if i != -1), default=len(value))
    return value[:cut], value[cut:]


def _resolve_reference(
    raw: str,
    *,
    is_link: bool,
    filename: str,
    content_path: str,
    page_routes: Mapping[str, str],
) -> str:
    """Rewrite one `src`/`href` per the rules in this module's
    docstring. Returns `raw` unchanged for anything that isn't a
    relative local path."""
    value = raw.strip()
    if not value or value.startswith(("#", "/")) or _URL_SCHEME.match(value):
        return raw
    path, suffix = _split_suffix(value)
    if not path:
        return raw

    if is_link and path.lower().endswith(".md"):
        target = posixpath.normpath(posixpath.join(posixpath.dirname(content_path), path))
        if target == ".." or target.startswith("../"):
            raise MarkdownReferenceError(
                f"{filename}: link {raw!r} climbs out of content/ -- a link to a "
                "Markdown page must point at a file under content/."
            )
        route = page_routes.get(target)
        if route is None:
            raise MarkdownReferenceError(
                f"{filename}: link {raw!r} points at content/{target}, which is not a "
                "page -- the file doesn't exist, is misspelled, or is marked "
                "`draft: true` (drafts have no route)."
            )
        return route + suffix

    rel = posixpath.normpath(path)
    if rel == ".":
        return raw
    if rel == _ASSETS_DIR or rel.startswith(_ASSETS_DIR + "/"):
        resolved = rel
    else:
        resolved = posixpath.normpath(f"{_ASSETS_DIR}/{rel}")
    if not resolved.startswith(_ASSETS_DIR + "/"):
        raise MarkdownReferenceError(
            f"{filename}: reference {raw!r} climbs out of {_ASSETS_DIR}/ -- relative paths "
            f"in Markdown are resolved against {_ASSETS_DIR}/, so the file has to live "
            f"under it (write {_ASSETS_DIR}/... or a path below it)."
        )
    return resolved + suffix


def _resolve_references(
    blocks: list[ARKNode], *, filename: str, content_path: str, page_routes: Mapping[str, str]
) -> None:
    """Rewrite, in place, every `Image` `src` and `Link` `href` in the
    freshly built `blocks` (nodes this module just created -- nothing
    shared is mutated). Fenced code is untouched: a `Code` node holds
    plain text, never an `Image`/`Link`."""

    def walk(item: object) -> None:
        if isinstance(item, ARKNode):
            if item.type == "Image" and isinstance(item.props.get("src"), str):
                item.props["src"] = _resolve_reference(
                    item.props["src"], is_link=False, filename=filename,
                    content_path=content_path, page_routes=page_routes,
                )
            elif item.type == "Link" and isinstance(item.props.get("href"), str):
                item.props["href"] = _resolve_reference(
                    item.props["href"], is_link=True, filename=filename,
                    content_path=content_path, page_routes=page_routes,
                )
            walk(item.children)
        elif isinstance(item, (list, tuple)):
            for child in item:
                walk(child)

    walk(blocks)


def parse_markdown(
    source: str,
    *,
    filename: str = "<content>",
    content_path: str | None = None,
    page_routes: Mapping[str, str] | None = None,
) -> list[ARKNode]:
    """Parse a Markdown document's body into a list of block-level
    `ARKNode`s, built from `arklight.api`'s existing components --
    `source` is expected to already have any front matter block
    removed (`arklight.content.frontmatter.parse_front_matter`'s
    `body` return value; Stage M1), since front matter has no
    Markdown-rendering meaning of its own.

    The returned list is an ordinary ARK AST fragment, ready for the
    same `normalize` -> `validate` -> `build` stages (`arklight.ir.
    normalize`/`validate`/`build`) any other page's children already
    go through -- nothing here validates or normalizes; that stays the
    existing pipeline's job, so a Markdown-sourced page is checked by
    exactly the same rules a Python-authored one is.

    `content_path`, if given, is this file's POSIX path relative to
    `content/` (e.g. `"docs/setup.md"`) and turns on local reference
    resolution (Stage M4, see the module docstring). `page_routes` maps
    every non-draft content file's such path to its route; it is what a
    link to another `.md` file is resolved through. With neither, the
    tree is returned with every reference exactly as written.

    Raises `MarkdownSyntaxError` for a fenced code block that opens
    but never closes, and `MarkdownReferenceError` (a subclass) for a
    local reference that cannot be resolved.
    """
    lines = source.split("\n")
    n = len(lines)
    blocks: list[ARKNode] = []
    i = 0

    while i < n:
        line = lines[i]

        if not line.strip():
            i += 1
            continue

        fence_match = _FENCE.match(line)
        if fence_match:
            indent, marker, _info = fence_match.groups()
            code_lines: list[str] = []
            opened_at = i + 1
            i += 1
            closed = False
            while i < n:
                close_match = _FENCE.match(lines[i])
                if (
                    close_match
                    and close_match.group(2) == marker
                    and close_match.group(1) == indent
                ):
                    closed = True
                    i += 1
                    break
                code_lines.append(lines[i])
                i += 1
            if not closed:
                raise MarkdownSyntaxError(
                    f"{filename}:{opened_at}: unterminated fenced code block -- "
                    f"the opening {marker!r} fence has no matching close"
                )
            blocks.append(Pre(Code("\n".join(code_lines))))
            continue

        heading_match = _ATX_HEADING.match(line)
        if heading_match:
            level = len(heading_match.group(1))
            blocks.append(Heading(_inline_plain_text(heading_match.group(2)), level=level))
            i += 1
            continue

        if _HRULE.match(line):
            blocks.append(HorizontalRule())
            i += 1
            continue

        image_match = _IMAGE_ONLY.match(line.strip())
        if image_match:
            alt, src = image_match.groups()
            blocks.append(Image(src=src, alt=alt))
            i += 1
            continue

        if line.lstrip().startswith(">"):
            quote_parts: list[str] = []
            while i < n and lines[i].lstrip().startswith(">"):
                quote_match = _BLOCKQUOTE.match(lines[i])
                quote_parts.append(quote_match.group(1) if quote_match else "")
                i += 1
            quote_text = " ".join(part for part in quote_parts if part.strip())
            blocks.append(Blockquote(_paragraph_node(_parse_inline(quote_text))))
            continue

        bullet_match = _BULLET.match(line)
        if bullet_match:
            items: list[ARKNode] = []
            while i < n:
                match = _BULLET.match(lines[i])
                if not match:
                    break
                items.append(Item(_inline_plain_text(match.group(3))))
                i += 1
            blocks.append(List(*items))
            continue

        numbered_match = _NUMBERED.match(line)
        if numbered_match:
            items = []
            while i < n:
                match = _NUMBERED.match(lines[i])
                if not match:
                    break
                items.append(Item(_inline_plain_text(match.group(3))))
                i += 1
            blocks.append(OrderedList(*items))
            continue

        if "|" in line and i + 1 < n and _is_table_separator(lines[i + 1]):
            table_lines = [line, lines[i + 1]]
            j = i + 2
            while j < n and lines[j].strip() and "|" in lines[j]:
                table_lines.append(lines[j])
                j += 1
            blocks.append(_build_table(table_lines))
            i = j
            continue

        # Paragraph: everything else. Consecutive non-blank lines that
        # don't open another block are soft-wrapped into one logical
        # paragraph, joined with a single space -- a CommonMark soft
        # line break, not a hard one; this module has no line-break
        # construct of its own (no trailing-double-space or `<br>`
        # handling), matching the proposal's mapping table, which lists
        # none.
        para_lines = [line.strip()]
        i += 1
        while i < n and lines[i].strip() and not _starts_new_block(lines[i]):
            para_lines.append(lines[i].strip())
            i += 1
        blocks.append(_paragraph_node(_parse_inline(" ".join(para_lines))))

    if content_path is not None:
        _resolve_references(
            blocks,
            filename=filename,
            content_path=content_path,
            page_routes=page_routes or {},
        )
    return blocks
