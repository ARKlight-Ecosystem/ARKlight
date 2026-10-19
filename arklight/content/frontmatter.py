"""
Front matter parsing for Markdown content pages.

Stage M1 of the Markdown-as-first-class-content landing order (see
`docs/Foundational/DESIGN-NOTES.md`'s "Design record: Markdown as
first-class content"), settling that design record's **Q3**:
"YAML-ish" was a placeholder, not a
decision, and full YAML pulls in a parser this project has
deliberately avoided everywhere else -- `arklight/cli/mdrender.py`'s
own stated reason for never taking a Markdown dependency applies here
too (`pyproject.toml` has no `[project.dependencies]` at all). This
module is a restricted, standard-library-only `key: value` reader, not
a YAML subset parser: no nesting, no lists, no block scalars, four
known keys.

A content file optionally opens with a fenced block delimited by a
line that is exactly `---`, immediately followed by one more line that
is exactly `---`:

    ---
    title: Getting Started
    route: /guide
    draft: false
    ---

    # Getting Started
    ...

The closed key set for this stage, per the addendum: `title`,
`description`, `route` (all plain strings, optionally wrapped in
matching `'`/`"` quotes, stripped), and `draft` (`true`/`false`,
case-insensitive). A file with no opening `---` on its first line has
no front matter at all -- `FrontMatter()`'s all-default values, and the
source is returned unchanged as the body. Every other way the block
can go wrong -- a missing closing fence, a line that isn't
`key: value`, a key outside the closed set, a key repeated, a `draft`
value that isn't `true`/`false` -- is a diagnostic, not a silent
no-op or a guess: `FrontMatterError`, naming the file and, wherever a
single line is at fault, that line number too, the same "fails loudly
instead of resolving silently" posture `arklight/parser/preamble.py`
already takes for its own directive comments.

Later Markdown-as-content stages build on this: Stage M2's parser
calls `parse_front_matter` once per `.md` file before handing the rest
of the document to its Markdown-to-IR recognizer; Stage M3's route
synthesis reads `.route`/`.draft` off the result to decide a page's
path and whether it is built at all. Nothing in this module knows
about either -- it only reads the block and hands back a value.
"""

from __future__ import annotations

from dataclasses import dataclass

#: The fixed, closed key set for Stage M1. An unrecognized key is a
#: diagnostic (`FrontMatterError`), never a silently-ignored extra --
#: per the addendum, "an unrecognized key is a diagnostic, not a
#: silent no-op."
KNOWN_KEYS = frozenset({"title", "description", "route", "draft"})

_DELIMITER = "---"
_TRUE_VALUES = frozenset({"true"})
_FALSE_VALUES = frozenset({"false"})


class FrontMatterError(ValueError):
    """Raised for a malformed or invalid front matter block: an
    unterminated `---` fence, a line that isn't `key: value`, a key
    outside `KNOWN_KEYS`, a key repeated within one block, or a
    `draft` value that isn't `true`/`false`. The message always names
    the file (the `filename` a caller passed to `parse_front_matter`,
    or `"<content>"` if none was given) and, for anything that is
    about one specific line, that line's 1-indexed number in the
    source passed in -- counting the opening `---` as line 1, same as
    any other line-numbered diagnostic in this codebase."""


@dataclass(frozen=True)
class FrontMatter:
    """The result of parsing one content file's front matter block.

    Every field defaults to what an absent block means: no override
    for the filename-derived title/route, no description, not a
    draft. Stage M3's precedence order (explicit `site.py`
    configuration, then front matter, then the filename-derived
    default) reads `title`/`route` being `None` as "this file did not
    set one" -- that's why these default to `None` rather than `""`,
    an empty string being a value someone could have actually written.
    """

    title: str | None = None
    description: str | None = None
    route: str | None = None
    draft: bool = False


def parse_front_matter(
    source: str, *, filename: str = "<content>"
) -> tuple[FrontMatter, str]:
    """Parse a content file's optional leading front matter block.

    Returns `(front_matter, body)`: `front_matter` is a `FrontMatter`
    (all-default if `source` has no front matter block at all), and
    `body` is `source` with the block -- both `---` fence lines and
    everything between them -- removed. `source` is otherwise passed
    through unchanged: no stripping of leading/trailing blank lines in
    the body, no normalization of line endings, so a caller doing its
    own line-number accounting against the original file sees exactly
    the lines it expects.

    Raises `FrontMatterError` for a block that opens but never closes,
    a line inside the block that isn't `key: value`, a key outside
    `KNOWN_KEYS`, a key given twice, or an unparsable `draft` value.
    """
    lines = source.splitlines(keepends=True)

    if not lines or _strip_newline(lines[0]) != _DELIMITER:
        return FrontMatter(), source

    closing_index: int | None = None
    for index in range(1, len(lines)):
        if _strip_newline(lines[index]) == _DELIMITER:
            closing_index = index
            break

    if closing_index is None:
        raise FrontMatterError(
            f"{filename}: unterminated front matter block -- the opening "
            f"'---' on line 1 has no matching closing '---'"
        )

    values: dict[str, tuple[str, int]] = {}
    for offset, raw_line in enumerate(lines[1:closing_index], start=2):
        line = _strip_newline(raw_line)
        if not line.strip():
            continue

        key, separator, raw_value = line.partition(":")
        if not separator:
            raise FrontMatterError(
                f"{filename}:{offset}: malformed front matter line -- "
                f"expected 'key: value', got {line!r}"
            )

        key = key.strip()
        if key not in KNOWN_KEYS:
            known = ", ".join(sorted(KNOWN_KEYS))
            raise FrontMatterError(
                f"{filename}:{offset}: unrecognized front matter key "
                f"{key!r} (expected one of: {known})"
            )
        if key in values:
            raise FrontMatterError(
                f"{filename}:{offset}: front matter key {key!r} is set "
                f"more than once (first set on line {values[key][1]})"
            )

        values[key] = (_unquote(raw_value.strip()), offset)

    draft = False
    if "draft" in values:
        raw_draft, draft_lineno = values["draft"]
        lowered = raw_draft.lower()
        if lowered in _TRUE_VALUES:
            draft = True
        elif lowered in _FALSE_VALUES:
            draft = False
        else:
            raise FrontMatterError(
                f"{filename}:{draft_lineno}: front matter key 'draft' must "
                f"be 'true' or 'false', got {raw_draft!r}"
            )

    front_matter = FrontMatter(
        title=values["title"][0] if "title" in values else None,
        description=values["description"][0] if "description" in values else None,
        route=values["route"][0] if "route" in values else None,
        draft=draft,
    )
    body = "".join(lines[closing_index + 1 :])
    return front_matter, body


def _strip_newline(line: str) -> str:
    return line.rstrip("\r\n")


def _unquote(value: str) -> str:
    """Strip one layer of matching `'...'`/`"..."` quoting, if present.

    A convenience for values that happen to contain a `:` or leading/
    trailing whitespace an author wants preserved -- not a general
    escaping scheme; nothing inside the quotes is interpreted.
    """
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "'\"":
        return value[1:-1]
    return value
