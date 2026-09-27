"""
`/` and `/index.html` are the same page. Before this fix they were
treated as different everywhere the runtime looked at the URL:
`persist=True` keyed `localStorage` by `location.pathname` (two stores
for one page, and the build rewrites nav links to `index.html`), and
the nav-highlight script compared full URLs (so "Home" was not
highlighted at the bare site root).

Executed for real under Node against minimal stand-ins for the
browser -- jsdom-style DOM/localStorage/location objects aren't
available in this environment, so these build the smallest possible
fakes by hand.
"""

from __future__ import annotations

import json
import shutil
import subprocess

import pytest

from arklight.backend.js.runtime.nav import NAV_HIGHLIGHT_JS
from arklight.backend.js.runtime.state import CREATE_STATE_JS, INIT_STATE_JS

NODE = shutil.which("node")
pytestmark = pytest.mark.skipif(NODE is None, reason="node not available")


def _run(script: str) -> str:
    return subprocess.run(
        [NODE, "-e", script], capture_output=True, text=True, check=True
    ).stdout.strip()


def _persist_script(pathname: str, storage: dict, action: str) -> str:
    return f"""
    var notified = [];
    var _store = {json.dumps(storage)};
    var localStorage = {{
      getItem: function (k) {{ return Object.prototype.hasOwnProperty.call(_store, k) ? _store[k] : null; }},
      setItem: function (k, v) {{ _store[k] = v; }}
    }};
    var location = {{ pathname: {json.dumps(pathname)}, search: "", hash: "" }};
    var body = {{
      attrs: {{
        "data-ark-state": JSON.stringify({{ minutes: 25 }}),
        "data-ark-persist": JSON.stringify(["minutes"])
      }},
      getAttribute: function (n) {{ return this.attrs[n] !== undefined ? this.attrs[n] : null; }}
    }};
    var document = {{ getElementById: function () {{ return null; }}, body: body }};
    {CREATE_STATE_JS}
    {INIT_STATE_JS}
    function arkNotify(msg) {{ notified.push(msg); }}
    function arkReportError(msg) {{ arkNotify(msg); }}
    var renderBindings = function () {{}};
    var renderClassBindings = function () {{}};
    var store = initState();
    {action}
    """


def test_a_write_at_index_html_is_stored_under_the_root_key():
    out = _run(
        _persist_script(
            "/index.html", {}, 'store.set("minutes", 50); console.log(JSON.stringify(_store));'
        )
    )
    assert json.loads(out) == {"ark:/:minutes": "50"}


def test_root_and_index_html_share_one_store():
    saved_at_root = {"ark:/:minutes": "50"}
    at_index = _run(_persist_script("/index.html", saved_at_root, 'console.log(store.get("minutes"));'))
    at_root = _run(_persist_script("/", saved_at_root, 'console.log(store.get("minutes"));'))
    assert at_index == at_root == "50"


def test_a_nested_index_html_normalizes_to_its_directory():
    out = _run(
        _persist_script(
            "/blog/index.html", {}, 'store.set("minutes", 9); console.log(JSON.stringify(_store));'
        )
    )
    assert json.loads(out) == {"ark:/blog/:minutes": "9"}


def test_other_pages_are_left_alone():
    out = _run(
        _persist_script(
            "/about.html", {}, 'store.set("minutes", 9); console.log(JSON.stringify(_store));'
        )
    )
    assert json.loads(out) == {"ark:/about.html:minutes": "9"}


def test_values_saved_before_the_fix_are_still_read():
    """Nobody's existing saved state is orphaned by this change."""
    legacy = {"ark:/index.html:minutes": "42"}
    out = _run(_persist_script("/index.html", legacy, 'console.log(store.get("minutes"));'))
    assert out == "42"


def test_the_normalized_key_wins_over_a_legacy_one():
    both = {"ark:/:minutes": "50", "ark:/index.html:minutes": "42"}
    out = _run(_persist_script("/index.html", both, 'console.log(store.get("minutes"));'))
    assert out == "50"


def test_only_one_localstorage_lookup_when_already_normalized():
    """`/` (no trailing index.html to strip) needs no fallback lookup."""
    out = _run(
        f"""
        var calls = 0;
        var _store = {{}};
        var localStorage = {{
          getItem: function (k) {{ calls++; return null; }},
          setItem: function () {{}}
        }};
        var location = {{ pathname: "/", search: "", hash: "" }};
        var body = {{
          attrs: {{
            "data-ark-state": JSON.stringify({{ minutes: 25 }}),
            "data-ark-persist": JSON.stringify(["minutes"])
          }},
          getAttribute: function (n) {{ return this.attrs[n] !== undefined ? this.attrs[n] : null; }}
        }};
        var document = {{ getElementById: function () {{ return null; }}, body: body }};
        {CREATE_STATE_JS}
        {INIT_STATE_JS}
        function arkNotify() {{}}
        function arkReportError() {{}}
        var renderBindings = function () {{}};
        var renderClassBindings = function () {{}};
        initState();
        console.log(calls);
        """
    )
    assert out == "1"


def _nav_script(href: str, link_hrefs: list[str]) -> str:
    return f"""
    var location = {{ href: {json.dumps(href)} }};
    var links = {json.dumps(link_hrefs)}.map(function (h) {{
      var cls = [];
      return {{ href: h, classList: {{ add: function (c) {{ cls.push(c); }} }}, cls: cls }};
    }});
    var document = {{ querySelectorAll: function () {{ return links; }} }};
    {NAV_HIGHLIGHT_JS}
    highlightActiveNavLink();
    console.log(JSON.stringify(links.map(function (l) {{ return l.cls.length; }})));
    """


@pytest.mark.parametrize(
    "here",
    ["https://example.test/", "https://example.test/index.html", "https://example.test/#top"],
)
def test_home_link_is_highlighted_at_the_root_and_at_index_html(here):
    out = _run(
        _nav_script(here, ["https://example.test/index.html", "https://example.test/about.html"])
    )
    assert json.loads(out) == [1, 0]


def test_about_link_is_highlighted_on_the_about_page_only():
    out = _run(
        _nav_script(
            "https://example.test/about.html",
            ["https://example.test/index.html", "https://example.test/about.html"],
        )
    )
    assert json.loads(out) == [0, 1]


def test_a_root_link_is_also_matched_from_index_html():
    out = _run(_nav_script("https://example.test/index.html", ["https://example.test/"]))
    assert json.loads(out) == [1]
