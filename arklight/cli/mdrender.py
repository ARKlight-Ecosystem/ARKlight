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
blockquotes, bullet/numbered lists, horizontal rules, and links.
Anything it doesn't specially handle -- pipe tables included -- passes
through unchanged; a raw table still reads fine in a monospace
terminal, so there's nothing to gain by reimplementing table layout
here.

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
import sys
from typing import TextIO

_RESET = "\x1b[0m"
_BOLD = "\x1b[1m"
_DIM = "\x1b[2m"
_ITALIC = "\x1b[3m"
_UNDERLINE = "\x1b[4m"

# 256-color codes, chosen only for contrast against both light and
# dark terminal backgrounds -- there's no "ARKlight brand palette" to
# match here, this is a dev-time CLI convenience, not shipped output.
_HEADING_COLORS: dict[int, str] = {
    1: "\x1b[1;38;5;214m",  # bold orange -- the document title
    2: "\x1b[1;38;5;39m",  # bold blue -- a top-level section
    3: "\x1b[1;38;5;80m",  # bold teal -- a subsection
}
_HEADING_DEFAULT_COLOR = "\x1b[1;38;5;250m"  # bold grey -- level 4+
_CODE_COLOR = "\x1b[38;5;180m"
_QUOTE_COLOR = "\x1b[2;38;5;245m"
_RULE_COLOR = "\x1b[2m"
_LINK_URL_COLOR = "\x1b[2;4;38;5;110m"
_BULLET_COLOR = "\x1b[38;5;214m"

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


def render_markdown(text: str, *, color: bool = True) -> str:
    """Render `text` (Markdown) for terminal display, line by line.
    `color=False` returns `text` completely unchanged -- the safe
    default for any caller that hasn't itself checked whether its
    stream can take ANSI codes (see `supports_color`/`resolve_color`).

    Fenced code blocks (`` ``` `` / `~~~`) are tracked and never run
    through inline styling -- their content is dimmed as a block, not
    parsed as Markdown, so a literal `**` inside an example stays
    literal. Everything else ARKlight's own docs use gets its own
    treatment (headings, blockquotes, bullet/numbered lists,
    horizontal rules); any line matching none of those still gets
    inline styling (bold/italic/code/links) applied, and a line
    matching none of that either -- a table row, a plain paragraph --
    passes through completely unchanged.
    """
    if not color:
        return text

    out_lines: list[str] = []
    in_fence = False
    fence_marker = ""
    fence_indent = ""

    for line in text.split("\n"):
        fence_match = _FENCE.match(line)
        if fence_match:
            indent, marker = fence_match.groups()
            if not in_fence:
                in_fence, fence_marker, fence_indent = True, marker, indent
            elif marker == fence_marker and indent == fence_indent:
                in_fence = False
            out_lines.append(f"{_DIM}{line}{_RESET}")
            continue

        if in_fence:
            out_lines.append(f"{_CODE_COLOR}{line}{_RESET}")
            continue

        heading_match = _ATX_HEADING.match(line)
        if heading_match:
            level = len(heading_match.group(1))
            title = heading_match.group(2)
            color_code = _HEADING_COLORS.get(level, _HEADING_DEFAULT_COLOR)
            out_lines.append(f"{color_code}{'#' * level} {_style_inline(title)}{_RESET}")
            continue

        if _HRULE.match(line):
            out_lines.append(f"{_RULE_COLOR}{line}{_RESET}")
            continue

        quote_match = _BLOCKQUOTE.match(line)
        if quote_match:
            indent, body = quote_match.groups()
            out_lines.append(f"{indent}{_QUOTE_COLOR}\u2502 {_style_inline(body)}{_RESET}")
            continue

        bullet_match = _BULLET.match(line)
        if bullet_match:
            indent, _marker, gap, body = bullet_match.groups()
            out_lines.append(f"{indent}{_BULLET_COLOR}\u2022{_RESET}{gap}{_style_inline(body)}")
            continue

        numbered_match = _NUMBERED.match(line)
        if numbered_match:
            indent, marker, gap, body = numbered_match.groups()
            out_lines.append(f"{indent}{_BULLET_COLOR}{marker}{_RESET}{gap}{_style_inline(body)}")
            continue

        out_lines.append(_style_inline(line))

    return "\n".join(out_lines)
