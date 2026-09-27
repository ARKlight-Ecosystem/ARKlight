"""
Stage 1 -- v0.060, "Typo diagnostics", also touches this module: a
registered *user* component (`arklight.ir.components.ComponentSpec`)
is now, optionally, part of the same knowledge base a typo gets ranked
against -- see `component_symbol_fact`/`build_knowledge_base`'s
`components=` parameter below, and
`USER-DEFINED-COMPONENTS-IMPLEMENTATION.md` [retired -- see CHANGELOG.md]'s Stage
1 row for why: previously `build_knowledge_base()` only ever read
`arklight.ir.schema.SCHEMA` (the closed, built-in vocabulary), so a
typo'd call to a real, registered user component (`NavBarr(...)`
instead of `NavBar(...)`) could never surface a "did you mean...?"
suggestion -- `NavBar` simply wasn't a symbol this module's knowledge
base had ever heard of, no matter how good Stage 2-5's ranking over
what it *did* know was.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from arklight.ir.components import ComponentSpec
from arklight.ir.platform_api import PLATFORM_API_REGISTRY
from arklight.ir.schema import (
    ACTION_REGISTRY,
    BEHAVIOR_REGISTRY,
    DERIVATION_REGISTRY,
    MODIFIER_REGISTRY,
    PREDICATE_REGISTRY,
    REVEAL_REGISTRY,
    SCHEMA,
)
from arklight.search._tokenize import tokenize


@dataclass(frozen=True)
class SymbolFact:
    name: str
    required_props: tuple[str, ...] = field(default_factory=tuple)
    allow_children: bool = True
    text_only_children: bool = False
    tokens: tuple[str, ...] = field(default_factory=tuple)


def component_symbol_fact(spec: ComponentSpec) -> SymbolFact:
    """
    Build a `SymbolFact` for one registered user component, the same
    shape `build_knowledge_base` already builds for every built-in
    `SCHEMA` entry -- so retrieval/ranking (`arklight.search.
    retrieval.retrieve_candidates`, `arklight.search.ranking.rank`)
    can't tell the two apart and don't need to.

    `required_props` is read off `spec.props` (a user component's own
    `Prop(...)` contract, see `arklight.ir.components.Prop.required`)
    rather than `NodeSpec.required_props` -- same *meaning*, different
    source, since a user component was never added to `SCHEMA`.

    `allow_children`/`text_only_children` are always `False`/`False`:
    Stage 0 deliberately gave a component call no positional-children
    slot at all (`NavBar(active="home")`, keyword props only -- see
    `USER-DEFINED-COMPONENTS-IMPLEMENTATION.md`'s "No children slot on
    a component call, yet" note), so unlike a built-in `Container`
    (`allow_children=True`) or `Heading` (`text_only_children=True`),
    a user component call site never has a children position for
    `arklight search`'s hint text to describe. Revisit this if/when a
    later stage gives components their own children slot.
    """
    required_props = tuple(
        sorted(name for name, prop in spec.props.items() if prop.required)
    )
    return SymbolFact(
        name=spec.name,
        required_props=required_props,
        allow_children=False,
        text_only_children=False,
        tokens=tuple(tokenize(spec.name)),
    )


# Capability fix (search-knowledge-state-and-keywords, Stage 1): the
# four page-scoped reactive-state declarations (`State`/`Bind`/
# `Computed`/`Watch`, `arklight.api`) are, deliberately, never
# `NodeSpec` entries in `SCHEMA` -- see `SCHEMA`'s own comment above
# `Repeat`/`Show` for why: unlike renderable content, they're
# page-scoped declarations Validation/IR-build pull out of the tree
# entirely, so they were never candidates for a `NodeSpec` (no HTML
# tag, no `allow_children` story of their own). That's the right call
# for compilation, but it also meant this module's knowledge base --
# and therefore every `arklight search` typo suggestion -- had never
# heard of them either: `arklight search State` (let alone a typo like
# `Statee`) fell straight through to "No component named", the same
# gap `component_symbol_fact` above closed for user components.
#
# `required_props` here is each function's own required argument
# name(s), read straight off `arklight.api`'s signatures (`State(name,
# ...)`, `Bind(name)`, `Computed(name, ...)`, `Watch(name, *,
# then)`) -- there's no `NodeSpec` to read them from.
STATE_KEYWORDS: dict[str, tuple[str, ...]] = {
    "State": ("name",),
    "Bind": ("name",),
    "Computed": ("name",),
    "Watch": ("name", "then"),
}

# The other half of the same gap: `BEHAVIOR_REGISTRY`/`REVEAL_REGISTRY`
# (on_click=/on_reveal= names), `ACTION_REGISTRY` (Action.*),
# `MODIFIER_REGISTRY` (event-modifier tokens), `DERIVATION_REGISTRY`
# (Derive.*), `PREDICATE_REGISTRY` (Predicate.*), and
# `PLATFORM_API_REGISTRY` (PlatformAPI.*) are each their own closed,
# compiler-validated vocabulary. `arklight.cli.search._resolve_js_vocab`
# already answers an *exact* (or dotted-prefix) lookup against every
# one of them, but that path never touched this module, so none of
# them were ever part of what `arklight.search.retrieval`/
# `arklight.search.ranking` score candidates from -- a typo like
# `incrment` or `debunce` got no "did you mean" of its own. Order here
# matches `arklight.cli.search._JS_VOCAB_SOURCES`, for the same
# "deterministic, not that it matters" reason that module gives; no
# real collision exists between any of these `snake_case`/`kebab-case`
# keywords and `SCHEMA`'s `PascalCase` node names or `STATE_KEYWORDS`
# above, but the "built-ins always win" skip below holds regardless.
_CLOSED_KEYWORD_REGISTRIES: tuple[dict[str, object], ...] = (
    BEHAVIOR_REGISTRY,
    REVEAL_REGISTRY,
    ACTION_REGISTRY,
    MODIFIER_REGISTRY,
    DERIVATION_REGISTRY,
    PREDICATE_REGISTRY,
    PLATFORM_API_REGISTRY,
)


def build_knowledge_base(
    *, components: dict[str, ComponentSpec] | None = None
) -> dict[str, SymbolFact]:
    """
    `components`, if given, is a `{name: ComponentSpec}` mapping --
    in practice `arklight.ir.components.COMPONENT_REGISTRY`, a
    project's own registered user components -- merged in alongside
    the built-in facts below. Defaults to `None` (no merge), so every
    existing caller that only ever wanted the built-in vocabulary is
    unaffected.

    The built-in facts are, since the search-knowledge-state-and-
    keywords capability fix, three closed sources rather than one:
    every `SCHEMA` entry (as before), `STATE_KEYWORDS` (`State`/
    `Bind`/`Computed`/`Watch`), and every entry of the seven closed
    registries in `_CLOSED_KEYWORD_REGISTRIES` (on_click/on_reveal
    behaviors, `Action.*`, event modifiers, `Derive.*`, `Predicate.*`,
    `PlatformAPI.*`). All three are unconditional -- not opt-in the
    way `components=` is -- since they're fixed, closed vocabulary
    every compiled site already agrees on, exactly like `SCHEMA`
    itself.

    Built-ins always win a name collision, checked in that same fixed
    order (`SCHEMA`, then `STATE_KEYWORDS`, then each closed registry,
    then `components`): each source is the closed, canonical
    vocabulary every other compiler stage already agrees on, so
    anything later in the order that happens to reuse an earlier
    source's name (`Heading`, `Container`, ...) is silently *not*
    added here rather than shadowing that name's real facts. Nothing
    about any of these registries -- or the component registry -- is
    affected; this only concerns what `arklight search`/the Stage 8
    typo-feedback loop sees.
    """
    facts: dict[str, SymbolFact] = {}
    for name, spec in SCHEMA.items():
        facts[name] = SymbolFact(
            name=name,
            required_props=spec.required_props,
            allow_children=spec.allow_children,
            text_only_children=spec.text_only_children,
            tokens=tuple(tokenize(name)),
        )
    for name, required_props in STATE_KEYWORDS.items():
        if name in facts:
            continue
        facts[name] = SymbolFact(
            name=name,
            required_props=required_props,
            allow_children=False,
            text_only_children=False,
            tokens=tuple(tokenize(name)),
        )
    for registry in _CLOSED_KEYWORD_REGISTRIES:
        for name in registry:
            if name in facts:
                continue
            facts[name] = SymbolFact(
                name=name,
                required_props=(),
                allow_children=False,
                text_only_children=False,
                tokens=tuple(tokenize(name)),
            )
    for name, component_spec in (components or {}).items():
        if name in facts:
            continue
        facts[name] = component_symbol_fact(component_spec)
    return facts
