"""
Preamble directives -- ARKlight's own, compiler-owned answer to the
"last import wins" problem with `from arklight import *` (and the same
star-import pattern against any other vocabulary source, ACC included),
plus the one directive that is not about vocabulary at all: `# define`.

A site file's `from X import *` line is *Python's* import statement:
Python resolves it and Python binds every name into the module
namespace, and if two of those statements bind the same name, Python's
own rule applies -- the second one silently wins. No diagnostic, no
attribution of which source lost, no way for ARKlight to even notice.
That is exactly the "silently resolved by picking a winner" antipattern
`arklight/capabilities.py` already refuses for duplicate ACC capability
identities (`CapabilityError`, not a coin toss) and
`arklight/ir/components.py` already refuses for `@component`
registration (`DuplicateComponentError`) -- but neither of those
guards touch the *first* step, getting names into the namespace to
begin with. That step still runs on raw Python import semantics,
with zero ARKlight involvement, which is exactly the gap this module closes.

Preamble directives move "get names into this module" itself onto
compiler-owned ground. Written as reserved-shape comments before the
first executable statement in a file:

    # include <stdlib.ARKlight>
    # include <acc.some_collection>

`# include <...>` tells ARKlight's own loader -- not Python's import
machinery -- which vocabulary source to bind, and the loader resolves
and binds every name itself, remembering which include supplied each
one. If a second include would rebind a name an earlier include
already bound to a *different* object, that is a collision:
`PreambleCollisionError`, naming every source involved, raised at load
time -- fails loudly, per `V1-DEFINITION.md`'s reliability doctrine,
instead of silently overwriting.

`# define`, the exception
-------------------------
    # define ROWS -> 3
    # define Btn -> Button

`# define <name> -> <text>` is lifted straight from C's `#define`: at
compile time the left-hand name is replaced by the right-hand text.
Both sides are strings -- the right one is *whatever the rest of the
line says*, so it can be a number, a string literal, another name, any
text that is valid Python where it lands. That makes it different in
kind from `# include` (and from the not-yet-accepted `# use`, see
`docs/Proposals/USE-PREAMBLE-PROPOSAL.md`): an include *binds
vocabulary*, a define *rewrites the file's own source*. It binds
nothing, resolves nothing, and needs no include to exist.

The rules, all of them small on purpose:

* The left side is a single Python identifier (not a keyword). It is
  matched as a whole *token* of the file's code, so `Btn` never
  touches `Btn2` or `xBtn`, and nothing inside a string literal (an
  f-string included, on every supported Python) or a comment is ever
  replaced. Exactly C's rule for identifiers.
* The right side is taken verbatim, from after `->` to the end of the
  line, trimmed. It must not be empty.
* One pass, no rescanning: replaced text is not scanned again. C
  rescans; here a define whose text mentions another define's name is
  refused instead (`validate_preamble`), so the missing rescan can
  never turn into a silent surprise.
* Per file. A define never leaks into another module, like a C
  translation unit.
* A define may not use the name of something an include already
  provides. Replacing `Button` everywhere would silently override the
  vocabulary -- the "no silent winner" rule again.
* Two defines for one name must agree; a repeat of the same one is
  harmless.
* The file must still parse once the defines are applied; if it
  doesn't, the error names the defines in effect instead of pointing
  at a line of rewritten code the author never wrote.

Substitution keeps every line where it was (the text is one line), so
line numbers in tracebacks and diagnostics still match the source.

Which files
-----------
Every Python file ARKlight takes in: the site file, each project
module it imports (`pages/`, `components/`, ...), and
`arklight.config.py`. See `arklight.parser.loader` for how -- an
import hook scoped to the project directory, so third-party packages
(ACC ones installed with pip included) stay ordinary Python.

Adding a directive later
------------------------
The door is deliberately open. A directive is one recogniser
(`_DIRECTIVE_PARSERS`) plus one normalization handler
(`_HANDLERS`), and, only if it has a rule that spans the whole
preamble, one check in `validate_preamble`. Nothing else in the module
knows how many kinds there are. `# use` is already reserved (see
`_RESERVED_DIRECTIVES`) so nobody can build on its shape before it is
designed.

What counts as the preamble
---------------------------
Only recognised directive comments *above the file's contents*: the
scan ends at the first token belonging to an actual statement
(`_leading_comment_lines`). A comment that merely looks like a
directive but sits after code has started -- in between statements, or
at the end of the file -- is an ordinary comment to ARKlight and is
never acted on.

Three phases, mirroring the compiler's own Normalization/Validation
split (`arklight/ir/normalize.py`, `arklight/ir/validate.py`)
-------------------------------------------------------------------
`parse_preamble` reads the directives, `normalize_preamble` *handles*
them, and `validate_preamble` is the only place anything *raises*.
Normalization fills the binding table from includes and collects the
define table; it never raises -- anything wrong (an unresolvable
include, a malformed or conflicting define, a reserved directive) is
recorded on the `NormalizedPreamble` instead. Validation then inspects
the result: first recorded problem, then any name still bound to two
different objects (`PreambleCollisionError`), then the cross-checks a
define needs the whole table for. `prepare_source` finally applies the
defines to the source text -- the one step that needs a validated
table -- and is what loaders call.

One check has to run *after* the file executes, because it is
about what the file itself did: `check_namespace_shadowing`. Python
lets a file's own `def Button(...)`, `Button = ...`, `from x import
Button`, or a leftover `from x import *` rebind a name the preamble
just bound, silently, and nothing before `exec` can see that. It
compares the finished namespace against what the preamble bound and
raises `PreambleCollisionError` for any name that changed -- the same
"no silent winner" rule, applied to names the file defines itself.

`from arklight import *` is retired in favor of `# include
<stdlib.ARKlight>`. It still works, but `find_retired_star_imports`/
`retired_star_import_notice` let the loader tell the author, through
the same channel the compiler's other notices use, to migrate.
"""

from __future__ import annotations

import ast
import importlib
import io
import keyword
import re
import tokenize
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Callable, Iterator, Mapping

from arklight.ir.components import ALLOW_REDEFINE_MARKER

_INCLUDE_RE = re.compile(r"^#\s*include\s*<\s*([^<>\s]+)\s*>\s*$")

# `# define <name> -> <text>`. The name is captured loosely (any run of
# non-space) and judged afterwards, so `# define a-b -> 3` gets a
# diagnostic about `a-b` instead of being silently mistaken for an
# ordinary comment. The text is the rest of the line, trimmed, and may
# be empty here -- normalization is what refuses that, so it is
# reported rather than ignored.
_DEFINE_RE = re.compile(r"^#\s*define\s+(\S+?)\s*->\s*(.*?)\s*$")

# Directive words that are claimed but not built. Each maps to the
# proposal that owns the design. A recognised shape (`# use <...>`)
# for one of these is refused, not skipped: silently ignoring it would
# let someone write it believing it does something.
_RESERVED_DIRECTIVES: dict[str, str] = {
    "use": "docs/Proposals/USE-PREAMBLE-PROPOSAL.md",
}
_RESERVED_RE = re.compile(
    r"^#\s*(" + "|".join(re.escape(word) for word in _RESERVED_DIRECTIVES) + r")\s*<"
)

# The one `# include <...>` label that always resolves, with no import
# needed: ARKlight's own public vocabulary, i.e. exactly what
# `from arklight import *` already gives a site file today.
_STDLIB_LABEL = "stdlib.ARKlight"

# Any other label must start with this prefix, naming a real,
# importable Python module ARKlight will introspect for its own
# `__all__` -- the same "no implicit trust beyond one documented
# contract" stance `arklight/capabilities.py` takes for ACC capability
# registration.
_ACC_PREFIX = "acc."

# Python 3.12 tokenizes an f-string into FSTRING_START ... FSTRING_END
# with real NAME tokens inside its `{}`; earlier versions hand back one
# STRING token. A define must behave the same on both, so names inside
# any f-string are skipped either way.
_FSTRING_START = getattr(tokenize, "FSTRING_START", None)
_FSTRING_END = getattr(tokenize, "FSTRING_END", None)


class PreambleError(SyntaxError):
    """Raised for a malformed, unresolved, or ambiguous preamble
    directive (`# include <...>` / `# define ... -> ...`)."""


class PreambleCollisionError(PreambleError):
    """Raised when two `# include` directives bind the same name to
    two different objects, or two `# define`s give one name two
    different texts.

    This is the specific failure the preamble exists to make loud: the
    equivalent situation with two raw `from X import *` statements is
    silently resolved by Python itself, in the second import's favor,
    with no error and no trace of what was lost.
    """


@dataclass(frozen=True)
class _Binding:
    value: Any
    source: str  # the include label it came from


@dataclass(frozen=True)
class _Define:
    text: str
    lineno: int


def _leading_comment_lines(source: str) -> list[tuple[int, str]]:
    """Return `(lineno, text)` for every comment token that appears in
    a source file's *preamble* -- the tokenizer sense of "before the
    first non-comment, non-blank logical line". Blank lines and
    comments may interleave freely; the first token belonging to an
    actual statement (an import, an assignment, anything) ends the
    preamble, exactly like a C preprocessor's leading directives don't
    require every comment in the file to sit at the very top, only the
    ones a caller wants recognized as directives to appear before code
    starts.
    """
    lines: list[tuple[int, str]] = []
    tokens = tokenize.generate_tokens(io.StringIO(source).readline)
    for tok_type, tok_string, start, _end, _line in tokens:
        if tok_type == tokenize.COMMENT:
            lines.append((start[0], tok_string))
        elif tok_type in (
            tokenize.NL,
            tokenize.NEWLINE,
            tokenize.ENCODING,
            tokenize.INDENT,
        ):
            continue
        elif tok_type == tokenize.ENDMARKER:
            break
        else:
            # First real statement token -- preamble is over.
            break
    return lines


def _resolve_include_source(label: str, *, filename: str) -> dict[str, Any]:
    """Resolve one `# include <label>` to its `{name: value}` vocabulary."""
    if label == _STDLIB_LABEL:
        import arklight

        return {name: getattr(arklight, name) for name in arklight.__all__}

    if label.startswith(_ACC_PREFIX):
        module_path = label[len(_ACC_PREFIX) :]
        try:
            module = importlib.import_module(module_path)
        except ImportError as exc:
            raise PreambleError(
                f"{filename}: `# include <{label}>` could not import "
                f"{module_path!r}: {exc}"
            ) from exc
        exported = getattr(module, "__all__", None)
        if not exported:
            raise PreambleError(
                f"{filename}: `# include <{label}>` -- {module_path!r} has "
                "no `__all__`, so ARKlight doesn't know what vocabulary it's "
                "meant to contribute. Define `__all__` in that module, the "
                "same contract `arklight.__all__` itself follows."
            )
        return {name: getattr(module, name) for name in exported}

    raise PreambleError(
        f"{filename}: unrecognized `# include <{label}>` -- expected "
        f"`<{_STDLIB_LABEL}>` or `<{_ACC_PREFIX}<dotted.module.path>>`."
    )


@dataclass(frozen=True)
class Directive:
    """One recognised preamble directive, as written -- nothing
    resolved yet. `kind` is `"include"` (`label` set), `"define"`
    (`name` and `text` set) or `"reserved"` (`name` is the reserved
    word)."""

    kind: str
    lineno: int
    label: str = ""
    name: str = ""
    text: str = ""


@dataclass
class NormalizedPreamble:
    """What normalization produced: the binding table with every
    `# include` applied, the table of `# define`s, plus `problems` --
    everything normalization couldn't apply, in the order it was met,
    *not raised*. Validation decides what to do about them."""

    filename: str
    bindings: dict[str, list[_Binding]] = field(default_factory=dict)
    defines: dict[str, _Define] = field(default_factory=dict)
    problems: list[PreambleError] = field(default_factory=list)


@dataclass(frozen=True)
class ResolvedPreamble:
    """A validated preamble: `bindings` is what the loader binds into
    the module namespace; `origins` records which include each name
    came from, so a later shadowing diagnostic can say what was
    overridden; `defines` is the validated `# define` table."""

    bindings: dict[str, Any]
    origins: dict[str, str]
    defines: dict[str, _Define] = field(default_factory=dict)


@dataclass(frozen=True)
class PreparedSource:
    """A file ready to run: its validated preamble, and its source
    with every `# define` applied (identical to the input when the
    file has none)."""

    resolved: ResolvedPreamble
    source: str


# ---------------------------------------------------------------------------
# Phase 1: parse -- one recogniser per directive shape
# ---------------------------------------------------------------------------


def _parse_include(text: str, lineno: int) -> Directive | None:
    match = _INCLUDE_RE.match(text)
    return Directive("include", lineno, label=match.group(1)) if match else None


def _parse_define(text: str, lineno: int) -> Directive | None:
    match = _DEFINE_RE.match(text)
    if not match:
        return None
    name, body = match.groups()
    return Directive("define", lineno, name=name, text=body)


def _parse_reserved(text: str, lineno: int) -> Directive | None:
    match = _RESERVED_RE.match(text)
    return Directive("reserved", lineno, name=match.group(1)) if match else None


# A new directive is registered here (and in `_HANDLERS` below).
_DIRECTIVE_PARSERS: tuple[Callable[[str, int], Directive | None], ...] = (
    _parse_include,
    _parse_define,
    _parse_reserved,
)


def parse_preamble(source: str) -> list[Directive]:
    """Phase 1: read every recognised directive comment in the
    source's preamble, in order. Pure text -- nothing is imported,
    resolved, or checked. Anything that isn't one of the directive
    shapes is just a comment and is skipped."""
    directives: list[Directive] = []
    for lineno, text in _leading_comment_lines(source):
        stripped = text.strip()
        for parser in _DIRECTIVE_PARSERS:
            directive = parser(stripped, lineno)
            if directive is not None:
                directives.append(directive)
                break
    return directives


# ---------------------------------------------------------------------------
# Phase 2: normalize -- handle each directive; record, never raise
# ---------------------------------------------------------------------------


def _apply_include(directive: Directive, result: NormalizedPreamble) -> None:
    try:
        resolved = _resolve_include_source(directive.label, filename=result.filename)
    except PreambleError as exc:
        result.problems.append(exc)
        return
    for name, value in resolved.items():
        result.bindings.setdefault(name, []).append(_Binding(value, directive.label))


def _apply_define(directive: Directive, result: NormalizedPreamble) -> None:
    where = f"{result.filename}:{directive.lineno}"
    name, text = directive.name, directive.text

    if not name.isidentifier() or keyword.iskeyword(name):
        result.problems.append(
            PreambleError(
                f"{where}: `# define {name} -> ...` -- the left side must be a "
                "single Python identifier that isn't a keyword; a define "
                "replaces whole names in the file's code."
            )
        )
        return
    if not text:
        result.problems.append(
            PreambleError(
                f"{where}: `# define {name} ->` has nothing on the right. "
                "Write the text that should replace the name."
            )
        )
        return

    earlier = result.defines.get(name)
    if earlier is not None:
        if earlier.text != text:
            result.problems.append(
                PreambleCollisionError(
                    f"{where}: `{name}` is already defined at line "
                    f"{earlier.lineno} as `{earlier.text}` -- two `# define`s "
                    "for one name would leave the later one silently winning. "
                    "Keep one."
                )
            )
        return  # an identical repeat is harmless
    result.defines[name] = _Define(text, directive.lineno)


def _apply_reserved(directive: Directive, result: NormalizedPreamble) -> None:
    result.problems.append(
        PreambleError(
            f"{result.filename}:{directive.lineno}: `# {directive.name} <...>` is "
            "reserved for a proposal that has not been accepted "
            f"({_RESERVED_DIRECTIVES[directive.name]}). It has no effect today, "
            "so ARKlight refuses it instead of silently ignoring it."
        )
    )


_HANDLERS: dict[str, Callable[[Directive, NormalizedPreamble], None]] = {
    "include": _apply_include,
    "define": _apply_define,
    "reserved": _apply_reserved,
}


def normalize_preamble(
    directives: list[Directive], *, filename: str = "<site>"
) -> NormalizedPreamble:
    """Phase 2: handle the directives. Includes fill the binding
    table; defines fill the define table. Never raises -- a directive
    that can't be applied is recorded in `problems` and left out, so
    `validate_preamble` can report it."""
    result = NormalizedPreamble(filename=filename)
    for directive in directives:
        _HANDLERS[directive.kind](directive, result)
    return result


# ---------------------------------------------------------------------------
# Phase 3: validate -- the only place the preamble fails
# ---------------------------------------------------------------------------


def _code_name_tokens(source: str) -> Iterator[tokenize.TokenInfo]:
    """Every NAME token of `source`'s code -- never one inside a
    string literal, f-strings included, whichever Python this is."""
    depth = 0
    for tok in tokenize.generate_tokens(io.StringIO(source).readline):
        if _FSTRING_START is not None:
            if tok.type == _FSTRING_START:
                depth += 1
                continue
            if tok.type == _FSTRING_END:
                depth -= 1
                continue
        if tok.type == tokenize.NAME and depth == 0:
            yield tok


def _names_in_text(text: str) -> list[str]:
    """Names a define's right-hand text mentions. A fragment that
    won't tokenize on its own (an unbalanced bracket, say) mentions
    none we can see; the parse check after substitution is what
    catches text that is actually wrong."""
    try:
        return [tok.string for tok in _code_name_tokens(text)]
    except (tokenize.TokenError, SyntaxError):
        return []


def validate_preamble(normalized: NormalizedPreamble) -> None:
    """Phase 3: the only place the preamble fails. Raises the first
    problem normalization recorded, then `PreambleCollisionError` for
    any name still bound to two different objects, then the two rules
    a `# define` can only be checked against the whole table for."""
    if normalized.problems:
        raise normalized.problems[0]

    for name, candidates in normalized.bindings.items():
        distinct_values = {id(candidate.value) for candidate in candidates}
        if len(distinct_values) > 1:
            named_sources = ", ".join(f"`{candidate.source}`" for candidate in candidates)
            raise PreambleCollisionError(
                f"{normalized.filename}: `{name}` is bound by more than one "
                f"`# include` to different objects ({named_sources}). ARKlight "
                "won't pick a winner: drop one of the includes, or have one "
                "side export a different name."
            )

    for name, define in normalized.defines.items():
        where = f"{normalized.filename}:{define.lineno}"
        provided = normalized.bindings.get(name)
        if provided:
            raise PreambleError(
                f"{where}: `# define {name} -> ...` -- `{name}` is already "
                f"provided by `# include <{provided[0].source}>`. Replacing it "
                "everywhere in this file would silently override that "
                "vocabulary. Pick a different name (for a component that is "
                "meant to override, use `@component(..., allow_redefine=True)`)."
            )
        for mentioned in _names_in_text(define.text):
            if mentioned in normalized.defines:
                raise PreambleError(
                    f"{where}: `# define {name} -> {define.text}` mentions "
                    f"`{mentioned}`, which is itself a `# define`. Defines are "
                    "applied in one pass and are not expanded again -- write "
                    f"out what `{mentioned}` stands for instead."
                )


# ---------------------------------------------------------------------------
# Applying the defines
# ---------------------------------------------------------------------------


def apply_defines(source: str, defines: Mapping[str, str]) -> tuple[str, int]:
    """Replace every whole-name token of `source`'s code that is a key
    of `defines` with its text; return `(new_source, replacements)`.

    Token-based, so a name inside a string literal or a comment is
    never touched, and `Btn` never matches inside `Btn2`. One pass:
    replaced text is not scanned again. Every replacement is one line
    of text, so no line moves.
    """
    if not defines:
        return source, 0
    lines = io.StringIO(source).readlines()
    edits: dict[int, list[tuple[int, int, str]]] = defaultdict(list)
    count = 0
    for tok in _code_name_tokens(source):
        text = defines.get(tok.string)
        if text is None:
            continue
        (row, col), (_end_row, end_col) = tok.start, tok.end
        edits[row].append((col, end_col, text))
        count += 1
    for row, spans in edits.items():
        line = lines[row - 1]
        for col, end_col, text in sorted(spans, reverse=True):  # right to left
            line = line[:col] + text + line[end_col:]
        lines[row - 1] = line
    return "".join(lines), count


def _apply_defines_checked(
    source: str, defines: Mapping[str, _Define], *, filename: str
) -> str:
    if not defines:
        return source
    try:
        ast.parse(source)
    except SyntaxError:
        # Not the defines' doing, and not ours to report: the loader's
        # own parse of this file says so, with its usual message.
        return source
    try:
        new_source, count = apply_defines(
            source, {name: define.text for name, define in defines.items()}
        )
    except (tokenize.TokenError, SyntaxError) as exc:
        raise PreambleError(
            f"{filename}: could not read the file's tokens to apply its "
            f"`# define`s: {exc}"
        ) from exc
    if count == 0:
        return source
    try:
        ast.parse(new_source, filename=filename)
    except SyntaxError as exc:
        in_effect = ", ".join(
            f"`{name} -> {define.text}` (line {define.lineno})"
            for name, define in defines.items()
        )
        raise PreambleError(
            f"{filename}: the file no longer parses once its `# define`s are "
            f"applied ({exc.msg}, line {exc.lineno}). Defines in effect: "
            f"{in_effect}. A define replaces the name everywhere it appears "
            "as a name -- attribute and keyword-argument names included."
        ) from exc
    return new_source


# ---------------------------------------------------------------------------
# Entry points
# ---------------------------------------------------------------------------


def resolve_preamble_detailed(source: str, *, filename: str = "<site>") -> ResolvedPreamble:
    """Parse, normalize, and validate `source`'s preamble; return the
    bindings plus where each one came from, and the define table."""
    normalized = normalize_preamble(parse_preamble(source), filename=filename)
    validate_preamble(normalized)
    return ResolvedPreamble(
        bindings={name: cands[0].value for name, cands in normalized.bindings.items()},
        origins={name: cands[0].source for name, cands in normalized.bindings.items()},
        defines=dict(normalized.defines),
    )


def resolve_preamble(source: str, *, filename: str = "<site>") -> dict[str, Any]:
    """
    Parse and resolve every directive in `source`'s preamble comments,
    returning the flat `{name: value}` mapping the loader should bind
    into the module namespace *before* executing the rest of the file
    -- ARKlight's own replacement for letting raw `from X import *`
    statements silently fight it out. (`# define`s bind nothing; see
    `prepare_source` for the whole job.)

    Raises `PreambleError` for a malformed or unresolvable directive,
    and `PreambleCollisionError` (a `PreambleError` subclass) when two
    includes bind the same name to two different objects.

    A file with no recognized directives resolves to `{}` -- callers
    keep working exactly as before if they never adopt this syntax.
    """
    return resolve_preamble_detailed(source, filename=filename).bindings


def prepare_source(source: str, *, filename: str = "<site>") -> PreparedSource:
    """Everything a loader needs before it can run `source`: the
    validated preamble (names to bind) and the source with every
    `# define` applied. This is the one call each loader makes."""
    resolved = resolve_preamble_detailed(source, filename=filename)
    return PreparedSource(
        resolved=resolved,
        source=_apply_defines_checked(source, resolved.defines, filename=filename),
    )


# ---------------------------------------------------------------------------
# After exec: names the file itself rebound
# ---------------------------------------------------------------------------


def _target_names(target: ast.expr) -> list[str]:
    if isinstance(target, ast.Name):
        return [target.id]
    if isinstance(target, (ast.Tuple, ast.List)):
        return [name for element in target.elts for name in _target_names(element)]
    if isinstance(target, ast.Starred):
        return _target_names(target.value)
    return []


def _collect_binders(
    body: list[ast.stmt],
    binders: dict[str, list[tuple[int, str]]],
    stars: list[tuple[int, str]],
) -> None:
    """Walk module-level statements (descending into `if`/`try`/`for`/
    `while`/`with` bodies, but not into a `def`/`class`'s own scope)
    and record every name they bind, with the line and kind."""
    for stmt in body:
        if isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef)):
            binders[stmt.name].append((stmt.lineno, "function definition"))
        elif isinstance(stmt, ast.ClassDef):
            binders[stmt.name].append((stmt.lineno, "class definition"))
        elif isinstance(stmt, ast.Assign):
            for target in stmt.targets:
                for name in _target_names(target):
                    binders[name].append((stmt.lineno, "assignment"))
        elif isinstance(stmt, (ast.AnnAssign, ast.AugAssign)):
            for name in _target_names(stmt.target):
                binders[name].append((stmt.lineno, "assignment"))
        elif isinstance(stmt, ast.Import):
            for alias in stmt.names:
                bound = alias.asname or alias.name.split(".")[0]
                binders[bound].append((stmt.lineno, "import"))
        elif isinstance(stmt, ast.ImportFrom):
            for alias in stmt.names:
                if alias.name == "*":
                    stars.append((stmt.lineno, stmt.module or "."))
                else:
                    binders[alias.asname or alias.name].append((stmt.lineno, "import"))
        else:
            if isinstance(stmt, (ast.For, ast.AsyncFor)):
                for name in _target_names(stmt.target):
                    binders[name].append((stmt.lineno, "loop variable"))
            for attr in ("body", "orelse", "finalbody"):
                _collect_binders(getattr(stmt, attr, []) or [], binders, stars)
            for handler in getattr(stmt, "handlers", []) or []:
                _collect_binders(handler.body, binders, stars)


def check_namespace_shadowing(
    resolved: ResolvedPreamble,
    namespace: dict[str, Any],
    *,
    source: str,
    filename: str,
) -> None:
    """After the site file has executed: raise `PreambleCollisionError`
    if the file rebound any name its own preamble bound.

    The preamble binds names *before* `exec`, so anything the file then
    defines under the same name (a `def`, an assignment, a plain or
    star import, a loop variable) silently replaces it -- Python's
    default, invisible to everything that ran before `exec`. This
    compares the finished namespace with what the preamble bound, by
    identity, so it sees every way of rebinding a name, including ones
    no static scan could (`globals()[...] = ...`); the source AST is
    consulted afterward only to say *where* it happened.

    A name is left alone if it's still the very same object (importing
    `Button` yourself after including it is harmless), if the file
    deleted it, or if the new value is a `@component(...,
    allow_redefine=True)` -- the explicit, per-component opt-in the
    registry already honors.
    """
    shadowed = [
        name
        for name, value in resolved.bindings.items()
        if name in namespace
        and namespace[name] is not value
        and not getattr(namespace[name], ALLOW_REDEFINE_MARKER, False)
    ]
    if not shadowed:
        return

    binders: dict[str, list[tuple[int, str]]] = defaultdict(list)
    stars: list[tuple[int, str]] = []
    try:
        _collect_binders(ast.parse(source, filename=filename).body, binders, stars)
    except SyntaxError:
        pass  # exec already succeeded on this source; nothing to attribute

    lines = []
    for name in shadowed:
        origin = resolved.origins.get(name, "the preamble")
        found = binders.get(name)
        if found:
            lineno, kind = found[-1]
            where = f"line {lineno}: {kind}"
        elif stars:
            lineno, module = stars[-1]
            where = f"line {lineno}: `from {module} import *`"
        else:
            where = "at runtime"
        lines.append(f"  - `{name}` (bound by `{origin}`, then rebound -- {where})")

    raise PreambleCollisionError(
        f"{filename}: this file rebinds name(s) its preamble already bound. "
        "Python would silently keep the later one; ARKlight refuses to:\n"
        + "\n".join(lines)
        + "\nRename yours so it doesn't share a name with included vocabulary "
        "(for a `@component(...)` that is meant to override, pass "
        "`allow_redefine=True`)."
    )


# ---------------------------------------------------------------------------
# Retired: `from arklight import *`
# ---------------------------------------------------------------------------

# Leading glyph matches the compiler's other always-shown notices (see
# `arklight.cli.main._stage_logger`), so this prints without --verbose.
_NOTICE_PREFIX = "\u26a0\ufe0f  [ARKlight NOTICE]:"


def find_retired_star_imports(source: str) -> list[int]:
    """Line numbers of every `from arklight import *` in `source`."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    return sorted(
        node.lineno
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom)
        and node.level == 0
        and node.module == "arklight"
        and any(alias.name == "*" for alias in node.names)
    )


def retired_star_import_notice(filename: str, lineno: int) -> str:
    """The message asking a site to move off `from arklight import *`."""
    return (
        f"{_NOTICE_PREFIX} {filename}:{lineno}: `from arklight import *` is "
        "retired.\n"
        "   Put `# include <stdlib.ARKlight>` at the top of the file, above "
        "all code, and delete this line.\n"
        "   ARKlight then binds the names itself and reports collisions, "
        "instead of Python silently keeping the last import.\n"
        "   It still works for now."
    )
