import pytest

from arklight.cli.search import resolve_exact, search_component
from arklight.ir.components import COMPONENT_REGISTRY, Prop, register_component
from arklight.ir.schema import SCHEMA


@pytest.fixture(autouse=True)
def _clean_registry():
    """Same isolation fixture `test_user_defined_components_stage0.py`
    uses -- a component registered by one test must not leak into the
    next one, or into unrelated `SearchEngine`-based tests elsewhere,
    since `search_component`/`SearchEngine.knowledge` both now read
    this registry live."""
    saved = dict(COMPONENT_REGISTRY)
    COMPONENT_REGISTRY.clear()
    yield
    COMPONENT_REGISTRY.clear()
    COMPONENT_REGISTRY.update(saved)


def _dummy_render(**_props):
    from arklight.api import Text

    return Text("x")


def test_search_exact_match_for_every_schema_entry():
    # Every real component name must resolve without falling back to
    # the "not found" / suggestion path.
    for name in SCHEMA:
        result = search_component(name)
        assert result.startswith(name)
        assert "No component named" not in result


def test_search_reports_no_children_when_children_disallowed():
    result = search_component("Image")
    assert "allows children: no" in result


def test_search_reports_required_props():
    result = search_component("Image")
    assert "src" in result


def test_search_reports_none_for_no_required_props():
    result = search_component("Container")
    assert "(none)" in result


def test_search_unknown_name_returns_suggestions():
    result = search_component("Butto")
    assert "No component named 'Butto' found" in result
    assert "Button" in result


def test_search_completely_unrelated_query_has_no_suggestions():
    result = search_component("qzxjklw_totally_unrelated")
    assert "nothing close enough to suggest" in result


def test_search_finds_exact_match_for_registered_user_component():
    # Previously fell straight through to the "not found" branch --
    # search_component()/resolve_exact() only ever checked SCHEMA, the
    # closed built-in vocabulary, never COMPONENT_REGISTRY.
    register_component(
        "NavBar",
        _dummy_render,
        props={"title": Prop(), "active": Prop(default=None)},
    )

    result = search_component("NavBar")

    assert result.startswith("NavBar")
    assert "No component named" not in result
    assert "user-defined component" in result
    assert "title" in result
    assert "active" in result


def test_search_user_component_lookup_is_case_insensitive():
    register_component("NavBar", _dummy_render)

    result = search_component("navbar")

    assert result.startswith("NavBar")
    assert "No component named" not in result


def test_search_builtin_wins_name_collision_over_user_component():
    # Same "built-ins always win" rule build_knowledge_base() already
    # applies -- a user component reusing a built-in's name must never
    # shadow the built-in's real schema facts here.
    register_component("Container", _dummy_render, props={"only_on_user_version": Prop()})

    result = search_component("Container")

    assert "user-defined component" not in result
    assert "only_on_user_version" not in result
    assert "(none)" in result  # Container's real, built-in required-props line


def test_search_unregistered_user_component_still_falls_back_to_suggestions():
    register_component("NavBar", _dummy_render)

    result = search_component("NavBarr")  # one letter off, not registered itself

    assert "No component named 'NavBarr' found" in result
    assert "NavBar" in result  # the registered component is a valid suggestion


def test_resolve_exact_covers_user_components_too():
    register_component("NavBar", _dummy_render)

    assert resolve_exact("NavBar") == "NavBar"
    assert resolve_exact("navbar") == "NavBar"
    assert resolve_exact("NotRegisteredAnywhere") is None
