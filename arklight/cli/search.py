"""
`arklight search <name>` -- schema lookup, backed by the Stage 1-6
deterministic ranking pipeline (`arklight.search.engine`) for
components, plus direct closed-registry lookups for every other
closed vocabulary the compiler validates against.

Read-only reflection over `arklight.ir.schema`, the single source of
truth every compiler stage already reads from -- no new data format,
no compiler-pipeline changes. Exists so remembering "does `Picture`
take `sources=` or `srcs=`", or "does `Action.increment` take
`delta=`", doesn't require opening `schema.py` by hand.

The typo-tolerant fallback (`_suggest`) calls `SearchEngine.search`
(retrieval -> structural importance -> ranking, see
DETERMINISTIC_RANKING_PLAN.md), and `SearchEngine.knowledge` has
always merged in a project's own `COMPONENT_REGISTRY` (see
`arklight.search.knowledge`'s Stage 1 docstring) -- so a typo'd call
to a *user*-registered component was already suggestible. What wasn't
covered until now: the **exact-match** path only ever consulted
`SCHEMA`/`COMPONENT_REGISTRY` -- the *component* vocabulary.

Components aren't the only closed vocabulary the compiler validates
`on_click=`/`Action.*`/`Derive.*`/`Predicate.*`/event-modifier tokens
against -- `BEHAVIOR_REGISTRY`, `REVEAL_REGISTRY`, `ACTION_REGISTRY`,
`MODIFIER_REGISTRY`, `DERIVATION_REGISTRY`, and `PREDICATE_REGISTRY`
are each their own separate closed registry in `arklight.ir.schema`
(same "registry, not a hardcoded dispatch table" discipline the
module's own comments describe), and none of them were ever reachable
from `arklight search` at all -- not even the JS vocabulary's own
equivalent of "the exact right name", let alone a typo of one.
`search_component()` now also tries each of those, in a fixed
priority order (components first, since that's the vocabulary this
command was built for), before falling back to the suggestion
pipeline. A leading `Action.`/`Derive.`/`Predicate.` prefix is
accepted and stripped -- that's how these names are actually written
in a site file (`Action.increment(...)`, `Derive.sum(...)`,
`Predicate.truthy(...)`), so requiring the bare registry key
(`increment`, `sum`, `truthy`) instead would make the lookup fight the
very syntax it exists to help with.

Two more closed vocabularies were, until the search-knowledge-state-
and-keywords capability fix below, invisible to *both* the exact-match
path above and the typo-tolerant suggestion pipeline: the four
reactive-state declarations (`State`/`Bind`/`Computed`/`Watch`,
`arklight.api` -- never `NodeSpec` entries in `SCHEMA`, see
`arklight.search.knowledge.STATE_KEYWORDS`'s own comment for why) and
the six-plus-one closed registries just named. `arklight.search.
knowledge.build_knowledge_base()` now folds `STATE_KEYWORDS` and every
one of those registries into its output unconditionally, so the
ranking pipeline's suggestions cover them too; `search_component()`
gained its own small `_resolve_state_keyword` exact-match path for the
first, alongside `_resolve_js_vocab` for the rest. See
`docs/Implementation/SEARCH-KNOWLEDGE-STATE-AND-KEYWORDS-ADDENDUM.md`.

Both `resolve_exact` and `search_component` now check
`COMPONENT_REGISTRY` too, falling back to it only when `SCHEMA` has no
match -- same "built-ins always win a name collision" rule
`build_knowledge_base()` already applies, so behavior for every
built-in name is completely unchanged; `tests/test_search.py`'s
existing exact-match/suggestion assertions still hold. `resolve_exact`
itself stays component-only on purpose: it backs the CLI's `--accept`
flag (`arklight.cli.main`'s `args.accept` branch calls `resolve_exact`
directly, not `search_component`), which feeds `arklight.search.
stats`' usage-acceptance table. That's still true after the search-
knowledge-state-and-keywords capability fix below, even though
`SearchEngine.knowledge` now *does* include `STATE_KEYWORDS` and every
closed registry's names (the usage/known-typo signals those feed rank
suggestions for them too now) -- `--accept` itself was never routed
through the ranking pipeline's knowledge base, only through
`resolve_exact`, so `--accept increment`/`--accept State` still prints
"isn't an exact component name" exactly as before. The new
`_resolve_state_keyword`/`_resolve_js_vocab` lookups are separate,
additive paths that `search_component` also tries, not a change to
what `--accept` can record.

One more closed, compiler-validated vocabulary lived outside
`arklight.ir.schema` entirely and was missed by the sweep above:
`PLATFORM_API_REGISTRY` (`arklight.ir.platform_api`), the
`PlatformAPI.notify(...)` / `PlatformAPI.clipboard_write(...)`
interface table `arklight.ir.validate._validate_platform_api` checks
capability names and arguments against -- written the same
`Namespace.name(...)` way as `Action.*`/`Derive.*`/`Predicate.*`, but
never wired into `_JS_VOCAB_SOURCES`, so `arklight search notify`
fell all the way through to "no component named" even though `notify`
is real, closed vocabulary the compiler knows about. It is now the
seventh (and last) source `_resolve_js_vocab` tries, with its own
`platformapi.` dotted-prefix and its own formatter
(`_format_platform_api_spec`) reporting args, required permissions,
and which backend(s), if any, currently implement the capability --
`PLATFORM_API_REGISTRY` alone can't answer that last part
(`BACKEND_PLATFORM_API_SUPPORT` is a separate table; see
`arklight/ir/platform_api.py`).
"""

from __future__ import annotations

from typing import Any

from arklight.ir.components import COMPONENT_REGISTRY, ComponentSpec
from arklight.ir.platform_api import (
    BACKEND_PLATFORM_API_SUPPORT,
    PLATFORM_API_REGISTRY,
    PlatformAPISpec,
)
from arklight.ir.schema import (
    ACTION_REGISTRY,
    BEHAVIOR_REGISTRY,
    DERIVATION_REGISTRY,
    MODIFIER_REGISTRY,
    PREDICATE_REGISTRY,
    REVEAL_REGISTRY,
    SCHEMA,
    ActionSpec,
    BehaviorSpec,
    DerivationSpec,
    ModifierSpec,
    NodeSpec,
    PredicateSpec,
    RevealSpec,
)
from arklight.search.engine import default_engine
from arklight.search.knowledge import STATE_KEYWORDS

# Ordered (label, registry, dotted-prefix-if-any) -- checked in this
# order by `_resolve_js_vocab`, after the component vocabulary has
# already had first refusal in `search_component`. Order here is
# display/priority only: names don't actually collide across these
# registries in practice (components are `PascalCase`, everything
# here is `snake_case`), but a fixed order keeps a lookup
# deterministic if that ever changes.
#
# `PLATFORM_API_REGISTRY` lives in `arklight.ir.platform_api`, not
# `arklight.ir.schema` like the other six -- a different module, but
# the same kind of closed, compiler-validated vocabulary, and the same
# `Namespace.name(...)` authoring shape as `Action`/`Derive`/
# `Predicate`, so it belongs in this list on identical terms.
_JS_VOCAB_SOURCES: tuple[tuple[str, dict[str, Any], str | None], ...] = (
    ("on_click behavior", BEHAVIOR_REGISTRY, None),
    ("on_reveal behavior", REVEAL_REGISTRY, None),
    ("Action", ACTION_REGISTRY, "action."),
    ("event modifier", MODIFIER_REGISTRY, None),
    ("Derive", DERIVATION_REGISTRY, "derive."),
    ("Predicate", PREDICATE_REGISTRY, "predicate."),
    ("Platform API", PLATFORM_API_REGISTRY, "platformapi."),
)


def _suggest(query: str, limit: int = 5, near: str | None = None) -> list[str]:
    """
    Typo-tolerant "did you mean" suggestions for `query`, ranked by
    the Stage 5 pipeline (lexical similarity + structural importance +
    usage history) over every known component name in `SCHEMA`. Same
    external contract as the old `difflib`-only version: a plain,
    already-ordered `list[str]`.
    """
    results = default_engine().search(query, limit=limit, near=near)
    return [result.name for result in results]


def record_acceptance(name: str) -> None:
    """Thin wrapper around `SearchEngine.accept` -- records that
    `name` was the symbol the user actually wanted, closing the
    learning loop from the CLI's `--accept` flag."""
    default_engine().accept(name)


def resolve_exact(query: str) -> str | None:
    """Case-insensitive exact-match lookup, returning the canonical
    (correctly-cased) name or `None`. Checks the built-in `SCHEMA`
    first, then a project's own `COMPONENT_REGISTRY` -- same
    "built-ins always win a name collision" rule
    `arklight.search.knowledge.build_knowledge_base()` already applies,
    so a user component that happens to share a built-in's name is
    never resolved to the user's version here. Shared by
    `search_component()`'s own exact-match branch and the CLI's
    `--accept` flag, so "what counts as an exact match" has exactly
    one definition."""
    exact = SCHEMA.get(query)
    if exact is not None:
        return query

    lowered = {name.lower(): name for name in SCHEMA}
    canonical = lowered.get(query.lower())
    if canonical is not None:
        return canonical

    exact = COMPONENT_REGISTRY.get(query)
    if exact is not None:
        return query

    lowered_user = {name.lower(): name for name in COMPONENT_REGISTRY}
    return lowered_user.get(query.lower())


def _format_spec(name: str, spec: NodeSpec) -> str:
    lines = [f"{name}"]

    if spec.required_props:
        props = ", ".join(spec.required_props)
        lines.append(f"  required props : {props}")
    else:
        lines.append("  required props : (none)")

    lines.append(f"  allows children: {'yes' if spec.allow_children else 'no'}")

    if spec.text_only_children:
        lines.append(
            "  children       : text only (Bind(...) is also allowed here --"
            " see docs/Foundational/DESIGN-NOTES.md, 'stateful JS')"
        )
    elif spec.allow_children:
        lines.append("  children       : any nested component")

    return "\n".join(lines)


def _format_component_spec(name: str, spec: ComponentSpec) -> str:
    """Same job as `_format_spec`, for a *user*-registered component
    (`arklight.ir.components.ComponentSpec`) instead of a built-in
    `NodeSpec` -- the two aren't the same shape (props here are a
    `{name: Prop}` dict with a `.required` flag per prop, not a flat
    `required_props` tuple; there's no `allow_children`/
    `text_only_children` at all, since Stage 0 gave component calls no
    children slot -- see `arklight.search.knowledge.
    component_symbol_fact`'s docstring), so it needs its own
    formatting rather than being squeezed through `_format_spec`."""
    lines = [f"{name} (user-defined component, mode={spec.mode!r})"]

    required = sorted(prop_name for prop_name, prop in spec.props.items() if prop.required)
    optional = sorted(prop_name for prop_name, prop in spec.props.items() if not prop.required)

    if required:
        lines.append(f"  required props : {', '.join(required)}")
    else:
        lines.append("  required props : (none)")

    if optional:
        lines.append(f"  optional props : {', '.join(optional)}")

    lines.append("  children       : none (component calls take no children slot yet)")

    if spec.default_style:
        lines.append(f"  default style  : yes (folded into .{name} in the site stylesheet)")

    if spec.state:
        lines.append(f"  owned state    : {', '.join(sorted(spec.state))}")

    if spec.backend_render_fns:
        backends = ", ".join(sorted(spec.backend_render_fns))
        lines.append(f"  backend overrides: {backends}")

    return "\n".join(lines)


def _format_state_spec(name: str, required_args: tuple[str, ...]) -> str:
    """Same job `_format_spec`/`_format_component_spec` do for a
    `NodeSpec`/`ComponentSpec`, for one of the four reactive-state
    declarations (`arklight.search.knowledge.STATE_KEYWORDS`) instead
    -- these are plain `arklight.api` functions, not `NodeSpec`
    entries (see that module's own comment for why), so there's no
    `allow_children`/`text_only_children` story to report, only the
    required argument name(s) `STATE_KEYWORDS` already carries."""
    lines = [f"{name} (reactive-state declaration -- direct child of Page(...))"]
    if required_args:
        lines.append(f"  required args  : {', '.join(required_args)}")
    else:
        lines.append("  required args  : (none)")
    return "\n".join(lines)


def _resolve_state_keyword(query: str) -> str | None:
    """Exact-match (case-insensitive) lookup against `STATE_KEYWORDS`
    (`State`/`Bind`/`Computed`/`Watch`) -- the same job
    `_resolve_js_vocab` below does for the seven closed registries,
    kept as its own tiny function rather than folded into
    `_JS_VOCAB_SOURCES` because these four are bare `PascalCase`
    declarations (`State(...)`), not `Namespace.name(...)` dotted
    calls, and read from `arklight.search.knowledge.STATE_KEYWORDS`
    rather than an `arklight.ir.schema` registry. Returns a formatted
    result string, or `None` if `query` doesn't match any of the four
    -- same "no bare name" contract `_resolve_js_vocab` has, for the
    same reason: no CLI `--accept` use case for this vocabulary
    either (see this module's docstring)."""
    lowered = {name.lower(): name for name in STATE_KEYWORDS}
    canonical = lowered.get(query.lower())
    if canonical is None:
        return None
    return _format_state_spec(canonical, STATE_KEYWORDS[canonical])


def _format_behavior_spec(name: str, label: str, spec: BehaviorSpec | RevealSpec) -> str:
    prop = "on_click" if label == "on_click behavior" else "on_reveal"
    lines = [f"{name} ({label}, {prop}={name!r})"]
    if spec.extra_props:
        lines.append(f"  extra props    : {', '.join(spec.extra_props)}")
    else:
        lines.append("  extra props    : (none)")
    return "\n".join(lines)


def _format_action_spec(name: str, spec: ActionSpec) -> str:
    lines = [f"Action.{name}"]
    if spec.args:
        lines.append(f"  args           : {', '.join(spec.args)}")
    else:
        lines.append("  args           : (none)")
    if spec.state_args:
        lines.append(f"  Bind(...) args : {', '.join(spec.state_args)} (read from state when the action runs)")
    return "\n".join(lines)


def _format_modifier_spec(name: str, spec: ModifierSpec) -> str:
    lines = [f"{name} (event modifier -- .with_modifiers({name!r}) or .{name}(...))"]
    if spec.has_param:
        lines.append(f"  takes a value  : yes, e.g. .{name}(300) -> \"{name}:300\"")
    else:
        lines.append("  takes a value  : no (boolean flag)")
    return "\n".join(lines)


def _format_derivation_spec(name: str, spec: DerivationSpec) -> str:
    lines = [f"Derive.{name}"]
    if spec.max_names is None:
        arity = f"{spec.min_names}+ names"
    elif spec.min_names == spec.max_names:
        arity = f"exactly {spec.min_names} name{'s' if spec.min_names != 1 else ''}"
    else:
        arity = f"{spec.min_names}-{spec.max_names} names"
    lines.append(f"  names          : {arity}")
    if spec.extra_args:
        lines.append(f"  extra args     : {', '.join(spec.extra_args)}")
    else:
        lines.append("  extra args     : (none)")
    return "\n".join(lines)


def _format_predicate_spec(name: str, spec: PredicateSpec) -> str:
    lines = [f"Predicate.{name}"]
    qualifier = "at least" if spec.variadic else "exactly"
    lines.append(f"  names          : {qualifier} {spec.names} name{'s' if spec.names != 1 else ''}")
    if spec.extra_args:
        lines.append(f"  extra args     : {', '.join(spec.extra_args)}")
    return "\n".join(lines)


def _format_platform_api_spec(name: str, spec: PlatformAPISpec) -> str:
    lines = [f"PlatformAPI.{name}"]
    if spec.args:
        lines.append(f"  args           : {', '.join(spec.args)}")
    else:
        lines.append("  args           : (none)")
    if spec.permissions:
        lines.append(f"  permissions    : {', '.join(spec.permissions)}")
    else:
        lines.append("  permissions    : (none)")
    implemented_by = sorted(
        backend
        for backend, capabilities in BACKEND_PLATFORM_API_SUPPORT.items()
        if name in capabilities
    )
    if implemented_by:
        lines.append(f"  implemented by : {', '.join(implemented_by)}")
    else:
        lines.append("  implemented by : (no backend yet)")
    if spec.description:
        lines.append(f"  description    : {spec.description}")
    return "\n".join(lines)


_JS_VOCAB_FORMATTERS: dict[int, Any] = {
    id(BEHAVIOR_REGISTRY): lambda name, label, spec: _format_behavior_spec(name, label, spec),
    id(REVEAL_REGISTRY): lambda name, label, spec: _format_behavior_spec(name, label, spec),
    id(ACTION_REGISTRY): lambda name, label, spec: _format_action_spec(name, spec),
    id(MODIFIER_REGISTRY): lambda name, label, spec: _format_modifier_spec(name, spec),
    id(DERIVATION_REGISTRY): lambda name, label, spec: _format_derivation_spec(name, spec),
    id(PREDICATE_REGISTRY): lambda name, label, spec: _format_predicate_spec(name, spec),
    id(PLATFORM_API_REGISTRY): lambda name, label, spec: _format_platform_api_spec(name, spec),
}


def _resolve_js_vocab(query: str) -> str | None:
    """Exact-match (case-insensitive) lookup across every non-component
    closed registry -- `BEHAVIOR_REGISTRY`, `REVEAL_REGISTRY`,
    `ACTION_REGISTRY`, `MODIFIER_REGISTRY`, `DERIVATION_REGISTRY`,
    `PREDICATE_REGISTRY`, `PLATFORM_API_REGISTRY` -- in that fixed
    order. Strips a leading `action.`/`derive.`/`predicate.`/
    `platformapi.` prefix (case-insensitively) first, since that's how
    these names are actually written in a site file (`PlatformAPI.
    notify(...)` included). Returns a formatted result string, or
    `None` if nothing matched in any of them -- deliberately not a
    bare name like `resolve_exact`, since the caller needs to know
    which registry (and therefore which formatter) matched, and
    there's no CLI `--accept` use case for this vocabulary the way
    there is for components (see this module's docstring)."""
    lowered = query.lower()

    for label, registry, prefix in _JS_VOCAB_SOURCES:
        candidate = lowered
        if prefix is not None and lowered.startswith(prefix):
            candidate = lowered[len(prefix):]

        lookup = {key.lower(): key for key in registry}
        canonical = lookup.get(candidate)
        if canonical is None:
            continue

        formatter = _JS_VOCAB_FORMATTERS[id(registry)]
        return formatter(canonical, label, registry[canonical])

    return None


def search_component(query: str, *, limit: int = 5, near: str | None = None) -> str:
    """
    Look `query` up and return a formatted schema summary.

    Checks, in order: the built-in `SCHEMA`; a project's own
    `COMPONENT_REGISTRY` (registered `@component(...)` functions);
    then every other closed vocabulary registry --
    `BEHAVIOR_REGISTRY`/`REVEAL_REGISTRY` (`on_click=`/`on_reveal=`
    behavior names), `ACTION_REGISTRY` (`Action.*`), `MODIFIER_REGISTRY`
    (event-modifier tokens), `DERIVATION_REGISTRY` (`Derive.*`),
    `PREDICATE_REGISTRY` (`Predicate.*`), and `PLATFORM_API_REGISTRY`
    (`PlatformAPI.*`). Exact match (case-insensitive)
    in any of them wins outright, built-ins taking priority on a
    component-name collision. Otherwise, returns a "not found" message
    with up to `limit` ranked suggestions drawn from the component
    vocabulary -- or says plainly that nothing close was found, rather
    than guessing. `near` optionally biases suggestion ranking toward
    symbols structurally close to `near` (personalized PageRank seed);
    default behavior (`near=None`) is unchanged from before Stage 7.

    `near`, when given, is validated unconditionally -- before the
    exact-match check below -- so an unknown `--near` always raises
    `SearchEngineError`, whether or not `query` itself turns out to be
    a hit. An exact match returns immediately without ever reaching
    `_suggest()`/`SearchEngine.search()` (there's nothing to rank), so
    without this upfront check `--near` would silently do nothing on
    a hit instead of the documented "NAME must be a component the
    usage graph has actually seen used" error -- validating first
    closes that gap.

    The suggestion fallback below now draws from the full knowledge
    base -- `SCHEMA`, `COMPONENT_REGISTRY`, `STATE_KEYWORDS`, and every
    closed registry `_resolve_js_vocab` below checks -- since the
    search-knowledge-state-and-keywords capability fix folded all of
    them into `arklight.search.knowledge.build_knowledge_base()`. A
    typo of e.g. `increment`, `debounce`, or `Statee` now gets a "did
    you mean" the same way a typo'd component name always has; see
    `docs/Implementation/SEARCH-KNOWLEDGE-STATE-AND-KEYWORDS-ADDENDUM.md`.
    """
    if near is not None:
        default_engine().validate_near(near)

    canonical = resolve_exact(query)
    if canonical is not None:
        if canonical in SCHEMA:
            return _format_spec(canonical, SCHEMA[canonical])
        return _format_component_spec(canonical, COMPONENT_REGISTRY[canonical])

    state_result = _resolve_state_keyword(query)
    if state_result is not None:
        return state_result

    js_vocab_result = _resolve_js_vocab(query)
    if js_vocab_result is not None:
        return js_vocab_result

    suggestions = _suggest(query, limit=limit, near=near)
    if not suggestions:
        return (
            f"No component named {query!r} found, and nothing close enough "
            f"to suggest. Run `arklight --search <partial-name>` with a "
            f"shorter fragment, or see docs/Foundational/ARCHITECTURE.md for the full "
            f"component list."
        )

    suggestion_list = ", ".join(suggestions)
    return f"No component named {query!r} found. Did you mean: {suggestion_list}?"
