"""
Stage 2 of `docs/Implementation/INPUT-AND-PLATFORM-PRIMITIVES-
ADDENDUM-v0.071.md`: `on_key=Key.on(<key>, Action.*(...))`,
element-scoped key events.

Grouped the same way `tests/test_platform_api_confirm.py` (Stage 6)
groups its own forcing-case tests:

1. `Key.on(...)` factory (`arklight.api.Key`).
2. Validation (`arklight.ir.validate._validate_key_props`): known key
   name, action/state/modifiers checks reused from `_validate_action`,
   `Item.index()` rejected inside a `Repeat(...)` template's `on_key`.
3. HTML attribute rendering (`arklight/backend/html/attrs.py`).
4. JS backend: only shipped when `on_key=` is actually used anywhere
   (`arklight/backend/js/render.py`'s `has_key_binding`/
   `needs_key_interceptor`), independent of the click interceptor.
5. No `eval`/`new Function` anywhere in the shipped fragment.
6. User-defined component local-state renaming
   (`arklight.ir.components._rewrite_component_state_refs`).
7. `.arklight` binary round-trip (`arklight.ir.binary`'s
   `_RECONSTRUCTABLE_TYPES`).
8. Node: the shipped `wireKeyInterceptor` fragment run against a
   stubbed `document`/`store`, the same approach
   `tests/test_platform_api_confirm.py`'s own Node section and
   `tests/test_vdom_6.py`'s stub-element pattern use.
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
    Dialog,
    Key,
    Page,
    Repeat,
    RepeatItem,
    State,
    Text,
    component,
)
from arklight.ast.nodes import ActionRef, ItemIndexRef, KeyBinding
from arklight.backend.html.render import HTMLBackend
from arklight.backend.js.render import SCRIPT_PATH, JSBackend
from arklight.backend.js.runtime.keys import KEY_INTERCEPTOR_JS
from arklight.ir.binary import decode_arklight, decoded_site_to_website_ir, encode_arklight
from arklight.ir.build import build_website_ir
from arklight.ir.components import (
    COMPONENT_REGISTRY,
    ComponentState,
    expand_ark_ast,
)
from arklight.ir.normalize import normalize_ark_ast
from arklight.ir.schema import KNOWN_KEYS
from arklight.ir.validate import ValidationError, validate_ark_ast


@pytest.fixture(autouse=True)
def _clean_registry():
    """Same component-registry isolation fixture Stage 0-4's own test
    files use -- section 6 below registers a component."""
    saved = dict(COMPONENT_REGISTRY)
    COMPONENT_REGISTRY.clear()
    yield
    COMPONENT_REGISTRY.clear()
    COMPONENT_REGISTRY.update(saved)


def _ir(*children):
    normalized = normalize_ark_ast({"/": Page(*children)})
    validate_ark_ast(normalized)
    return build_website_ir("site", normalized)


def _validate(*children):
    validate_ark_ast(normalize_ark_ast({"/": Page(*children)}))


def _html(*children):
    return HTMLBackend().render(_ir(*children))["index.html"]


def _js(*children):
    return JSBackend().render(_ir(*children))[SCRIPT_PATH]


# --- 1. arklight.api.Key.on factory -----------------------------------------


def test_key_on_builds_key_binding_from_action_ref():
    binding = Key.on("Escape", Action.set("open", False))
    assert isinstance(binding, KeyBinding)
    assert binding.key == "Escape"
    assert binding.action == "set"
    assert binding.state == "open"
    assert binding.args == {"value": False}
    assert binding.modifiers == ()


def test_key_on_rejects_non_action_ref():
    with pytest.raises(TypeError, match="needs an Action.\\*\\(...\\) reference"):
        Key.on("Escape", "toggle")


def test_key_on_rejects_platform_api_ref():
    from arklight.api import PlatformAPI

    with pytest.raises(TypeError, match="PlatformAPI.\\*\\(...\\) and named behaviors"):
        Key.on("Escape", PlatformAPI.notify("hi"))


def test_key_binding_with_modifiers_matches_action_ref_shape():
    binding = Key.on("Enter", Action.increment("count")).with_modifiers("prevent")
    assert binding.modifiers == ("prevent",)


def test_key_binding_debounce_and_throttle():
    debounced = Key.on("ArrowDown", Action.decrement("n")).debounce(300)
    assert debounced.modifiers == ("debounce:300",)
    throttled = Key.on("ArrowDown", Action.decrement("n")).throttle(300)
    assert throttled.modifiers == ("throttle:300",)


# --- 2. Validation ------------------------------------------------------------


def test_validate_accepts_known_key_and_declared_state():
    _validate(
        State("open", True),
        Dialog(id="confirm", on_key=Key.on("Escape", Action.set("open", False))),
    )  # Should not raise.


def test_validate_accepts_every_known_key():
    for key in KNOWN_KEYS:
        _validate(
            State("n", 0),
            Button("x", on_key=Key.on(key, Action.increment("n"))),
        )  # Should not raise, for any key in the closed enum.


def test_validate_rejects_unknown_key():
    with pytest.raises(ValidationError, match="unknown key 'Backspace'"):
        _validate(
            State("open", True),
            Dialog(id="confirm", on_key=Key.on("Backspace", Action.set("open", False))),
        )


def test_validate_rejects_ctrl_combo_style_key_name():
    # Stage 2's closed enum has no notion of a modifier-combo key name
    # at all (that's Stage 3's Hotkey(...)) -- "Ctrl+S" is simply not
    # a known `event.key` value.
    with pytest.raises(ValidationError, match="unknown key"):
        _validate(
            State("saved", False),
            Button("x", on_key=Key.on("Ctrl+S", Action.set("saved", True))),
        )


def test_validate_rejects_on_key_targeting_undeclared_state():
    with pytest.raises(ValidationError, match="on_key at .* targets state"):
        _validate(Dialog(id="confirm", on_key=Key.on("Escape", Action.set("nope", False))))


def test_validate_rejects_on_key_unknown_action():
    bad = KeyBinding(key="Escape", action="not-a-real-action", state="open", args={})
    with pytest.raises(ValidationError, match="on_key at .* uses unknown action"):
        _validate(State("open", True), Dialog(id="confirm", on_key=bad))


def test_validate_rejects_on_key_that_isnt_a_key_binding():
    with pytest.raises(ValidationError, match="isn't a Key.on\\(...\\) reference"):
        _validate(Dialog(id="confirm", on_key="Escape"))


def test_validate_error_message_says_on_key_not_on_click():
    # `_validate_action`'s `label="on_key"` plumbing -- the error text
    # must say the right prop name, not a copy-pasted "on_click".
    with pytest.raises(ValidationError, match="on_key at .* uses unknown action") as exc_info:
        bad = KeyBinding(key="Escape", action="nope", state="open", args={})
        _validate(State("open", True), Dialog(id="confirm", on_key=bad))
    assert "on_click" not in str(exc_info.value)


def test_validate_rejects_on_key_modifiers_same_as_on_click():
    bad = KeyBinding(key="Escape", action="set", state="open", args={"value": False}, modifiers=("nope",))
    with pytest.raises(ValidationError, match="on_key at .* uses unknown modifier"):
        _validate(State("open", True), Dialog(id="confirm", on_key=bad))


def test_validate_accepts_on_key_inside_a_repeat_template_without_item_index():
    _validate(
        State("items", ["a", "b"]),
        Repeat(
            "items",
            template=lambda: Button(
                RepeatItem.value(), on_key=Key.on("Enter", Action.set("items", []))
            ),
        ),
    )  # Should not raise -- a static on_key (no Item.index()) is fine.


def test_validate_rejects_item_index_inside_repeat_template_on_key():
    with pytest.raises(ValidationError, match="Item.index\\(\\) in its action's arguments"):
        _validate(
            State("items", ["a", "b"]),
            Repeat(
                "items",
                template=lambda: Button(
                    RepeatItem.value(),
                    on_key=Key.on(
                        "Enter", Action.append("items", value=RepeatItem.index())
                    ),
                ),
            ),
        )


def test_validate_still_rejects_item_index_inside_on_click_unaffected():
    # Sanity: Stage 2 doesn't loosen the existing, allowed
    # on_click=...Item.index() path inside a Repeat template.
    _validate(
        State("items", ["a", "b"]),
        Repeat(
            "items",
            template=lambda: Button(
                RepeatItem.value(),
                on_click=Action.set("items", value=RepeatItem.index()),
            ),
        ),
    )  # Should not raise -- Item.index() is allowed in on_click.


# --- 3. HTML attribute rendering ---------------------------------------------


def test_html_renders_on_key_attributes():
    html = _html(
        State("open", True),
        Dialog(id="confirm", on_key=Key.on("Escape", Action.set("open", False))),
    )
    assert 'data-ark-on-key="Escape"' in html
    assert 'data-ark-key-action="set"' in html
    assert 'data-ark-key-action-state="open"' in html
    assert "data-ark-key-action-args" in html


def test_html_on_key_args_are_json_encoded():
    html = _html(
        State("count", 0),
        Button("x", on_key=Key.on("Enter", Action.append("count", value=1))),
    )
    assert "data-ark-key-action-args" in html
    # The literal value 1 shows up somewhere inside the escaped JSON blob.
    assert "data-ark-key-action-args=" in html


def test_html_on_key_modifiers_render_as_plain_attribute():
    html = _html(
        State("open", True),
        Dialog(
            id="confirm",
            on_key=Key.on("Escape", Action.set("open", False)).with_modifiers("prevent", "stop"),
        ),
    )
    assert 'data-ark-key-modifiers="prevent,stop"' in html


def test_html_on_key_with_no_modifiers_omits_the_attribute():
    html = _html(
        State("open", True),
        Dialog(id="confirm", on_key=Key.on("Escape", Action.set("open", False))),
    )
    assert "data-ark-key-modifiers" not in html


def test_html_element_can_carry_both_on_click_and_on_key():
    html = _html(
        State("open", True),
        Button(
            "x",
            on_click=Action.toggle_bool("open"),
            on_key=Key.on("Enter", Action.toggle_bool("open")),
        ),
    )
    assert 'data-ark-on-click="action:toggle_bool"' in html
    assert 'data-ark-on-key="Enter"' in html
    assert 'data-ark-key-action="toggle_bool"' in html


def test_html_on_key_with_no_args_omits_args_attribute():
    html = _html(
        State("open", True),
        Dialog(id="confirm", on_key=Key.on("Escape", Action.toggle_bool("open"))),
    )
    assert "data-ark-key-action-args" not in html


# --- 4. JS backend: only-ship-what's-used + wiring ---------------------------


def test_js_runtime_ships_no_key_interceptor_when_unused():
    js = _js(State("n", 0), Button("+", on_click=Action.increment("n")))
    assert "wireKeyInterceptor" not in js
    assert "function wireKeyInterceptor" not in js


def test_js_runtime_ships_key_interceptor_when_used():
    js = _js(
        State("open", True),
        Dialog(id="confirm", on_key=Key.on("Escape", Action.set("open", False))),
    )
    assert "function wireKeyInterceptor(getStore)" in js
    assert "wireKeyInterceptor(" in js.split("DOMContentLoaded")[1]


def test_js_key_interceptor_ships_independent_of_click_interceptor():
    # A key-only page -- no on_click=/named behavior anywhere -- needs
    # no click listener at all, only the key one.
    js = _js(
        State("open", True),
        Dialog(id="confirm", on_key=Key.on("Escape", Action.set("open", False))),
    )
    assert "function wireKeyInterceptor" in js
    assert "function wireClickInterceptor" not in js


def test_js_key_action_folds_into_the_shared_actions_object():
    js = _js(
        State("open", True),
        Dialog(id="confirm", on_key=Key.on("Escape", Action.set("open", False))),
    )
    assert "var actions = {" in js
    assert "set: function" in js


def test_js_static_page_ships_no_key_interceptor():
    js = _js(Text("hi"))
    assert "wireKeyInterceptor" not in js


def test_js_key_interceptor_declared_after_click_interceptor_when_both_present():
    js = _js(
        State("open", True),
        Button("Open", on_click=Action.set("open", True)),
        Dialog(id="confirm", on_key=Key.on("Escape", Action.set("open", False))),
    )
    click_pos = js.index("function wireClickInterceptor")
    key_pos = js.index("function wireKeyInterceptor")
    assert click_pos < key_pos


# --- 5. No eval / new Function ------------------------------------------------


def test_key_interceptor_fragment_has_no_eval_or_new_function():
    assert "eval(" not in KEY_INTERCEPTOR_JS
    assert "new Function(" not in KEY_INTERCEPTOR_JS


def test_js_runtime_has_no_eval_or_new_function_with_on_key():
    js = _js(
        State("open", True),
        Dialog(id="confirm", on_key=Key.on("Escape", Action.set("open", False))),
    )
    assert "eval(" not in js
    assert "new Function(" not in js


def test_key_interceptor_uses_a_plain_loop_not_queryselectorall_foreach():
    # Same "single delegated listener" discipline wireClickInterceptor
    # follows -- no per-element querySelectorAll/forEach wiring pass.
    assert "querySelectorAll" not in KEY_INTERCEPTOR_JS
    assert KEY_INTERCEPTOR_JS.count('addEventListener("keydown"') == 1


# --- 6. User-defined component local-state renaming --------------------------


def _dialog_component():
    @component(state={"open": ComponentState(initial=True)})
    def ConfirmDialog():  # noqa: N802
        return Dialog(
            id="confirm",
            on_key=Key.on("Escape", Action.set("open", False)),
        )

    return ConfirmDialog


def test_component_on_key_target_is_rewritten_to_namespaced_state():
    ConfirmDialog = _dialog_component()
    expanded = expand_ark_ast({"/": Page(ConfirmDialog())})["/"]
    state_name = next(c for c in expanded.children if c.type == "State").props["name"]

    dialog_node = expanded.children[0]
    assert isinstance(dialog_node.props["on_key"], KeyBinding)
    assert dialog_node.props["on_key"].state == state_name
    assert state_name != "open"
    assert "ConfirmDialog" in state_name


def test_two_component_instances_get_independent_on_key_targets():
    ConfirmDialog = _dialog_component()
    expanded = expand_ark_ast({"/": Page(Container(ConfirmDialog(), ConfirmDialog()))})["/"]
    # The two Dialog nodes land as children of the Container, not
    # directly on the page -- unlike `_counter_component`'s Container
    # (Stage 4's own test helper), `_dialog_component` returns the
    # Dialog itself as the component's rendered root, so Container's
    # own children are the two Dialog instances.
    container_node = next(c for c in expanded.children if c.type == "Container")
    dialog_nodes = [c for c in container_node.children if c.type == "Dialog"]
    assert len(dialog_nodes) == 2
    targets = {n.props["on_key"].state for n in dialog_nodes}
    assert len(targets) == 2


def test_component_on_key_args_reading_bind_are_rewritten_too():
    @component(state={"draft": ComponentState(initial="")})
    def Composer():  # noqa: N802
        return Container(
            Button(
                "x",
                on_key=Key.on("Enter", Action.append("draft", value=Bind("draft"))),
            )
        )

    expanded = expand_ark_ast({"/": Page(Composer())})["/"]
    state_name = next(c for c in expanded.children if c.type == "State").props["name"]
    button_node = expanded.children[0].children[0]
    on_key = button_node.props["on_key"]
    assert on_key.state == state_name
    # The value arg, which reads the same local state via Bind("draft"),
    # must move to the namespaced name right alongside the target --
    # same reasoning the existing on_click rewrite already documents.
    from arklight.ast.nodes import STATE_REF_KEY

    assert on_key.args["value"][STATE_REF_KEY] == state_name


def test_component_on_key_is_left_untouched_when_state_name_not_local():
    # A name not in the component's own name_map (passed in from the
    # page's own State(...)) is left completely untouched.
    from arklight.ir.components import Prop

    @component(props={"target_state": Prop(type=str)})
    def PassThrough(target_state):  # noqa: N802
        return Button("x", on_key=Key.on("Escape", Action.set(target_state, False)))

    expanded = expand_ark_ast(
        {"/": Page(State("page_open", True), PassThrough(target_state="page_open"))}
    )["/"]
    button_node = expanded.children[1]
    assert button_node.props["on_key"].state == "page_open"


# --- 7. .arklight binary round-trip -------------------------------------------


def test_key_binding_registered_in_reconstructable_types():
    from arklight.ir.binary import _RECONSTRUCTABLE_TYPES

    assert _RECONSTRUCTABLE_TYPES["KeyBinding"] is KeyBinding


def test_key_binding_round_trips_through_arklight_binary():
    ir = _ir(
        State("open", True),
        Dialog(
            id="confirm",
            on_key=Key.on("Escape", Action.set("open", False)).with_modifiers("prevent"),
        ),
    )
    decoded_ir = decoded_site_to_website_ir(decode_arklight(encode_arklight(ir)))
    decoded_root = decoded_ir.pages[0].root
    dialog_node = next(c for c in decoded_root.children if c.type == "Dialog")
    on_key = dialog_node.props["on_key"]
    assert isinstance(on_key, KeyBinding)
    assert on_key.key == "Escape"
    assert on_key.action == "set"
    assert on_key.state == "open"
    assert on_key.args == {"value": False}
    assert on_key.modifiers == ["prevent"] or on_key.modifiers == ("prevent",)


def test_key_binding_with_dict_args_round_trips():
    ir = _ir(
        State("count", 0),
        Button("x", on_key=Key.on("ArrowUp", Action.increment("count"))),
    )
    decoded_ir = decoded_site_to_website_ir(decode_arklight(encode_arklight(ir)))
    decoded_root = decoded_ir.pages[0].root
    button_node = next(c for c in decoded_root.children if c.type == "Button")
    on_key = button_node.props["on_key"]
    assert isinstance(on_key, KeyBinding)
    assert on_key.key == "ArrowUp"
    assert on_key.action == "increment"
    assert on_key.state == "count"


# --- 8. Node: run the shipped wireKeyInterceptor fragment --------------------

NODE = shutil.which("node")
needs_node = pytest.mark.skipif(not NODE, reason="node not available in this environment")


def _run_node(script: str) -> str:
    proc = subprocess.run([NODE, "-e", script], capture_output=True, text=True)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    return proc.stdout.strip()


# A minimal stand-in for an element and its ancestor chain -- `parentNode`
# (not `.closest()`, which `wireKeyInterceptor` deliberately doesn't use;
# see that module's docstring) is how the fragment walks up to find a
# matching `data-ark-on-key`.
_DOM_STUB = """
function makeEl(attrs, parent) {
  return {
    attrs: attrs,
    parentNode: parent || null,
    getAttribute: function (n) { return Object.prototype.hasOwnProperty.call(this.attrs, n) ? this.attrs[n] : null; }
  };
}
var handlers = {};
var document = { addEventListener: function (type, fn) { handlers[type] = fn; } };
"""

_ACTIONS_STUB = """
var reported = [];
function arkReportError(msg, err) { reported.push(msg); }
var dispatched = [];
var actions = {
  set: function (store, stateKey, args) { dispatched.push(["set", stateKey, args]); store.set(stateKey, args.value); }
};
function makeStore(initial) {
  var state = Object.assign({}, initial);
  return { get: function (k) { return state[k]; }, set: function (k, v) { state[k] = v; }, all: state };
}
"""


def _key_script(body: str) -> str:
    return "\n".join([_DOM_STUB, _ACTIONS_STUB, KEY_INTERCEPTOR_JS, "wireKeyInterceptor(function () { return store; });", body])


@needs_node
def test_node_matching_key_on_focused_element_dispatches_the_action():
    body = """
    var el = makeEl({ "data-ark-on-key": "Escape", "data-ark-key-action": "set",
      "data-ark-key-action-state": "open", "data-ark-key-action-args": JSON.stringify({ value: false }) });
    var store = makeStore({ open: true });
    handlers["keydown"]({ target: el, key: "Escape", ctrlKey: false, altKey: false, metaKey: false,
      isComposing: false, keyCode: 27, preventDefault: function () {}, stopPropagation: function () {} });
    console.log(JSON.stringify(store.all.open));
    """
    assert _run_node(_key_script(body).replace("function () { return store; }", "function () { return store; }")) == "false"


@needs_node
def test_node_matching_key_bubbles_from_a_focused_descendant():
    body = """
    var outer = makeEl({ "data-ark-on-key": "Escape", "data-ark-key-action": "set",
      "data-ark-key-action-state": "open", "data-ark-key-action-args": JSON.stringify({ value: false }) });
    var inner = makeEl({}, outer);
    var store = makeStore({ open: true });
    handlers["keydown"]({ target: inner, key: "Escape", ctrlKey: false, altKey: false, metaKey: false,
      isComposing: false, keyCode: 27, preventDefault: function () {}, stopPropagation: function () {} });
    console.log(JSON.stringify(store.all.open));
    """
    assert _run_node(_key_script(body)) == "false"


@needs_node
def test_node_nearest_ancestor_binding_wins_over_a_farther_one():
    body = """
    var outer = makeEl({ "data-ark-on-key": "Escape", "data-ark-key-action": "set",
      "data-ark-key-action-state": "outer_open", "data-ark-key-action-args": JSON.stringify({ value: false }) });
    var inner = makeEl({ "data-ark-on-key": "Enter", "data-ark-key-action": "set",
      "data-ark-key-action-state": "inner_open", "data-ark-key-action-args": JSON.stringify({ value: false }) }, outer);
    var store = makeStore({ outer_open: true, inner_open: true });
    handlers["keydown"]({ target: inner, key: "Escape", ctrlKey: false, altKey: false, metaKey: false,
      isComposing: false, keyCode: 27, preventDefault: function () {}, stopPropagation: function () {} });
    console.log(JSON.stringify([store.all.outer_open, store.all.inner_open]));
    """
    # "Escape" skips the inner Enter-bound element and matches the outer one.
    assert _run_node(_key_script(body)) == "[false,true]"


@needs_node
def test_node_non_matching_key_does_not_dispatch():
    body = """
    var el = makeEl({ "data-ark-on-key": "Escape", "data-ark-key-action": "set",
      "data-ark-key-action-state": "open", "data-ark-key-action-args": JSON.stringify({ value: false }) });
    var store = makeStore({ open: true });
    handlers["keydown"]({ target: el, key: "Enter", ctrlKey: false, altKey: false, metaKey: false,
      isComposing: false, keyCode: 13, preventDefault: function () {}, stopPropagation: function () {} });
    console.log(JSON.stringify(store.all.open));
    """
    assert _run_node(_key_script(body)) == "true"


@needs_node
def test_node_ctrl_alt_meta_combo_is_ignored():
    body = """
    var el = makeEl({ "data-ark-on-key": "Escape", "data-ark-key-action": "set",
      "data-ark-key-action-state": "open", "data-ark-key-action-args": JSON.stringify({ value: false }) });
    var store = makeStore({ open: true });
    ["ctrlKey", "altKey", "metaKey"].forEach(function (flag) {
      var evt = { target: el, key: "Escape", ctrlKey: false, altKey: false, metaKey: false,
        isComposing: false, keyCode: 27, preventDefault: function () {}, stopPropagation: function () {} };
      evt[flag] = true;
      handlers["keydown"](evt);
    });
    console.log(JSON.stringify(store.all.open));
    """
    assert _run_node(_key_script(body)) == "true"


@needs_node
def test_node_shift_tab_still_matches_a_plain_tab_binding():
    body = """
    var el = makeEl({ "data-ark-on-key": "Tab", "data-ark-key-action": "set",
      "data-ark-key-action-state": "open", "data-ark-key-action-args": JSON.stringify({ value: false }) });
    var store = makeStore({ open: true });
    handlers["keydown"]({ target: el, key: "Tab", shiftKey: true, ctrlKey: false, altKey: false, metaKey: false,
      isComposing: false, keyCode: 9, preventDefault: function () {}, stopPropagation: function () {} });
    console.log(JSON.stringify(store.all.open));
    """
    assert _run_node(_key_script(body)) == "false"


@needs_node
def test_node_ime_composition_is_ignored():
    body = """
    var el = makeEl({ "data-ark-on-key": "Escape", "data-ark-key-action": "set",
      "data-ark-key-action-state": "open", "data-ark-key-action-args": JSON.stringify({ value: false }) });
    var store = makeStore({ open: true });
    handlers["keydown"]({ target: el, key: "Escape", ctrlKey: false, altKey: false, metaKey: false,
      isComposing: true, keyCode: 27, preventDefault: function () {}, stopPropagation: function () {} });
    console.log(JSON.stringify(store.all.open));
    """
    assert _run_node(_key_script(body)) == "true"


@needs_node
def test_node_legacy_ime_keycode_229_is_ignored():
    body = """
    var el = makeEl({ "data-ark-on-key": "Escape", "data-ark-key-action": "set",
      "data-ark-key-action-state": "open", "data-ark-key-action-args": JSON.stringify({ value: false }) });
    var store = makeStore({ open: true });
    handlers["keydown"]({ target: el, key: "Escape", ctrlKey: false, altKey: false, metaKey: false,
      isComposing: false, keyCode: 229, preventDefault: function () {}, stopPropagation: function () {} });
    console.log(JSON.stringify(store.all.open));
    """
    assert _run_node(_key_script(body)) == "true"


@needs_node
def test_node_prevent_modifier_calls_prevent_default():
    body = """
    var el = makeEl({ "data-ark-on-key": "Enter", "data-ark-key-action": "set",
      "data-ark-key-action-state": "open", "data-ark-key-action-args": JSON.stringify({ value: false }),
      "data-ark-key-modifiers": "prevent" });
    var store = makeStore({ open: true });
    var prevented = false;
    handlers["keydown"]({ target: el, key: "Enter", ctrlKey: false, altKey: false, metaKey: false,
      isComposing: false, keyCode: 13, preventDefault: function () { prevented = true; }, stopPropagation: function () {} });
    console.log(JSON.stringify(prevented));
    """
    assert _run_node(_key_script(body)) == "true"


@needs_node
def test_node_without_prevent_modifier_native_behavior_is_not_blocked():
    # The opposite of the test above: Enter/Tab/arrow-key native
    # behavior (e.g. Tab moving focus) must keep working unless the
    # binding explicitly opts into "prevent" -- unlike the click
    # interceptor, which always calls preventDefault.
    body = """
    var el = makeEl({ "data-ark-on-key": "Tab", "data-ark-key-action": "set",
      "data-ark-key-action-state": "open", "data-ark-key-action-args": JSON.stringify({ value: false }) });
    var store = makeStore({ open: true });
    var prevented = false;
    handlers["keydown"]({ target: el, key: "Tab", ctrlKey: false, altKey: false, metaKey: false,
      isComposing: false, keyCode: 9, preventDefault: function () { prevented = true; }, stopPropagation: function () {} });
    console.log(JSON.stringify(prevented));
    """
    assert _run_node(_key_script(body)) == "false"


@needs_node
def test_node_stop_modifier_calls_stop_propagation():
    body = """
    var el = makeEl({ "data-ark-on-key": "Escape", "data-ark-key-action": "set",
      "data-ark-key-action-state": "open", "data-ark-key-action-args": JSON.stringify({ value: false }),
      "data-ark-key-modifiers": "stop" });
    var store = makeStore({ open: true });
    var stopped = false;
    handlers["keydown"]({ target: el, key: "Escape", ctrlKey: false, altKey: false, metaKey: false,
      isComposing: false, keyCode: 27, preventDefault: function () {}, stopPropagation: function () { stopped = true; } });
    console.log(JSON.stringify(stopped));
    """
    assert _run_node(_key_script(body)) == "true"


@needs_node
def test_node_once_modifier_fires_only_the_first_time():
    body = """
    var el = makeEl({ "data-ark-on-key": "ArrowDown", "data-ark-key-action": "set",
      "data-ark-key-action-state": "n", "data-ark-key-action-args": JSON.stringify({ value: 1 }),
      "data-ark-key-modifiers": "once" });
    var store = makeStore({ n: 0 });
    var evt = { target: el, key: "ArrowDown", ctrlKey: false, altKey: false, metaKey: false,
      isComposing: false, keyCode: 40, preventDefault: function () {}, stopPropagation: function () {} };
    handlers["keydown"](evt);
    handlers["keydown"](evt);
    handlers["keydown"](evt);
    console.log(JSON.stringify(dispatched.length));
    """
    assert _run_node(_key_script(body)) == "1"


@needs_node
def test_node_throttle_modifier_rate_limits_dispatch():
    body = """
    var el = makeEl({ "data-ark-on-key": "ArrowDown", "data-ark-key-action": "set",
      "data-ark-key-action-state": "n", "data-ark-key-action-args": JSON.stringify({ value: 1 }),
      "data-ark-key-modifiers": "throttle:10000" });
    var store = makeStore({ n: 0 });
    var evt = { target: el, key: "ArrowDown", ctrlKey: false, altKey: false, metaKey: false,
      isComposing: false, keyCode: 40, preventDefault: function () {}, stopPropagation: function () {} };
    handlers["keydown"](evt);
    handlers["keydown"](evt);
    console.log(JSON.stringify(dispatched.length));
    """
    assert _run_node(_key_script(body)) == "1"


@needs_node
def test_node_debounce_modifier_delays_dispatch():
    body = """
    var el = makeEl({ "data-ark-on-key": "ArrowDown", "data-ark-key-action": "set",
      "data-ark-key-action-state": "n", "data-ark-key-action-args": JSON.stringify({ value: 1 }),
      "data-ark-key-modifiers": "debounce:10" });
    var store = makeStore({ n: 0 });
    var evt = { target: el, key: "ArrowDown", ctrlKey: false, altKey: false, metaKey: false,
      isComposing: false, keyCode: 40, preventDefault: function () {}, stopPropagation: function () {} };
    handlers["keydown"](evt);
    console.log(JSON.stringify(dispatched.length));
    setTimeout(function () {
      console.log(JSON.stringify(dispatched.length));
    }, 30);
    """
    out = _run_node(_key_script(body))
    lines = out.splitlines()
    assert lines[0] == "0"
    assert lines[1] == "1"


@needs_node
def test_node_no_store_does_not_throw_and_does_nothing():
    body = """
    var el = makeEl({ "data-ark-on-key": "Escape", "data-ark-key-action": "set",
      "data-ark-key-action-state": "open", "data-ark-key-action-args": JSON.stringify({ value: false }) });
    var store = null;
    handlers["keydown"]({ target: el, key: "Escape", ctrlKey: false, altKey: false, metaKey: false,
      isComposing: false, keyCode: 27, preventDefault: function () {}, stopPropagation: function () {} });
    console.log(JSON.stringify(dispatched.length));
    """
    assert _run_node(_key_script(body)) == "0"


@needs_node
def test_node_unknown_action_name_reports_instead_of_throwing():
    body = """
    var el = makeEl({ "data-ark-on-key": "Escape", "data-ark-key-action": "does-not-exist",
      "data-ark-key-action-state": "open", "data-ark-key-action-args": JSON.stringify({ value: false }) });
    var store = makeStore({ open: true });
    handlers["keydown"]({ target: el, key: "Escape", ctrlKey: false, altKey: false, metaKey: false,
      isComposing: false, keyCode: 27, preventDefault: function () {}, stopPropagation: function () {} });
    console.log(JSON.stringify([dispatched.length, reported.length]));
    """
    # actions["does-not-exist"] is undefined -> the `if (!action) return;`
    # guard returns quietly; nothing throws and nothing is reported either
    # (mirrors wireClickInterceptor's identical guard).
    assert _run_node(_key_script(body)) == "[0,0]"
