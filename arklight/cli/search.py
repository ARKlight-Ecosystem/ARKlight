"""
`arklight search <name>` -- component schema lookup, backed by the
Stage 1-6 deterministic ranking pipeline (`arklight.search.engine`).

Read-only reflection over `arklight.ir.schema.SCHEMA`, the single
source of truth every compiler stage already reads from -- no new data
format, no compiler-pipeline changes. Exists so remembering "does
`Picture` take `sources=` or `srcs=`" doesn't require opening
`schema.py` by hand once the vocabulary is 80+ names deep.

The typo-tolerant fallback (`_suggest`) calls `SearchEngine.search`
(retrieval -> structural importance -> ranking, see
DETERMINISTIC_RANKING_PLAN.md), and `SearchEngine.knowledge` has
always merged in a project's own `COMPONENT_REGISTRY` (see
`arklight.search.knowledge`'s Stage 1 docstring) -- so a typo'd call
to a *user*-registered component was already suggestible. What wasn't
covered until now: the **exact-match** path (`resolve_exact` /
`search_component`'s main branch) only ever consulted `SCHEMA`, the
closed built-in vocabulary. Typing the *correct*, exact name of a
registered user component (`arklight search NavBar`, where `NavBar` is
a real `@component(...)`-registered function) fell straight through
to the "not found" branch and printed typo suggestions for a name that
wasn't actually a typo -- `SCHEMA` and `COMPONENT_REGISTRY` are two
separate closed vocabularies and only one of them was ever checked
here. Both `resolve_exact` and `search_component` now check
`COMPONENT_REGISTRY` too, falling back to it only when `SCHEMA` has no
match -- same "built-ins always win a name collision" rule
`build_knowledge_base()` already applies, so behavior for every
built-in name is completely unchanged; `tests/test_search.py`'s
existing exact-match/suggestion assertions still hold.
"""

from __future__ import annotations

from arklight.ir.components import COMPONENT_REGISTRY, ComponentSpec
from arklight.ir.schema import SCHEMA, NodeSpec
from arklight.search.engine import default_engine


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
            " see docs/DESIGN-NOTES.md, 'stateful JS')"
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


def search_component(query: str, *, limit: int = 5, near: str | None = None) -> str:
    """
    Look `query` up and return a formatted schema summary.

    Checks the built-in `SCHEMA` first, then a project's own
    `COMPONENT_REGISTRY` (registered `@component(...)` functions) --
    exact match (case-insensitive) in either wins outright, built-ins
    taking priority on a name collision. Otherwise, returns a "not
    found" message with up to `limit` ranked suggestions drawn from
    *both* vocabularies -- or says plainly that nothing close was
    found, rather than guessing. `near` optionally biases suggestion
    ranking toward symbols structurally close to `near` (personalized
    PageRank seed); default behavior (`near=None`) is unchanged from
    before Stage 7.
    """
    canonical = resolve_exact(query)
    if canonical is not None:
        if canonical in SCHEMA:
            return _format_spec(canonical, SCHEMA[canonical])
        return _format_component_spec(canonical, COMPONENT_REGISTRY[canonical])

    suggestions = _suggest(query, limit=limit, near=near)
    if not suggestions:
        return (
            f"No component named {query!r} found, and nothing close enough "
            f"to suggest. Run `arklight --search <partial-name>` with a "
            f"shorter fragment, or see docs/ARCHITECTURE.md for the full "
            f"component list."
        )

    suggestion_list = ", ".join(suggestions)
    return f"No component named {query!r} found. Did you mean: {suggestion_list}?"
