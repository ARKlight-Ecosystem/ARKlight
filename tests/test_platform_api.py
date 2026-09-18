"""
`v0.065` (`docs/Proposals/PLATFORM-API-IR-PROPOSAL.md`): Platform
APIs -- `PlatformAPI.notify(...)`/`PlatformAPI.clipboard_write(...)`
on `on_click=`, compiled to a `PlatformAPIRef` the same way
`Action.*(...)` compiles to an `ActionRef`.

Grouped to mirror the feature's own layers:

1. `arklight.api.PlatformAPI` factory functions build the right
   `PlatformAPIRef`.
2. Validation (`arklight.ir.validate`) catches unknown capabilities
   and unknown keyword arguments.
3. HTML attribute rendering (`arklight.backend.html.attrs`) compiles
   a `PlatformAPIRef` to `data-ark-on-click="platform:<capability>"` +
   `data-ark-platform-api-args`.
4. The JS backend (`arklight.backend.js.render`) ships only the
   capability fragments a site's IR actually references, dispatches
   them through the click interceptor's `"platform:"` branch, and
   `check_backend_support` (`arklight.ir.platform_api`) fails the
   build for a backend that doesn't implement a referenced capability.
"""

import pytest

from arklight.api import Button, Page, PlatformAPI, Text
from arklight.ast.nodes import PlatformAPIRef
from arklight.backend.html.render import HTMLBackend
from arklight.backend.js.render import JSBackend, SCRIPT_PATH
from arklight.ir.build import build_website_ir
from arklight.ir.normalize import normalize_ark_ast
from arklight.ir.platform_api import PlatformAPIError, check_backend_support
from arklight.ir.validate import ValidationError, validate_ark_ast


def _ir(pages):
    normalized = normalize_ark_ast(pages)
    validate_ark_ast(normalized)
    return build_website_ir("site", normalized)


def _plain_ir():
    return _ir({"/": Page(Text("hi"))})


# --- 1. arklight.api.PlatformAPI factories -----------------------------


def test_platform_api_notify_builds_ref_with_title_and_body():
    ref = PlatformAPI.notify("Saved!", body="Your changes were saved.")
    assert isinstance(ref, PlatformAPIRef)
    assert ref.capability == "notify"
    assert ref.args == {"title": "Saved!", "body": "Your changes were saved."}


def test_platform_api_notify_omits_body_when_not_given():
    ref = PlatformAPI.notify("Saved!")
    assert ref.args == {"title": "Saved!"}


def test_platform_api_clipboard_write_builds_ref_with_text():
    ref = PlatformAPI.clipboard_write("https://example.com")
    assert ref.capability == "clipboard_write"
    assert ref.args == {"text": "https://example.com"}


# --- 2. Validation -------------------------------------------------------


def test_validate_rejects_unknown_platform_capability():
    bad_ref = PlatformAPIRef(capability="does_not_exist", args={})
    with pytest.raises(ValidationError, match="unknown platform API capability"):
        validate_ark_ast(normalize_ark_ast({"/": Page(Button("Go", on_click=bad_ref))}))


def test_validate_rejects_unexpected_platform_api_argument():
    bad_ref = PlatformAPIRef(capability="notify", args={"title": "Hi", "unexpected": "nope"})
    with pytest.raises(ValidationError, match="unexpected keyword argument"):
        validate_ark_ast(normalize_ark_ast({"/": Page(Button("Go", on_click=bad_ref))}))


def test_validate_accepts_known_platform_api_calls():
    pages = {
        "/": Page(
            Button("Notify", on_click=PlatformAPI.notify("Hi", body="there")),
            Button("Copy", on_click=PlatformAPI.clipboard_write("hello")),
        )
    }
    # Should not raise.
    validate_ark_ast(normalize_ark_ast(pages))


# --- 3. HTML attribute rendering ------------------------------------------


def test_html_renders_platform_api_on_click_attribute():
    pages = {"/": Page(Button("Notify me", on_click=PlatformAPI.notify("Saved!", body="ok")))}
    html = HTMLBackend().render(_ir(pages))["index.html"]
    assert 'data-ark-on-click="platform:notify"' in html
    assert "data-ark-platform-api-args" in html
    assert "Saved!" in html


def test_html_platform_api_args_do_not_leak_action_attributes():
    pages = {"/": Page(Button("Copy", on_click=PlatformAPI.clipboard_write("hello")))}
    html = HTMLBackend().render(_ir(pages))["index.html"]
    assert 'data-ark-on-click="platform:clipboard_write"' in html
    assert "data-ark-action-state" not in html


# --- 4. JS backend: only-ship-what's-used + dispatch wiring ---------------


def test_js_runtime_ships_no_platform_apis_when_none_are_used():
    js = JSBackend().render(_plain_ir())[SCRIPT_PATH]
    assert "notify: function" not in js
    assert "clipboard_write: function" not in js
    assert "var platformApis" not in js


def test_js_runtime_ships_only_the_platform_api_actually_used():
    pages = {"/": Page(Button("Notify me", on_click=PlatformAPI.notify("Saved!")))}
    js = JSBackend().render(_ir(pages))[SCRIPT_PATH]
    assert "notify: function" in js
    assert "clipboard_write: function" not in js
    assert "var platformApis = {" in js
    assert "wireClickInterceptor" in js


def test_js_runtime_ships_both_platform_apis_when_both_used():
    pages = {
        "/": Page(
            Button("Notify", on_click=PlatformAPI.notify("Hi")),
            Button("Copy", on_click=PlatformAPI.clipboard_write("hello")),
        )
    }
    js = JSBackend().render(_ir(pages))[SCRIPT_PATH]
    assert "notify: function" in js
    assert "clipboard_write: function" in js


def test_js_click_interceptor_dispatches_platform_prefix():
    pages = {"/": Page(Button("Notify me", on_click=PlatformAPI.notify("Hi")))}
    js = JSBackend().render(_ir(pages))[SCRIPT_PATH]
    assert 'raw.indexOf("platform:")' in js
    assert "platformApis[capability]" in js


def test_js_platform_api_only_page_still_needs_click_interceptor_with_no_state():
    # A platform-API-only page (no State(...) anywhere) still needs
    # the click interceptor, same as a behavior-only page -- neither
    # depends on has_state.
    pages = {"/": Page(Button("Notify me", on_click=PlatformAPI.notify("Hi")))}
    js = JSBackend().render(_ir(pages))[SCRIPT_PATH]
    assert "createState" not in js
    assert "wireClickInterceptor" in js


def test_js_runtime_has_no_eval_or_new_function_with_platform_apis():
    pages = {
        "/": Page(
            Button("Notify", on_click=PlatformAPI.notify("Hi")),
            Button("Copy", on_click=PlatformAPI.clipboard_write("hello")),
        )
    }
    js = JSBackend().render(_ir(pages))[SCRIPT_PATH]
    assert "eval(" not in js
    assert "new Function(" not in js


# --- 5. Backend-capability check -----------------------------------------


def test_check_backend_support_passes_for_web_backend():
    # Should not raise -- "web" implements both registered capabilities.
    check_backend_support({"notify", "clipboard_write"}, backend_name="web")


def test_check_backend_support_raises_for_unimplemented_backend():
    with pytest.raises(PlatformAPIError, match="not implemented by backend 'android'"):
        check_backend_support({"notify"}, backend_name="android")


def test_check_backend_support_names_every_unsupported_capability_at_once():
    with pytest.raises(PlatformAPIError) as exc_info:
        check_backend_support({"notify", "clipboard_write"}, backend_name="desktop")
    message = str(exc_info.value)
    assert "notify" in message
    assert "clipboard_write" in message


def test_js_backend_render_raises_when_capability_unsupported(monkeypatch):
    # Simulate a future backend name gap by pointing check_backend_support's
    # own registry at a backend that supports nothing, via the real "web"
    # entry temporarily narrowed -- exercises that JSBackend.render()
    # actually calls check_backend_support rather than only importing it.
    import arklight.backend.js.render as render_module

    monkeypatch.setitem(render_module.check_backend_support.__globals__["BACKEND_PLATFORM_API_SUPPORT"], "web", frozenset())
    pages = {"/": Page(Button("Notify me", on_click=PlatformAPI.notify("Hi")))}
    ir = _ir(pages)
    with pytest.raises(PlatformAPIError, match="not implemented by backend 'web'"):
        JSBackend().render(ir)
