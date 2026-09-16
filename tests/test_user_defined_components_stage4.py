"""
v0.060, Stage 4: component-owned state.

Covers `arklight.api.component(..., state=...)` /
`_validate_component_state`, `arklight.ir.components`'s
`ComponentState`/`_namespaced_state_name`/`_hoist_component_state`/
`_rewrite_component_state_refs`, and the end-to-end path this all
exists for: a component declaring `state={...}` gets its own local,
instance-scoped reactive state -- `Bind(...)`/`on_click=Action.*(...)`/
`bind_class=Bind.when(...)`/`bind_value=Bind.model(...)` all work
exactly like they would against a page-level `State(...)`, and two
call sites of the same component never share one value. See
`docs/Foundational/USER-DEFINED-COMPONENTS-IMPLEMENTATION.md`'s Stage
4 row, and `tests/test_user_defined_components_stage0.py` through
`tests/test_user_defined_components_stage3.py` for the earlier stages
this mirrors the conventions of.
"""

from __future__ import annotations

import textwrap

import pytest

from arklight.api import (
    Action,
    Bind,
    Button,
    Container,
    Page,
    Predicate,
    Show,
    Text,
    component,
)
from arklight.backend.html.render import HTMLBackend
from arklight.compiler.pipeline import compile_site_file
from arklight.ir.components import (
    COMPONENT_REGISTRY,
    ComponentError,
    ComponentState,
    expand_ark_ast,
    expand_node,
    register_component,
)


@pytest.fixture(autouse=True)
def _clean_registry():
    """Same isolation fixture Stage 0-3's test files already use."""
    saved = dict(COMPONENT_REGISTRY)
    COMPONENT_REGISTRY.clear()
    yield
    COMPONENT_REGISTRY.clear()
    COMPONENT_REGISTRY.update(saved)


# ---------------------------------------------------------------------------
# `component(..., state=...)` registration + validation
# ---------------------------------------------------------------------------


def test_component_decorator_accepts_bare_initial_values():
    @component(state={"count": 0})
    def Counter():  # noqa: N802
        return Container(Text(Bind("count")))

    spec = COMPONENT_REGISTRY["Counter"]
    assert spec.state == {"count": ComponentState(initial=0)}


def test_component_decorator_accepts_explicit_component_state():
    @component(state={"count": ComponentState(initial=5, persist=True)})
    def Counter():  # noqa: N802
        return Container(Text(Bind("count")))

    spec = COMPONENT_REGISTRY["Counter"]
    assert spec.state == {"count": ComponentState(initial=5, persist=True)}


def test_component_without_state_is_unaffected():
    @component()
    def Widget():  # noqa: N802
        return Text("hi")

    assert COMPONENT_REGISTRY["Widget"].state == {}


def test_state_rejects_empty_dict():
    with pytest.raises(ValueError, match="non-empty dict"):

        @component(state={})
        def Bad():  # noqa: N802
            return Text("hi")


def test_state_rejects_non_string_name():
    with pytest.raises(ValueError, match="non-string or empty"):

        @component(state={"": 0})
        def Bad():  # noqa: N802
            return Text("hi")


def test_register_component_stores_state_directly():
    # Lower-level entry point (bypasses `component(...)`'s validation,
    # same "validation is `arklight.api`'s job, not the registry's"
    # division of labor earlier stages already established for
    # `props`/`default_style`).
    spec = register_component(
        "Counter", lambda: None, state={"count": ComponentState(initial=0)}
    )
    assert spec.state == {"count": ComponentState(initial=0)}


# ---------------------------------------------------------------------------
# Expansion: hoisting + reference rewriting
# ---------------------------------------------------------------------------


def _counter_component():
    @component(state={"count": ComponentState(initial=0)})
    def Counter():  # noqa: N802
        return Container(
            Text(Bind("count")),
            Button("+1", on_click=Action.increment("count")),
        )

    return Counter


def test_expansion_hoists_a_real_state_node_onto_the_page():
    Counter = _counter_component()
    expanded = expand_ark_ast({"/": Page(Counter())})["/"]
    state_children = [c for c in expanded.children if c.type == "State"]
    assert len(state_children) == 1
    assert state_children[0].props["initial"] == 0
    assert state_children[0].props["persist"] is False


def test_expansion_rewrites_bind_and_action_to_the_hoisted_name():
    Counter = _counter_component()
    expanded = expand_ark_ast({"/": Page(Counter())})["/"]
    state_name = next(c for c in expanded.children if c.type == "State").props["name"]

    rendered_root = expanded.children[0]
    text_node, button_node = rendered_root.children
    bind_node = text_node.children[0]
    assert bind_node.props["name"] == state_name
    assert button_node.props["on_click"].state == state_name
    # The namespaced name is never the bare local name a reader of the
    # component's own render function would recognize -- it always
    # carries the component's own name and an instance id along with it.
    assert state_name != "count"
    assert "Counter" in state_name


def test_two_instances_get_independent_namespaced_state():
    Counter = _counter_component()
    expanded = expand_ark_ast({"/": Page(Container(Counter(), Counter()))})["/"]
    state_children = [c for c in expanded.children if c.type == "State"]
    assert len(state_children) == 2
    names = {c.props["name"] for c in state_children}
    assert len(names) == 2  # no collision between the two instances

    outer = expanded.children[0]
    first_bind = outer.children[0].children[0].children[0]
    second_bind = outer.children[1].children[0].children[0]
    assert first_bind.props["name"] != second_bind.props["name"]
    assert first_bind.props["name"] in names
    assert second_bind.props["name"] in names


def test_persist_flows_through_to_the_hoisted_state_node():
    @component(state={"open": ComponentState(initial=False, persist=True)})
    def Accordion():  # noqa: N802
        return Container(
            Button("toggle", on_click=Action.toggle_bool("open")),
            Show(Predicate.truthy("open"), Text("body")),
        )

    expanded = expand_ark_ast({"/": Page(Accordion())})["/"]
    state_node = next(c for c in expanded.children if c.type == "State")
    assert state_node.props["initial"] is False
    assert state_node.props["persist"] is True


def test_bind_class_and_bind_value_are_rewritten():
    from arklight.api import Bind as BindHelper
    from arklight.api import Input

    @component(state={"query": ComponentState(initial="")})
    def Search():  # noqa: N802
        return Container(
            Input(bind_value=BindHelper.model("query")),
            Container(class_name="box", bind_class=BindHelper.when("query", "has-query")),
        )

    expanded = expand_ark_ast({"/": Page(Search())})["/"]
    state_name = next(c for c in expanded.children if c.type == "State").props["name"]
    root = expanded.children[0]
    input_node, box_node = root.children
    assert input_node.props["bind_value"] == state_name
    assert box_node.props["bind_class"].state == state_name


def test_props_passed_in_from_the_page_are_left_untouched():
    # A component may still *consume* a `Bind(...)`/`ActionRef` passed
    # in as an ordinary prop from a page-level `State(...)` -- that is
    # not this component's own local state, and must not be rewritten.
    @component(props=None, state={"count": ComponentState(initial=0)})
    def Counter():  # noqa: N802
        return Container(Text(Bind("count")))

    from arklight.api import State as PageState

    page = Page(
        PageState("total", 100),
        Container(Text(Bind("total"))),
        Counter(),
    )
    expanded = expand_ark_ast({"/": page})["/"]
    outer_bind = expanded.children[1].children[0].children[0]
    assert outer_bind.props["name"] == "total"


def test_nested_state_owning_components_both_get_hoisted():
    @component(state={"inner_count": ComponentState(initial=0)})
    def Inner():  # noqa: N802
        return Text(Bind("inner_count"))

    @component(state={"outer_count": ComponentState(initial=0)})
    def Outer():  # noqa: N802
        return Container(Text(Bind("outer_count")), Inner())

    expanded = expand_ark_ast({"/": Page(Outer())})["/"]
    state_children = [c for c in expanded.children if c.type == "State"]
    assert len(state_children) == 2


def test_bare_expand_node_without_hoisting_context_raises():
    Counter = _counter_component()
    with pytest.raises(ComponentError, match="declares its own state"):
        expand_node(Counter())


def test_component_without_state_survives_bare_expand_node():
    # Confirms Stage 4 is purely additive: a non-stateful component
    # behaves exactly as it did in Stage 0-3 with a bare expand_node()
    # call (no hoisted=/counter=).
    @component()
    def Plain():  # noqa: N802
        return Text("hi")

    expanded = expand_node(Page(Plain()))
    assert expanded.children[0].children == ["hi"]


def test_a_page_with_no_stateful_components_gets_no_extra_children():
    @component()
    def Plain():  # noqa: N802
        return Text("hi")

    page = Page(Plain())
    expanded = expand_ark_ast({"/": page})["/"]
    assert len(expanded.children) == 1


# ---------------------------------------------------------------------------
# End-to-end: compiled HTML output
# ---------------------------------------------------------------------------


def test_end_to_end_counter_component_renders_and_validates(tmp_path):
    site_dir = tmp_path / "site"
    site_dir.mkdir()
    (site_dir / "site.py").write_text(
        textwrap.dedent(
            """
            from arklight import *

            @component(state={"count": ComponentState(initial=0)})
            def Counter():
                return Container(
                    Text(Bind("count")),
                    Button("+1", on_click=Action.increment("count")),
                )

            site = Site()

            @site.page("/")
            def home():
                return Page(Counter())
            """
        )
    )

    ir = compile_site_file(site_dir / "site.py")
    page = ir.pages[0]
    assert len(page.state) == 1
    ((state_name, initial),) = page.state.items()
    assert initial == 0

    html = HTMLBackend().render(ir)["index.html"]
    assert f'data-ark-bind="{state_name}"' in html


def test_end_to_end_two_counters_are_independent(tmp_path):
    site_dir = tmp_path / "site"
    site_dir.mkdir()
    (site_dir / "site.py").write_text(
        textwrap.dedent(
            """
            from arklight import *

            @component(state={"count": ComponentState(initial=0)})
            def Counter():
                return Container(
                    Text(Bind("count")),
                    Button("+1", on_click=Action.increment("count")),
                )

            site = Site()

            @site.page("/")
            def home():
                return Page(Counter(), Counter())
            """
        )
    )

    ir = compile_site_file(site_dir / "site.py")
    page = ir.pages[0]
    assert len(page.state) == 2
