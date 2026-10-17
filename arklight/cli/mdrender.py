"""
Vendored, dependency-free Markdown-to-ANSI terminal renderer.

ARKlight ships with zero runtime dependencies -- `pyproject.toml` has
no `[project.dependencies]` at all. The compiler itself, and every CLI
convenience built on it, is meant to run from nothing but a Python
stdlib install. `arklight search --retrieve-doc`
(`arklight/cli/doc_retrieval.py`) dumps real Markdown files straight
from `docs/`, byte for byte, on purpose -- and on an ANSI-capable
terminal that Markdown reads as a wall of literal `#`/`**`/`` ` ``
characters instead of the formatted page it would be on GitHub.

Pulling in an actual third-party terminal-Markdown package (`rich`,
`mistune`, ...) would be the first runtime dependency this project has
ever had, and would sit oddly with the same "no vendor SDK, no
generated glue" stance the compiler itself already takes elsewhere
(see `arklight/ir/platform_api.py`'s own docstring). So this is a
small renderer of ARKlight's own, written to the same zero-dependency
rule, covering exactly what the docs actually use: ATX headings
(`#` through `######`), bold/italic, inline code, fenced code blocks,
blockquotes, bullet/numbered lists, horizontal rules, links, and pipe
tables -- reflowed to the terminal's actual width rather than dumped
as a fixed-width wall of text or left as raw `|`-delimited source.

Rendering is inert (`render_markdown` returns `text` completely
unchanged) unless a caller explicitly asks for `color=True`, and
whether to ask is entirely the caller's decision (`supports_color`/
`resolve_color` below, or a caller's own check) -- never this module's.
That split is what keeps `doc_retrieval.run_retrieve_doc`'s own
Markdown-returning tests passing unmodified: only the CLI's actual
print site (`arklight/cli/main.py::_cmd_search`) ever asks for color.
"""

from __future__ import annotations

import os
import re
import shutil
import sys
import textwrap
from typing import TextIO

_RESET = "\x1b[0m"
_BOLD = "\x1b[1m"
_DIM = "\x1b[2m"
_ITALIC = "\x1b[3m"
_UNDERLINE = "\x1b[4m"

# 24-bit color, chosen as one warm clay/terracotta accent plus neutral
# greys -- a small, cohesive palette rather than a rainbow of
# unrelated per-level hues, and legible against both light and dark
# terminal backgrounds. There's no "ARKlight brand palette" this needs
# to match; this is a dev-time CLI convenience, not shipped output.
_HEADING_COLORS: dict[int, str] = {
    1: "\x1b[1;38;2;204;120;92m",  # bold clay -- the document title
    2: "\x1b[1;38;2;196;148;107m",  # bold warm tan -- a top-level section
    3: "\x1b[1;38;2;166;151;128m",  # bold muted taupe -- a subsection
}
_HEADING_DEFAULT_COLOR = "\x1b[1;38;2;140;140;140m"  # bold grey -- level 4+
_CODE_COLOR = "\x1b[38;2;214;163;115m"
_QUOTE_COLOR = "\x1b[2;38;2;153;145;133m"
_RULE_COLOR = "\x1b[2m"
_LINK_URL_COLOR = "\x1b[2;4;38;2;204;120;92m"
_BULLET_COLOR = "\x1b[38;2;204;120;92m"
_TABLE_BORDER_COLOR = "\x1b[2;38;2;130;130;130m"
_TABLE_HEADER_COLOR = "\x1b[1;38;2;204;120;92m"

_ATX_HEADING = re.compile(r"^(#{1,6})\s+(.*?)\s*#*\s*$")
_FENCE = re.compile(r"^(\s*)(```|~~~)")
_HRULE = re.compile(r"^\s*([-*_=])(?:\s*\1){2,}\s*$")
_BLOCKQUOTE = re.compile(r"^(\s*)>\s?(.*)$")
_BULLET = re.compile(r"^(\s*)([-*+])(\s+)(.*)$")
_NUMBERED = re.compile(r"^(\s*)(\d+[.)])(\s+)(.*)$")

_INLINE_CODE = re.compile(r"`([^`]+)`")
_LINK = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")
_BOLD_RE = re.compile(r"(\*\*|__)(?!\s)(.+?)(?<!\s)\1")
_ITALIC_RE = re.compile(r"(?<!\*)\*(?!\*)(?!\s)([^*]+?)(?<!\s)\*(?!\*)|(?<!_)_(?!_)(?!\s)([^_]+?)(?<!\s)_(?!_)")

_PLACEHOLDER = re.compile(r"\x00(\d+)\x00")

_TABLE_SEP_CELL = re.compile(r"^:?-{1,}:?$")

_DEFAULT_WIDTH = 80
_MIN_WIDTH = 20


def supports_color(stream: TextIO | None = None) -> bool:
    """True if `stream` (default `sys.stdout`) should get ANSI
    styling: `FORCE_COLOR` set wins outright; else `NO_COLOR`
    (https://no-color.org) being set (to anything, including empty)
    turns it off; else it comes down to whether `stream` is a real
    terminal. Matches the `NO_COLOR`/`FORCE_COLOR` precedence most
    other CLIs already use, so `arklight search --retrieve-doc | less
    -R` and friends behave the way people expect."""
    if os.environ.get("FORCE_COLOR"):
        return True
    if os.environ.get("NO_COLOR") is not None:
        return False
    stream = sys.stdout if stream is None else stream
    isatty = getattr(stream, "isatty", None)
    return bool(isatty and isatty())


def resolve_color(choice: str, *, stream: TextIO | None = None) -> bool:
    """Turn a `--color {auto,always,never}` CLI choice into the actual
    `color=` bool `render_markdown` wants. `"auto"` defers to
    `supports_color`; `"always"`/`"never"` are unconditional
    overrides, the same three-state shape `git --color` and `ripgrep`
    both already use."""
    if choice == "always":
        return True
    if choice == "never":
        return False
    return supports_color(stream)


def terminal_width(stream: TextIO | None = None) -> int:
    """The column count to wrap rendered Markdown to: whatever
    `shutil.get_terminal_size` reports for `stream` (itself `COLUMNS`-
    env-var aware, then an actual terminal-size ioctl, in that order),
    floored at `_MIN_WIDTH` so a tiny or misreported terminal doesn't
    collapse wrapping into nonsense, and falling back to
    `_DEFAULT_WIDTH` when nothing better is available (piped output,
    a non-terminal stream) -- the same default `shutil` itself uses.
    `stream` is accepted for symmetry with `supports_color` /
    `resolve_color` but isn't consulted directly: `shutil` only knows
    how to size the process's actual stdout, not an arbitrary stream.
    """
    del stream  # see docstring -- kept only for call-site symmetry
    columns = shutil.get_terminal_size(fallback=(_DEFAULT_WIDTH, 24)).columns
    return max(columns, _MIN_WIDTH)


def _wrap_text(text: str, width: int) -> list[str]:
    """Word-wrap one logical line of Markdown prose to `width`
    columns, raw (pre-styling) text in, raw text out. Long words are
    never force-broken: a URL or an unbroken identifier wider than
    `width` is left on its own overflowing line rather than split
    mid-word, since this is plain prose wrapping, not table-cell
    packing (`_wrap_cell` below does the opposite trade-off, on
    purpose). An empty/whitespace-only input always yields one empty
    line rather than zero lines, so callers never have to special-case
    "this block of content had nothing in it"."""
    width = max(width, 1)
    wrapped = textwrap.wrap(
        text,
        width=width,
        break_long_words=False,
        break_on_hyphens=False,
        drop_whitespace=True,
    )
    return wrapped if wrapped else [""]


def _style_inline(text: str) -> str:
    """Apply inline styling (bold, italic, code spans, links) to one
    already-extracted line of Markdown prose. Code spans are pulled
    out and replaced with a placeholder first, so `**`/`_` characters
    *inside* a backticked span (e.g. `` `**not bold**` ``) are never
    mistaken for emphasis markers -- the placeholder is restored, already
    styled, as the very last step."""
    placeholders: list[str] = []

    def _stash_code(match: re.Match[str]) -> str:
        placeholders.append(f"{_CODE_COLOR}{match.group(1)}{_RESET}")
        return f"\x00{len(placeholders) - 1}\x00"

    text = _INLINE_CODE.sub(_stash_code, text)
    text = _LINK.sub(
        lambda m: f"{_UNDERLINE}{m.group(1)}{_RESET} {_LINK_URL_COLOR}({m.group(2)}){_RESET}",
        text,
    )
    text = _BOLD_RE.sub(lambda m: f"{_BOLD}{m.group(2)}{_RESET}", text)
    text = _ITALIC_RE.sub(lambda m: f"{_ITALIC}{m.group(1) or m.group(2)}{_RESET}", text)

    return _PLACEHOLDER.sub(lambda m: placeholders[int(m.group(1))], text)


# ---------------------------------------------------------------------------
# Pipe tables
# ---------------------------------------------------------------------------


def _split_table_row(line: str) -> list[str]:
    """Split one `| a | b |`-style source line into its raw cell
    strings, stripped of surrounding whitespace, with a leading/
    trailing bare pipe dropped and `\\|` un-escaped back to a literal
    `|` inside a cell. Returns `[]` for a line with nothing between
    pipes at all (e.g. an empty string), which callers treat as "not
    a table row"."""
    stripped = line.strip()
    if stripped.startswith("|"):
        stripped = stripped[1:]
    if stripped.endswith("|") and not stripped.endswith("\\|"):
        stripped = stripped[:-1]
    if not stripped:
        return []
    return [cell.strip().replace("\\|", "|") for cell in re.split(r"(?<!\\)\|", stripped)]


def _is_table_separator(line: str) -> bool:
    """True for a GFM table's delimiter row (`|---|:---:|---:|`,
    with or without the outer pipes, any run length of `-`): every
    cell must be dashes with optional leading/trailing `:` for
    alignment, and there must be at least one cell."""
    cells = _split_table_row(line)
    return bool(cells) and all(_TABLE_SEP_CELL.match(cell) for cell in cells)


def _column_alignment(sep_cell: str) -> str:
    left, right = sep_cell.startswith(":"), sep_cell.endswith(":")
    if left and right:
        return "center"
    if right:
        return "right"
    return "left"


def _wrap_cell(text: str, width: int) -> list[str]:
    """Word-wrap one table cell's raw text to `width` columns. Unlike
    `_wrap_text`, long words *are* force-broken (`textwrap`'s default):
    a table cell has a hard column budget it must not blow past, so a
    single unbroken token wider than the column -- a long identifier,
    a URL -- gets split rather than left to overflow the box."""
    width = max(width, 1)
    wrapped = textwrap.wrap(text, width=width, drop_whitespace=True)
    return wrapped if wrapped else [""]


def _pad_cell(text: str, width: int, align: str) -> str:
    pad = max(width - len(text), 0)
    if align == "right":
        return " " * pad + text
    if align == "center":
        left = pad // 2
        return " " * left + text + " " * (pad - left)
    return text + " " * pad


def _table_column_widths(rows: list[list[str]], n_cols: int, width: int) -> list[int]:
    """Pick a width per column: each column's natural width (its
    longest cell, floored at 3) when the whole table already fits in
    `width`; otherwise every column is scaled down proportionally
    (wider columns give up more), each floored at 3, with any
    leftover-from-rounding column-width added to or trimmed from the
    single widest column so the columns' widths always sum to exactly
    the space available. Cell wrapping (`_wrap_cell`) is what actually
    makes the shrunk columns' content still fit."""
    natural = [max((len(row[c]) for row in rows), default=0) for c in range(n_cols)]
    natural = [max(w, 3) for w in natural]

    overhead = 3 * n_cols + 1  # one "| " + " |" pair of margins per column, plus one more bar
    available = max(width - overhead, n_cols * 3)

    total = sum(natural)
    if total <= available:
        return natural

    scale = available / total
    scaled = [max(3, int(w * scale)) for w in natural]
    diff = available - sum(scaled)
    while diff != 0:
        idx = scaled.index(max(scaled))
        if diff > 0:
            scaled[idx] += diff
            diff = 0
        elif scaled[idx] > 3:
            scaled[idx] -= 1
            diff += 1
        else:
            break  # every column is already at the floor; let it overflow slightly
    return scaled


def _table_hline(col_widths: list[int], left: str, mid: str, right: str) -> str:
    segments = ["─" * (w + 2) for w in col_widths]
    return f"{_TABLE_BORDER_COLOR}{left}{mid.join(segments)}{right}{_RESET}"


def _table_row_lines(
    cells: list[str], col_widths: list[int], aligns: list[str], *, is_header: bool
) -> list[str]:
    wrapped_cols = [_wrap_cell(cell, w) for cell, w in zip(cells, col_widths)]
    height = max(len(wc) for wc in wrapped_cols)

    bar = f"{_TABLE_BORDER_COLOR}│{_RESET}"
    out = []
    for row_idx in range(height):
        rendered_cells = []
        for col_idx, wrapped in enumerate(wrapped_cols):
            raw = wrapped[row_idx] if row_idx < len(wrapped) else ""
            padded = _pad_cell(raw, col_widths[col_idx], aligns[col_idx])
            styled = _style_inline(padded)
            if is_header:
                styled = f"{_TABLE_HEADER_COLOR}{styled}{_RESET}"
            rendered_cells.append(styled)
        out.append(f"{bar} " + f" {bar} ".join(rendered_cells) + f" {bar}")
    return out


def _render_table(table_lines: list[str], width: int) -> list[str]:
    """Render a full pipe-table block (header row, delimiter row, then
    zero or more data rows -- exactly what the caller already detected
    with `_is_table_separator`) as a bordered, column-aligned box that
    fits `width`, wrapping cell content onto extra lines rather than
    overflowing when the table is wider than the terminal."""
    header = _split_table_row(table_lines[0])
    sep = _split_table_row(table_lines[1])
    data = [_split_table_row(line) for line in table_lines[2:]]

    n_cols = max([len(header), len(sep)] + [len(row) for row in data])

    def pad_row(row: list[str]) -> list[str]:
        return row + [""] * (n_cols - len(row))

    header = pad_row(header)
    data = [pad_row(row) for row in data]
    aligns = [_column_alignment(sep[c]) if c < len(sep) else "left" for c in range(n_cols)]

    col_widths = _table_column_widths([header, *data], n_cols, width)

    out = [_table_hline(col_widths, "┌", "┬", "┐")]
    out.extend(_table_row_lines(header, col_widths, aligns, is_header=True))
    out.append(_table_hline(col_widths, "├", "┼", "┤"))
    for row in data:
        out.extend(_table_row_lines(row, col_widths, aligns, is_header=False))
    out.append(_table_hline(col_widths, "└", "┴", "┘"))
    return out


def render_markdown(text: str, *, color: bool = True, width: int | None = None) -> str:
    """Render `text` (Markdown) for terminal display, line by line.
    `color=False` returns `text` completely unchanged -- the safe
    default for any caller that hasn't itself checked whether its
    stream can take ANSI codes (see `supports_color`/`resolve_color`).

    `width` is the column budget prose, headings, list items,
    blockquotes, and tables are reflowed to; `None` (the default)
    resolves it from the real terminal via `terminal_width()` at call
    time, so a caller doesn't need to know or guess its own width.

    Fenced code blocks (`` ``` `` / `~~~`) are tracked and never run
    through inline styling or wrapping -- their content is dimmed as a
    block, not parsed as Markdown or reflowed, so a literal `**`
    inside an example stays literal and code indentation survives
    exactly. Everything else ARKlight's own docs use gets its own
    treatment (headings, blockquotes, bullet/numbered lists,
    horizontal rules, pipe tables); any line matching none of those
    still gets inline styling (bold/italic/code/links) and word
    wrapping applied.
    """
    if not color:
        return text

    if width is None:
        width = terminal_width()
    width = max(width, _MIN_WIDTH)

    lines = text.split("\n")
    n = len(lines)
    out_lines: list[str] = []
    in_fence = False
    fence_marker = ""
    fence_indent = ""

    i = 0
    while i < n:
        line = lines[i]

        fence_match = _FENCE.match(line)
        if fence_match:
            indent, marker = fence_match.groups()
            if not in_fence:
                in_fence, fence_marker, fence_indent = True, marker, indent
            elif marker == fence_marker and indent == fence_indent:
                in_fence = False
            out_lines.append(f"{_DIM}{line}{_RESET}")
            i += 1
            continue

        if in_fence:
            out_lines.append(f"{_CODE_COLOR}{line}{_RESET}")
            i += 1
            continue

        if not line.strip():
            out_lines.append(line)
            i += 1
            continue

        if "|" in line and i + 1 < n and _is_table_separator(lines[i + 1]):
            table_lines = [line, lines[i + 1]]
            j = i + 2
            while j < n and lines[j].strip() and "|" in lines[j]:
                table_lines.append(lines[j])
                j += 1
            out_lines.extend(_render_table(table_lines, width))
            i = j
            continue

        heading_match = _ATX_HEADING.match(line)
        if heading_match:
            level = len(heading_match.group(1))
            title = heading_match.group(2)
            color_code = _HEADING_COLORS.get(level, _HEADING_DEFAULT_COLOR)
            prefix = f"{'#' * level} "
            wrapped_title = _wrap_text(title, max(width - len(prefix), 10)) if title else [""]
            out_lines.append(f"{color_code}{prefix}{_style_inline(wrapped_title[0])}{_RESET}")
            indent = " " * len(prefix)
            for cont in wrapped_title[1:]:
                out_lines.append(f"{color_code}{indent}{_style_inline(cont)}{_RESET}")
            i += 1
            continue

        if _HRULE.match(line):
            out_lines.append(f"{_RULE_COLOR}{line}{_RESET}")
            i += 1
            continue

        quote_match = _BLOCKQUOTE.match(line)
        if quote_match:
            indent, body = quote_match.groups()
            bar_prefix = f"{indent}{_QUOTE_COLOR}│ "
            wrapped_body = _wrap_text(body, max(width - len(indent) - 2, 10)) if body else [""]
            out_lines.append(f"{bar_prefix}{_style_inline(wrapped_body[0])}{_RESET}")
            for cont in wrapped_body[1:]:
                out_lines.append(f"{bar_prefix}{_style_inline(cont)}{_RESET}")
            i += 1
            continue

        bullet_match = _BULLET.match(line)
        if bullet_match:
            indent, _marker, gap, body = bullet_match.groups()
            prefix_width = len(indent) + 1 + len(gap)
            wrapped_body = _wrap_text(body, max(width - prefix_width, 10)) if body else [""]
            out_lines.append(
                f"{indent}{_BULLET_COLOR}•{_RESET}{gap}{_style_inline(wrapped_body[0])}"
            )
            cont_indent = " " * prefix_width
            for cont in wrapped_body[1:]:
                out_lines.append(f"{cont_indent}{_style_inline(cont)}")
            i += 1
            continue

        numbered_match = _NUMBERED.match(line)
        if numbered_match:
            indent, marker, gap, body = numbered_match.groups()
            prefix_width = len(indent) + len(marker) + len(gap)
            wrapped_body = _wrap_text(body, max(width - prefix_width, 10)) if body else [""]
            out_lines.append(
                f"{indent}{_BULLET_COLOR}{marker}{_RESET}{gap}{_style_inline(wrapped_body[0])}"
            )
            cont_indent = " " * prefix_width
            for cont in wrapped_body[1:]:
                out_lines.append(f"{cont_indent}{_style_inline(cont)}")
            i += 1
            continue

        for wrapped in _wrap_text(line, width):
            out_lines.append(_style_inline(wrapped))
        i += 1

    return "\n".join(out_lines)
