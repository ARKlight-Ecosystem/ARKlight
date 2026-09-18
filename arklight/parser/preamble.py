"""
Preamble directives -- ARKlight's own, compiler-owned answer to the
"last import wins" problem with `from arklight import *` (and the same
star-import pattern against any other vocabulary source, ACC included).

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
begin with. That step still runs on raw Python import semantics, with
zero ARKlight involvement, which is exactly the gap this module closes.

Preamble directives move "get names into this module" itself onto
compiler-owned ground. Written as reserved-shape comments before the
first executable statement in a site file:

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

    # define Btn -> Button
    # define Button -> acc.some_collection.Button

`# define <alias> -> <target>` resolves a collision explicitly (or
just adds a local alias). A bare target name must resolve unambiguously
across everything included so far; a dotted target
(`<include-label>.<name>`) picks one specific include's copy by name,
for exactly the case where two includes disagree about what a name
means.

`from arklight import *` keeps working exactly as it always has --
this module only ever acts on comments matching the two directive
shapes above, so raw Python import statements are completely
untouched and this is purely additive. But a site file that uses
`# include`/`# define` instead of writing its own `from ... import *`
lines gets ARKlight's own collision detection for free, and that is
the intended migration path (see `AUTHORING-GUIDE.md`'s "Preamble
directives" section).

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

`# define <alias> -> <target>` is a rename -- replace the left name
with the right one -- which is canonicalization, so normalization is
where it is applied: an include's names go into the binding table, a
define replaces its alias's entry, and that is all normalization does.
It never raises; anything wrong (an unresolvable include, a define
whose target doesn't exist or is ambiguous, two defines disagreeing
about one alias) is recorded on the `NormalizedPreamble` instead.
Validation then inspects the normalized table and is what actually
fails the load -- first recorded problem, then any name still bound to
two different objects (`PreambleCollisionError`).

One check has to run *after* the site file executes, because it is
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
import re
import tokenize
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any

from arklight.ir.components import ALLOW_REDEFINE_MARKER

_INCLUDE_RE = re.compile(r"^#\s*include\s*<\s*([^<>\s]+)\s*>\s*$")
_DEFINE_RE = re.compile(r"^#\s*define\s+([A-Za-z_][A-Za-z0-9_]*)\s*->\s*([A-Za-z_][A-Za-z0-9_.]*)\s*$")

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


class PreambleError(SyntaxError):
    """Raised for a malformed, unresolved, or ambiguous preamble
    directive (`# include <...>` / `# define ... -> ...`)."""


class PreambleCollisionError(PreambleError):
    """Raised when two `# include` directives bind the same name to
    two different objects and no `# define` disambiguates it.

    This is the specific failure `# include`/`# define` exist to make
    loud: the equivalent situation with two raw `from X import *`
    statements is silently resolved by Python itself, in the second
    import's favor, with no error and no trace of what was lost.
    """


@dataclass(frozen=True)
class _Binding:
    value: Any
    source: str  # the include label (or "# define (line N)") it came from


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


def _resolve_define_target(
    target: str,
    *,
    sources: dict[str, dict[str, Any]],
    bindings: dict[str, list[_Binding]],
    filename: str,
    lineno: int,
) -> Any:
    if "." in target:
        label, _, name = target.rpartition(".")
        source = sources.get(label)
        if source is None:
            raise PreambleError(
                f"{filename}:{lineno}: `# define ... -> {target}` refers to "
                f"include label `{label}`, but no `# include <{label}>` has "
                "appeared yet in this file's preamble."
            )
        if name not in source:
            raise PreambleError(
                f"{filename}:{lineno}: `{label}` has no `{name}` to define "
                f"from (`# include <{label}>`)."
            )
        return source[name]

    candidates = bindings.get(target)
    if not candidates:
        raise PreambleError(
            f"{filename}:{lineno}: `# define ... -> {target}` refers to "
            f"`{target}`, which nothing included so far provides."
        )
    distinct_values = {id(candidate.value) for candidate in candidates}
    if len(distinct_values) > 1:
        raise PreambleError(
            f"{filename}:{lineno}: `{target}` is ambiguous -- bound by more "
            f"than one include to different objects. Use `<label>.{target}` "
            "to pick one explicitly."
        )
    return candidates[0].value


@dataclass(frozen=True)
class Directive:
    """One recognised preamble directive, as written -- nothing
    resolved yet. `kind` is `"include"` (`label` set) or `"define"`
    (`alias` and `target` set)."""

    kind: str
    lineno: int
    label: str = ""
    alias: str = ""
    target: str = ""


@dataclass
class NormalizedPreamble:
    """What normalization produced: the binding table with every
    `# include` applied and every `# define` substituted in, plus
    `problems` -- everything normalization couldn't apply, in the
    order it was met, *not raised*. Validation decides what to do
    about them."""

    filename: str
    bindings: dict[str, list[_Binding]] = field(default_factory=dict)
    sources: dict[str, dict[str, Any]] = field(default_factory=dict)
    problems: list[PreambleError] = field(default_factory=list)


@dataclass(frozen=True)
class ResolvedPreamble:
    """A validated preamble: `bindings` is what the loader binds into
    the module namespace; `origins` records which include (or
    `# define` line) each name came from, so a later shadowing
    diagnostic can say what was overridden."""

    bindings: dict[str, Any]
    origins: dict[str, str]


def parse_preamble(source: str) -> list[Directive]:
    """Phase 1: read every recognised `# include`/`# define` comment
    in the source's preamble, in order. Pure text -- nothing is
    imported, resolved, or checked. Anything that isn't one of the two
    directive shapes is just a comment and is skipped."""
    directives: list[Directive] = []
    for lineno, text in _leading_comment_lines(source):
        stripped = text.strip()

        include_match = _INCLUDE_RE.match(stripped)
        if include_match:
            directives.append(Directive("include", lineno, label=include_match.group(1)))
            continue

        define_match = _DEFINE_RE.match(stripped)
        if define_match:
            alias, target = define_match.groups()
            directives.append(Directive("define", lineno, alias=alias, target=target))
    return directives


def normalize_preamble(
    directives: list[Directive], *, filename: str = "<site>"
) -> NormalizedPreamble:
    """Phase 2: handle the directives. Includes fill the binding
    table; a `# define` replaces its alias's entry with its target's
    value (the left name now means the right one). Never raises --
    a directive that can't be applied is recorded in `problems` and
    left out, so `validate_preamble` can report it."""
    result = NormalizedPreamble(filename=filename)
    defined_at: dict[str, tuple[int, Any]] = {}

    for directive in directives:
        if directive.kind == "include":
            try:
                resolved = _resolve_include_source(directive.label, filename=filename)
            except PreambleError as exc:
                result.problems.append(exc)
                continue
            result.sources[directive.label] = resolved
            for name, value in resolved.items():
                result.bindings.setdefault(name, []).append(_Binding(value, directive.label))
            continue

        try:
            value = _resolve_define_target(
                directive.target,
                sources=result.sources,
                bindings=result.bindings,
                filename=filename,
                lineno=directive.lineno,
            )
        except PreambleError as exc:
            result.problems.append(exc)
            continue

        earlier = defined_at.get(directive.alias)
        if earlier is not None and earlier[1] is not value:
            result.problems.append(
                PreambleCollisionError(
                    f"{filename}:{directive.lineno}: `{directive.alias}` is "
                    f"already defined at line {earlier[0]} as a different "
                    "object -- two `# define`s for one alias would leave "
                    "the later one silently winning. Keep one."
                )
            )
            continue
        defined_at[directive.alias] = (directive.lineno, value)

        # A `# define` is the author's own explicit disambiguation
        # for `alias` -- it replaces (not appends to) whatever
        # `alias` currently holds, rather than becoming one more
        # candidate that could itself collide.
        result.bindings[directive.alias] = [
            _Binding(value, f"# define (line {directive.lineno})")
        ]
    return result


def validate_preamble(normalized: NormalizedPreamble) -> None:
    """Phase 3: the only place the preamble fails. Raises the first
    problem normalization recorded, then `PreambleCollisionError` for
    any name still bound to two different objects."""
    if normalized.problems:
        raise normalized.problems[0]

    for name, candidates in normalized.bindings.items():
        distinct_values = {id(candidate.value) for candidate in candidates}
        if len(distinct_values) > 1:
            named_sources = ", ".join(f"`{candidate.source}`" for candidate in candidates)
            raise PreambleCollisionError(
                f"{normalized.filename}: `{name}` is bound by more than one "
                f"`# include` to different objects ({named_sources}). Add "
                f"`# define {name} -> <label>.{name}` to pick one "
                "explicitly, or rename one side's export."
            )


def resolve_preamble_detailed(source: str, *, filename: str = "<site>") -> ResolvedPreamble:
    """Parse, normalize, and validate `source`'s preamble; return the
    bindings plus where each one came from."""
    normalized = normalize_preamble(parse_preamble(source), filename=filename)
    validate_preamble(normalized)
    return ResolvedPreamble(
        bindings={name: cands[0].value for name, cands in normalized.bindings.items()},
        origins={name: cands[0].source for name, cands in normalized.bindings.items()},
    )


def resolve_preamble(source: str, *, filename: str = "<site>") -> dict[str, Any]:
    """
    Parse and resolve every `# include`/`# define` directive in
    `source`'s preamble comments, returning the flat `{name: value}`
    mapping the loader should bind into the module namespace *before*
    executing the rest of the file -- ARKlight's own replacement for
    letting raw `from X import *` statements silently fight it out.

    Raises `PreambleError` for a malformed or unresolvable directive,
    and `PreambleCollisionError` (a `PreambleError` subclass) when two
    includes bind the same name to two different objects and no
    `# define` picks one.

    A file with no recognized directives resolves to `{}` -- callers
    keep working exactly as before if they never adopt this syntax.
    """
    return resolve_preamble_detailed(source, filename=filename).bindings


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
