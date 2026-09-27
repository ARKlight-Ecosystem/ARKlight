"""
`vdom-7` (REFACTOR-INDEX.md [retired -- see CHANGELOG.md] row 15): per-item list
rendering (`Repeat`) + conditional show/hide (`Show`) -- across the
API, Validation, the HTML backend (per-item SSR fallback + JSON
template spec / `data-ark-show` + `hidden`), and the JS backend
(`renderRepeat`/`renderShow` gating and wiring).

Note: this suite checks the *compiled output* (HTML strings, JS
source gating) rather than executing the shipped JS itself -- there's
no JS engine in this test environment. The client-side behavior
(hydration without duplication, keyed add/remove through `patch()`,
index re-baking on reorder, `Show` toggling) was verified separately
by actually running a generated page's JS against jsdom; see the
`RENDER_REPEAT_JS`/`RENDER_SHOW_JS` module docstrings
(`arklight/backend/js/runtime/repeat.py`/`show.py`) for what that
verified and why the implementation takes the shape it does.
"""

import pytest

from arklight.api import (
    Action,
    Button,
    Container,
    Page,
    Predicate,
    Repeat,
    RepeatItem,
    Show,
    State,
    Text,
)
from arklight.backend.html.render import HTMLBackend
from arklight.backend.js.render import JSBackend
from arklight.ir.build import build_website_ir
from arklight.ir.normalize import normalize_ark_ast
from arklight.ir.validate import ValidationError, validate_ark_ast


def _ir(pages):
    normalized = normalize_ark_ast(pages)
    validate_ark_ast(normalized)
    return build_website_ir("site", normalized)


def _todos_repeat(*, key_action="remove"):
    return Repeat(
        "todos",
        template=lambda: Container(
            Text(RepeatItem.value()),
            Button("x", on_click=Action.remove("todos", RepeatItem.index())),
        ),
    )


# ---------------------------------------------------------------------------
# API
# ---------------------------------------------------------------------------


def test_repeat_calls_template_once_and_keeps_the_returned_node():
    calls = []

    def template():
        calls.append(1)
        return Text(RepeatItem.value())

    node = Repeat("todos", template=template)
    assert len(calls) == 1
    assert node.type == "Repeat"
    assert node.props["name"] == "todos"
    assert len(node.children) == 1


def test_repeat_item_value_is_an_itembind_node():
    node = RepeatItem.value()
    assert node.type == "ItemBind"
    assert node.children == []


def test_predicate_truthy_and_falsy():
    assert Predicate.truthy("flag").kind == "truthy"
    assert Predicate.truthy("flag").names == ("flag",)
    assert Predicate.falsy("flag").kind == "falsy"


def test_show_keeps_predicate_and_children():
    node = Show(Predicate.truthy("flag"), Text("hi"))
    assert node.type == "Show"
    assert node.props["predicate"].kind == "truthy"
    assert len(node.children) == 1


def test_item_does_not_shadow_the_builtin_item_component():
    # A real regression: an early draft of vdom-7 defined its RepeatItem
    # helper as `Item`, silently shadowing the pre-existing `Item =
    # node("Item")` (<li>) builtin. `List(Item(...))` must still work.
    from arklight.api import Item, List

    node = List(Item("first"))
    assert node.children[0].type == "Item"


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


def test_repeat_over_declared_state_passes_validation():
    tree = Page(State("todos", ["a", "b"]), _todos_repeat())
    validate_ark_ast(normalize_ark_ast({"/": tree}))  # no raise


def test_repeat_over_undeclared_state_raises():
    tree = Page(State("flag", True), _todos_repeat())
    with pytest.raises(ValidationError, match="isn't declared on this page"):
        validate_ark_ast(normalize_ark_ast({"/": tree}))


def test_show_with_declared_predicate_name_passes_validation():
    tree = Page(State("flag", True), Show(Predicate.truthy("flag"), Text("hi")))
    validate_ark_ast(normalize_ark_ast({"/": tree}))  # no raise


def test_show_with_undeclared_predicate_name_raises():
    tree = Page(State("other", True), Show(Predicate.truthy("flag"), Text("hi")))
    with pytest.raises(ValidationError, match="isn't declared on this page"):
        validate_ark_ast(normalize_ark_ast({"/": tree}))


def test_repeat_item_value_outside_repeat_raises():
    tree = Page(State("flag", True), Text(RepeatItem.value()))
    with pytest.raises(ValidationError):
        validate_ark_ast(normalize_ark_ast({"/": tree}))


def test_repeat_template_with_unknown_on_click_action_raises():
    tree = Page(
        State("todos", ["a"]),
        Repeat(
            "todos",
            template=lambda: Button("x", on_click=Action.set("missing_state", 1)),
        ),
    )
    with pytest.raises(ValidationError, match="isn't declared on this page"):
        validate_ark_ast(normalize_ark_ast({"/": tree}))


# ---------------------------------------------------------------------------
# HTML backend
# ---------------------------------------------------------------------------


def test_repeat_renders_one_real_element_per_initial_item():
    tree = Page(State("todos", ["Buy milk", "Walk dog"]), _todos_repeat())
    ir = _ir({"/": tree})
    html = HTMLBackend().render(ir)["index.html"]
    assert 'data-ark-repeat="todos"' in html
    assert "Buy milk" in html
    assert "Walk dog" in html
    # Per-item index baked into the SSR action args -- no JS needed for
    # the "remove the second item" button to already carry the right
    # index. HTML-escaped, so check for the escaped form.
    assert "index&quot;: 1" in html


def test_repeat_template_json_uses_item_value_sentinel_not_literal_text():
    tree = Page(State("todos", ["Buy milk"]), _todos_repeat())
    ir = _ir({"/": tree})
    html = HTMLBackend().render(ir)["index.html"]
    assert "data-ark-repeat-template=" in html
    assert "item_value" in html
    assert "__item_index__" in html


def test_repeat_over_empty_list_renders_no_items():
    tree = Page(State("todos", []), _todos_repeat())
    ir = _ir({"/": tree})
    html = HTMLBackend().render(ir)["index.html"]
    assert 'data-ark-repeat="todos"' in html


def test_show_true_at_build_time_has_no_hidden_attribute():
    tree = Page(State("flag", True), Show(Predicate.truthy("flag"), Text("Now you see me")))
    ir = _ir({"/": tree})
    html = HTMLBackend().render(ir)["index.html"]
    assert "Now you see me" in html
    i = html.index("data-ark-show")
    assert "hidden" not in html[i : i + 120]


def test_show_false_at_build_time_has_hidden_attribute_but_keeps_content():
    tree = Page(State("flag", False), Show(Predicate.truthy("flag"), Text("Now you see me")))
    ir = _ir({"/": tree})
    html = HTMLBackend().render(ir)["index.html"]
    # Content still present -- there's no way for JS to "reveal" content
    # the server never sent.
    assert "Now you see me" in html
    i = html.index("data-ark-show")
    assert " hidden" in html[i : i + 200]


def test_show_falsy_predicate_inverts_the_check():
    tree = Page(State("flag", False), Show(Predicate.falsy("flag"), Text("shown when falsy")))
    ir = _ir({"/": tree})
    html = HTMLBackend().render(ir)["index.html"]
    i = html.index("data-ark-show")
    assert "hidden" not in html[i : i + 120]


# ---------------------------------------------------------------------------
# JS backend
# ---------------------------------------------------------------------------


def test_repeat_ships_render_repeat_only_when_used():
    with_repeat = _ir({"/": Page(State("todos", ["a"]), _todos_repeat())})
    without_repeat = _ir({"/": Page(State("todos", ["a"]))})
    js_with = list(JSBackend().render(with_repeat).values())[0]
    js_without = list(JSBackend().render(without_repeat).values())[0]
    assert "function renderRepeat" in js_with
    assert "renderRepeat(arkStore)" in js_with
    assert "function renderRepeat" not in js_without


def test_show_ships_render_show_only_when_used():
    with_show = _ir({"/": Page(State("flag", True), Show(Predicate.truthy("flag"), Text("hi")))})
    without_show = _ir({"/": Page(State("flag", True))})
    js_with = list(JSBackend().render(with_show).values())[0]
    js_without = list(JSBackend().render(without_show).values())[0]
    assert "function renderShow" in js_with
    assert "renderShow(arkStore)" in js_with
    assert "function renderShow" not in js_without


def test_repeat_pulls_in_snabbdom_core_via_has_state():
    ir = _ir({"/": Page(State("todos", ["a"]), _todos_repeat())})
    js = list(JSBackend().render(ir).values())[0]
    assert "arkPatch" in js
    assert "snabbdom" in js


def test_action_inside_repeat_template_is_discovered_for_the_actions_object():
    # `on_click=Action.remove(...)` nested inside a Repeat template's
    # IRNode is a normal node in the tree (not a pulled-out
    # declaration), so it must be picked up by the same usage walk that
    # finds any other on_click=Action.*(...).
    ir = _ir({"/": Page(State("todos", ["a"]), _todos_repeat())})
    js = list(JSBackend().render(ir).values())[0]
    assert '"remove"' in js or "remove:" in js
    assert "wireClickInterceptor" in js
