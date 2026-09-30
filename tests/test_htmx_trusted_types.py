"""
Tests for the "boosted links are dead" fix on `Site(app_shell=True)`.

Root cause: the CSP `csp.py` emits (`require-trusted-types-for 'script'`)
makes Chromium / Android WebView reject a plain string at every HTML or
script injection sink -- and vendored HTMX has several on the boosted
navigation path (`Document.parseHTMLUnsafe()` / `DOMParser.parseFromString()`
in `I()`, the `hx-preserve` pantry `insertAdjacentHTML`, `<script>`
re-creation). The XHR succeeded, the parse threw a `TypeError`, nothing
swapped, and the link looked dead.

Three pieces are pinned here:

1. `arklight/backend/js/htmx.py`'s `_apply_trusted_types_patch` routes
   exactly those sinks through one closure-scoped policy,
   `arklight-htmx`, which `csp.py` allow-lists.
2. `wireHtmxErrorHandling()` degrades a boosted GET whose request or
   swap failed into one real navigation, instead of a dead link.
3. On `file://` (where XHR can never work) the runtime switches
   `hx-boost` off before HTMX's init reads it and says so once.
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess

import pytest

from arklight.api import Button, Action, Page, State
from arklight.backend.js import htmx
from arklight.backend.js.htmx import (
    HTMX_JS,
    HTMX_UPSTREAM_JS,
    _TT_PRELUDE,
    _TT_REPLACEMENTS,
    _apply_trusted_types_patch,
)
from arklight.backend.js.render import SCRIPT_PATH, JSBackend
from arklight.backend.js.runtime import (
    APP_SHELL_FILE_PROTOCOL_BOOST_OFF_JS,
    APP_SHELL_FILE_PROTOCOL_CHECK_JS,
    HTMX_ERROR_HANDLING_JS,
)
from arklight.ir.build import build_website_ir
from arklight.ir.normalize import normalize_ark_ast
from arklight.ir.validate import validate_ark_ast

NODE = shutil.which("node")
needs_node = pytest.mark.skipif(not NODE, reason="node not available in this environment")


def _run_node(script: str) -> list[str]:
    result = subprocess.run([NODE, "-e", script], capture_output=True, text=True, check=True)
    return result.stdout.strip().splitlines()


def _js(pages, *, app_shell=False) -> str:
    normalized = normalize_ark_ast(pages)
    validate_ark_ast(normalized)
    ir = build_website_ir("site", normalized, app_shell=app_shell)
    return JSBackend().render(ir)[SCRIPT_PATH]


_PAGES = {"/": Page(State("n", 0), Button("+", on_click=Action.increment("n")))}


# ---------------------------------------------------------------------------
# 1. The vendored-htmx Trusted Types patch
# ---------------------------------------------------------------------------


def test_upstream_literal_is_untouched_and_shipped_bytes_are_the_patched_one():
    assert "arkTT" not in HTMX_UPSTREAM_JS
    assert HTMX_UPSTREAM_JS.startswith('var htmx=function(){"use strict";const Q=')
    assert HTMX_JS != HTMX_UPSTREAM_JS
    assert HTMX_JS.startswith('var htmx=function(){"use strict";' + _TT_PRELUDE)
    # Removing the patch's additions gives back the upstream bytes exactly.
    assert _apply_trusted_types_patch(HTMX_UPSTREAM_JS) == HTMX_JS


def test_every_anchor_matches_upstream_exactly_once():
    for old, _new in _TT_REPLACEMENTS:
        assert HTMX_UPSTREAM_JS.count(old) == 1, old[:60]


def test_patch_fails_loudly_when_an_anchor_disappears():
    # A future htmx bump that changes a sink must not silently ship an
    # unpatched (dead-link) runtime.
    with pytest.raises(RuntimeError, match="Trusted Types patch anchor"):
        _apply_trusted_types_patch(HTMX_UPSTREAM_JS.replace("parseHTMLUnsafe", "parseHTMLUnsafeX"))


def test_no_unwrapped_trusted_types_sink_is_left_in_shipped_htmx():
    js = HTMX_JS
    # DOMParser / parseHTMLUnsafe: only ever fed through arkTT.h(...)
    assert re.findall(r"parseHTMLUnsafe\((?!arkTT\.h\()", js) == []
    assert re.findall(r"parseFromString\((?!arkTT\.h\()", js) == []
    # insertAdjacentHTML: the pantry call is wrapped. (The indicator-style
    # call in `Wn()` is unwrapped on purpose -- it is switched off with
    # `htmx.config.includeIndicatorStyles = false`, see js/render.py.)
    assert 'insertAdjacentHTML("afterend",arkTT.h(' in js
    assert 'insertAdjacentHTML("afterend",' in js and js.count('insertAdjacentHTML("afterend",') == 1
    # Script re-creation.
    assert "t.textContent=arkTT.s(e.textContent)" in js
    assert 'arkTT.u(e.value)' in js
    # Nothing assigns innerHTML/outerHTML from a string.
    assert re.findall(r"\.(?:innerHTML|outerHTML)\s*=[^=]", js) == []


def test_preserved_script_with_a_live_twin_is_neutralized_not_recreated():
    # On `moveBefore` browsers (Chromium 133+ / current Android WebView)
    # htmx inserts the fresh copy of `<script id="ark-runtime" hx-preserve>`
    # into the live document before swapping the preserved original back
    # in, and a script parsed by parseHTMLUnsafe still executes on
    # insertion -- re-running the whole runtime on every boosted swap
    # (found in a real Chromium 153 run: a duplicate
    # `createPolicy("arklight-htmx")`, doubled listeners).
    assert (
        '&&e.id&&te().getElementById(e.id)){e.type="text/x-arklight-preserved";return}' in HTMX_JS
    )
    # Only a preserved script that has a live counterpart is skipped;
    # everything else still goes through r() and executes as before.
    assert "const t=r(e);const n=e.parentNode;" in HTMX_JS


def test_indicator_styles_stay_switched_off_in_the_generated_runtime():
    # The one remaining un-wrapped sink relies on this.
    js = _js(_PAGES, app_shell=True)
    assert "htmx.config.includeIndicatorStyles = false;" in js


def test_generated_runtime_contains_the_patched_htmx_and_still_parses():
    js = _js(_PAGES, app_shell=True)
    assert HTMX_JS in js
    assert "arkTT" in js
    if NODE:
        import tempfile

        with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False) as fh:
            fh.write(js)
        subprocess.run([NODE, "--check", fh.name], check=True)


def _prelude_script(setup: str, body: str) -> str:
    return f"""
    {setup}
    {_TT_PRELUDE}
    {body}
    """


@needs_node
def test_policy_is_named_arklight_htmx_and_wraps_all_three_kinds():
    script = _prelude_script(
        """
        var created = [];
        var window = { trustedTypes: { createPolicy: function (name, rules) {
          created.push(name);
          return {
            createHTML: function (s) { return { kind: "html", v: rules.createHTML(s) }; },
            createScript: function (s) { return { kind: "script", v: rules.createScript(s) }; },
            createScriptURL: function (s) { return { kind: "url", v: rules.createScriptURL(s) }; }
          };
        } } };
        """,
        """
        process.stdout.write(JSON.stringify({
          created: created, h: arkTT.h("<p>"), s: arkTT.s("x()"), u: arkTT.u("a.js")
        }) + "\\n");
        """,
    )
    out = json.loads(_run_node(script)[0])
    assert out["created"] == ["arklight-htmx"]
    assert out["h"] == {"kind": "html", "v": "<p>"}
    assert out["s"] == {"kind": "script", "v": "x()"}
    assert out["u"] == {"kind": "url", "v": "a.js"}


@needs_node
def test_wrapper_degrades_to_plain_strings_without_trusted_types():
    script = _prelude_script(
        "var window = {};",
        'process.stdout.write(JSON.stringify([arkTT.h("<p>"), arkTT.s("s"), arkTT.u("u")]) + "\\n");',
    )
    assert json.loads(_run_node(script)[0]) == ["<p>", "s", "u"]


@needs_node
def test_wrapper_degrades_when_the_csp_does_not_allow_list_the_policy():
    # createPolicy throws for a name outside the CSP's trusted-types
    # list; the runtime must still load (and fall back to plain strings).
    script = _prelude_script(
        """
        var window = { trustedTypes: { createPolicy: function () {
          throw new TypeError("Policy arklight-htmx disallowed");
        } } };
        """,
        'process.stdout.write(JSON.stringify(arkTT.h("<p>")) + "\\n");',
    )
    assert json.loads(_run_node(script)[0]) == "<p>"


def test_policy_object_is_not_reachable_from_outside_htmx_closure():
    # Declared with `const` inside `var htmx=function(){...}`, never
    # assigned to window / Q / the htmx public object.
    assert HTMX_JS.count("arkTT=") == 1
    assert "window.arkTT" not in HTMX_JS
    assert "Q.arkTT" not in HTMX_JS


# ---------------------------------------------------------------------------
# 2. Dead boosted link -> one real navigation
# ---------------------------------------------------------------------------


def _fallback_script(body: str) -> str:
    return f"""
    var reported = [];
    var assigned = [];
    function arkReportError(msg, err) {{ reported.push(msg); }}
    var handlers = {{}};
    var document = {{ body: {{ addEventListener: function (t, fn) {{ handlers[t] = fn; }} }} }};
    var window = {{ location: {{ assign: function (u) {{ assigned.push(u); }} }} }};
    {HTMX_ERROR_HANDLING_JS}
    wireHtmxErrorHandling();
    function detail(extra) {{
      var d = {{ boosted: true, requestConfig: {{ verb: "get" }},
                 pathInfo: {{ requestPath: "about.html", finalRequestPath: "about.html" }},
                 elt: {{ tagName: "A", href: "https://x.test/site/about.html" }} }};
      for (var k in extra) d[k] = extra[k];
      return d;
    }}
    {body}
    process.stdout.write(JSON.stringify({{ assigned: assigned, reported: reported.length }}) + "\\n");
    """


@needs_node
@pytest.mark.parametrize("event", ["htmx:sendError", "htmx:swapError", "htmx:onLoadError"])
def test_failed_boosted_get_falls_back_to_a_real_navigation(event):
    out = json.loads(_run_node(_fallback_script(f'handlers["{event}"]({{ detail: detail({{}}) }});'))[0])
    # The anchor's resolved href wins over the raw attribute value.
    assert out["assigned"] == ["https://x.test/site/about.html"]


@needs_node
def test_fallback_uses_the_request_path_when_the_element_is_not_a_link():
    out = json.loads(
        _run_node(
            _fallback_script(
                'handlers["htmx:sendError"]({ detail: detail({ elt: { tagName: "BODY" } }) });'
            )
        )[0]
    )
    assert out["assigned"] == ["about.html"]


@needs_node
def test_swap_error_then_onload_error_navigates_and_reports_once():
    # htmx fires both for one failed swap.
    out = json.loads(
        _run_node(
            _fallback_script(
                'handlers["htmx:swapError"]({ detail: detail({}) });'
                'handlers["htmx:onLoadError"]({ detail: detail({}) });'
            )
        )[0]
    )
    assert len(out["assigned"]) == 1
    assert out["reported"] == 1


@needs_node
def test_fallback_never_replays_a_non_get_request():
    out = json.loads(
        _run_node(
            _fallback_script(
                'handlers["htmx:sendError"]({ detail: detail({ requestConfig: { verb: "post" } }) });'
            )
        )[0]
    )
    assert out["assigned"] == []
    assert out["reported"] == 1  # still reported, just not replayed


@needs_node
def test_fallback_ignores_requests_that_were_not_boosted_navigation():
    out = json.loads(
        _run_node(_fallback_script('handlers["htmx:sendError"]({ detail: detail({ boosted: false }) });'))[0]
    )
    assert out["assigned"] == []


@needs_node
@pytest.mark.parametrize("event", ["htmx:responseError", "htmx:timeout", "htmx:targetError", "htmx:invalidPath"])
def test_only_dead_link_failures_navigate(event):
    # The server answered (or nothing was ever cancelled): a real load
    # would show the same thing, so these keep the existing notice only.
    out = json.loads(_run_node(_fallback_script(f'handlers["{event}"]({{ detail: detail({{}}) }});'))[0])
    assert out["assigned"] == []
    assert out["reported"] == 1


@needs_node
def test_fallback_never_throws_when_location_assign_is_broken():
    script = _fallback_script("").replace(
        "assigned.push(u);", 'throw new Error("blocked");'
    ) + ""
    script = script.replace(
        'process.stdout.write',
        'handlers["htmx:sendError"]({ detail: detail({}) }); process.stdout.write',
    )
    assert json.loads(_run_node(script)[0])["assigned"] == []


# ---------------------------------------------------------------------------
# 3. file:// -> hx-boost off, told once
# ---------------------------------------------------------------------------


def _boost_off_script(protocol: str) -> str:
    return f"""
    var removed = [];
    var window = {{ location: {{ protocol: "{protocol}" }} }};
    var document = {{ body: {{ removeAttribute: function (n) {{ removed.push(n); }} }} }};
    {APP_SHELL_FILE_PROTOCOL_BOOST_OFF_JS}
    process.stdout.write(JSON.stringify(removed) + "\\n");
    """


@needs_node
def test_boost_is_removed_on_file_protocol():
    assert json.loads(_run_node(_boost_off_script("file:"))[0]) == ["hx-boost"]


@needs_node
@pytest.mark.parametrize("protocol", ["http:", "https:"])
def test_boost_is_kept_over_http(protocol):
    assert json.loads(_run_node(_boost_off_script(protocol))[0]) == []


@needs_node
def test_boost_off_never_throws_without_window_or_body():
    assert _run_node(f'{APP_SHELL_FILE_PROTOCOL_BOOST_OFF_JS}\nprocess.stdout.write("ok\\n");') == ["ok"]


@needs_node
def test_file_notice_also_goes_to_console_warn():
    script = f"""
    var warned = [], notified = [];
    var console = {{ warn: function (m) {{ warned.push(m); }} }};
    function arkNotify(m) {{ notified.push(m); }}
    var window = {{ location: {{ protocol: "file:" }} }};
    {APP_SHELL_FILE_PROTOCOL_CHECK_JS}
    warnIfAppShellServedFromFileProtocol();
    process.stdout.write(JSON.stringify({{ warned: warned, notified: notified }}) + "\\n");
    """
    out = json.loads(_run_node(script)[0])
    assert len(out["warned"]) == 1 and out["warned"][0].startswith("[ARKlight] ")
    assert "htmx is unavailable" in out["warned"][0]
    assert out["notified"] == [out["warned"][0][len("[ARKlight] ") :]]


def test_boost_off_is_emitted_before_htmx_inits_and_only_for_app_shell():
    shell = _js(_PAGES, app_shell=True)
    assert shell.count("function disableBoostOnFileProtocol()") == 1
    # Top level, right after HTMX's config lines: i.e. before the runtime
    # IIFE, so it runs before HTMX's own DOMContentLoaded init (registered
    # earlier still, inside the vendored bundle).
    boost_off = shell.index("function disableBoostOnFileProtocol()")
    assert shell.index("htmx.config.includeIndicatorStyles = false;") < boost_off
    assert boost_off < shell.index("(function () {\n  \"use strict\";")
    assert boost_off < shell.index('document.addEventListener("DOMContentLoaded", function () {')
    # ...and it really is after HTMX's own (earlier-registered) init listener,
    # which is why it must be synchronous rather than a ready-time call.
    assert shell.index('addEventListener("DOMContentLoaded",e)') < boost_off

    # A plain (non-app-shell) stateful site never boosts, so it never
    # carries the file:// machinery.
    plain = _js(_PAGES, app_shell=False)
    assert "disableBoostOnFileProtocol" not in plain
    assert "warnIfAppShellServedFromFileProtocol" not in plain


def test_error_handling_fragment_still_avoids_eval():
    for fragment in (HTMX_ERROR_HANDLING_JS, APP_SHELL_FILE_PROTOCOL_BOOST_OFF_JS):
        assert "eval(" not in fragment
        assert "new Function" not in fragment
    assert htmx  # module import kept explicit for readers grepping the tests
