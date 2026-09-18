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
"""

from __future__ import annotations

import importlib
import io
import re
import tokenize
from dataclasses import dataclass
from typing import Any

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
    bindings: dict[str, list[_Binding]] = {}
    sources: dict[str, dict[str, Any]] = {}

    for lineno, text in _leading_comment_lines(source):
        stripped = text.strip()

        include_match = _INCLUDE_RE.match(stripped)
        if include_match:
            label = include_match.group(1)
            resolved = _resolve_include_source(label, filename=filename)
            sources[label] = resolved
            for name, value in resolved.items():
                bindings.setdefault(name, []).append(_Binding(value, label))
            continue

        define_match = _DEFINE_RE.match(stripped)
        if define_match:
            alias, target = define_match.groups()
            value = _resolve_define_target(
                target,
                sources=sources,
                bindings=bindings,
                filename=filename,
                lineno=lineno,
            )
            # A `# define` is the author's own explicit disambiguation
            # for `alias` -- it replaces (not appends to) whatever
            # `alias` currently holds, rather than becoming one more
            # candidate that could itself collide.
            bindings[alias] = [_Binding(value, f"# define (line {lineno})")]
            continue

        # Any other comment -- a remark, a shebang, a `# type: ignore`
        # -- is just a comment. ARKlight only ever acts on the two
        # directive shapes above.

    resolved: dict[str, Any] = {}
    for name, candidates in bindings.items():
        distinct_values = {id(candidate.value) for candidate in candidates}
        if len(distinct_values) > 1:
            named_sources = ", ".join(f"`{candidate.source}`" for candidate in candidates)
            raise PreambleCollisionError(
                f"{filename}: `{name}` is bound by more than one `# include` "
                f"to different objects ({named_sources}). Add "
                f"`# define {name} -> <label>.{name}` to pick one "
                "explicitly, or rename one side's export."
            )
        resolved[name] = candidates[0].value

    return resolved
