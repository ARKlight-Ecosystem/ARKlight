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
`]`, `}`, or a run of those, optionally with a trailing comma) must be
flush with the indentation of the line that opened it -- that's the
one indentation a closing-only line is allowed to have:

    Page(
        Button("ok"),
        Text("hi"),
    )

Part 3 adds two more diagnostics, in the same spirit, both aimed at
the same failure mode: a component tree that has drifted into
something no longer readable at a glance.

First, a closing-only line is no longer exempt from indentation
entirely -- it must line up with the opener it closes. This is a
mistake part 2 let through silently:

    page(
           container(
                 ...
          )

          container(
                 ...
         )
    )

Neither `)` above sits flush with the `container(` it closes (7 vs. 6
and 7 vs. 5), and part 2's "any closing-only line is exempt" rule
never caught that. It does now.

Second, a component tree that nests brackets more than
`DEFAULT_MAX_NESTING_DEPTH` deep raises `TreeNestingTooDeepError`
rather than compiling: correctly-indented-but-endlessly-nested trees
are just as unreadable as flat ones, and indentation alone can't fix
that -- the author needs to pull a branch out into its own function.
This has nothing to do with a missing comma; a missing comma is a
plain `SyntaxError` from `ast.parse` and this module never touches
it.

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

#: How many `(`/`[`/`{` levels a component tree may nest before it stops
#: being readable at a glance and `TreeNestingTooDeepError` is raised
#: instead of compiling. Chosen to comfortably fit ARKlight's own
#: multi-level layouts (page -> section -> card -> row -> ...) while
#: still catching a tree that's clearly grown past a single function's
#: worth of content. A caller can pass a different `max_depth` to
#: `check_bracket_nesting` for a file with unusual, deliberate needs.
DEFAULT_MAX_NESTING_DEPTH = 8

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
    indented further than the line that opened it, or when a
    closing-only line isn't flush with the line that opened the
    bracket it closes.

    A plain `SyntaxError` subclass. This module has no dependency on
    `arklight.parser.preamble`'s `PreambleError` on purpose --
    callers that want it handled alongside a bad preamble directive
    (`arklight.parser.loader`, `arklight.config`) catch both
    explicitly rather than this module reaching up to borrow their
    base class.
    """


class TreeNestingTooDeepError(BracketIndentationError):
    """Raised when `(`/`[`/`{` nesting goes past `max_depth` levels.

    A subclass of `BracketIndentationError` -- not a separate
    diagnostic category -- so every existing `except
    BracketIndentationError` (`arklight.parser.loader`,
    `arklight.config`) already handles this too, with no call site
    changes needed. Distinct from it in name only so a caller that
    wants to tell "misaligned" from "too deep" apart still can.

    Unrelated to a missing comma between siblings: that's a
    grammatical error `ast.parse` reports on its own, not something
    this module checks or raises for.
    """


@dataclass(frozen=True)
class _OpenBracket:
    char: str
    open_lineno: int
    open_indent: int


def _line_indent(line: str) -> int:
    return len(line) - len(line.lstrip(" \t"))


def check_bracket_nesting(
    source: str,
    *,
    filename: str = "<site>",
    max_depth: int = DEFAULT_MAX_NESTING_DEPTH,
) -> None:
    """Raise `BracketIndentationError` on the first continuation line
    -- inside an open `(`, `[`, or `{` -- whose indentation does not
    exceed the indentation of the line that opened the bracket, or on
    the first closing-only line that isn't flush with the line that
    opened the bracket it closes.

    Raise `TreeNestingTooDeepError` (a `BracketIndentationError`) the
    moment `(`/`[`/`{` nesting exceeds `max_depth` levels -- a tree
    that deep is unreadable no matter how carefully every one of its
    lines is indented, and indentation checking alone can't fix that;
    the author needs to factor a branch out into its own function.

    A missing comma between siblings is a separate, ordinary
    `SyntaxError` that `ast.parse` reports on its own; this function
    never checks for it and never raises for it.

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

    def check_closing_row(row: int) -> None:
        # The line that closes a bracket -- and only such a line, see
        # the OP/_CLOSERS branch below -- must be flush with the line
        # that opened it. Any other indentation (more, less, or just
        # inconsistent from one sibling to the next) is exactly the
        # drifted, hard-to-follow layout this module exists to catch.
        opener = stack[-1]
        row_line = lines[row - 1] if 0 < row <= len(lines) else ""
        row_indent = _line_indent(row_line)
        if row_indent != opener.open_indent:
            raise BracketIndentationError(
                f"{filename}:{row}: line closing `{opener.char}` opened on "
                f"line {opener.open_lineno} must be flush with that line "
                f"(opening indent {opener.open_indent}, got {row_indent})."
            )

    for tok_type, tok_string, start, end, _line in tokens:
        row, _col = start

        if tok_type == tokenize.OP and tok_string in _OPENERS:
            open_line = lines[row - 1] if 0 < row <= len(lines) else ""
            stack.append(_OpenBracket(tok_string, row, _line_indent(open_line)))
            checked_rows.add(row)
            if len(stack) > max_depth:
                raise TreeNestingTooDeepError(
                    f"{filename}:{row}: `{tok_string}` nests {len(stack)} "
                    f"levels of `(`/`[`/`{{` deep, past the readability "
                    f"limit of {max_depth}. Pull part of this tree out "
                    f"into its own function and call that instead."
                )
            continue

        if tok_type == tokenize.OP and tok_string in _CLOSERS:
            # A line whose *first* token is a closer never reaches the
            # generic branch below, so it's only ever checked here --
            # against the opener it closes, and only once per row (the
            # first closer on a row of several, e.g. "))", is the one
            # whose column the row's indentation actually represents).
            if stack:
                if row not in checked_rows:
                    check_closing_row(row)
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
