"""
v0.060, Stage 1: typo diagnostics for user-defined components.

Covers `arklight.search.knowledge.component_symbol_fact`/
`build_knowledge_base(components=...)`, `SearchEngine.knowledge`'s
merge of `COMPONENT_REGISTRY` into the built-in `SCHEMA` facts, and
the end-to-end path this all exists for: a typo'd call to a
*registered user* component now gets the same "did you mean...?"
treatment (and the same Stage 8 confusion-recording) a typo'd built-in
like `Headign(...)` already got -- see
`USER-DEFINED-COMPONENTS-IMPLEMENTATION.md` [retired -- see CHANGELOG.md]'s Stage
1 row, and `tests/test_search_feedback.py` for the built-in-only
version of the same tests this file mirrors.
"""

from __future__ import annotations

import textwrap

import pytest

from arklight.compiler.pipeline import CompileError, compile_site_file
from arklight.ir.components import COMPONENT_REGISTRY, Prop, register_component
from arklight.ir.schema import SCHEMA
from arklight.search.engine import SearchEngine
from arklight.search.feedback import record_name_error_feedback
from arklight.search.knowledge import build_knowledge_base, component_symbol_fact
from arklight.search.stats import is_known_confusion


@pytest.fixture(autouse=True)
def _clean_registry():
    """Same isolation fixture `test_user_defined_components_stage0.py`
    already uses -- tests would otherwise leak registrations into each
    other (and, worse here, into unrelated `SearchEngine`-based tests
    elsewhere, since `.knowledge` now reads this registry live)."""
    saved = dict(COMPONENT_REGISTRY)
    COMPONENT_REGISTRY.clear()
    yield
    COMPONENT_REGISTRY.clear()
    COMPONENT_REGISTRY.update(saved)


# ---------------------------------------------------------------------------
# component_symbol_fact
# ---------------------------------------------------------------------------


def test_component_symbol_fact_reflects_required_props():
    spec = register_component(
        "NavBar",
        lambda active=None: None,
        props={"active": Prop(default=None), "label": Prop()},
    )
    fact = component_symbol_fact(spec)
    assert fact.name == "NavBar"
    assert fact.required_props == ("label",)
    assert fact.allow_children is False
    assert fact.text_only_children is False
    assert fact.tokens == ("nav", "bar")


def test_component_symbol_fact_with_no_required_props():
    spec = register_component("Widget", lambda: None)
    fact = component_symbol_fact(spec)
    assert fact.required_props == ()


# ---------------------------------------------------------------------------
# build_knowledge_base(components=...)
# ---------------------------------------------------------------------------


def test_build_knowledge_base_without_components_is_unchanged():
    # No `components=` argument at all -- every existing caller (there
    # were several before Stage 1) still gets every built-in `SCHEMA`
    # fact, nothing missing. (Since the search-knowledge-state-and-
    # keywords capability fix, `facts` is a strict superset of
    # `SCHEMA` -- it also always carries `STATE_KEYWORDS` and the
    # closed registries -- so this checks containment, not equality.)
    facts = build_knowledge_base()
    assert set(SCHEMA) <= set(facts)


def test_build_knowledge_base_merges_in_registered_components():
    spec = register_component("NavBar", lambda: None)
    facts = build_knowledge_base(components=COMPONENT_REGISTRY)
    assert "NavBar" in facts
    assert facts["NavBar"] == component_symbol_fact(spec)
    # Built-ins are still all present, untouched.
    assert set(SCHEMA) <= set(facts)


def test_build_knowledge_base_never_lets_a_user_component_shadow_a_builtin():
    # A user component that happens to reuse a built-in's name doesn't
    # overwrite that name's real schema facts in the knowledge base --
    # SCHEMA stays the closed, canonical source for its own names.
    # `allow_redefine=True`: registering a built-in's name is refused by
    # default now; this is the deliberate-override state the knowledge
    # base still has to stay correct for.
    register_component("Heading", lambda: None, props={"level": Prop()}, allow_redefine=True)
    facts = build_knowledge_base(components=COMPONENT_REGISTRY)
    assert facts["Heading"] == build_knowledge_base()["Heading"]


# ---------------------------------------------------------------------------
# SearchEngine.knowledge / .search -- the live merge
# ---------------------------------------------------------------------------


@pytest.fixture
def engine(tmp_path):
    db_path = tmp_path / "search.sqlite3"
    eng = SearchEngine(roots=[], db_path=db_path)
    yield eng
    eng.close()


def test_engine_knowledge_includes_registered_user_components(engine):
    register_component("NavBar", lambda: None)
    assert "NavBar" in engine.knowledge


def test_engine_knowledge_picks_up_registrations_made_after_first_access(engine):
    # `.knowledge` is accessed once (with an empty registry) before
    # `NavBar` is ever registered -- confirms the merge isn't a
    # snapshot frozen at first access (see `SearchEngine.knowledge`'s
    # own docstring for why that matters for the real
    # `compile_site_file` path).
    assert "NavBar" not in engine.knowledge
    register_component("NavBar", lambda: None)
    assert "NavBar" in engine.knowledge


def test_engine_search_suggests_a_registered_component_for_a_typo(engine):
    register_component("NavBar", lambda: None)
    results = engine.search("NavBarr", limit=3)
    assert "NavBar" in [result.name for result in results]


def test_engine_search_still_suggests_builtins_when_registry_is_empty(engine):
    results = engine.search("Headign", limit=3)
    assert "Heading" in [result.name for result in results]


# ---------------------------------------------------------------------------
# End-to-end: a typo'd call to a real, registered component
# ---------------------------------------------------------------------------


def test_record_name_error_feedback_resolves_a_user_component_typo(engine):
    register_component("NavBar", lambda: None)
    record_name_error_feedback("name 'NavBarr' is not defined", engine)
    assert is_known_confusion(engine.stats, "NavBarr", "NavBar")


def test_a_real_user_component_typo_build_records_a_confusion(tmp_path, monkeypatch):
    # Same repro shape as
    # `test_search_feedback.test_a_real_component_typo_build_records_a_confusion`,
    # but for a project's own registered component instead of a
    # built-in.
    site_dir = tmp_path / "site"
    site_dir.mkdir()
    (site_dir / "site.py").write_text(
        textwrap.dedent(
            """
            from arklight import *

            @component()
            def NavBar():
                return Container(Link("Home", href="/"))

            site = Site()

            @site.page("/")
            def home():
                return Page(NavBarr())
            """
        )
    )

    db_path = tmp_path / "search.sqlite3"
    monkeypatch.setattr(
        "arklight.compiler.pipeline.default_engine",
        lambda: SearchEngine(roots=[], db_path=db_path),
    )

    with pytest.raises(CompileError, match="NavBarr"):
        compile_site_file(site_dir / "site.py")

    check_engine = SearchEngine(db_path=db_path)
    try:
        assert is_known_confusion(check_engine.stats, "NavBarr", "NavBar")
    finally:
        check_engine.close()
