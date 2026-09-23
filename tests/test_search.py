import pytest

from arklight.cli.search import resolve_exact, search_component
from arklight.ir.components import COMPONENT_REGISTRY, Prop, register_component
from arklight.ir.schema import SCHEMA
from arklight.search.engine import SearchEngineError


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


def test_search_unknown_near_raises_even_on_exact_match():
    # Regression: an exact match used to return immediately without
    # ever validating `near`, so `--near BogusName` silently did
    # nothing instead of the documented error whenever the query
    # itself happened to be a hit. `near` must now be validated
    # unconditionally, before the exact-match short circuit.
    with pytest.raises(SearchEngineError):
        search_component("Image", near="TotallyUnknownSymbol")


def test_search_unknown_near_raises_on_a_miss_too():
    # Same error, same message, on the miss path -- unchanged from
    # before this fix, kept here so both branches are covered
    # side-by-side.
    with pytest.raises(SearchEngineError):
        search_component("Butto", near="TotallyUnknownSymbol")


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
    # `allow_redefine=True`: registering a built-in's name is refused by
    # default now; this is the deliberate-override state the search
    # layer still has to stay correct for.
    register_component(
        "Container",
        _dummy_render,
        props={"only_on_user_version": Prop()},
        allow_redefine=True,
    )

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


def test_search_finds_action_by_bare_name():
    result = search_component("increment")
    assert result.startswith("Action.increment")
    assert "delta" in result
    assert "No component named" not in result


def test_search_finds_action_by_dotted_name_case_insensitively():
    result = search_component("ACTION.Increment")
    assert result.startswith("Action.increment")


def test_search_finds_action_with_no_args():
    result = search_component("toggle_bool")
    assert result.startswith("Action.toggle_bool")
    assert "(none)" in result


def test_search_finds_on_click_behavior():
    result = search_component("toggle")
    assert result.startswith("toggle")
    assert "on_click behavior" in result
    assert "toggle_class" in result


def test_search_finds_on_reveal_behavior_separately_from_on_click():
    result = search_component("reveal")
    assert result.startswith("reveal")
    assert "on_reveal behavior" in result


def test_search_finds_event_modifier_with_param():
    result = search_component("debounce")
    assert "event modifier" in result
    assert "takes a value  : yes" in result


def test_search_finds_event_modifier_without_param():
    result = search_component("prevent")
    assert "event modifier" in result
    assert "takes a value  : no" in result


def test_search_finds_derivation_by_dotted_name():
    result = search_component("Derive.sum")
    assert result.startswith("Derive.sum")
    assert "1+ names" in result


def test_search_finds_derivation_with_fixed_arity():
    result = search_component("compare")
    assert result.startswith("Derive.compare")
    assert "exactly 2 names" in result
    assert "op" in result


def test_search_finds_predicate_by_dotted_name():
    result = search_component("Predicate.truthy")
    assert result.startswith("Predicate.truthy")
    assert "exactly 1 name" in result


def test_search_component_vocabulary_still_wins_over_js_vocab_on_exact_match():
    # No real name collision exists between PascalCase components and
    # snake_case JS vocab, but the priority order (components first)
    # should still hold if that ever changes.
    result = search_component("Container")
    assert "event modifier" not in result
    assert "Action." not in result


def test_search_unknown_query_does_not_match_js_vocab_by_accident():
    result = search_component("incrementt")
    assert "No component named 'incrementt' found" in result


def test_search_finds_platform_api_by_bare_name():
    result = search_component("notify")
    assert result.startswith("PlatformAPI.notify")
    assert "title, body" in result
    assert "notifications" in result
    assert "No component named" not in result


def test_search_finds_platform_api_by_dotted_name_case_insensitively():
    result = search_component("PLATFORMAPI.Clipboard_Write")
    assert result.startswith("PlatformAPI.clipboard_write")
    assert "text" in result


def test_search_platform_api_reports_implementing_backend():
    result = search_component("notify")
    assert "implemented by : web" in result


def test_search_every_platform_api_registry_entry_is_reachable():
    from arklight.ir.platform_api import PLATFORM_API_REGISTRY

    for name in PLATFORM_API_REGISTRY:
        result = search_component(name)
        assert result.startswith(f"PlatformAPI.{name}")
        assert "No component named" not in result
