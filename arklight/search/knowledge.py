"""
Stage 1 -- v0.060, "Typo diagnostics", also touches this module: a
registered *user* component (`arklight.ir.components.ComponentSpec`)
is now, optionally, part of the same knowledge base a typo gets ranked
against -- see `component_symbol_fact`/`build_knowledge_base`'s
`components=` parameter below, and
`docs/Foundational/USER-DEFINED-COMPONENTS-IMPLEMENTATION.md`'s Stage
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
from arklight.ir.schema import SCHEMA
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


def build_knowledge_base(
    *, components: dict[str, ComponentSpec] | None = None
) -> dict[str, SymbolFact]:
    """
    `components`, if given, is a `{name: ComponentSpec}` mapping --
    in practice `arklight.ir.components.COMPONENT_REGISTRY`, a
    project's own registered user components -- merged in alongside
    the built-in `SCHEMA` facts. Defaults to `None` (no merge), so
    every existing caller that only ever wanted the built-in
    vocabulary is unaffected.

    Built-ins always win a name collision: `SCHEMA` is the closed,
    canonical vocabulary every other compiler stage already agrees on,
    so a user component that happens to reuse a built-in's name
    (`Heading`, `Container`, ...) is silently *not* added here rather
    than shadowing that name's real schema facts with the user's own.
    Nothing about the component registry itself is affected -- this
    only concerns what `arklight search`/the Stage 8 typo-feedback
    loop sees.
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
    for name, component_spec in (components or {}).items():
        if name in facts:
            continue
        facts[name] = component_symbol_fact(component_spec)
    return facts
