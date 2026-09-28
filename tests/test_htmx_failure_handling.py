"""
Tests for closing two gaps `htmx-4` (`Site(app_shell=True)`) left open:

1. HTMX's own request/swap failures (`htmx:responseError`,
   `htmx:sendError`, `htmx:timeout`, `htmx:swapError`,
   `htmx:targetError`, `htmx:invalidPath`) previously went nowhere --
   nothing on the page ever listened for them, so a failed boosted
   navigation just silently did nothing. `wireHtmxErrorHandling()`
   (`arklight/backend/js/runtime/notify.py`) funnels every one of them
   into `arkReportError`, same as any other runtime failure.
2. An `app_shell` page opened directly from disk (`file://...`)
   instead of served over http(s) has every boosted link silently fail
   (browsers refuse XHR against `file://`). `warnIfAppShellServed
   FromFileProtocol()` checks `location.protocol` once and calls
   `arkNotify` directly, since some browsers never even dispatch HTMX's
   own failure events in that case.

Both ship wherever `needs_htmx` is true (a plain nav-only `app_shell`
page included), and `needs_notify` is widened to match so `arkNotify`/
`arkReportError` exist for them to call into.

Node-execution tests mirror `tests/test_runtime_error_handling.py`'s
approach: run the real fragment source with only the globals it reads
stubbed out.
"""

from __future__ import annotations

import json
import shutil
import subprocess

import pytest

from arklight.api import Action, Button, Page, State, Text
from arklight.backend.js.render import SCRIPT_PATH, JSBackend
from arklight.backend.js.runtime import (
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


def _ir(pages, *, app_shell=False):
    normalized = normalize_ark_ast(pages)
    validate_ark_ast(normalized)
    return build_website_ir("site", normalized, app_shell=app_shell)


def _js(pages, *, app_shell=False) -> str:
    return JSBackend().render(_ir(pages, app_shell=app_shell))[SCRIPT_PATH]


# ---------------------------------------------------------------------------
# Shipping / gating
# ---------------------------------------------------------------------------


def test_plain_static_page_ships_neither_fragment():
    js = _js({"/": Page(Text("hi"))})
    assert "wireHtmxErrorHandling" not in js
    assert "warnIfAppShellServedFromFileProtocol" not in js
    assert "function arkNotify" not in js


def test_stateful_page_with_no_hx_trigger_and_no_app_shell_ships_neither():
    # Action.increment(...) with no .with_modifiers(...)/.debounce(...)/
    # .throttle(...) compiles to no hx-trigger attribute at all, so
    # needs_htmx stays False here -- unchanged "only ship what's used"
    # behavior from before this change.
    js = _js({"/": Page(State("n", 0), Button("+", on_click=Action.increment("n")))})
    assert "wireHtmxErrorHandling" not in js
    assert "warnIfAppShellServedFromFileProtocol" not in js
    # The pre-existing error funnel is still shipped (has_state alone).
    assert "function arkReportError" in js


def test_hx_trigger_page_ships_htmx_error_handling_but_not_file_check():
    js = _js(
        {
            "/": Page(
                State("n", 0),
                Button("+", on_click=Action.increment("n").debounce(300)),
            )
        }
    )
    assert "function wireHtmxErrorHandling()" in js
    assert "wireHtmxErrorHandling();" in js
    # Not an app_shell site -- the file:// check is irrelevant here.
    assert "warnIfAppShellServedFromFileProtocol" not in js


def test_plain_nav_only_app_shell_page_ships_both_fragments():
    # No state, no behaviors, no hx-trigger anywhere -- previously
    # shipped HTMX itself (needs_htmx = ir.app_shell) but none of the
    # notify machinery it would need to report a failure through.
    js = _js({"/": Page(Text("hi"))}, app_shell=True)
    assert "function wireHtmxErrorHandling()" in js
    assert "function warnIfAppShellServedFromFileProtocol()" in js
    assert "function arkNotify" in js
    assert "function arkReportError" in js
    assert "wireHtmxErrorHandling();" in js
    assert "warnIfAppShellServedFromFileProtocol();" in js


def test_both_registered_exactly_once_at_ready_never_from_init_page():
    js = _js({"/": Page(Text("hi"))}, app_shell=True)
    assert js.count("wireHtmxErrorHandling();") == 1
    assert js.count("warnIfAppShellServedFromFileProtocol();") == 1
    init_page = js.split("function arkInitPage() {")[1].split("\n  }\n")[0]
    assert "wireHtmxErrorHandling" not in init_page
    assert "warnIfAppShellServedFromFileProtocol" not in init_page
    ready = js.split('document.addEventListener("DOMContentLoaded", function () {')[1].split("  });")[0]
    assert "wireHtmxErrorHandling();" in ready
    assert "warnIfAppShellServedFromFileProtocol();" in ready


def test_app_shell_does_not_reregister_after_boosted_swap():
    js = _js({"/": Page(Text("hi"))}, app_shell=True)
    after_settle = js.split('addEventListener("htmx:afterSettle", arkInitPage);')[0]
    # arkInitPage itself (called from both DOMContentLoaded and
    # htmx:afterSettle) never mentions either new function -- both are
    # registered once, outside arkInitPage, same contract as
    # wireErrorBoundary/wireClickInterceptor.
    init_page = js.split("function arkInitPage() {")[1].split("\n  }\n")[0]
    assert "wireHtmxErrorHandling" not in init_page
    assert "warnIfAppShellServedFromFileProtocol" not in init_page
    assert 'addEventListener("htmx:afterSettle", arkInitPage);' in js


def test_new_fragments_never_use_eval_or_new_function():
    for fragment in (HTMX_ERROR_HANDLING_JS, APP_SHELL_FILE_PROTOCOL_CHECK_JS):
        assert "eval(" not in fragment
        assert "new Function" not in fragment


def test_generated_runtime_still_parses_for_app_shell_site():
    js = _js(
        {"/": Page(State("n", 0), Button("+", on_click=Action.increment("n").debounce(300)))},
        app_shell=True,
    )
    if NODE:
        import tempfile

        with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False) as fh:
            fh.write(js)
        subprocess.run([NODE, "--check", fh.name], check=True)


# ---------------------------------------------------------------------------
# wireHtmxErrorHandling(): each failure event reaches arkReportError
# ---------------------------------------------------------------------------


def _htmx_error_script(body: str) -> str:
    return f"""
    var reported = [];
    function arkReportError(msg, err) {{ reported.push([msg, err]); }}
    var handlers = {{}};
    var document = {{ body: {{ addEventListener: function (type, fn) {{ handlers[type] = fn; }} }} }};
    {HTMX_ERROR_HANDLING_JS}
    wireHtmxErrorHandling();
    {body}
    process.stdout.write(JSON.stringify({{ reported: reported, registered: Object.keys(handlers) }}) + "\\n");
    """


@needs_node
def test_wire_htmx_error_handling_registers_every_failure_event():
    out = json.loads(_run_node(_htmx_error_script(""))[0])
    assert sorted(out["registered"]) == sorted(
        [
            "htmx:responseError",
            "htmx:sendError",
            "htmx:timeout",
            "htmx:swapError",
            "htmx:targetError",
            "htmx:invalidPath",
            "htmx:onLoadError",
        ]
    )


@needs_node
def test_wire_htmx_error_handling_reports_response_error_with_detail_error():
    script = _htmx_error_script(
        'handlers["htmx:responseError"]({ detail: { error: "Response Status Error Code 500" } });'
    )
    out = json.loads(_run_node(script)[0])
    assert len(out["reported"]) == 1
    assert out["reported"][0][1] == "Response Status Error Code 500"


@needs_node
def test_wire_htmx_error_handling_tolerates_missing_detail():
    script = _htmx_error_script('handlers["htmx:sendError"](undefined);')
    out = json.loads(_run_node(script)[0])
    assert len(out["reported"]) == 1
    assert out["reported"][0][1] is None


@needs_node
def test_wire_htmx_error_handling_never_throws_when_reporter_is_broken():
    script = f"""
    var handlers = {{}};
    var document = {{ body: {{ addEventListener: function (type, fn) {{ handlers[type] = fn; }} }} }};
    function arkReportError() {{ throw new Error("reporter down"); }}
    {HTMX_ERROR_HANDLING_JS}
    wireHtmxErrorHandling();
    handlers["htmx:timeout"]({{}});
    handlers["htmx:invalidPath"](undefined);
    process.stdout.write("ok\\n");
    """
    assert _run_node(script) == ["ok"]


# ---------------------------------------------------------------------------
# warnIfAppShellServedFromFileProtocol(): the file:// check itself
# ---------------------------------------------------------------------------


def _file_check_script(protocol: str) -> str:
    return f"""
    var notified = [];
    function arkNotify(msg) {{ notified.push(msg); }}
    var window = {{ location: {{ protocol: "{protocol}" }} }};
    {APP_SHELL_FILE_PROTOCOL_CHECK_JS}
    warnIfAppShellServedFromFileProtocol();
    process.stdout.write(JSON.stringify({{ notified: notified }}) + "\\n");
    """


@needs_node
def test_file_protocol_triggers_notice():
    out = json.loads(_run_node(_file_check_script("file:"))[0])
    assert len(out["notified"]) == 1
    assert "file://" in out["notified"][0]
    assert "http" in out["notified"][0]
    # The notice says what is actually happening now: htmx is off and
    # navigation is plain page loads (not "links will not work").
    assert "htmx is unavailable" in out["notified"][0]
    assert "plain page loads" in out["notified"][0]


@needs_node
def test_http_protocol_does_not_trigger_notice():
    out = json.loads(_run_node(_file_check_script("https:"))[0])
    assert out["notified"] == []


@needs_node
def test_plain_http_protocol_also_does_not_trigger_notice():
    out = json.loads(_run_node(_file_check_script("http:"))[0])
    assert out["notified"] == []


@needs_node
def test_file_protocol_check_never_throws_when_window_is_missing():
    script = f"""
    function arkNotify() {{ throw new Error("should not be reached, or if reached, must not escape"); }}
    {APP_SHELL_FILE_PROTOCOL_CHECK_JS}
    warnIfAppShellServedFromFileProtocol();
    process.stdout.write("ok\\n");
    """
    assert _run_node(script) == ["ok"]
