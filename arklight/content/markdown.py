"""
Markdown-to-IR parser.

Stage M2 of the Markdown-as-first-class-content landing order -- the
ladder's core parsing stage; see `docs/Foundational/DESIGN-NOTES.md`'s
"Design record: Markdown as first-class content" (the ladder's
accepted proposal and implementation addendum, both retired once all
ten stages shipped). `parse_markdown` turns a
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

**Style hooks (Stage M6; see `CHANGELOG.md`'s `M6` entry).**
`style_hooks=True`
runs a small post-pass (`_apply_style_hooks`, after the tree above is
otherwise fully built) that attaches a stable `class_name` -- and, on
every `Heading`, a slugged `id` -- to each block this parser produces,
under a fixed `ark-md-*` prefix (`ark-md-h1`..`ark-md-h6`, `ark-md-p`,
`ark-md-list`/`ark-md-ordered-list`/`ark-md-item`, `ark-md-pre`/
`ark-md-code-block`, `ark-md-blockquote`, `ark-md-table` and its
`ark-md-thead`/`ark-md-tbody`/`ark-md-tr`/`ark-md-th`/`ark-md-td`
children, `ark-md-hr`, `ark-md-img`, plus `ark-md-strong`/`ark-md-em`/
`ark-md-code`/`ark-md-link` for the rare case where a whole paragraph
collapses to one bare inline node -- see `_paragraph_node`). This is
what `Site.style(...)`/`Site.style_selector(...)` (CSS authored in
`site.py`) has to hook into and style on. `arklight.backend.css.
markdown_defaults.MARKDOWN_CSS_BODY` ships a baseline look for every
one of these classes, always included in the generated stylesheet --
**default styling only, for now.** There is no dedicated,
supported way yet to swap that default out wholesale for Markdown
content specifically; the only lever today is the same generic
`allow_redefine=True` escape hatch `RESERVED_UTILITY_CLASSES` already
gives every other built-in utility class (`.card`, `.nav`, ...), since
each `ark-md-*` class is registered there too. A first-class
Markdown-theming surface is a later, unscheduled stage -- see the
addendum.

The flag defaults to `False`: a bare `parse_markdown(...)` call (this
stage's own direct callers in `tests/test_markdown.py`, and anyone
calling this module outside the real build pipeline) gets the exact
same tree Stage M2-M4 always produced, byte-for-byte -- no surprise
`class_name`/`id` props appear unless asked for. The one caller that
assembles real site pages, `arklight.content.discovery.
synthesize_page`, always passes `style_hooks=True`: a Markdown-authored
page gets these hooks automatically, with nothing to opt into in
`site.py` -- see that module for why this is the "implicitly handled
by the compiler" half of the stage, as opposed to the `markdown-
production` template's `components/` visibility story (Stage M8, same
addendum file).

`content/*.md` is not a `Page(...)`-authored page re-expressed in a
different syntax: it is not feature parity. The construct mapping
table above is the entire Markdown vocabulary this parser understands
-- no component props, no `State`/`Bind`/`Action`, no behaviors, no
custom components -- so a Markdown file can only ever produce what
that table can express, styled by what this stage adds. A page that
needs any of that goes through a `@site.page(...)`-decorated function
instead (mixing both in one project is Stage M5's own `markdown-
production` template, and is the supported, intended way to get both).
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
    Span,
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


def _parse_inline(text: str) -> list:
    """Split `text` into an ordered list of inline runs: a plain run
    stays a bare `str`, a recognized span becomes its matching
    `Code`/`Link`/`Strong`/`Em` node. Always returns at least one run
    (`""` for empty input), so callers never have to special-case zero
    runs.

    **Fragmentation bugfix (Stage M9 pass):** this used to wrap every
    plain run in `Text(run)` right here. `Text` is a real, generic IR
    node type that renders as its own `<p>` tag unconditionally
    (`arklight.backend.html.tag_map.TAG_MAP["Text"] == "p"`) -- so a
    paragraph like `"Some **bold** text"` produced *three* runs,
    `[Text("Some "), Strong("bold"), Text(" text")]`, and rendered as
    `<p>Some </p><strong>bold</strong><p> text</p>`: the sentence torn
    across two sibling `<p>` elements with an inline `<strong>`
    stranded between them, instead of one paragraph. The same
    `TableHeaderCell(*_parse_inline(cell))`/`TableCell(*_parse_inline(cell))`
    construction (just below, in `_parse_table`) meant any table cell
    mixing plain text with inline markup got a stray `<p>` nested
    inside its `<th>`/`<td>` the same way.

    A bare run now stays a plain `str` here, deferring the "does this
    need wrapping" decision to each caller -- because the honest
    answer turned out to depend on the parent, not on `_parse_inline`
    itself. `arklight.ir.normalize.normalize_children` wraps *any*
    bare-string child of a non-text-only IR parent (`Container`,
    `TableHeaderCell`, `TableCell` all qualify) in a `Text(...)` node
    on its own, unconditionally -- that is deliberate, existing,
    relied-upon behavior for ordinary hand-authored `site.py` trees
    (`Container("Panel")` meaning "a one-paragraph panel";
    `tests/test_normalize.py` pins it), so it cannot be changed or
    special-cased for Markdown without breaking that. A lone run
    (no inline markup at all) *should* still get `Text(...)`'s `<p>`
    wrapping -- that's correct, and `_paragraph_node` below still asks
    for it explicitly. Only the *multi-run* case needs a different
    answer, and `_paragraph_node`/`_parse_table` supply it with
    `_spanify`: wrapping each bare-string run in `Span(...)` before it
    ever reaches `Container`/`TableHeaderCell`/`TableCell`, so
    `normalize_children` finds no bare string left to wrap. `Span` is
    the existing, already-registered closed-vocabulary inline tag
    (`arklight.ir.schema.SCHEMA["Span"].text_only_children is True`,
    `TAG_MAP["Span"] == "span"`) built for exactly this: text with no
    semantic meaning of its own that must render inline, not as its
    own block. No new `arklight.ir.schema.SCHEMA` entry, per this
    module's own docstring constraint -- `Span` already existed."""
    runs: list = []
    pos = 0
    for match in _INLINE_TOKEN.finditer(text):
        if match.start() > pos:
            runs.append(text[pos : match.start()])
        runs.append(_inline_node_from_match(match))
        pos = match.end()
    if pos < len(text) or not runs:
        runs.append(text[pos:])
    return runs


def _spanify(runs: list) -> list[ARKNode]:
    """Multi-run case only (see `_parse_inline`'s bugfix note): wrap
    each bare `str` run in `Span(...)` so it survives
    `arklight.ir.normalize.normalize_children`'s otherwise-correct
    "bare string under a non-text-only parent becomes `Text(...)`"
    pass without being fragmented into its own `<p>`. Inline element
    runs (`Strong`/`Em`/`Code`/`Link`) pass through unchanged -- they
    already render inline and were never the problem."""
    return [Span(run) if isinstance(run, str) else run for run in runs]


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


def _paragraph_node(runs: list) -> ARKNode:
    """One run collapses to that run directly -- except a bare `str`
    run (a plain-text-only paragraph, no inline markup at all) still
    needs `Text(...)`'s own `<p>` wrapping, since `_parse_inline` no
    longer wraps plain runs itself (see its docstring's bugfix note);
    an all-`**bold**` paragraph collapses to `Strong(...)` directly,
    not a one-child `Container`, matching the proposal's mapping table
    exactly. More than one run is wrapped in `Container`, with every
    bare-string run passed through `_spanify` first so normalization
    can't fragment the paragraph into sibling `<p>`s around an inline
    element -- see `_parse_inline`'s docstring for the full bugfix
    story. See this module's docstring."""
    if len(runs) == 1:
        return runs[0] if isinstance(runs[0], ARKNode) else Text(runs[0])
    return Container(*_spanify(runs))


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

    # Same single-vs-multi-run split as `_paragraph_node` above, and
    # for the same reason (see `_parse_inline`'s docstring): a lone
    # run that's a bare string (plain-text cell, no markup at all)
    # still gets `Text(...)`'s own `<p>` wrapping -- matching
    # `parse_markdown`'s pre-Stage-M9 raw-tree shape for this case
    # exactly, since nothing about that case was ever broken. A lone
    # run that's already an `ARKNode` (a cell that collapses to one
    # bare inline element, e.g. a `**bold**`-only cell) passes through
    # unchanged. Only the *multi*-run case -- a cell mixing plain text
    # with inline markup -- needs `_spanify`, for the identical
    # fragmentation reason a multi-run paragraph does.
    def cell_runs(cell: str) -> list:
        runs = _parse_inline(cell)
        if len(runs) == 1:
            return runs if isinstance(runs[0], ARKNode) else [Text(runs[0])]
        return _spanify(runs)

    header_row = TableRow(*[TableHeaderCell(*cell_runs(cell)) for cell in pad(header)])
    body_rows = [
        TableRow(*[TableCell(*cell_runs(cell)) for cell in pad(row)]) for row in data
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


# ---------------------------------------------------------------------------
# Style hooks (Stage M6) -- see the module docstring's "Style hooks" section
# for the full rationale and the disclaimer. Every class name below must stay
# in sync with `arklight.backend.css.markdown_defaults`, which is what
# actually styles them by default, and with that module's own
# `HOOK_CLASS_NAMES` export, which `arklight.api.RESERVED_UTILITY_CLASSES`
# reads to protect them the same way `.card`/`.nav`/etc. already are.
# ---------------------------------------------------------------------------

_HEADING_HOOK_CLASS = "ark-md-h{level}"
_PARAGRAPH_HOOK_CLASS = "ark-md-p"
_LIST_HOOK_CLASS = "ark-md-list"
_ORDERED_LIST_HOOK_CLASS = "ark-md-ordered-list"
_ITEM_HOOK_CLASS = "ark-md-item"
_PRE_HOOK_CLASS = "ark-md-pre"
_CODE_BLOCK_HOOK_CLASS = "ark-md-code-block"
_TABLE_HOOK_CLASS = "ark-md-table"
_THEAD_HOOK_CLASS = "ark-md-thead"
_TBODY_HOOK_CLASS = "ark-md-tbody"
_TR_HOOK_CLASS = "ark-md-tr"
_TH_HOOK_CLASS = "ark-md-th"
_TD_HOOK_CLASS = "ark-md-td"

# A whole paragraph can collapse to a single bare inline node
# (`_paragraph_node`, e.g. `parse_markdown("**bold**")` ->
# `[Strong("bold")]`) -- there is no wrapping paragraph element at all
# in that case, so this gets its own class per inline type rather than
# the generic `ark-md-p`, which would misname the actual `<strong>`/
# `<em>`/`<code>`/`<a>` tag that's really there.
_PARAGRAPH_COLLAPSE_HOOK_CLASSES = {
    "Strong": "ark-md-strong",
    "Em": "ark-md-em",
    "Code": "ark-md-code",
    "Link": "ark-md-link",
}

_SIMPLE_BLOCK_HOOK_CLASSES = {
    "HorizontalRule": "ark-md-hr",
    "Image": "ark-md-img",
    "Blockquote": "ark-md-blockquote",
}

_SLUG_RE = re.compile(r"[^a-z0-9]+")


def _slugify(text: str) -> str:
    """A heading's plain text -> a URL-fragment-safe `id`: lowercased,
    runs of anything that isn't `[a-z0-9]` collapsed to one `-`, with
    leading/trailing `-` stripped. Falls back to `"section"` for a
    heading with no usable text (`### ` alone, or a heading that was
    only punctuation) so `id` is never an empty string."""
    slug = _SLUG_RE.sub("-", text.strip().lower()).strip("-")
    return slug or "section"


def _apply_style_hooks(blocks: list[ARKNode]) -> None:
    """Stage M6 post-pass: attach `class_name` (and, on `Heading`,
    `id`) to every block `parse_markdown` just built, in place --
    `blocks` is freshly constructed by this call (never anything a
    caller already holds a reference to and still wants hook-free), the
    same assumption `_resolve_references` already makes. Only the
    block-level list and the small, fixed structural shapes this
    parser itself produces (table sections/rows/cells, list items, a
    fenced block's inner `Code`) are walked -- deliberately *not* a
    generic recursive walk into every inline run the way
    `_resolve_references` does, since an inline `Text`/`Strong`/`Em`/
    `Code`/`Link` run nested inside a multi-run paragraph's `Container`
    is not itself a paragraph and classing it `ark-md-p` would be
    wrong; default styling for those reaches them with ordinary
    descendant selectors off the paragraph/cell/blockquote class
    instead (see `markdown_defaults.MARKDOWN_CSS_BODY`).

    `setdefault` throughout: idempotent if ever called twice, and never
    clobbers a `class_name`/`id` this module itself may set some other
    way in the future."""
    seen_slugs: dict[str, int] = {}

    def unique_id(text: str) -> str:
        base = _slugify(text)
        count = seen_slugs.get(base, 0)
        seen_slugs[base] = count + 1
        return base if count == 0 else f"{base}-{count + 1}"

    def tag(target: ARKNode, class_name: str) -> None:
        target.props.setdefault("class_name", class_name)

    def tag_table(table: ARKNode) -> None:
        tag(table, _TABLE_HOOK_CLASS)
        for section in table.children:
            if not isinstance(section, ARKNode):
                continue
            if section.type == "TableHead":
                tag(section, _THEAD_HOOK_CLASS)
            elif section.type == "TableBody":
                tag(section, _TBODY_HOOK_CLASS)
            for row in section.children:
                if not isinstance(row, ARKNode) or row.type != "TableRow":
                    continue
                tag(row, _TR_HOOK_CLASS)
                for cell in row.children:
                    if not isinstance(cell, ARKNode):
                        continue
                    if cell.type == "TableHeaderCell":
                        tag(cell, _TH_HOOK_CLASS)
                    elif cell.type == "TableCell":
                        tag(cell, _TD_HOOK_CLASS)

    for block in blocks:
        if not isinstance(block, ARKNode):
            continue
        if block.type == "Heading":
            level = block.props.get("level", 1)
            tag(block, _HEADING_HOOK_CLASS.format(level=level))
            title = block.children[0] if block.children else ""
            block.props.setdefault(
                "id", unique_id(title if isinstance(title, str) else "")
            )
        elif block.type in ("Text", "Container"):
            tag(block, _PARAGRAPH_HOOK_CLASS)
        elif block.type == "List":
            tag(block, _LIST_HOOK_CLASS)
            for item in block.children:
                if isinstance(item, ARKNode) and item.type == "Item":
                    tag(item, _ITEM_HOOK_CLASS)
        elif block.type == "OrderedList":
            tag(block, _ORDERED_LIST_HOOK_CLASS)
            for item in block.children:
                if isinstance(item, ARKNode) and item.type == "Item":
                    tag(item, _ITEM_HOOK_CLASS)
        elif block.type == "Pre":
            tag(block, _PRE_HOOK_CLASS)
            for inner in block.children:
                if isinstance(inner, ARKNode) and inner.type == "Code":
                    tag(inner, _CODE_BLOCK_HOOK_CLASS)
        elif block.type == "Table":
            tag_table(block)
        elif block.type in _SIMPLE_BLOCK_HOOK_CLASSES:
            tag(block, _SIMPLE_BLOCK_HOOK_CLASSES[block.type])
        elif block.type in _PARAGRAPH_COLLAPSE_HOOK_CLASSES:
            tag(block, _PARAGRAPH_COLLAPSE_HOOK_CLASSES[block.type])


def parse_markdown(
    source: str,
    *,
    filename: str = "<content>",
    content_path: str | None = None,
    page_routes: Mapping[str, str] | None = None,
    style_hooks: bool = False,
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

    `style_hooks`, if `True` (Stage M6, see the module docstring's
    "Style hooks" section), attaches a stable `class_name` -- and, on
    every `Heading`, a slugged `id` -- to each block produced, under a
    fixed `ark-md-*` prefix that `Site.style(...)`/`Site.style_selector(...)`
    can target. Defaults to `False`, so a bare call (this is what every
    test in `tests/test_markdown.py` makes) gets the exact tree Stage
    M2-M4 always produced. `arklight.content.discovery.synthesize_page`,
    the only caller that assembles real site pages, always passes
    `True`.

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
    if style_hooks:
        _apply_style_hooks(blocks)
    return blocks
