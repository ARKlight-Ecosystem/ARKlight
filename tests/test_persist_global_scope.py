"""
App-Shell Capability Proposal (docs/Proposals/APP-SHELL-CAPABILITY-
PROPOSAL.md), "Amendments on acceptance": `State(name, initial,
persist=True, scope="global")` opts a persisted key out of
`vdom-8`'s per-page-path `localStorage` namespacing -- across the
API, Validation, the IR (`IRPage.persist_global`), the HTML backend
(`data-ark-persist-global` hydration attribute), and the JS backend
(`initState()`'s global-scoped read-override-on-init /
write-on-change pair). Mirrors `tests/test_vdom_8.py`'s own layout and
conventions, one section per layer.
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


def test_state_scope_defaults_to_none():
    node = State("count", 0, persist=True)
    assert node.props["scope"] is None


def test_state_scope_global_is_recorded_on_the_node():
    node = State("count", 0, persist=True, scope="global")
    assert node.props["scope"] == "global"


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


def test_state_persist_true_scope_global_passes_validation():
    tree = Page(State("cart_count", 0, persist=True, scope="global"), Text("hi"))
    validate_ark_ast(normalize_ark_ast({"/": tree}))  # no raise


def test_state_scope_unknown_value_raises():
    tree = Page(State("count", 0, persist=True, scope="tab"), Text("hi"))
    with pytest.raises(ValidationError, match="recognized persistence scope"):
        validate_ark_ast(normalize_ark_ast({"/": tree}))


def test_state_scope_global_without_persist_raises():
    tree = Page(State("count", 0, scope="global"), Text("hi"))
    with pytest.raises(ValidationError, match="no persist=True"):
        validate_ark_ast(normalize_ark_ast({"/": tree}))


# ---------------------------------------------------------------------------
# IR
# ---------------------------------------------------------------------------


def test_ir_page_persist_global_lists_only_global_scoped_keys_in_declaration_order():
    tree = Page(
        State("theme", "light", persist=True),
        State("cart_count", 0, persist=True, scope="global"),
        State("draft", ""),
        State("locale", "en", persist=True, scope="global"),
        Text("hi"),
    )
    ir = _ir({"/": tree})
    # Plain path-scoped keys stay in `persist`, global-scoped keys move
    # to `persist_global` -- the two lists never share a name.
    assert ir.pages[0].persist == ["theme"]
    assert ir.pages[0].persist_global == ["cart_count", "locale"]


def test_ir_page_persist_global_empty_when_no_state_uses_global_scope():
    tree = Page(State("theme", "light", persist=True), Text("hi"))
    ir = _ir({"/": tree})
    assert ir.pages[0].persist_global == []
    # Unchanged behavior for a plain persist=True page.
    assert ir.pages[0].persist == ["theme"]


def test_ir_page_persist_global_empty_on_a_stateless_page():
    tree = Page(Text("hi"))
    ir = _ir({"/": tree})
    assert ir.pages[0].persist_global == []


# ---------------------------------------------------------------------------
# HTML backend
# ---------------------------------------------------------------------------


def test_html_backend_emits_data_ark_persist_global_when_used():
    tree = Page(State("cart_count", 0, persist=True, scope="global"), Text("hi"))
    ir = _ir({"/": tree})
    html = HTMLBackend().render(ir)["index.html"]
    assert 'data-ark-persist-global="[&quot;cart_count&quot;]"' in html


def test_html_backend_omits_data_ark_persist_global_when_unused():
    tree = Page(State("theme", "light", persist=True), Text("hi"))
    ir = _ir({"/": tree})
    html = HTMLBackend().render(ir)["index.html"]
    assert "data-ark-persist-global" not in html


def test_html_backend_plain_persist_output_is_byte_for_byte_unaffected():
    # SYSTEM-DESIGN-AGREEMENTS.md's "byte-for-byte unaffected when
    # opted out": a page using only plain persist=True (no scope=)
    # must emit the exact same data-ark-persist markup as it did
    # before this feature existed.
    tree = Page(State("theme", "light", persist=True), Text("hi"))
    ir = _ir({"/": tree})
    html = HTMLBackend().render(ir)["index.html"]
    assert 'data-ark-persist="[&quot;theme&quot;]"' in html
    assert "data-ark-persist-global" not in html


def test_html_backend_app_shell_state_marker_carries_persist_global_too():
    tree = Page(State("cart_count", 0, persist=True, scope="global"), Text("hi"))
    normalized = normalize_ark_ast({"/": tree})
    validate_ark_ast(normalized)
    ir = build_website_ir("site", normalized, app_shell=True)
    html = HTMLBackend().render(ir)["index.html"]
    assert '<div id="ark-state"' in html
    assert 'data-ark-persist-global="[&quot;cart_count&quot;]"' in html
    assert "hx-boost=" in html


def test_html_backend_both_persist_kinds_can_coexist_on_one_page():
    tree = Page(
        State("theme", "light", persist=True),
        State("cart_count", 0, persist=True, scope="global"),
        Text("hi"),
    )
    ir = _ir({"/": tree})
    html = HTMLBackend().render(ir)["index.html"]
    assert 'data-ark-persist="[&quot;theme&quot;]"' in html
    assert 'data-ark-persist-global="[&quot;cart_count&quot;]"' in html


# ---------------------------------------------------------------------------
# JS backend
# ---------------------------------------------------------------------------


def test_js_backend_ships_persist_global_read_and_write_on_any_stateful_page():
    # Unlike wireWatchers/renderModelBindings/renderRepeat/renderShow,
    # and exactly like plain persist (vdom-8), global-scoped
    # persistence isn't gated behind a has-usage flag -- the
    # read-override/write-back pair is a fixed, always-present part of
    # initState() on any stateful page, a no-op loop over an empty
    # `persistGlobal` array when no State(...) on that page actually
    # uses scope="global".
    tree = Page(State("count", 0), Button("+", on_click=Action.increment("count", 1)))
    ir = _ir({"/": tree})
    js = JSBackend().render(ir)["arklight.js"]
    assert "data-ark-persist-global" in js
    assert '"ark:global:"' in js


def test_js_backend_persist_global_reads_and_writes_are_each_own_try_catch():
    tree = Page(State("cart_count", 0, persist=True, scope="global"), Text("hi"))
    ir = _ir({"/": tree})
    js = JSBackend().render(ir)["arklight.js"]
    # One try/catch for the global-scoped read, one for the
    # global-scoped write -- distinct from plain persist's own pair
    # and from the outer initState() try/catch, same degrade-quietly
    # discipline every localStorage access in this runtime holds.
    assert js.count('localStorage.getItem("ark:global:" + key)') == 1
    assert js.count('localStorage.setItem("ark:global:" + key') == 1


# ---------------------------------------------------------------------------
# End-to-end: the shipped `initState`/`createState` fragments, run
# under Node against minimal stand-ins for `document`/`localStorage`/
# `location` (no real DOM/storage available in this environment),
# actually read a global-scoped persisted override on init, write
# changes back out unprefixed by page path, and never let a
# path-scoped and a global-scoped key with different names collide.
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


def test_node_init_state_overrides_initial_value_from_global_localstorage_key():
    from arklight.backend.js.runtime.state import CREATE_STATE_JS, INIT_STATE_JS

    script = f"""
    var notified = [];
    {_fake_storage('{ "ark:global:cart_count": JSON.stringify(3) }')}
    var location = {{ pathname: "/checkout" }};
    var body = {{
      attrs: {{
        "data-ark-state": JSON.stringify({{ cart_count: 0 }}),
        "data-ark-persist-global": JSON.stringify(["cart_count"])
      }},
      getAttribute: function (n) {{ return this.attrs[n] !== undefined ? this.attrs[n] : null; }}
    }};
    var document = {{ getElementById: function () {{ return null; }}, body: body }};
    {_NODE_HARNESS.format(create_state_js=CREATE_STATE_JS, init_state_js=INIT_STATE_JS)}
    var store = initState();
    console.log(store.get("cart_count"));
    """
    assert _run_node(script) == "3"


def test_node_global_scoped_value_follows_the_visitor_between_different_pages():
    # The entire point of scope="global": a value written while
    # initState() runs with one `location.pathname` is read back by a
    # later initState() run with a *different* `location.pathname` --
    # exactly what plain persist=True (path-prefixed) cannot do.
    from arklight.backend.js.runtime.state import CREATE_STATE_JS, INIT_STATE_JS

    def _init_on_page(pathname):
        return f"""
        var location = {{ pathname: {pathname!r} }};
        var body = {{
          attrs: {{
            "data-ark-state": JSON.stringify({{ cart_count: 0 }}),
            "data-ark-persist-global": JSON.stringify(["cart_count"])
          }},
          getAttribute: function (n) {{ return this.attrs[n] !== undefined ? this.attrs[n] : null; }}
        }};
        var document = {{ getElementById: function () {{ return null; }}, body: body }};
        """

    script = f"""
    var notified = [];
    {_fake_storage()}
    {_init_on_page("/products")}
    {_NODE_HARNESS.format(create_state_js=CREATE_STATE_JS, init_state_js=INIT_STATE_JS)}
    var storeOnProducts = initState();
    storeOnProducts.set("cart_count", 2);
    {_init_on_page("/checkout")}
    var storeOnCheckout = initState();
    console.log(storeOnCheckout.get("cart_count"));
    """
    assert _run_node(script) == "2"


def test_node_plain_persist_still_isolated_per_page_alongside_a_global_key():
    # Both kinds of persistence on the same page, same init pass: the
    # path-scoped key stays page-local, the global-scoped key doesn't
    # -- they must never cross-contaminate each other's storage slot.
    from arklight.backend.js.runtime.state import CREATE_STATE_JS, INIT_STATE_JS

    initial_store = (
        '{ "ark:/a:theme": JSON.stringify("dark"), '
        '"ark:global:cart_count": JSON.stringify(5) }'
    )
    script = f"""
    var notified = [];
    {_fake_storage(initial_store)}
    var location = {{ pathname: "/a" }};
    var body = {{
      attrs: {{
        "data-ark-state": JSON.stringify({{ theme: "light", cart_count: 0 }}),
        "data-ark-persist": JSON.stringify(["theme"]),
        "data-ark-persist-global": JSON.stringify(["cart_count"])
      }},
      getAttribute: function (n) {{ return this.attrs[n] !== undefined ? this.attrs[n] : null; }}
    }};
    var document = {{ getElementById: function () {{ return null; }}, body: body }};
    {_NODE_HARNESS.format(create_state_js=CREATE_STATE_JS, init_state_js=INIT_STATE_JS)}
    var store = initState();
    console.log(store.get("theme") + "|" + store.get("cart_count"));
    """
    assert _run_node(script) == "dark|5"


def test_node_malformed_global_value_falls_back_to_server_initial():
    from arklight.backend.js.runtime.state import CREATE_STATE_JS, INIT_STATE_JS

    script = f"""
    var notified = [];
    {_fake_storage('{ "ark:global:cart_count": "not valid json" }')}
    var location = {{ pathname: "/checkout" }};
    var body = {{
      attrs: {{
        "data-ark-state": JSON.stringify({{ cart_count: 9 }}),
        "data-ark-persist-global": JSON.stringify(["cart_count"])
      }},
      getAttribute: function (n) {{ return this.attrs[n] !== undefined ? this.attrs[n] : null; }}
    }};
    var document = {{ getElementById: function () {{ return null; }}, body: body }};
    {_NODE_HARNESS.format(create_state_js=CREATE_STATE_JS, init_state_js=INIT_STATE_JS)}
    var store = initState();
    console.log(store.get("cart_count") + "|" + notified.length);
    """
    assert _run_node(script) == "9|0"
