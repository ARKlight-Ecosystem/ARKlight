"""
Capability fix: live-input -> action-value.

`Action.append("tasks", Bind("draft"))` / `Action.set("x", Bind("y"))`
-- an `Action.*(...)` argument that reads a `State(...)`/`Computed(...)`
when the action runs, instead of a compile-time literal. See
`docs/Proposals/ACTION-VALUE-FROM-STATE-PROPOSAL.md`,
`arklight.ast.nodes.STATE_REF_KEY` (wire shape),
`arklight.ir.validate._validate_action_args` (build-time rules),
`arklight/backend/js/runtime/action_args.py` (resolution).

Before this fix the same call passed Validation and then crashed the
HTML backend with a raw `TypeError: Object of type ARKNode is not JSON
serializable` (`test_bind_arg_no_longer_reaches_json_serialization_as_a_raw_node`
pins that).
"""

from __future__ import annotations

import json
import shutil
import subprocess

import pytest

from arklight.api import (
    Action,
    Bind,
    Button,
    Computed,
    Container,
    Derive,
    Input,
    Page,
    Repeat,
    RepeatItem,
    State,
    Text,
    Watch,
    component,
)
from arklight.ast.nodes import STATE_REF_KEY, ActionRef, ARKNode
from arklight.backend.html.render import HTMLBackend
from arklight.backend.js.render import JSBackend
from arklight.backend.js.runtime.dispatch import CLICK_INTERCEPTOR_JS
from arklight.backend.js.runtime.watch import WIRE_WATCHERS_JS
from arklight.cli.search import _format_action_spec
from arklight.ir.build import build_website_ir
from arklight.ir.components import COMPONENT_REGISTRY, ComponentState, expand_ark_ast
from arklight.ir.normalize import normalize_ark_ast
from arklight.ir.schema import ACTION_REGISTRY
from arklight.ir.validate import ValidationError, validate_ark_ast

NODE = shutil.which("node")


@pytest.fixture(autouse=True)
def _clean_component_registry():
    saved = dict(COMPONENT_REGISTRY)
    COMPONENT_REGISTRY.clear()
    yield
    COMPONENT_REGISTRY.clear()
    COMPONENT_REGISTRY.update(saved)


def _validate(tree):
    validate_ark_ast(normalize_ark_ast({"/": tree}))


def _ir(tree):
    normalized = normalize_ark_ast({"/": tree})
    validate_ark_ast(normalized)
    return build_website_ir("site", normalized)


def _html(tree) -> str:
    return HTMLBackend().render(_ir(tree))["index.html"]


def _add_task_page(**button_kwargs):
    return Page(
        State("draft", ""),
        State("tasks", []),
        Input(bind_value=Bind.model("draft")),
        Button("Add", on_click=Action.append("tasks", Bind("draft")), **button_kwargs),
    )


# ---------------------------------------------------------------------------
# API
# ---------------------------------------------------------------------------


def test_bind_as_append_value_builds_a_state_marker():
    ref = Action.append("tasks", Bind("draft"))
    assert ref.args == {"value": {STATE_REF_KEY: "draft"}}


def test_bind_as_set_value_builds_a_state_marker():
    assert Action.set("name", Bind("draft")).args == {"value": {STATE_REF_KEY: "draft"}}


def test_literal_arguments_are_untouched():
    assert Action.append("tasks", "milk").args == {"value": "milk"}
    assert Action.set("n", 5).args == {"value": 5}
    assert Action.increment("count").args == {"delta": 1}
    assert Action.remove("tasks", 0).args == {"index": 0}


def test_marker_is_a_plain_json_safe_dict_not_a_node():
    value = Action.append("tasks", Bind("draft")).args["value"]
    assert type(value) is dict
    assert json.loads(json.dumps(value)) == value


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


def test_bind_arg_from_declared_state_passes():
    _validate(_add_task_page())  # no raise


def test_bind_arg_may_read_a_computed():
    tree = Page(
        State("a", 1),
        State("b", 2),
        State("out", 0),
        Computed("total", deps=("a", "b"), derive=Derive.sum("a", "b")),
        Button("Save total", on_click=Action.set("out", Bind("total"))),
    )
    _validate(tree)  # no raise


def test_bind_arg_from_undeclared_state_raises():
    tree = Page(State("tasks", []), Button("Add", on_click=Action.append("tasks", Bind("nope"))))
    with pytest.raises(ValidationError, match=r"reads Bind\('nope'\).*isn't declared"):
        _validate(tree)


def test_error_lists_the_states_that_are_declared():
    tree = Page(State("tasks", []), Button("Add", on_click=Action.append("tasks", Bind("nope"))))
    with pytest.raises(ValidationError, match="tasks"):
        _validate(tree)


def test_bind_arg_target_must_still_be_mutable_state():
    # Reading a Computed is fine (above); *writing* one is still refused.
    tree = Page(
        State("a", 1),
        State("b", 2),
        Computed("total", deps=("a", "b"), derive=Derive.sum("a", "b")),
        Button("Go", on_click=Action.set("total", Bind("a"))),
    )
    with pytest.raises(ValidationError, match="targets state 'total'"):
        _validate(tree)


@pytest.mark.parametrize(
    "action",
    [
        Action.increment("n", Bind("step")),
        Action.decrement("n", Bind("step")),
        Action.remove("n", Bind("step")),
    ],
)
def test_arguments_that_cant_be_read_from_state_are_refused(action):
    tree = Page(State("n", 0), State("step", 1), Button("Go", on_click=action))
    with pytest.raises(ValidationError, match="can't be read from state"):
        _validate(tree)


def test_refusal_names_the_actions_that_do_accept_bind():
    tree = Page(State("n", 0), State("step", 1), Button("Go", on_click=Action.increment("n", Bind("step"))))
    with pytest.raises(ValidationError, match=r"append\(value\)"):
        _validate(tree)


def test_literal_dict_using_the_reserved_key_is_refused():
    bad = ActionRef(action="set", state="x", args={"value": {STATE_REF_KEY: "a", "extra": 1}})
    tree = Page(State("x", None), State("a", 1), Button("Go", on_click=bad))
    with pytest.raises(ValidationError, match="reserved key"):
        _validate(tree)


def test_marker_with_non_string_name_is_refused():
    bad = ActionRef(action="set", state="x", args={"value": {STATE_REF_KEY: 5}})
    tree = Page(State("x", None), Button("Go", on_click=bad))
    with pytest.raises(ValidationError, match="reserved key"):
        _validate(tree)


def test_bind_arg_no_longer_reaches_json_serialization_as_a_raw_node():
    # Regression for the original failure: an ActionRef built by hand
    # that still holds a Bind *node* used to pass Validation and blow
    # up later as `TypeError: ... ARKNode is not JSON serializable`.
    raw = ActionRef(action="append", state="tasks", args={"value": ARKNode(type="Bind", props={"name": "draft"}, children=[])})
    tree = Page(State("draft", ""), State("tasks", []), Button("Add", on_click=raw))
    with pytest.raises(ValidationError, match="Build the action with Action"):
        _validate(tree)


def test_watch_then_may_read_state():
    tree = Page(
        State("draft", ""),
        State("last", ""),
        Watch("draft", then=Action.set("last", Bind("draft"))),
    )
    _validate(tree)  # no raise


def test_watch_then_reading_undeclared_state_raises():
    tree = Page(State("last", ""), State("draft", ""), Watch("draft", then=Action.set("last", Bind("nope"))))
    with pytest.raises(ValidationError, match="isn't declared"):
        _validate(tree)


def test_repeat_template_action_may_read_state():
    tree = Page(
        State("draft", ""),
        State("tasks", []),
        Repeat("tasks", template=lambda: Button("copy", on_click=Action.set("draft", Bind("draft")))),
    )
    _validate(tree)  # no raise


def test_repeat_template_reading_undeclared_state_raises():
    tree = Page(
        State("draft", ""),
        State("tasks", []),
        Repeat("tasks", template=lambda: Button("copy", on_click=Action.set("draft", Bind("nope")))),
    )
    with pytest.raises(ValidationError, match="isn't declared"):
        _validate(tree)


def test_registry_opts_in_only_set_and_append_value():
    opted_in = {name: spec.state_args for name, spec in ACTION_REGISTRY.items() if spec.state_args}
    assert opted_in == {"set": ("value",), "append": ("value",)}


# ---------------------------------------------------------------------------
# Compilation
# ---------------------------------------------------------------------------


def test_html_button_carries_the_marker_in_its_action_args():
    html = _html(_add_task_page())
    assert "data-ark-action-args=" in html
    # HTML-escaped JSON: {"value": {"__state__": "draft"}}
    assert "&quot;__state__&quot;: &quot;draft&quot;" in html


def test_watch_blob_carries_the_marker():
    ir = _ir(
        Page(
            State("draft", ""),
            State("last", ""),
            Watch("draft", then=Action.set("last", Bind("draft"))),
        )
    )
    assert ir.pages[0].watch[0]["then"]["args"] == {"value": {STATE_REF_KEY: "draft"}}
    json.dumps(ir.pages[0].watch)  # serializable, no raw node anywhere


def test_repeat_template_spec_carries_the_marker_for_client_built_items():
    html = _html(
        Page(
            State("draft", ""),
            State("tasks", ["a"]),
            Repeat("tasks", template=lambda: Button(RepeatItem.value(), on_click=Action.set("draft", Bind("draft")))),
        )
    )
    assert "__state__" in html  # both the server-rendered item and the template spec


def test_js_runtime_ships_the_resolver_with_the_dispatchers():
    js = JSBackend().render(_ir(_add_task_page()))["arklight.js"]
    assert "resolveActionArgs" in js
    assert "resolveActionArgs(store, args)" in js


def test_arklight_binary_roundtrip_keeps_the_marker():
    from arklight.ir.binary import decode_arklight, decoded_site_to_website_ir, encode_arklight

    ir = _ir(_add_task_page())
    rebuilt = decoded_site_to_website_ir(decode_arklight(encode_arklight(ir)))
    button = next(n for n in _walk(rebuilt.pages[0].root) if n.type == "Button")
    assert button.props["on_click"].args == {"value": {STATE_REF_KEY: "draft"}}
    # ...and the rebuilt site still compiles to the same wiring.
    assert "&quot;__state__&quot;: &quot;draft&quot;" in HTMLBackend().render(rebuilt)["index.html"]


def _walk(node):
    yield node
    for child in node.children:
        if not isinstance(child, str):
            yield from _walk(child)


# ---------------------------------------------------------------------------
# Component-owned state
# ---------------------------------------------------------------------------


def test_component_local_state_read_in_an_action_arg_is_renamed_with_its_target():
    @component(state={"draft": ComponentState(initial=""), "items": ComponentState(initial=[])})
    def Adder():  # noqa: N802
        return Container(
            Input(bind_value=Bind.model("draft")),
            Button("Add", on_click=Action.append("items", Bind("draft"))),
        )

    expanded = expand_ark_ast({"/": Page(Adder())})["/"]
    names = {c.props["name"] for c in expanded.children if c.type == "State"}
    draft_key = next(n for n in names if n.endswith("draft"))
    button = next(n for n in _walk(expanded) if n.type == "Button")
    args = button.props["on_click"].args
    assert args["value"] == {STATE_REF_KEY: draft_key}  # renamed, not the bare "draft"
    assert draft_key != "draft"
    # And the whole page validates: the rewritten read resolves to the hoisted state.
    validate_ark_ast(normalize_ark_ast({"/": expanded}))


def test_component_arg_reading_a_page_level_state_is_left_alone():
    @component(state={"items": ComponentState(initial=[])})
    def Logger():  # noqa: N802
        return Button("Log", on_click=Action.append("items", Bind("page_wide")))

    expanded = expand_ark_ast({"/": Page(State("page_wide", ""), Logger())})["/"]
    button = next(n for n in _walk(expanded) if n.type == "Button")
    assert button.props["on_click"].args["value"] == {STATE_REF_KEY: "page_wide"}


# ---------------------------------------------------------------------------
# `arklight search`
# ---------------------------------------------------------------------------


def test_search_output_shows_which_args_take_bind():
    out = _format_action_spec("append", ACTION_REGISTRY["append"])
    assert "Bind(...) args" in out and "value" in out
    assert "Bind(...) args" not in _format_action_spec("increment", ACTION_REGISTRY["increment"])


# ---------------------------------------------------------------------------
# JS runtime (Node-driven, stubs only what the fragment itself needs)
# ---------------------------------------------------------------------------

needs_node = pytest.mark.skipif(not NODE, reason="node not available in this environment")


def _run_node(script: str) -> str:
    return subprocess.run([NODE, "-e", script], capture_output=True, text=True, check=True).stdout.strip()


_STORE_STUB = """
function arkNotify(msg) { throw new Error(msg); }
function createState(initial) {
  var state = Object.assign({}, initial);
  var listeners = [];
  return {
    get: function (key) { return state[key]; },
    set: function (key, value) { state[key] = value; listeners.forEach(function (fn) { fn(); }); },
    subscribe: function (fn) { listeners.push(fn); }
  };
}
var actions = {
  set: function (store, key, args) { store.set(key, args.value); },
  append: function (store, key, args) { store.set(key, (store.get(key) || []).concat([args.value])); }
};
"""


@needs_node
def test_node_watch_resolves_state_marker_at_dispatch_time_and_never_mutates_the_spec():
    script = f"""
    {_STORE_STUB}
    {WIRE_WATCHERS_JS}
    var store = createState({{ src: "a", log: [] }});
    var specs = [{{ name: "src", then: {{ action: "append", state: "log", args: {{ value: {{ "{STATE_REF_KEY}": "src" }} }} }} }}];
    wireWatchers(store, specs);
    store.set("src", "b");
    store.set("src", "c");
    console.log(JSON.stringify(store.get("log")));
    console.log(JSON.stringify(specs[0].then.args));
    """
    lines = _run_node(script).splitlines()
    # Each dispatch reads the value *then*; the second isn't stuck on the first.
    assert json.loads(lines[0]) == ["b", "c"]
    assert json.loads(lines[1]) == {"value": {STATE_REF_KEY: "src"}}


@needs_node
def test_node_click_interceptor_resolves_state_marker_and_leaves_literals_alone():
    script = f"""
    {_STORE_STUB}
    var behaviors = {{}}; var platformApis = {{}};
    var handlers = [];
    var document = {{ addEventListener: function (type, fn) {{ handlers.push(fn); }} }};
    {CLICK_INTERCEPTOR_JS}
    var store = createState({{ draft: "buy milk", tasks: [], tag: "" }});
    wireClickInterceptor(function () {{ return store; }});
    function click(actionName, stateKey, args) {{
      var attrs = {{
        "data-ark-on-click": "action:" + actionName,
        "data-ark-action-state": stateKey,
        "data-ark-action-args": JSON.stringify(args)
      }};
      var el = {{ getAttribute: function (n) {{ return n in attrs ? attrs[n] : null; }} }};
      handlers[0]({{ target: {{ closest: function () {{ return el; }} }}, preventDefault: function () {{}}, stopPropagation: function () {{}} }});
    }}
    click("append", "tasks", {{ value: {{ "{STATE_REF_KEY}": "draft" }} }});
    store.set("draft", "walk dog");
    click("append", "tasks", {{ value: {{ "{STATE_REF_KEY}": "draft" }} }});
    click("append", "tasks", {{ value: "literal" }});
    click("set", "tag", {{ value: {{ nested: true }} }});
    console.log(JSON.stringify(store.get("tasks")));
    console.log(JSON.stringify(store.get("tag")));
    """
    lines = _run_node(script).splitlines()
    assert json.loads(lines[0]) == ["buy milk", "walk dog", "literal"]
    assert json.loads(lines[1]) == {"nested": True}  # plain objects without the marker pass through
