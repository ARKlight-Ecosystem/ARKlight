"""
`PlatformAPI.confirm` -- a one-shot native confirm prompt, Stage 6 of
`docs/Implementation/INPUT-AND-PLATFORM-PRIMITIVES-ADDENDUM-v0.071.md`
(the last and weakest-forcing-case rung of that six-stage ladder).

Grouped like `tests/test_platform_api.py`/`tests/test_platform_api_db.py`:

1. `PlatformAPI.confirm(...)` factory builds the right `PlatformAPIRef`.
2. Validation (`arklight.ir.validate`): `message` must be a non-empty
   string, `into` must be a declared `State(...)`.
3. HTML attribute rendering.
4. JS backend: only shipped when used, dispatched through the existing
   `"platform:"` branch.
5. Backend support: Web implements `confirm`; Android/Desktop don't.
6. Node: the confirm fragment against a stubbed `window.confirm`.
"""

import json
import shutil
import subprocess

import pytest

from arklight.api import Button, Page, PlatformAPI, State, Text
from arklight.ast.nodes import PlatformAPIRef
from arklight.backend.html.render import HTMLBackend
from arklight.backend.js.platform_apis.confirm import JS_FRAGMENT as CONFIRM_FRAGMENT
from arklight.backend.js.render import SCRIPT_PATH, JSBackend
from arklight.ir.build import build_website_ir
from arklight.ir.normalize import normalize_ark_ast
from arklight.ir.platform_api import BACKEND_PLATFORM_API_SUPPORT, PlatformAPIError, check_backend_support
from arklight.ir.validate import ValidationError, validate_ark_ast


def _ir(*children):
    normalized = normalize_ark_ast({"/": Page(*children)})
    validate_ark_ast(normalized)
    return build_website_ir("site", normalized)


def _plain_ir():
    return _ir(Text("hi"))


def _validate(*children):
    validate_ark_ast(normalize_ark_ast({"/": Page(*children)}))


def _js(*children):
    return JSBackend().render(_ir(*children))[SCRIPT_PATH]


# --- 1. arklight.api.PlatformAPI.confirm factory --------------------------


def test_platform_api_confirm_builds_ref_with_message_and_into():
    ref = PlatformAPI.confirm("Delete this file?", into="really_delete")
    assert isinstance(ref, PlatformAPIRef)
    assert ref.capability == "confirm"
    assert ref.args == {"message": "Delete this file?", "into": "really_delete"}


# --- 2. Validation ----------------------------------------------------------


def test_validate_accepts_confirm_with_declared_into():
    _validate(
        State("really_delete", False),
        Button("Delete", on_click=PlatformAPI.confirm("Delete this file?", into="really_delete")),
    )  # Should not raise.


def test_validate_rejects_confirm_into_undeclared_state():
    with pytest.raises(ValidationError, match="writes into 'nope'"):
        _validate(Button("Delete", on_click=PlatformAPI.confirm("Sure?", into="nope")))


def test_validate_rejects_confirm_into_a_computed_name():
    from arklight.api import Computed, Derive

    with pytest.raises(ValidationError, match="writes into 'shout'"):
        _validate(
            State("text", ""),
            Computed("shout", deps=("text",), derive=Derive.uppercase("text")),
            Button("Delete", on_click=PlatformAPI.confirm("Sure?", into="shout")),
        )


def test_validate_rejects_confirm_with_empty_message():
    bad_ref = PlatformAPIRef(capability="confirm", args={"message": "", "into": "x"})
    with pytest.raises(ValidationError, match="non-empty string `message`"):
        _validate(State("x", False), Button("Delete", on_click=bad_ref))


def test_validate_rejects_confirm_missing_message():
    bad_ref = PlatformAPIRef(capability="confirm", args={"into": "x"})
    with pytest.raises(ValidationError, match="non-empty string `message`"):
        _validate(State("x", False), Button("Delete", on_click=bad_ref))


def test_validate_rejects_confirm_missing_into():
    bad_ref = PlatformAPIRef(capability="confirm", args={"message": "Sure?"})
    with pytest.raises(ValidationError, match="writes into None"):
        _validate(State("x", False), Button("Delete", on_click=bad_ref))


def test_validate_rejects_confirm_unexpected_argument():
    bad_ref = PlatformAPIRef(capability="confirm", args={"message": "Sure?", "into": "x", "extra": 1})
    with pytest.raises(ValidationError, match="unexpected keyword argument"):
        _validate(State("x", False), Button("Delete", on_click=bad_ref))


# --- 3. HTML attribute rendering --------------------------------------------


def test_html_renders_platform_api_confirm_on_click_attribute():
    pages = {
        "/": Page(
            State("really_delete", False),
            Button("Delete", on_click=PlatformAPI.confirm("Delete this file?", into="really_delete")),
        )
    }
    normalized = normalize_ark_ast(pages)
    validate_ark_ast(normalized)
    html = HTMLBackend().render(build_website_ir("site", normalized))["index.html"]
    assert 'data-ark-on-click="platform:confirm"' in html
    assert "data-ark-platform-api-args" in html
    assert "Delete this file?" in html


# --- 4. JS backend: only-ship-what's-used + dispatch wiring ----------------


def test_js_runtime_ships_no_confirm_when_unused():
    js = JSBackend().render(_plain_ir())[SCRIPT_PATH]
    assert "confirm: function" not in js


def test_js_runtime_ships_confirm_when_used():
    js = _js(
        State("really_delete", False),
        Button("Delete", on_click=PlatformAPI.confirm("Sure?", into="really_delete")),
    )
    assert "confirm: function" in js
    assert "var platformApis = {" in js
    assert "wireClickInterceptor" in js


def test_js_click_interceptor_dispatches_confirm_through_platform_prefix():
    js = _js(
        State("really_delete", False),
        Button("Delete", on_click=PlatformAPI.confirm("Sure?", into="really_delete")),
    )
    assert 'raw.indexOf("platform:")' in js
    assert "platformApis[capability]" in js


def test_js_runtime_has_no_eval_or_new_function_with_confirm():
    js = _js(
        State("really_delete", False),
        Button("Delete", on_click=PlatformAPI.confirm("Sure?", into="really_delete")),
    )
    assert "eval(" not in js
    assert "new Function(" not in js


# --- 5. Backend-capability check --------------------------------------------


def test_confirm_is_registered_as_web_only_support():
    assert "confirm" in BACKEND_PLATFORM_API_SUPPORT["web"]
    assert "confirm" not in BACKEND_PLATFORM_API_SUPPORT["android"]
    assert "confirm" not in BACKEND_PLATFORM_API_SUPPORT["desktop"]


def test_check_backend_support_passes_for_web_backend_with_confirm():
    check_backend_support({"confirm"}, backend_name="web")  # Should not raise.


def test_check_backend_support_raises_for_android_with_confirm():
    with pytest.raises(PlatformAPIError, match="not implemented by backend 'android'"):
        check_backend_support({"confirm"}, backend_name="android")


def test_js_backend_render_raises_when_confirm_unsupported(monkeypatch):
    import arklight.backend.js.render as render_module

    monkeypatch.setitem(
        render_module.check_backend_support.__globals__["BACKEND_PLATFORM_API_SUPPORT"], "web", frozenset()
    )
    ir = _ir(
        State("really_delete", False),
        Button("Delete", on_click=PlatformAPI.confirm("Sure?", into="really_delete")),
    )
    with pytest.raises(PlatformAPIError, match="not implemented by backend 'web'"):
        JSBackend().render(ir)


# --- 6. Node: run the shipped JavaScript ------------------------------------

NODE = shutil.which("node")
needs_node = pytest.mark.skipif(not NODE, reason="node not available in this environment")


def _run_node(script: str) -> list:
    proc = subprocess.run([NODE, "-e", script], capture_output=True, text=True)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    return [json.loads(line) for line in proc.stdout.strip().splitlines()]


_STORE_STUB = """
var notes = [];
function arkNotify(msg) { notes.push(msg); }
function makeStore(initial) {
  var state = Object.assign({}, initial);
  return { get: function (k) { return state[k]; }, set: function (k, v) { state[k] = v; }, all: state };
}
"""


def _confirm_script(body: str, *, window_confirm: str) -> str:
    return "\n".join(
        [
            _STORE_STUB,
            "var window = { confirm: " + window_confirm + " };",
            "var platformApis = {\n" + CONFIRM_FRAGMENT + "\n};",
            "var confirm = platformApis.confirm;",
            body,
        ]
    )


@needs_node
def test_node_confirm_writes_true_into_state_on_ok():
    body = """
    var s = makeStore({});
    confirm({ message: "Delete?", into: "x" }, s);
    console.log(JSON.stringify([s.all.x, notes]));
    """
    script = _confirm_script(body, window_confirm="function (msg) { return true; }")
    (result,) = _run_node(script)
    value, notices = result
    assert value is True
    assert notices == []


@needs_node
def test_node_confirm_writes_false_into_state_on_cancel():
    body = """
    var s = makeStore({});
    confirm({ message: "Delete?", into: "x" }, s);
    console.log(JSON.stringify(s.all.x));
    """
    script = _confirm_script(body, window_confirm="function (msg) { return false; }")
    assert _run_node(script) == [False]


@needs_node
def test_node_confirm_passes_the_message_through():
    body = """
    var seen = null;
    window.confirm = function (msg) { seen = msg; return true; };
    var s = makeStore({});
    confirm({ message: "Delete this file?", into: "x" }, s);
    console.log(JSON.stringify(seen));
    """
    script = _confirm_script(body, window_confirm="function () { return true; }")
    assert _run_node(script) == ["Delete this file?"]


@needs_node
def test_node_confirm_without_window_confirm_notifies_instead_of_throwing():
    script = "\n".join(
        [
            _STORE_STUB,
            "var window = {};",
            "var platformApis = {\n" + CONFIRM_FRAGMENT + "\n};",
            "var confirm = platformApis.confirm;",
            "var s = makeStore({});",
            'confirm({ message: "Delete?", into: "x" }, s);',
            "console.log(JSON.stringify([s.all.x, notes.length]));",
        ]
    )
    (result,) = _run_node(script)
    value, note_count = result
    assert value is None  # never written
    assert note_count == 1


@needs_node
def test_node_confirm_catches_a_throwing_window_confirm():
    body = """
    var s = makeStore({});
    confirm({ message: "Delete?", into: "x" }, s);
    console.log(JSON.stringify([s.all.x, notes.length]));
    """
    script = _confirm_script(
        body, window_confirm='function () { throw new Error("blocked"); }'
    )
    (result,) = _run_node(script)
    value, note_count = result
    assert value is None
    assert note_count == 1


@needs_node
def test_node_confirm_does_nothing_without_a_store():
    script = "\n".join(
        [
            _STORE_STUB,
            'var window = { confirm: function () { return true; } };',
            "var platformApis = {\n" + CONFIRM_FRAGMENT + "\n};",
            "var confirm = platformApis.confirm;",
            'confirm({ message: "Delete?", into: "x" }, null);',
            "console.log(JSON.stringify(notes));",
        ]
    )
    assert _run_node(script) == [[]]
