"""
Tests for `0.06505`: closing the JS runtime error-handling coverage gap
(`docs/Proposals/RUNTIME-ERROR-HANDLING-PROPOSAL.md`).

Three layers, mirroring the proposal:

- 3a: per-element guards in `recomputeAll`, `renderBindings`,
  `renderClassBindings`, `renderModelBindings`, `renderRepeat`,
  `renderShow` and `wireModelBinding`'s write-back -- one bad case
  reports and the rest of the pass keeps running.
- 3b: `wireErrorBoundary()`, a page-level `error`/`unhandledrejection`
  floor, registered once and shipped only where `arkNotify` ships.
- 3c: `arkReportError(message, err)`, the single funnel, with the closed
  `window.ARKLIGHT_ON_ERROR(message, err)` override (`false` suppresses
  the default notice; a throwing hook never blocks it).

The fragment tests run the real fragment source under Node with only the
globals each fragment reads stubbed, same approach as
`tests/test_action_value_from_state.py`.
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
    Derive,
    Input,
    Page,
    Predicate,
    Repeat,
    RepeatItem,
    Show,
    State,
    Text,
    Watch,
)
from arklight.backend.js.render import SCRIPT_PATH, JSBackend
from arklight.backend.js.runtime import (
    ERROR_BOUNDARY_JS,
    ERROR_REPORT_JS,
    RENDER_MODEL_BINDINGS_JS,
    RENDER_REPEAT_JS,
    RENDER_SHOW_JS,
    WIRE_MODEL_BINDING_JS,
)
from arklight.backend.js.runtime.bindings import (
    RENDER_BINDINGS_JS,
    RENDER_CLASS_BINDINGS_JS,
)
from arklight.backend.js.runtime.state import CREATE_STATE_JS
from arklight.ir.build import build_website_ir
from arklight.ir.normalize import normalize_ark_ast
from arklight.ir.validate import validate_ark_ast

NODE = shutil.which("node")
needs_node = pytest.mark.skipif(not NODE, reason="node not available in this environment")


def _run_node(script: str) -> list[str]:
    result = subprocess.run([NODE, "-e", script], capture_output=True, text=True, check=True)
    return result.stdout.strip().splitlines()


def _ir(pages, **kwargs):
    normalized = normalize_ark_ast(pages)
    validate_ark_ast(normalized)
    return build_website_ir("site", normalized, **kwargs)


def _js(pages) -> str:
    return JSBackend().render(_ir(pages))[SCRIPT_PATH]


# Records what arkReportError was asked to report; never throws.
_REPORT_STUB = """
var reported = [];
function arkReportError(msg, err) { reported.push(msg); }
"""


# ---------------------------------------------------------------------------
# Shipping / gating
# ---------------------------------------------------------------------------


def test_static_page_ships_no_error_reporting_code():
    js = _js({"/": Page(Text("hi"))})
    assert "arkReportError" not in js
    assert "wireErrorBoundary" not in js


def test_stateful_page_ships_funnel_and_boundary():
    js = _js({"/": Page(State("n", 0), Button("+", on_click=Action.increment("n")))})
    assert "function arkReportError(message, err)" in js
    assert "function wireErrorBoundary()" in js
    # arkNotify itself is untouched and still shipped.
    assert "function arkNotify(message)" in js


def test_behavior_only_page_ships_funnel_and_boundary():
    js = _js({"/": Page(Button("Show", on_click="toggle", behavior_target="#panel"))})
    assert "function arkReportError(message, err)" in js
    assert "wireErrorBoundary();" in js


def test_boundary_registered_once_at_ready_never_from_init_page():
    js = _js({"/": Page(State("n", 0), Button("+", on_click=Action.increment("n")))})
    assert js.count("wireErrorBoundary();") == 1
    init_page = js.split("function arkInitPage() {")[1].split("\n  }\n")[0]
    assert "wireErrorBoundary" not in init_page
    ready = js.split('document.addEventListener("DOMContentLoaded", function () {')[1].split("  });")[0]
    assert "wireErrorBoundary();" in ready


def test_app_shell_does_not_reregister_boundary_after_boosted_swap():
    pages = {"/": Page(State("n", 0), Button("+", on_click=Action.increment("n")))}
    js = JSBackend().render(_ir(pages, app_shell=True))[SCRIPT_PATH]
    assert js.count("wireErrorBoundary();") == 1
    assert 'addEventListener("htmx:afterSettle", arkInitPage)' in js


def test_generated_runtime_still_parses_for_every_stateful_primitive():
    # One page that turns on every primitive this change touches, so a
    # syntax slip in any guarded fragment fails here rather than in a browser.
    pages = {
        "/": Page(
            State("a", 1),
            State("b", 2),
            State("draft", ""),
            State("items", ["x"]),
            Computed("total", deps=("a", "b"), derive=Derive.sum("a", "b")),
            Input(bind_value=Bind.model("draft")),
            Text(Bind("total")),
            Show(Predicate.truthy("a"), Text("shown")),
            Repeat("items", template=lambda: Text(RepeatItem.value())),
            Button("Add", on_click=Action.append("items", Bind("draft"))),
            Watch("items", then=Action.reset("draft")),
        )
    }
    js = _js(pages)
    for needle in ("renderRepeat", "renderShow", "renderModelBindings", "recomputeAll", "wireWatchers"):
        assert needle in js
    if NODE:
        import tempfile

        with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False) as fh:
            fh.write(js)
        subprocess.run([NODE, "--check", fh.name], check=True)


def test_new_fragments_never_use_eval_or_new_function():
    # (The whole generated file can't be grepped -- vendored htmx carries
    # its own `eval`; tests/test_htmx_5.py owns that boundary.)
    for fragment in (ERROR_REPORT_JS, ERROR_BOUNDARY_JS):
        assert "eval(" not in fragment
        assert "new Function" not in fragment


# ---------------------------------------------------------------------------
# 3c: arkReportError / ARKLIGHT_ON_ERROR
# ---------------------------------------------------------------------------


def _report_script(window_js: str, body: str) -> str:
    return f"""
    var logged = [];
    var console = {{ error: function () {{ logged.push(Array.prototype.join.call(arguments, "|")); }} }};
    var window = {window_js};
    var notified = [];
    function arkNotify(msg) {{ notified.push(msg); }}
    {ERROR_REPORT_JS}
    {body}
    console_out({{ logged: logged, notified: notified }});
    function console_out(o) {{ process.stdout.write(JSON.stringify(o) + "\\n"); }}
    """


@needs_node
def test_report_without_hook_logs_and_notifies():
    out = json.loads(_run_node(_report_script("{}", 'arkReportError("boom msg", "E");'))[0])
    assert out["notified"] == ["boom msg"]
    assert out["logged"] == ["[ARKlight] boom msg|E"]


@needs_node
def test_report_calls_hook_with_message_and_error_then_notifies():
    hook = "{ ARKLIGHT_ON_ERROR: function (m, e) { seen.push([m, e]); } }"
    script = "var seen = [];\n" + _report_script(hook, 'arkReportError("m1", "err1"); seen.push("done");')
    # `seen` is declared before the window literal references it lazily.
    script = script.replace("console_out({", "logged.push(JSON.stringify(seen)); console_out({", 1)
    out = json.loads(_run_node(script)[0])
    assert out["notified"] == ["m1"]
    assert json.loads(out["logged"][-1]) == [["m1", "err1"], "done"]


@needs_node
def test_hook_returning_false_suppresses_default_notice_only():
    hook = "{ ARKLIGHT_ON_ERROR: function () { return false; } }"
    out = json.loads(_run_node(_report_script(hook, 'arkReportError("quiet", "E");'))[0])
    assert out["notified"] == []
    assert out["logged"] == ["[ARKlight] quiet|E"]  # console trace is not suppressed


@needs_node
@pytest.mark.parametrize("ret", ["undefined", "true", "0", "null", '""'])
def test_hook_returning_anything_but_false_leaves_default_notice(ret):
    hook = "{ ARKLIGHT_ON_ERROR: function () { return %s; } }" % ret
    out = json.loads(_run_node(_report_script(hook, 'arkReportError("shown", "E");'))[0])
    assert out["notified"] == ["shown"]


@needs_node
def test_throwing_hook_never_blocks_default_notice_or_escapes():
    hook = '{ ARKLIGHT_ON_ERROR: function () { throw new Error("bad override"); } }'
    out = json.loads(_run_node(_report_script(hook, 'arkReportError("still shown", "E");'))[0])
    assert out["notified"] == ["still shown"]


@needs_node
def test_non_function_hook_is_ignored():
    out = json.loads(_run_node(_report_script('{ ARKLIGHT_ON_ERROR: "nope" }', 'arkReportError("m", "E");'))[0])
    assert out["notified"] == ["m"]


@needs_node
def test_throwing_console_never_blocks_notice():
    script = f"""
    var console = {{ error: function () {{ throw new Error("no console"); }} }};
    var window = {{}};
    var notified = [];
    function arkNotify(msg) {{ notified.push(msg); }}
    {ERROR_REPORT_JS}
    arkReportError("m", "E");
    process.stdout.write(JSON.stringify(notified) + "\\n");
    """
    assert json.loads(_run_node(script)[0]) == ["m"]


# ---------------------------------------------------------------------------
# 3b: page-level boundary
# ---------------------------------------------------------------------------


_BOUNDARY_HARNESS = """
var listeners = {};
var window = { addEventListener: function (type, fn) { listeners[type] = fn; } };
var reported = [];
function arkReportError(msg, err) { reported.push([msg, String(err)]); }
"""


@needs_node
def test_boundary_reports_uncaught_errors_and_rejections():
    script = f"""
    {_BOUNDARY_HARNESS}
    {ERROR_BOUNDARY_JS}
    wireErrorBoundary();
    listeners.error({{ message: "x is not defined", error: "ERR1" }});
    listeners.unhandledrejection({{ reason: "REJ1" }});
    process.stdout.write(JSON.stringify(reported) + "\\n");
    process.stdout.write(Object.keys(listeners).sort().join(",") + "\\n");
    """
    lines = _run_node(script)
    reported = json.loads(lines[0])
    assert [r[1] for r in reported] == ["ERR1", "REJ1"]
    assert all("unexpected" in r[0] for r in reported)
    assert lines[1] == "error,unhandledrejection"


@needs_node
def test_boundary_ignores_resize_observer_chatter():
    script = f"""
    {_BOUNDARY_HARNESS}
    {ERROR_BOUNDARY_JS}
    wireErrorBoundary();
    listeners.error({{ message: "ResizeObserver loop completed with undelivered notifications." }});
    listeners.error({{ message: "ResizeObserver loop limit exceeded" }});
    process.stdout.write(String(reported.length) + "\\n");
    """
    assert _run_node(script) == ["0"]


@needs_node
def test_boundary_listeners_never_throw_even_if_reporting_does():
    script = f"""
    var listeners = {{}};
    var window = {{ addEventListener: function (type, fn) {{ listeners[type] = fn; }} }};
    function arkReportError() {{ throw new Error("reporter down"); }}
    {ERROR_BOUNDARY_JS}
    wireErrorBoundary();
    listeners.error({{ message: "m", error: "E" }});
    listeners.unhandledrejection({{}});
    listeners.error(undefined);
    process.stdout.write("ok\\n");
    """
    assert _run_node(script) == ["ok"]


# ---------------------------------------------------------------------------
# 3a: per-element guards
# ---------------------------------------------------------------------------


@needs_node
def test_recompute_guards_each_computed_entry_independently():
    script = f"""
    {_REPORT_STUB}
    var derivations = {{
      boom: function () {{ throw new Error("bad derive"); }},
      double: function (state, names) {{ return state[names[0]] * 2; }}
    }};
    {CREATE_STATE_JS}
    var store = createState({{ n: 2 }}, [
      ["broken", {{ kind: "boom", names: [], args: {{}} }}],
      ["twice",  {{ kind: "double", names: ["n"], args: {{}} }}]
    ]);
    var notifiedListener = 0;
    store.subscribe(function () {{ notifiedListener += 1; }});
    store.set("n", 5);
    process.stdout.write(JSON.stringify({{
      twice: store.get("twice"), reported: reported.length, listener: notifiedListener
    }}) + "\\n");
    """
    out = json.loads(_run_node(script)[0])
    # A later Computed still recomputes, set() still notifies subscribers,
    # and each failing pass reported (construction + the set()).
    assert out == {"twice": 10, "reported": 2, "listener": 1}


def _dom_stub(elements_by_selector: str) -> str:
    return f"""
    var document = {{ querySelectorAll: function (sel) {{ return ({elements_by_selector})[sel] || []; }} }};
    """


@needs_node
def test_render_bindings_one_bad_element_does_not_stop_the_rest():
    script = f"""
    {_REPORT_STUB}
    var patched = [];
    var snabbdom = {{ h: function (sel, data, text) {{
      if (text === "BAD") throw new Error("vnode failure");
      return {{ text: text }};
    }} }};
    function arkSelectorFor() {{ return "span"; }}
    function arkPatch(old, next) {{ patched.push(next.text); }}
    function el(key) {{ return {{ getAttribute: function () {{ return key; }} }}; }}
    {_dom_stub('{"[data-ark-bind]": [el("bad"), el("good1"), el("good2")]}')}
    var store = {{ get: function (k) {{ return k === "bad" ? "BAD" : k.toUpperCase(); }} }};
    {RENDER_BINDINGS_JS}
    renderBindings(store);
    process.stdout.write(JSON.stringify({{ patched: patched, reported: reported.length }}) + "\\n");
    """
    out = json.loads(_run_node(script)[0])
    assert out == {"patched": ["GOOD1", "GOOD2"], "reported": 1}


@needs_node
def test_render_class_bindings_one_bad_element_does_not_stop_the_rest():
    script = f"""
    {_REPORT_STUB}
    var toggled = [];
    function el(cls, key, bad) {{
      return {{
        getAttribute: function (n) {{ return n === "data-ark-bind-class" ? cls : key; }},
        classList: {{ toggle: function (c, on) {{ if (bad) throw new Error("dom"); toggled.push([c, on]); }} }}
      }};
    }}
    {_dom_stub('{"[data-ark-bind-class]": [el("a", "k", true), el("b", "k", false)]}')}
    {RENDER_CLASS_BINDINGS_JS}
    renderClassBindings({{ get: function () {{ return 1; }} }});
    process.stdout.write(JSON.stringify({{ toggled: toggled, reported: reported.length }}) + "\\n");
    """
    assert json.loads(_run_node(script)[0]) == {"toggled": [["b", True]], "reported": 1}


@needs_node
def test_render_model_bindings_one_bad_element_does_not_stop_the_rest():
    script = f"""
    {_REPORT_STUB}
    var writes = [];
    function good(key) {{
      var o = {{ getAttribute: function () {{ return key; }} }};
      Object.defineProperty(o, "value", {{ get: function () {{ return ""; }}, set: function (v) {{ writes.push(v); }} }});
      return o;
    }}
    var bad = {{ getAttribute: function () {{ return "bad"; }} }};
    Object.defineProperty(bad, "value", {{ get: function () {{ return ""; }}, set: function () {{ throw new Error("readonly"); }} }});
    {_dom_stub('{"[data-ark-model]": [bad, good("g")]}')}
    {RENDER_MODEL_BINDINGS_JS}
    renderModelBindings({{ get: function () {{ return "v"; }} }});
    process.stdout.write(JSON.stringify({{ writes: writes, reported: reported.length }}) + "\\n");
    """
    assert json.loads(_run_node(script)[0]) == {"writes": ["v"], "reported": 1}


@needs_node
def test_render_show_malformed_spec_on_one_element_does_not_stop_the_rest():
    script = f"""
    {_REPORT_STUB}
    var good = {{ hidden: null, getAttribute: function () {{ return '{{"kind":"truthy","names":["on"]}}'; }} }};
    var bad = {{ hidden: null, getAttribute: function () {{ return "{{not json"; }} }};
    {_dom_stub('{"[data-ark-show]": [bad, good]}')}
    {RENDER_SHOW_JS}
    renderShow({{ get: function () {{ return true; }} }});
    process.stdout.write(JSON.stringify({{ hidden: good.hidden, badHidden: bad.hidden, reported: reported.length }}) + "\\n");
    """
    assert json.loads(_run_node(script)[0]) == {"hidden": False, "badHidden": None, "reported": 1}


@needs_node
def test_render_repeat_malformed_template_on_one_container_does_not_stop_the_rest():
    script = f"""
    {_REPORT_STUB}
    var snabbdom = {{ h: function (sel, data, children) {{
      // Same shape the vendored core produces: a string child becomes `text`.
      return typeof children === "string"
        ? {{ sel: sel, data: data, text: children }}
        : {{ sel: sel, data: data, children: children }};
    }} }};
    function arkSelectorFor() {{ return "ul"; }}
    function arkPatch() {{}}
    function container(tpl) {{
      return {{
        children: [{{}}],
        getAttribute: function (n) {{ return n === "data-ark-repeat" ? "items" : tpl; }}
      }};
    }}
    var bad = container("{{not json");
    var good = container('{{"tag":"li","text":{{"item_value":true}}}}');
    {_dom_stub('{"[data-ark-repeat]": [bad, good]}')}
    {RENDER_REPEAT_JS}
    renderRepeat({{ get: function () {{ return ["x"]; }} }});
    process.stdout.write(JSON.stringify({{
      goodInit: good.__arkRepeatInit === true, badInit: !!bad.__arkRepeatInit, reported: reported.length
    }}) + "\\n");
    """
    assert json.loads(_run_node(script)[0]) == {"goodInit": True, "badInit": False, "reported": 1}


def _model_harness(store_set_body: str, element_extra: str = "") -> str:
    return f"""
    {_REPORT_STUB}
    var handlers = {{}};
    var document = {{ addEventListener: function (type, fn) {{ handlers[type] = fn; }} }};
    var attrs = {{ "data-ark-model": "q"{element_extra} }};
    var el = {{ value: "typed", getAttribute: function (n) {{ return n in attrs ? attrs[n] : null; }} }};
    var event = {{ target: {{ closest: function () {{ return el; }} }} }};
    var sets = [];
    var store = {{ set: function (k, v) {{ {store_set_body} sets.push([k, v]); }} }};
    {WIRE_MODEL_BINDING_JS}
    wireModelBinding(function () {{ return store; }});
    """


@needs_node
def test_model_input_write_back_failure_is_reported_not_thrown():
    script = _model_harness('throw new Error("recompute failed");') + """
    handlers.input(event);
    process.stdout.write(JSON.stringify({ reported: reported.length, sets: sets.length }) + "\\n");
    """
    assert json.loads(_run_node(script)[0]) == {"reported": 1, "sets": 0}


@needs_node
def test_model_input_write_back_unchanged_when_nothing_fails():
    script = _model_harness("") + """
    handlers.input(event);
    process.stdout.write(JSON.stringify({ reported: reported.length, sets: sets }) + "\\n");
    """
    assert json.loads(_run_node(script)[0]) == {"reported": 0, "sets": [["q", "typed"]]}


@needs_node
def test_model_input_debounced_write_back_failure_is_reported_not_thrown():
    script = _model_harness('throw new Error("late failure");', ', "data-ark-model-modifiers": "debounce:1"') + """
    handlers.input(event);
    process.on("uncaughtException", function () { process.stdout.write("escaped\\n"); });
    setTimeout(function () {
      process.stdout.write(JSON.stringify({ reported: reported.length }) + "\\n");
    }, 30);
    """
    assert _run_node(script) == ['{"reported":1}']


@needs_node
def test_model_input_throttled_write_back_failure_is_reported_not_thrown():
    script = _model_harness('throw new Error("throttled failure");', ', "data-ark-model-modifiers": "throttle:1000"') + """
    handlers.input(event);
    process.stdout.write(JSON.stringify({ reported: reported.length }) + "\\n");
    """
    assert json.loads(_run_node(script)[0]) == {"reported": 1}
