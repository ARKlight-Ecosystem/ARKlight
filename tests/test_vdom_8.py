"""
`vdom-8` (REFACTOR-INDEX.md [retired -- see CHANGELOG.md] row 16): `State(name, initial,
persist=True)` opts a state key into `localStorage` persistence --
across the API, Validation, the IR (`IRPage.persist`), the HTML backend
(`data-ark-persist` hydration attribute), and the JS backend
(`initState()`'s read-override-on-init / write-on-change pair).
"""

import pytest

from arklight.api import Action, Button, Page, State, Text
from arklight.backend.html.render import HTMLBackend
from arklight.backend.js.render import JSBackend
from arklight.ir.build import build_website_ir
from arklight.ir.normalize import normalize_ark_ast
from arklight.ir.validate import ValidationError, validate_ark_ast


def _ir(pages):
    normalized = normalize_ark_ast(pages)
    validate_ark_ast(normalized)
    return build_website_ir("site", normalized)


# ---------------------------------------------------------------------------
# API
# ---------------------------------------------------------------------------


def test_state_persist_defaults_to_false():
    node = State("count", 0)
    assert node.props["persist"] is False


def test_state_persist_true_is_recorded_on_the_node():
    node = State("count", 0, persist=True)
    assert node.props["persist"] is True


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


def test_state_persist_true_passes_validation():
    tree = Page(State("count", 0, persist=True), Text("hi"))
    validate_ark_ast(normalize_ark_ast({"/": tree}))  # no raise


def test_state_persist_non_bool_raises():
    tree = Page(State("count", 0, persist="yes"), Text("hi"))
    with pytest.raises(ValidationError, match="must be a bool"):
        validate_ark_ast(normalize_ark_ast({"/": tree}))


# ---------------------------------------------------------------------------
# IR
# ---------------------------------------------------------------------------


def test_ir_page_persist_lists_only_persisted_keys_in_declaration_order():
    tree = Page(
        State("theme", "light", persist=True),
        State("draft", ""),
        State("sidebar_open", True, persist=True),
        Text("hi"),
    )
    ir = _ir({"/": tree})
    assert ir.pages[0].persist == ["theme", "sidebar_open"]


def test_ir_page_persist_empty_when_no_state_persists():
    tree = Page(State("count", 0), Text("hi"))
    ir = _ir({"/": tree})
    assert ir.pages[0].persist == []


def test_ir_page_persist_empty_on_a_stateless_page():
    tree = Page(Text("hi"))
    ir = _ir({"/": tree})
    assert ir.pages[0].persist == []


# ---------------------------------------------------------------------------
# HTML backend
# ---------------------------------------------------------------------------


def test_html_backend_emits_data_ark_persist_when_used():
    tree = Page(State("theme", "light", persist=True), Text("hi"))
    ir = _ir({"/": tree})
    html = HTMLBackend().render(ir)["index.html"]
    assert 'data-ark-persist="[&quot;theme&quot;]"' in html


def test_html_backend_omits_data_ark_persist_when_unused():
    tree = Page(State("count", 0), Text("hi"))
    ir = _ir({"/": tree})
    html = HTMLBackend().render(ir)["index.html"]
    assert "data-ark-persist" not in html


def test_html_backend_app_shell_state_marker_carries_persist_too():
    tree = Page(State("theme", "light", persist=True), Text("hi"))
    normalized = normalize_ark_ast({"/": tree})
    validate_ark_ast(normalized)
    ir = build_website_ir("site", normalized, app_shell=True)
    html = HTMLBackend().render(ir)["index.html"]
    assert '<div id="ark-state"' in html
    assert 'data-ark-persist="[&quot;theme&quot;]"' in html
    assert "hx-boost=" in html


# ---------------------------------------------------------------------------
# JS backend
# ---------------------------------------------------------------------------


def test_js_backend_ships_persist_read_and_write_on_any_stateful_page():
    # Unlike wireWatchers/renderModelBindings/renderRepeat/renderShow,
    # persistence isn't gated behind a has_persist usage flag -- the
    # read-override/write-back pair is a fixed, always-present part of
    # initState() on any stateful page (see runtime/state.py's module
    # docstring), a no-op loop over an empty `persist` array when no
    # State(...) on that page actually uses persist=True.
    tree = Page(State("count", 0), Button("+", on_click=Action.increment("count", 1)))
    ir = _ir({"/": tree})
    js = JSBackend().render(ir)["arklight.js"]
    assert "data-ark-persist" in js
    assert "localStorage.getItem(" in js
    assert "localStorage.setItem(" in js


def test_js_backend_persist_reads_and_writes_are_each_own_try_catch():
    tree = Page(State("theme", "light", persist=True), Text("hi"))
    ir = _ir({"/": tree})
    js = JSBackend().render(ir)["arklight.js"]
    # Two dedicated try/catch blocks around the localStorage calls,
    # distinct from the outer initState() try/catch that guards JSON
    # parsing of the hydration blob itself -- a localStorage failure
    # must degrade quietly, never trip arkNotify's page-wide warning.
    assert js.count("localStorage.getItem(") == 1
    assert js.count("localStorage.setItem(") == 1


# ---------------------------------------------------------------------------
# End-to-end: the shipped `initState`/`createState` fragments, run
# under Node against minimal stand-ins for `document`/`localStorage`/
# `location` (no real DOM/storage available in this environment),
# actually read a persisted override on init and write changes back
# out, degrading quietly on a bad stored value.
# ---------------------------------------------------------------------------

_NODE_HARNESS = """
{create_state_js}
{init_state_js}
function arkNotify(msg) {{ notified.push(msg); }}
function arkReportError(msg) {{ arkNotify(msg); }}
var renderBindings = function () {{}};
var renderClassBindings = function () {{}};
"""


def _run_node(script: str) -> str:
    node = pytest.importorskip("shutil").which("node")
    if not node:
        pytest.skip("node not available in this environment")
    import subprocess

    result = subprocess.run([node, "-e", script], capture_output=True, text=True, check=True)
    return result.stdout.strip()


def _fake_storage(initial=None):
    return """
    var _store = {store};
    var localStorage = {{
      getItem: function (k) {{ return Object.prototype.hasOwnProperty.call(_store, k) ? _store[k] : null; }},
      setItem: function (k, v) {{ _store[k] = v; }}
    }};
    """.format(store=initial if initial is not None else "{}")


def test_node_init_state_overrides_initial_value_from_localstorage():
    from arklight.backend.js.runtime.state import CREATE_STATE_JS, INIT_STATE_JS

    script = f"""
    var notified = [];
    {_fake_storage('{ "ark:/page:theme": JSON.stringify("dark") }')}
    var location = {{ pathname: "/page" }};
    var body = {{
      attrs: {{
        "data-ark-state": JSON.stringify({{ theme: "light" }}),
        "data-ark-persist": JSON.stringify(["theme"])
      }},
      getAttribute: function (n) {{ return this.attrs[n] !== undefined ? this.attrs[n] : null; }}
    }};
    var document = {{ getElementById: function () {{ return null; }}, body: body }};
    {_NODE_HARNESS.format(create_state_js=CREATE_STATE_JS, init_state_js=INIT_STATE_JS)}
    var store = initState();
    console.log(store.get("theme"));
    """
    assert _run_node(script) == "dark"


def test_node_init_state_falls_back_to_server_value_on_malformed_stored_json():
    from arklight.backend.js.runtime.state import CREATE_STATE_JS, INIT_STATE_JS

    script = f"""
    var notified = [];
    {_fake_storage('{ "ark:/page:theme": "not valid json" }')}
    var location = {{ pathname: "/page" }};
    var body = {{
      attrs: {{
        "data-ark-state": JSON.stringify({{ theme: "light" }}),
        "data-ark-persist": JSON.stringify(["theme"])
      }},
      getAttribute: function (n) {{ return this.attrs[n] !== undefined ? this.attrs[n] : null; }}
    }};
    var document = {{ getElementById: function () {{ return null; }}, body: body }};
    {_NODE_HARNESS.format(create_state_js=CREATE_STATE_JS, init_state_js=INIT_STATE_JS)}
    var store = initState();
    console.log(store.get("theme") + "|" + notified.length);
    """
    assert _run_node(script) == "light|0"


def test_node_state_change_writes_persisted_key_back_to_localstorage():
    from arklight.backend.js.runtime.state import CREATE_STATE_JS, INIT_STATE_JS

    script = f"""
    var notified = [];
    {_fake_storage()}
    var location = {{ pathname: "/page" }};
    var body = {{
      attrs: {{
        "data-ark-state": JSON.stringify({{ count: 0 }}),
        "data-ark-persist": JSON.stringify(["count"])
      }},
      getAttribute: function (n) {{ return this.attrs[n] !== undefined ? this.attrs[n] : null; }}
    }};
    var document = {{ getElementById: function () {{ return null; }}, body: body }};
    {_NODE_HARNESS.format(create_state_js=CREATE_STATE_JS, init_state_js=INIT_STATE_JS)}
    var store = initState();
    store.set("count", 7);
    console.log(_store["ark:/page:count"]);
    """
    assert _run_node(script) == "7"


def test_node_unpersisted_key_never_touches_localstorage():
    from arklight.backend.js.runtime.state import CREATE_STATE_JS, INIT_STATE_JS

    script = f"""
    var notified = [];
    {_fake_storage()}
    var location = {{ pathname: "/page" }};
    var body = {{
      attrs: {{
        "data-ark-state": JSON.stringify({{ count: 0, draft: "" }})
      }},
      getAttribute: function (n) {{ return this.attrs[n] !== undefined ? this.attrs[n] : null; }}
    }};
    var document = {{ getElementById: function () {{ return null; }}, body: body }};
    {_NODE_HARNESS.format(create_state_js=CREATE_STATE_JS, init_state_js=INIT_STATE_JS)}
    var store = initState();
    store.set("draft", "hello");
    console.log(Object.keys(_store).length);
    """
    assert _run_node(script) == "0"
