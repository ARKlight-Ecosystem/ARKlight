"""
Tests for `State(..., query=..., history=...)` -- URL query-parameter
state syncing (`docs/Proposals/URL-STATE-AS-PRIMITIVE-PROPOSAL.md`,
`docs/version history/v0.064.md`). Landed as a third accepted piece
of `v0.064`, alongside `arklight search --retrieve-doc`, under the
same "make room for one more" precedent `PROGRESS.md`'s Snapshot
table already documents for `v0.041`/`v0.065`.

Mirrors `tests/test_js_vocabulary_v0063.py`'s `media=` section for the
API/Validation/IR/HTML/JS-gating coverage. The coercion, write-back,
and `popstate` round-trip logic itself -- the part that can't be
checked from compiled-output string assertions alone -- gets a real
Node.js smoke test at the bottom, same precedent
`test_js_vocabulary_v0063.py`'s
`test_node_runtime_reveal_default_toggle_class_matches_docs` and
`test_vdom_7.py`'s module docstring (jsdom-style verification of
shipped runtime fragments) already establish for this suite.
"""

from __future__ import annotations

import json
import shutil
import subprocess

import pytest

from arklight.api import Action, Bind, Button, Page, State, Text
from arklight.backend.html.render import HTMLBackend
from arklight.backend.js.render import JSBackend
from arklight.backend.js.runtime.query import WIRE_QUERY_SYNC_JS
from arklight.backend.js.runtime.state import CREATE_STATE_JS, INIT_STATE_JS
from arklight.ir.build import build_website_ir
from arklight.ir.normalize import normalize_ark_ast
from arklight.ir.schema import KNOWN_QUERY_HISTORY_MODES
from arklight.ir.validate import ValidationError, validate_ark_ast


def _ir(pages, **kwargs):
    normalized = normalize_ark_ast(pages)
    validate_ark_ast(normalized)
    return build_website_ir("site", normalized, **kwargs)


# ---------------------------------------------------------------------------
# API -- State(..., query=..., history=...)
# ---------------------------------------------------------------------------


def test_state_query_and_history_default_to_none():
    node = State("count", 0)
    assert node.props["query"] is None
    assert node.props["history"] is None


def test_state_query_and_history_round_trip_into_props():
    node = State("page", 1, query="page", history="push")
    assert node.props == {
        "name": "page",
        "initial": 1,
        "persist": False,
        "media": None,
        "query": "page",
        "history": "push",
    }


def test_state_query_is_independent_of_persist_and_media():
    # `query=` combines freely with `persist=`/`media=` -- documented as
    # mutually independent in `State(...)`'s own docstring.
    node = State(
        "is_wide",
        False,
        persist=True,
        media="(min-width: 768px)",
        query="wide",
    )
    assert node.props["persist"] is True
    assert node.props["media"] == "(min-width: 768px)"
    assert node.props["query"] == "wide"


# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------


def test_known_query_history_modes_is_replace_and_push_only():
    assert KNOWN_QUERY_HISTORY_MODES == frozenset({"replace", "push"})


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


def test_validate_accepts_legal_query_key():
    tree = Page(State("page", 1, query="page"))
    validate_ark_ast(normalize_ark_ast({"/": tree}))  # no raise


@pytest.mark.parametrize(
    "key",
    [
        "1bad",  # leading digit
        "bad key",  # whitespace
        "bad/key",  # slash
        "bad?key",  # already-reserved query-string character
        "",  # empty
    ],
)
def test_validate_rejects_illegal_query_key(key):
    tree = Page(State("bad", 1, query=key))
    with pytest.raises(ValidationError, match="query"):
        validate_ark_ast(normalize_ark_ast({"/": tree}))


def test_validate_rejects_non_string_query():
    tree = Page(State("bad", 1, query=123))  # type: ignore[arg-type]
    with pytest.raises(ValidationError, match="query"):
        validate_ark_ast(normalize_ark_ast({"/": tree}))


def test_validate_accepts_hyphen_underscore_and_dot_in_query_key():
    tree = Page(
        State("a", 1, query="sort-order"),
        State("b", 1, query="_internal"),
        State("c", 1, query="v2.page"),
    )
    validate_ark_ast(normalize_ark_ast({"/": tree}))  # no raise


def test_validate_accepts_known_history_modes():
    for mode in ("replace", "push"):
        tree = Page(State("page", 1, query="page", history=mode))
        validate_ark_ast(normalize_ark_ast({"/": tree}))  # no raise


def test_validate_rejects_unknown_history_mode():
    tree = Page(State("page", 1, query="page", history="reload"))
    with pytest.raises(ValidationError, match="history"):
        validate_ark_ast(normalize_ark_ast({"/": tree}))


def test_validate_rejects_history_without_query():
    tree = Page(State("page", 1, history="push"))
    with pytest.raises(ValidationError, match="query"):
        validate_ark_ast(normalize_ark_ast({"/": tree}))


def test_validate_leaves_plain_state_untouched():
    # No query=/history= at all -- unchanged behavior for existing
    # State(...) calls, same guarantee media= makes in v0.063.
    tree = Page(State("count", 0))
    validate_ark_ast(normalize_ark_ast({"/": tree}))  # no raise


# ---------------------------------------------------------------------------
# IR build -- IRPage.query, _query_type_tag
# ---------------------------------------------------------------------------


def test_state_without_query_leaves_query_list_empty():
    tree = Page(State("count", 0))
    ir = _ir({"/": tree})
    assert ir.pages[0].query == []


def test_query_prop_round_trips_through_ir_with_default_history_mode():
    tree = Page(State("page", 1, query="page"))
    ir = _ir({"/": tree})
    assert ir.pages[0].query == [("page", "page", "int", "replace")]


def test_query_prop_round_trips_through_ir_with_explicit_push_history():
    tree = Page(State("page", 1, query="page", history="push"))
    ir = _ir({"/": tree})
    assert ir.pages[0].query == [("page", "page", "int", "push")]


def test_query_param_name_may_differ_from_state_name():
    tree = Page(State("current_page", 1, query="p"))
    ir = _ir({"/": tree})
    assert ir.pages[0].query == [("current_page", "p", "int", "replace")]


def test_query_type_tag_bool_before_int():
    # bool is a subclass of int in Python -- must be checked first,
    # same ordering pitfall the derivations catalog already accounts
    # for.
    tree = Page(State("flag", True, query="flag"))
    ir = _ir({"/": tree})
    assert ir.pages[0].query == [("flag", "flag", "bool", "replace")]


def test_query_type_tag_str_for_non_bool_non_int_initial():
    tree = Page(State("q", "hello", query="q"))
    ir = _ir({"/": tree})
    assert ir.pages[0].query == [("q", "q", "str", "replace")]


def test_query_type_tag_str_for_none_initial():
    tree = Page(State("q", None, query="q"))
    ir = _ir({"/": tree})
    assert ir.pages[0].query == [("q", "q", "str", "replace")]


def test_multiple_query_states_preserve_declaration_order():
    tree = Page(
        State("page", 1, query="page"),
        State("show_done", True, query="show"),
        State("search", "", query="q"),
    )
    ir = _ir({"/": tree})
    assert ir.pages[0].query == [
        ("page", "page", "int", "replace"),
        ("show_done", "show", "bool", "replace"),
        ("search", "q", "str", "replace"),
    ]


def test_query_and_persist_and_media_lists_are_independent():
    tree = Page(
        State("page", 1, query="page"),
        State("saved", 0, persist=True),
        State("is_wide", False, media="(min-width: 768px)"),
    )
    ir = _ir({"/": tree})
    assert ir.pages[0].query == [("page", "page", "int", "replace")]
    assert ir.pages[0].persist == ["saved"]
    assert ir.pages[0].media == [("is_wide", "(min-width: 768px)")]


def test_state_initial_value_unaffected_by_query_prop():
    # query= carries no value of its own -- state[name] still holds
    # the server-rendered initial, same as persist=/media=.
    tree = Page(State("page", 1, query="page"))
    ir = _ir({"/": tree})
    assert ir.pages[0].state == {"page": 1}


# ---------------------------------------------------------------------------
# HTML render -- data-ark-query attribute
# ---------------------------------------------------------------------------


def test_html_render_emits_data_ark_query_attribute():
    tree = Page(State("page", 1, query="page", history="push"))
    html = HTMLBackend().render(_ir({"/": tree}))["index.html"]
    assert "data-ark-query=" in html
    assert "page" in html
    assert "int" in html
    assert "push" in html


def test_html_render_omits_data_ark_query_when_no_query_state():
    tree = Page(State("count", 0))
    html = HTMLBackend().render(_ir({"/": tree}))["index.html"]
    assert "data-ark-query=" not in html


def test_html_render_places_data_ark_query_on_state_marker_when_app_shell():
    tree = Page(State("page", 1, query="page"))
    html = HTMLBackend().render(_ir({"/": tree}, app_shell=True))["index.html"]
    assert 'id="ark-state"' in html
    marker_start = html.index('id="ark-state"')
    marker_line_end = html.index(">", marker_start)
    assert "data-ark-query=" in html[marker_start:marker_line_end]


def test_html_render_places_data_ark_query_on_body_when_not_app_shell():
    tree = Page(State("page", 1, query="page"))
    html = HTMLBackend().render(_ir({"/": tree}, app_shell=False))["index.html"]
    assert 'id="ark-state"' not in html
    body_start = html.index("<body")
    body_end = html.index(">", body_start)
    assert "data-ark-query=" in html[body_start:body_end]


# ---------------------------------------------------------------------------
# JS render -- has_query gating (only ship wireQuerySync when used)
# ---------------------------------------------------------------------------


def test_js_render_reads_data_ark_query_attribute_unconditionally_when_stateful():
    # The read/coerce/write-back half is folded directly into
    # STATE_CORE_JS/initState(), unconditionally, whenever any page has
    # state at all -- same discipline persist=/media= already hold.
    tree = Page(State("count", 0))
    js = JSBackend().render(_ir({"/": tree}))["arklight.js"]
    assert "data-ark-query" in js
    assert "coerceQueryValue" in js
    assert "serializeQueryValue" in js


def test_js_render_ships_wire_query_sync_when_query_used():
    tree = Page(State("page", 1, query="page"))
    js = JSBackend().render(_ir({"/": tree}))["arklight.js"]
    assert "function wireQuerySync" in js
    assert "wireQuerySync(function" in js
    assert 'addEventListener("popstate"' in js


def test_js_render_omits_wire_query_sync_when_query_unused():
    tree = Page(State("count", 0), Button("+", on_click=Action.increment("count", 1)))
    js = JSBackend().render(_ir({"/": tree}))["arklight.js"]
    assert "function wireQuerySync" not in js
    assert "wireQuerySync(" not in js


def test_js_render_omits_wire_query_sync_on_fully_stateless_page():
    tree = Page(Text("hello"))
    js = JSBackend().render(_ir({"/": tree}))["arklight.js"]
    assert "function wireQuerySync" not in js
    assert "data-ark-query" not in js


def test_js_render_only_ships_wire_query_sync_once_across_pages():
    ir = _ir(
        {
            "/": Page(State("page", 1, query="page")),
            "/other": Page(State("sort", "name", query="sort")),
        }
    )
    js = JSBackend().render(ir)["arklight.js"]
    assert js.count("function wireQuerySync") == 1


# ---------------------------------------------------------------------------
# End-to-end: query state combined with the rest of a page builds and
# renders cleanly.
# ---------------------------------------------------------------------------


def test_query_state_combined_with_bind_and_action():
    tree = Page(
        State("page", 1, query="page", history="push"),
        Text(Bind("page")),
        Button("Next", on_click=Action.increment("page", 1)),
    )
    ir = _ir({"/": tree})
    html = HTMLBackend().render(ir)["index.html"]
    js = JSBackend().render(ir)["arklight.js"]

    assert "data-ark-query=" in html
    assert "function wireQuerySync" in js
    assert "increment: function" in js


# ---------------------------------------------------------------------------
# Node.js smoke test: coercion, write-back, and popstate round-trip
# against the actual shipped runtime fragments (not just their
# compiled-output presence).
# ---------------------------------------------------------------------------


_NODE_HARNESS = """
'use strict';
var attrs = %(attrs)s;
var marker = {
  getAttribute: function (name) {
    return Object.prototype.hasOwnProperty.call(attrs, name) ? attrs[name] : null;
  }
};
var document = {
  getElementById: function (id) { return id === "ark-state" ? marker : null; },
  body: marker
};

function parseUrl(url) {
  var hashIdx = url.indexOf("#");
  var hash = hashIdx === -1 ? "" : url.slice(hashIdx);
  var rest = hashIdx === -1 ? url : url.slice(0, hashIdx);
  var qIdx = rest.indexOf("?");
  var search = qIdx === -1 ? "" : rest.slice(qIdx);
  var pathname = qIdx === -1 ? rest : rest.slice(0, qIdx);
  return { pathname: pathname, search: search, hash: hash };
}

var location = parseUrl(%(initial_url)s);
var historyLog = [];
var history = {
  replaceState: function (state, title, url) {
    historyLog.push(["replace", url]);
    var parsed = parseUrl(url);
    location.pathname = parsed.pathname;
    location.search = parsed.search;
    location.hash = parsed.hash;
  },
  pushState: function (state, title, url) {
    historyLog.push(["push", url]);
    var parsed = parseUrl(url);
    location.pathname = parsed.pathname;
    location.search = parsed.search;
    location.hash = parsed.hash;
  }
};

var windowListeners = {};
var window = { addEventListener: function (name, fn) { windowListeners[name] = fn; } };

function arkNotify(msg) { /* no-op in this harness */ }
function renderBindings(store) { /* no DOM in this harness */ }
function renderClassBindings(store) { /* no DOM in this harness */ }

%(create_state_js)s
%(init_state_js)s
%(wire_query_sync_js)s

var STATE_KEY = %(state_key)s;

var store = initState();
var results = {};
results.afterInit = store ? store.get(STATE_KEY) : null;

if (store) { store.set(STATE_KEY, 5); }
results.historyModeAfterSet = historyLog.length ? historyLog[historyLog.length - 1][0] : null;
results.searchAfterSet = location.search;

wireQuerySync(function () { return store; });

location.search = "?other=x&page=9";
if (windowListeners.popstate) { windowListeners.popstate(); }
results.afterPopstateWithPage = store ? store.get(STATE_KEY) : null;

location.search = "?other=x";
if (windowListeners.popstate) { windowListeners.popstate(); }
results.afterPopstateWithoutPage = store ? store.get(STATE_KEY) : null;

console.log(JSON.stringify(results));
"""


def _run_node_harness(*, attrs, initial_url, state_key="page"):
    node = shutil.which("node")
    if not node:
        pytest.skip("node not available in this environment")
    script = _NODE_HARNESS % {
        "attrs": json.dumps(attrs),
        "initial_url": json.dumps(initial_url),
        "state_key": json.dumps(state_key),
        "create_state_js": CREATE_STATE_JS,
        "init_state_js": INIT_STATE_JS,
        "wire_query_sync_js": WIRE_QUERY_SYNC_JS,
    }
    result = subprocess.run(
        [node, "-e", script], capture_output=True, text=True, check=True
    )
    return json.loads(result.stdout.strip())


def _query_attrs(*, initial=None, query_tuples=()):
    return {
        "data-ark-state": json.dumps(initial if initial is not None else {"page": 1}),
        "data-ark-computed": "[]",
        "data-ark-watch": "[]",
        "data-ark-persist": "[]",
        "data-ark-media": "[]",
        "data-ark-query": json.dumps(list(query_tuples)),
    }


def test_node_runtime_reads_url_override_on_init():
    attrs = _query_attrs(query_tuples=[["page", "page", "int", "push"]])
    results = _run_node_harness(attrs=attrs, initial_url="/?page=7")
    assert results["afterInit"] == 7


def test_node_runtime_falls_back_to_initial_on_missing_query_param():
    attrs = _query_attrs(query_tuples=[["page", "page", "int", "push"]])
    results = _run_node_harness(attrs=attrs, initial_url="/")
    assert results["afterInit"] == 1


def test_node_runtime_falls_back_to_initial_on_malformed_query_value():
    attrs = _query_attrs(query_tuples=[["page", "page", "int", "push"]])
    results = _run_node_harness(attrs=attrs, initial_url="/?page=not-a-number")
    assert results["afterInit"] == 1


def test_node_runtime_writes_back_via_push_state_when_history_is_push():
    attrs = _query_attrs(query_tuples=[["page", "page", "int", "push"]])
    results = _run_node_harness(attrs=attrs, initial_url="/")
    assert results["historyModeAfterSet"] == "push"
    assert "page=5" in results["searchAfterSet"]


def test_node_runtime_writes_back_via_replace_state_when_history_is_replace():
    attrs = _query_attrs(query_tuples=[["page", "page", "int", "replace"]])
    results = _run_node_harness(attrs=attrs, initial_url="/")
    assert results["historyModeAfterSet"] == "replace"
    assert "page=5" in results["searchAfterSet"]


def test_node_runtime_popstate_applies_url_carried_value():
    attrs = _query_attrs(query_tuples=[["page", "page", "int", "push"]])
    results = _run_node_harness(attrs=attrs, initial_url="/")
    assert results["afterPopstateWithPage"] == 9


def test_node_runtime_popstate_falls_back_to_server_default_when_param_absent():
    attrs = _query_attrs(
        initial={"page": 1}, query_tuples=[["page", "page", "int", "push"]]
    )
    results = _run_node_harness(attrs=attrs, initial_url="/")
    # The second popstate simulation in the harness drops ?page from the
    # URL entirely -- wireQuerySync must fall back to the server-
    # rendered default (1), not leave the post-set value (5)/prior
    # popstate value (9) stuck.
    assert results["afterPopstateWithoutPage"] == 1


def test_node_runtime_bool_coercion_round_trips():
    attrs = _query_attrs(
        initial={"show": False}, query_tuples=[["show", "show", "bool", "replace"]]
    )
    results = _run_node_harness(attrs=attrs, initial_url="/?show=true", state_key="show")
    assert results["afterInit"] is True
