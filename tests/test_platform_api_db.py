"""
`PlatformAPI.db` -- persistent local key/value storage, one author-
facing interface with a per-backend engine (IndexedDB on Web; an Android
SQLite half is not on this branch -- sync plan Stage 11).

Grouped like `tests/test_platform_api.py`, plus a Node section that runs
the *shipped* JavaScript rather than only inspecting it:

1. `PlatformAPI.db.*` factories build the right `PlatformAPIRef`.
2. Validation (`arklight.ir.validate`): op/argument rules, `into` must be
   a declared `State(...)`, `Bind(...)` args must name declared state.
3. HTML attribute rendering.
4. JS backend: only shipped when used, dispatched through the existing
   `"platform:"` branch.
5. Backend support: only Web implements `db` on `main`; Android/Desktop don't.
6. Node: the db fragment against an in-memory IndexedDB stub and against a
   fake Android bridge, and the real click interceptor resolving `Bind(...)`.
"""

import json
import shutil
import subprocess

import pytest

from arklight.api import Bind, Button, Page, PlatformAPI, Repeat, State, Text
from arklight.ast.nodes import PlatformAPIRef
from arklight.backend.html.render import HTMLBackend
from arklight.backend.js.platform_apis.db import JS_FRAGMENT as DB_FRAGMENT
from arklight.backend.js.render import SCRIPT_PATH, JSBackend
from arklight.backend.js.runtime.dispatch import CLICK_INTERCEPTOR_JS
from arklight.ir.build import build_website_ir
from arklight.ir.normalize import normalize_ark_ast
from arklight.ir.platform_api import (
    BACKEND_PLATFORM_API_SUPPORT,
    DB_OPERATIONS,
    PLATFORM_API_REGISTRY,
    PlatformAPIError,
    check_backend_support,
)
from arklight.ir.validate import ValidationError, validate_ark_ast


def _validate(*nodes):
    validate_ark_ast(normalize_ark_ast({"/": Page(*nodes)}))


def _ir(*nodes):
    normalized = normalize_ark_ast({"/": Page(*nodes)})
    validate_ark_ast(normalized)
    return build_website_ir("site", normalized)


# --- 1. Factories ---------------------------------------------------------


def test_db_set_builds_ref():
    ref = PlatformAPI.db.set("draft", "hello")
    assert isinstance(ref, PlatformAPIRef)
    assert ref.capability == "db"
    assert ref.args == {"op": "set", "key": "draft", "value": "hello"}


def test_db_get_builds_ref_with_into():
    assert PlatformAPI.db.get("draft", into="text").args == {
        "op": "get",
        "key": "draft",
        "into": "text",
    }


def test_db_delete_builds_ref():
    assert PlatformAPI.db.delete("draft").args == {"op": "delete", "key": "draft"}


def test_db_keys_omits_prefix_when_not_given():
    assert PlatformAPI.db.keys(into="all").args == {"op": "keys", "into": "all"}
    assert PlatformAPI.db.keys(into="all", prefix="d").args == {
        "op": "keys",
        "into": "all",
        "prefix": "d",
    }


def test_db_bind_args_become_state_markers():
    ref = PlatformAPI.db.set(Bind("which"), Bind("text"))
    assert ref.args["key"] == {"__state__": "which"}
    assert ref.args["value"] == {"__state__": "text"}


# --- 2. Validation ---------------------------------------------------------


def test_validate_accepts_every_db_operation():
    _validate(
        State("text", ""),
        State("names", []),
        Button("s", on_click=PlatformAPI.db.set("k", Bind("text"))),
        Button("g", on_click=PlatformAPI.db.get("k", into="text")),
        Button("d", on_click=PlatformAPI.db.delete("k")),
        Button("l", on_click=PlatformAPI.db.keys(into="names", prefix="k")),
    )


def test_validate_accepts_json_values_including_none_and_nested():
    _validate(Button("s", on_click=PlatformAPI.db.set("k", {"a": [1, 2.5, None, True]})))
    _validate(Button("s", on_click=PlatformAPI.db.set("k", None)))


def test_validate_accepts_db_inside_a_repeat_template():
    _validate(
        State("items", ["a"]),
        State("out", None),
        Repeat("items", template=lambda: Button("go", on_click=PlatformAPI.db.get("k", into="out"))),
    )


def test_validate_rejects_into_undeclared_state_inside_a_repeat_template():
    with pytest.raises(ValidationError, match="writes into 'nope'"):
        _validate(
            State("items", ["a"]),
            Repeat("items", template=lambda: Button("go", on_click=PlatformAPI.db.get("k", into="nope"))),
        )


def test_validate_rejects_into_undeclared_state():
    with pytest.raises(ValidationError, match="writes into 'nope'"):
        _validate(Button("g", on_click=PlatformAPI.db.get("k", into="nope")))


def test_validate_rejects_into_a_computed_name():
    from arklight.api import Computed, Derive

    with pytest.raises(ValidationError, match="writes into 'shout'"):
        _validate(
            State("text", ""),
            Computed("shout", deps=("text",), derive=Derive.uppercase("text")),
            Button("g", on_click=PlatformAPI.db.get("k", into="shout")),
        )


def test_validate_rejects_bind_of_undeclared_state():
    with pytest.raises(ValidationError, match=r"reads Bind\('zz'\)"):
        _validate(Button("s", on_click=PlatformAPI.db.set("k", Bind("zz"))))


def test_validate_rejects_empty_key():
    with pytest.raises(ValidationError, match="non-empty string"):
        _validate(Button("s", on_click=PlatformAPI.db.set("", 1)))


def test_validate_rejects_non_string_key():
    with pytest.raises(ValidationError, match="must be a string or a Bind"):
        _validate(Button("s", on_click=PlatformAPI.db.set(7, 1)))


def test_validate_rejects_non_json_value():
    with pytest.raises(ValidationError, match="JSON-serializable"):
        _validate(Button("s", on_click=PlatformAPI.db.set("k", object())))


@pytest.mark.parametrize(
    "args, message",
    [
        ({"op": "drop", "key": "k"}, "unknown op 'drop'"),
        ({"key": "k"}, "unknown op None"),
        ({"op": "set", "key": "k"}, r"missing required argument\(s\) \['value'\]"),
        ({"op": "get", "key": "k"}, r"missing required argument\(s\) \['into'\]"),
        ({"op": "delete", "key": "k", "value": 1}, r"doesn't accept argument\(s\) \['value'\]"),
        ({"op": "keys", "into": "x", "key": "k"}, r"doesn't accept argument\(s\) \['key'\]"),
        ({"op": "set", "key": "k", "value": 1, "bogus": 1}, "unexpected keyword argument"),
    ],
)
def test_validate_rejects_malformed_hand_built_db_refs(args, message):
    ref = PlatformAPIRef(capability="db", args=args)
    with pytest.raises(ValidationError, match=message):
        _validate(State("x", None), Button("b", on_click=ref))


def test_db_operation_table_matches_the_registry_args():
    # Every argument an op can take must be a declared arg of the capability.
    declared = set(PLATFORM_API_REGISTRY["db"].args)
    assert "op" in declared
    for op, (required, optional) in DB_OPERATIONS.items():
        assert set(required + optional) <= declared, op


# --- 3. HTML ---------------------------------------------------------------


def test_html_renders_db_click_attributes_with_state_marker():
    ir = _ir(State("text", ""), Button("Save", on_click=PlatformAPI.db.set("draft", Bind("text"))))
    html = HTMLBackend().render(ir)["index.html"]
    assert 'data-ark-on-click="platform:db"' in html
    assert "data-ark-platform-api-args" in html
    assert "__state__" in html
    assert "data-ark-action-state" not in html


# --- 4. JS backend ----------------------------------------------------------


def _js(*nodes):
    return JSBackend().render(_ir(*nodes))[SCRIPT_PATH]


def test_js_ships_no_db_code_when_unused():
    js = _js(Button("Notify", on_click=PlatformAPI.notify("Hi")))
    assert "arkDbBridge" not in js
    assert "indexedDB" not in js
    assert "db: (function" not in js


def test_js_ships_db_fragment_when_used_and_not_the_others():
    js = _js(Button("Load", on_click=PlatformAPI.db.delete("k")))
    assert "db: (function" in js
    assert "arkDbBridge" in js
    assert "indexedDB" in js
    assert "notify: function" not in js
    assert "clipboard_write: function" not in js
    assert "var platformApis = {" in js
    assert "wireClickInterceptor" in js


def test_js_db_fragment_shipped_once_however_many_calls():
    js = _js(
        State("t", ""),
        Button("a", on_click=PlatformAPI.db.set("k", Bind("t"))),
        Button("b", on_click=PlatformAPI.db.get("k", into="t")),
        Button("c", on_click=PlatformAPI.db.delete("k")),
    )
    assert js.count("db: (function") == 1


def test_js_db_coexists_with_other_platform_apis():
    js = _js(
        Button("a", on_click=PlatformAPI.db.delete("k")),
        Button("b", on_click=PlatformAPI.notify("Hi")),
    )
    assert "db: (function" in js
    assert "notify: function" in js


def test_js_click_interceptor_resolves_bind_and_passes_store_to_platform_apis():
    js = _js(State("t", ""), Button("s", on_click=PlatformAPI.db.set("k", Bind("t"))))
    assert "resolveActionArgs(platformStore, platformArgs)" in js
    assert "platformApi(platformArgs, platformStore)" in js


def test_js_db_runtime_has_no_eval_or_new_function():
    js = _js(
        State("t", ""),
        Button("s", on_click=PlatformAPI.db.set("k", Bind("t"))),
        Button("g", on_click=PlatformAPI.db.get("k", into="t")),
    )
    assert "eval(" not in js
    assert "new Function(" not in js


def test_js_db_page_with_no_state_still_works_without_a_store():
    js = _js(Button("d", on_click=PlatformAPI.db.delete("k")))
    assert "createState" not in js
    assert "function () { return null; }" in js


# --- 5. Backend support ------------------------------------------------------


def test_only_web_implements_db_on_main():
    # "android" would be listed here with a SQLite engine, but that backend
    # is excluded from `main` (sync plan Stage 11), so it stays empty.
    assert "db" in BACKEND_PLATFORM_API_SUPPORT["web"]
    assert "db" not in BACKEND_PLATFORM_API_SUPPORT["android"]
    assert "db" not in BACKEND_PLATFORM_API_SUPPORT["desktop"]


def test_check_backend_support_passes_db_for_web():
    check_backend_support({"db"}, backend_name="web")


def test_check_backend_support_rejects_db_for_android():
    with pytest.raises(PlatformAPIError, match="not implemented by backend 'android'"):
        check_backend_support({"db"}, backend_name="android")


def test_check_backend_support_rejects_db_for_desktop():
    with pytest.raises(PlatformAPIError, match="not implemented by backend 'desktop'"):
        check_backend_support({"db"}, backend_name="desktop")


def test_search_reports_db_and_its_backends():
    from arklight.cli.search import _format_platform_api_spec

    text = _format_platform_api_spec("db", PLATFORM_API_REGISTRY["db"])
    assert text.startswith("PlatformAPI.db")
    assert "implemented by : web" in text


# --- 6. Node: run the shipped JavaScript --------------------------------------

NODE = shutil.which("node")
needs_node = pytest.mark.skipif(not NODE, reason="node not available in this environment")


def _run_node(script: str) -> list:
    proc = subprocess.run([NODE, "-e", script], capture_output=True, text=True)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    return [json.loads(line) for line in proc.stdout.strip().splitlines()]


# A minimal in-memory IndexedDB: enough of open/transaction/objectStore
# (put/get/delete/getAllKeys, completion after each request) for the
# fragment's own usage. It tests the fragment's logic, not the browser's IDB.
_IDB_STUB = """
var idbData = {};
var indexedDB = {
  open: function () {
    var request = {};
    setTimeout(function () {
      request.result = {
        createObjectStore: function () {},
        transaction: function () {
          var t = { oncomplete: null, onerror: null, onabort: null };
          t.objectStore = function () {
            function req(fn) {
              var r = { result: undefined };
              setTimeout(function () {
                r.result = fn();
                setTimeout(function () { if (t.oncomplete) t.oncomplete(); }, 0);
              }, 0);
              return r;
            }
            return {
              put: function (v, k) { return req(function () { idbData[k] = v; return k; }); },
              get: function (k) { return req(function () { return idbData[k]; }); },
              "delete": function (k) { return req(function () { delete idbData[k]; }); },
              getAllKeys: function () { return req(function () { return Object.keys(idbData); }); }
            };
          };
          return t;
        }
      };
      if (request.onupgradeneeded) request.onupgradeneeded();
      if (request.onsuccess) request.onsuccess();
    }, 0);
    return request;
  }
};
"""

_STORE_STUB = """
var notes = [];
function arkNotify(msg) { notes.push(msg); }
function arkReportError(msg, err) { notes.push("ERR " + msg + " " + (err && err.message)); }
function makeStore(initial) {
  var state = Object.assign({}, initial);
  return { get: function (k) { return state[k]; }, set: function (k, v) { state[k] = v; }, all: state };
}
var settle = function () { return new Promise(function (r) { setTimeout(r, 40); }); };
"""


def _db_script(body: str, *, window: str = "var window = {};") -> str:
    return "\n".join(
        [
            _STORE_STUB,
            _IDB_STUB,
            window,
            "var platformApis = {\n" + DB_FRAGMENT + "\n};",
            "var db = platformApis.db;",
            "(async function () {\n" + body + "\n})().catch(function (e) { console.log(JSON.stringify('FAIL ' + e.stack)); });",
        ]
    )


@needs_node
def test_node_db_roundtrip_prefix_sort_delete_on_indexeddb_path():
    body = """
    var s = makeStore({});
    db({ op: "set", key: "draft:2", value: "two" }, s);
    db({ op: "set", key: "draft:1", value: { a: [1, null] } }, s);
    db({ op: "set", key: "other", value: 3 }, s);
    db({ op: "set", key: "nothing", value: null }, s);
    db({ op: "get", key: "draft:1", into: "x" }, s);
    db({ op: "get", key: "missing", into: "y" }, s);
    db({ op: "get", key: "nothing", into: "z" }, s);
    db({ op: "keys", into: "all" }, s);
    db({ op: "keys", into: "drafts", prefix: "draft" }, s);
    await settle();
    db({ op: "delete", key: "draft:1" }, s);
    db({ op: "delete", key: "never-there" }, s);
    db({ op: "keys", into: "after", prefix: "draft" }, s);
    await settle();
    console.log(JSON.stringify([s.all.x, s.all.y, s.all.z, s.all.all, s.all.drafts, s.all.after, notes]));
    """
    (result,) = _run_node(_db_script(body))
    x, y, z, all_keys, drafts, after, notes = result
    assert x == {"a": [1, None]}
    assert y is None  # missing key
    assert z is None  # stored null reads back as null
    assert all_keys == ["draft:1", "draft:2", "nothing", "other"]  # sorted
    assert drafts == ["draft:1", "draft:2"]
    assert after == ["draft:2"]
    assert notes == []


@needs_node
def test_node_db_preserves_request_order_for_back_to_back_calls():
    body = """
    var s = makeStore({});
    db({ op: "set", key: "seq", value: 1 }, s);
    db({ op: "set", key: "seq", value: 2 }, s);
    db({ op: "get", key: "seq", into: "v" }, s);
    await settle();
    console.log(JSON.stringify(s.all.v));
    """
    assert _run_node(_db_script(body)) == [2]


@needs_node
def test_node_db_empty_key_notifies_instead_of_throwing():
    body = """
    var s = makeStore({});
    db({ op: "set", key: "", value: 1 }, s);
    db({ op: "get", key: null, into: "x" }, s);
    await settle();
    console.log(JSON.stringify(notes));
    """
    (notes,) = _run_node(_db_script(body))
    assert len(notes) == 2


@needs_node
def test_node_db_without_indexeddb_shows_notice_not_error():
    script = "\n".join(
        [
            _STORE_STUB,
            "var window = {};",  # no indexedDB, no bridge
            "var platformApis = {\n" + DB_FRAGMENT + "\n};",
            "(async function () {",
            "  platformApis.db({ op: 'set', key: 'k', value: 1 }, makeStore({}));",
            "  await settle();",
            "  console.log(JSON.stringify(notes));",
            "})();",
        ]
    )
    (notes,) = _run_node(script)
    assert len(notes) == 1 and "local storage" in notes[0]


_BRIDGE_STUB = """
var table = {};
var bridge = {
  onmessage: null,
  sent: [],
  postMessage: function (text) {
    var req = JSON.parse(text);
    bridge.sent.push(req);
    var ok = true, result = null, error;
    if (req.op === "set") table[req.key] = req.value;
    else if (req.op === "get") result = req.key in table ? table[req.key] : null;
    else if (req.op === "delete") delete table[req.key];
    else if (req.op === "keys") result = Object.keys(table);
    else { ok = false; error = "unknown op"; }
    if (bridge.fail) { ok = false; error = "boom"; }
    setTimeout(function () {
      bridge.onmessage({ data: JSON.stringify({ id: req.id, ok: ok, result: result, error: error }) });
    }, 1);
  }
};
"""


@needs_node
def test_node_db_uses_the_android_bridge_when_present_never_indexeddb():
    script = "\n".join(
        [
            _STORE_STUB,
            _BRIDGE_STUB,
            "var window = { arkDbBridge: bridge };",  # note: no indexedDB defined at all
            "var platformApis = {\n" + DB_FRAGMENT + "\n};",
            "(async function () {",
            "  var s = makeStore({});",
            "  var db = platformApis.db;",
            "  db({ op: 'set', key: 'b:1', value: { q: 1 } }, s);",
            "  db({ op: 'set', key: 'a:1', value: 'x' }, s);",
            "  db({ op: 'get', key: 'b:1', into: 'g' }, s);",
            "  db({ op: 'keys', into: 'k', prefix: '' }, s);",
            "  await settle();",
            "  db({ op: 'delete', key: 'a:1' }, s);",
            "  db({ op: 'keys', into: 'k2', prefix: 'a' }, s);",
            "  await settle();",
            "  bridge.fail = true;",
            "  db({ op: 'set', key: 'z', value: 1 }, s);",
            "  await settle();",
            "  console.log(JSON.stringify([s.all.g, s.all.k, s.all.k2, notes.length, bridge.sent[0]]));",
            "})();",
        ]
    )
    ((g, keys, keys_after_delete, note_count, first_request),) = _run_node(script)
    assert g == {"q": 1}
    assert keys == ["a:1", "b:1"]
    assert keys_after_delete == []
    assert note_count == 1  # the bridge error surfaced as a notice
    # Wire format: values cross as JSON *text*, ids are integers.
    assert first_request == {"id": 1, "op": "set", "key": "b:1", "value": '{"q":1}'}


@needs_node
def test_node_click_interceptor_resolves_bind_and_hands_the_store_to_db():
    script = "\n".join(
        [
            _STORE_STUB,
            _IDB_STUB,
            "var window = {};",
            "var handlers = [];",
            "var document = { addEventListener: function (type, fn) { handlers.push(fn); } };",
            "var actions = {}; var behaviors = {};",
            "var platformApis = {\n" + DB_FRAGMENT + "\n};",
            CLICK_INTERCEPTOR_JS,
            "var store = makeStore({ text: 'hello', which: 'note' });",
            "wireClickInterceptor(function () { return store; });",
            "function click(attrs) {",
            "  var el = { getAttribute: function (k) { return k in attrs ? attrs[k] : null; } };",
            "  handlers[0]({ target: { closest: function () { return el; } },",
            "                preventDefault: function () {}, stopPropagation: function () {} });",
            "}",
            "(async function () {",
            "  click({ 'data-ark-on-click': 'platform:db',",
            "          'data-ark-platform-api-args': JSON.stringify({ op: 'set',",
            "            key: { __state__: 'which' }, value: { __state__: 'text' } }) });",
            "  await settle();",
            "  click({ 'data-ark-on-click': 'platform:db',",
            "          'data-ark-platform-api-args': JSON.stringify({ op: 'get', key: 'note', into: 'text' }) });",
            "  await settle();",
            "  console.log(JSON.stringify([idbData, store.all.text, notes]));",
            "})();",
        ]
    )
    ((stored, text_after_get, notes),) = _run_node(script)
    # Key came from state ("note"), value from state ("hello"), stored as JSON text.
    assert stored == {"note": '"hello"'}
    assert text_after_get == "hello"
    assert notes == []
