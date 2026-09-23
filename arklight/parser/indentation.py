"""
Bracket-nesting indentation diagnostic.

Python's own grammar doesn't care how a continuation line inside an
open `(`, `[`, or `{` is indented -- the tokenizer treats everything
between an opening bracket and its match as one logical line, so *any*
indentation compiles, including none at all:

    Page(
    Button("ok"),
    Text("hi"),
    )

That freedom is exactly what lets bracketed ARKlight component trees
drift into flat, unreadable columns: nothing before this module ever
told the author the content of a `(...)` had stopped looking nested.

ARKlight's compiler is stricter here than Python: a line that
continues an open `(`, `[`, or `{` must be indented *further* than the
line that opened it. A line that only closes the bracket (a lone `)`,
`]`, `}`, or a run of those, optionally with a trailing comma) is
exempt -- closing flush with the opener's own indentation is the
idiomatic style and is always allowed:

    Page(
        Button("ok"),
        Text("hi"),
    )

This mirrors `arklight.parser.preamble`'s own stance: something Python
silently allows but that quietly erodes a file's readability becomes a
loud, named compiler diagnostic instead.
"""

from __future__ import annotations

import io
import tokenize
from dataclasses import dataclass

_OPENERS = {"(": ")", "[": "]", "{": "}"}
_CLOSERS = {")": "(", "]": "[", "}": "{"}

_IGNORED_TOKEN_TYPES = {
    tokenize.NL,
    tokenize.NEWLINE,
    tokenize.COMMENT,
    tokenize.INDENT,
    tokenize.DEDENT,
    tokenize.ENCODING,
    tokenize.ENDMARKER,
}


class BracketIndentationError(SyntaxError):
    """Raised when a line continuing an open `(`, `[`, or `{` is not
    indented further than the line that opened it.

    A plain `SyntaxError` subclass. This module has no dependency on
    `arklight.parser.preamble`'s `PreambleError` on purpose --
    callers that want it handled alongside a bad preamble directive
    (`arklight.parser.loader`, `arklight.config`) catch both
    explicitly rather than this module reaching up to borrow their
    base class.
    """


@dataclass(frozen=True)
class _OpenBracket:
    char: str
    open_lineno: int
    open_indent: int


def _line_indent(line: str) -> int:
    return len(line) - len(line.lstrip(" \t"))


def check_bracket_nesting(source: str, *, filename: str = "<site>") -> None:
    """Raise `BracketIndentationError` on the first continuation line
    -- inside an open `(`, `[`, or `{` -- whose indentation does not
    exceed the indentation of the line that opened the bracket. A line
    that only closes bracket(s) is exempt.

    Source that fails to tokenize raises nothing here; the loader's
    own `ast.parse` step reports that failure with its usual message,
    and this check has nothing useful to add to it.
    """
    try:
        tokens = list(tokenize.generate_tokens(io.StringIO(source).readline))
    except (tokenize.TokenError, IndentationError, SyntaxError):
        return

    lines = source.splitlines()
    stack: list[_OpenBracket] = []
    checked_rows: set[int] = set()

    def check_row(row: int) -> None:
        opener = stack[-1]
        row_line = lines[row - 1] if 0 < row <= len(lines) else ""
        row_indent = _line_indent(row_line)
        if row_indent <= opener.open_indent:
            raise BracketIndentationError(
                f"{filename}:{row}: line inside `{opener.char}` opened on "
                f"line {opener.open_lineno} must be indented further than "
                f"that line (opening indent {opener.open_indent}, got "
                f"{row_indent})."
            )

    for tok_type, tok_string, start, end, _line in tokens:
        row, _col = start

        if tok_type == tokenize.OP and tok_string in _OPENERS:
            open_line = lines[row - 1] if 0 < row <= len(lines) else ""
            stack.append(_OpenBracket(tok_string, row, _line_indent(open_line)))
            checked_rows.add(row)
            continue

        if tok_type == tokenize.OP and tok_string in _CLOSERS:
            # A line whose *first* token is a closer is exempt: it
            # never reaches the generic branch below, so no check
            # ever runs against it.
            if stack:
                stack.pop()
            checked_rows.add(row)
            continue

        if tok_type in _IGNORED_TOKEN_TYPES:
            continue

        if tok_type == tokenize.STRING and end[0] != row:
            # A multi-line string literal. Only its own opening row is
            # source layout the author chose; every row inside the
            # literal is string content, not code, and must not be
            # judged as a continuation line.
            if stack and row not in checked_rows:
                check_row(row)
            checked_rows.update(range(row, end[0] + 1))
            continue

        if not stack or row in checked_rows:
            checked_rows.add(row)
            continue

        checked_rows.add(row)
        check_row(row)
