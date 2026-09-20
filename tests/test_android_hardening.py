"""
Android native-shell hardening -- first slice of
docs/Proposals/ANDROID-BACKEND-HARDENING-PROPOSAL.md (`0.06507`).

Everything here checks the *generated text* (`MainActivity.kt`,
`AndroidManifest.xml`) and the `android.allow_navigation` config
validation. Nothing compiles the Kotlin or runs it on a device --
`arklight android scaffold` is templating only -- so the structural
checks below (balanced braces/comments, no leftover template
placeholders) exist to catch the one failure mode a Python-string
template has: an f-string mistake that emits a syntactically broken
Kotlin file that no other test would notice.
"""

from pathlib import Path

import pytest

from arklight.backend.android import runtime
from arklight.cli.android import AndroidError, scaffold_project
from arklight.compiler.pipeline import build

SIMPLE_SITE = """
from arklight import *
site = Site()

@site.page("/")
def home():
    return Page(Heading("Hi"))
"""

_PNG_BYTES = b"\x89PNG\r\n\x1a\n" + b"0" * 64


def _build_dir(tmp_path: Path) -> Path:
    (tmp_path / "site.py").write_text(SIMPLE_SITE)
    out_dir = tmp_path / "ARK"
    build(tmp_path / "site.py", out_dir)
    return out_dir


def _config(tmp_path: Path, android_section: str) -> None:
    (tmp_path / "arklight.config.py").write_text(
        f'CONFIG = {{\n    "android": {android_section},\n}}\n'
    )


def _scaffold(tmp_path: Path, android_section: str | None = None) -> Path:
    out_dir = _build_dir(tmp_path)
    if android_section is not None:
        _config(tmp_path, android_section)
    project_dir = tmp_path / "android-project"
    scaffold_project(out_dir, output_dir=project_dir)
    return project_dir


def _main_activity(project_dir: Path, package_path: str = "com/arklight/app") -> str:
    return (project_dir / f"app/src/main/java/{package_path}/MainActivity.kt").read_text()


def _manifest(project_dir: Path) -> str:
    return (project_dir / "app/src/main/AndroidManifest.xml").read_text()


# --------------------------------------------------------------------
# Default scaffold: the fixed-behavior fixes, no new config needed
# --------------------------------------------------------------------


def test_default_activity_routes_external_links_out_of_the_webview(tmp_path):
    kt = _main_activity(_scaffold(tmp_path))

    assert "override fun shouldOverrideUrlLoading(" in kt
    assert "request.isForMainFrame && routeNavigation(request.url)" in kt
    assert "Intent(Intent.ACTION_VIEW, uri)" in kt
    # A device with no handler for a link must not crash the activity.
    assert "catch (e: ActivityNotFoundException)" in kt


def test_default_activity_has_no_allowed_hosts(tmp_path):
    kt = _main_activity(_scaffold(tmp_path))

    assert "private val ALLOWED_HOSTS: List<String> = emptyList()" in kt


def test_default_activity_keeps_own_origin_in_the_webview(tmp_path):
    kt = _main_activity(_scaffold(tmp_path))

    assert 'private const val ASSET_HOST = "appassets.androidplatform.net"' in kt
    assert 'private const val SITE_URL = "https://appassets.androidplatform.net/assets/index.html"' in kt


def test_only_web_and_contact_schemes_leave_the_app(tmp_path):
    # Every other scheme keeps the WebView's own default handling, so
    # this change can't newly break e.g. an in-page `blob:`/`about:` load.
    kt = _main_activity(_scaffold(tmp_path))

    assert 'setOf("http", "https", "mailto", "tel", "sms")' in kt


def test_default_activity_uses_the_back_dispatcher_not_the_deprecated_override(tmp_path):
    kt = _main_activity(_scaffold(tmp_path))

    assert "override fun onBackPressed()" not in kt
    assert "DEPRECATION" not in kt
    assert "OnBackPressedCallback(false)" in kt
    assert "onBackPressedDispatcher.addCallback(this, backCallback)" in kt
    # Enabled only while there is history, so the system keeps the
    # back-to-home gesture when there isn't.
    assert "backCallback.isEnabled = view.canGoBack()" in kt


def test_default_activity_saves_and_restores_webview_state(tmp_path):
    kt = _main_activity(_scaffold(tmp_path))

    assert "webView.saveState(outState)" in kt
    assert "webView.restoreState(savedInstanceState) == null" in kt
    # First launch (no saved state) still loads the site.
    assert "webView.loadUrl(SITE_URL)" in kt


def test_default_activity_handles_main_frame_load_errors(tmp_path):
    kt = _main_activity(_scaffold(tmp_path))

    assert "override fun onReceivedError(" in kt
    assert "if (request.isForMainFrame)" in kt
    assert "loadDataWithBaseURL(" in kt
    # The page is a fixed string; nothing from the failed URL goes in it.
    assert "LOAD_ERROR_HTML" in kt
    assert "<script" not in kt.split("LOAD_ERROR_HTML =", 1)[1]


def test_web_contents_debugging_follows_the_build_type(tmp_path):
    kt = _main_activity(_scaffold(tmp_path))

    assert "ApplicationInfo.FLAG_DEBUGGABLE" in kt
    assert "WebView.setWebContentsDebuggingEnabled(" in kt
    assert "setWebContentsDebuggingEnabled(true)" not in kt


def test_default_manifest_opts_into_predictive_back(tmp_path):
    manifest = _manifest(_scaffold(tmp_path))

    assert 'android:enableOnBackInvokedCallback="true"' in manifest


def test_default_manifest_does_not_request_internet(tmp_path):
    # An offline, baked-in-assets app should not ask for the network.
    manifest = _manifest(_scaffold(tmp_path))

    assert "android.permission.INTERNET" not in manifest
    assert "<uses-permission" not in manifest


def test_manifest_is_still_a_well_formed_document(tmp_path):
    import xml.etree.ElementTree as ET

    for section in (None, '{"allow_navigation": ["login.example.com"]}'):
        sub = tmp_path / ("plain" if section is None else "nav")
        sub.mkdir()
        manifest = _manifest(_scaffold(sub, section))
        root = ET.fromstring(manifest)
        assert root.tag == "manifest"
        assert root.find("application/activity") is not None


# --------------------------------------------------------------------
# allow_navigation
# --------------------------------------------------------------------


def test_allow_navigation_hosts_reach_the_activity(tmp_path):
    kt = _main_activity(
        _scaffold(tmp_path, '{"allow_navigation": ["login.example.com", "*.pay.example.org"]}')
    )

    assert (
        'private val ALLOWED_HOSTS: List<String> = listOf("login.example.com", "*.pay.example.org")'
        in kt
    )


def test_allow_navigation_adds_internet_permission(tmp_path):
    manifest = _manifest(_scaffold(tmp_path, '{"allow_navigation": ["login.example.com"]}'))

    assert '<uses-permission android:name="android.permission.INTERNET" />' in manifest
    # The permission sits before <application>, where the schema wants it.
    assert manifest.index("<uses-permission") < manifest.index("<application")


def test_empty_allow_navigation_is_the_default(tmp_path):
    project = _scaffold(tmp_path, '{"allow_navigation": []}')

    assert "android.permission.INTERNET" not in _manifest(project)
    assert "emptyList()" in _main_activity(project)


def test_allow_navigation_is_lowercased_and_deduplicated_in_order(tmp_path):
    kt = _main_activity(
        _scaffold(
            tmp_path,
            '{"allow_navigation": ["Login.Example.com", "login.example.com", "a.example.net"]}',
        )
    )

    assert 'listOf("login.example.com", "a.example.net")' in kt


def test_allow_navigation_composes_with_other_android_keys(tmp_path):
    project = _scaffold(
        tmp_path,
        '{"package_id": "com.example.arkfolio", "edge_to_edge": True, '
        '"allow_navigation": ["login.example.com"]}',
    )
    kt = _main_activity(project, "com/example/arkfolio")

    assert kt.startswith("package com.example.arkfolio")
    assert "WindowCompat.setDecorFitsSystemWindows(window, false)" in kt
    assert 'listOf("login.example.com")' in kt


@pytest.mark.parametrize(
    "entry",
    [
        "login.example.com",
        "*.example.com",
        "a-b.example.co.uk",
        "x1.y2.example.org",
        "192.168.0.1",
    ],
)
def test_valid_allow_navigation_entries_are_accepted(tmp_path, entry):
    kt = _main_activity(_scaffold(tmp_path, f'{{"allow_navigation": ["{entry}"]}}'))

    assert f'"{entry}"' in kt


@pytest.mark.parametrize(
    "entry",
    [
        "https://login.example.com",  # scheme
        "login.example.com/path",  # path
        "login.example.com:8443",  # port
        "localhost",  # single label
        "*.com",  # bare wildcard over a TLD
        "*",
        "*.*.example.com",
        "foo.*.example.com",
        "-bad.example.com",
        "bad-.example.com",
        "bad..example.com",
        "exa mple.com",
        "",
        'quote".example.com',  # would close the Kotlin string
        "dollar$.example.com",  # Kotlin string template
        "back\\slash.example.com",
    ],
)
def test_malformed_allow_navigation_entries_fail_the_scaffold(tmp_path, entry):
    out_dir = _build_dir(tmp_path)
    (tmp_path / "arklight.config.py").write_text(
        f'CONFIG = {{"android": {{"allow_navigation": [{entry!r}]}}}}\n'
    )

    with pytest.raises(AndroidError, match="allow_navigation"):
        scaffold_project(out_dir, output_dir=tmp_path / "android-project")


@pytest.mark.parametrize("value", ['"login.example.com"', "5", "None", '{"a.example.com": 1}', "[5]"])
def test_allow_navigation_must_be_a_list_of_strings(tmp_path, value):
    out_dir = _build_dir(tmp_path)
    _config(tmp_path, f'{{"allow_navigation": {value}}}')

    with pytest.raises(AndroidError, match="allow_navigation"):
        scaffold_project(out_dir, output_dir=tmp_path / "android-project")


def test_scheme_error_message_says_what_to_write_instead(tmp_path):
    out_dir = _build_dir(tmp_path)
    _config(tmp_path, '{"allow_navigation": ["https://login.example.com"]}')

    with pytest.raises(AndroidError) as excinfo:
        scaffold_project(out_dir, output_dir=tmp_path / "android-project")

    message = str(excinfo.value)
    assert "https://login.example.com" in message
    assert "bare hostname" in message
    assert "No scheme" in message


def test_a_failed_allow_navigation_scaffold_writes_nothing(tmp_path):
    out_dir = _build_dir(tmp_path)
    _config(tmp_path, '{"allow_navigation": ["localhost"]}')
    project_dir = tmp_path / "android-project"

    with pytest.raises(AndroidError):
        scaffold_project(out_dir, output_dir=project_dir)

    assert not project_dir.exists()


def test_runtime_builder_rejects_a_host_the_cli_would_have_rejected():
    # `project_files` is public and pure; it must not trust its caller
    # with text it splices into a Kotlin string literal.
    with pytest.raises(ValueError, match="allow_navigation"):
        runtime.project_files(
            app_name="A",
            package_id="com.example.a",
            version_name="1.0.0",
            version_code=1,
            orientation="portrait",
            edge_to_edge=False,
            has_custom_icon=False,
            has_splash=False,
            allow_navigation=['x".com'],
        )


def test_project_files_default_is_unchanged_for_existing_callers():
    files = runtime.project_files(
        app_name="A",
        package_id="com.example.a",
        version_name="1.0.0",
        version_code=1,
        orientation="portrait",
        edge_to_edge=False,
        has_custom_icon=False,
        has_splash=False,
    )

    assert "android.permission.INTERNET" not in files["app/src/main/AndroidManifest.xml"]
    assert "emptyList()" in files["app/src/main/java/com/example/a/MainActivity.kt"]


# --------------------------------------------------------------------
# Structural sanity of the generated Kotlin (every variant)
# --------------------------------------------------------------------


def _variants():
    for edge in (False, True):
        for splash in (False, True):
            for hosts in ((), ("login.example.com", "*.pay.example.org")):
                yield edge, splash, hosts


@pytest.mark.parametrize("edge,splash,hosts", list(_variants()))
def test_generated_activity_is_structurally_sound(edge, splash, hosts):
    kt = runtime._main_activity_kt("com.example.a", edge, splash, hosts)

    # Unfilled template placeholders / f-string escapes leaking through.
    for leftover in ("{splash", "{edge", "{allowed", "{_ASSET", "{{", "}}"):
        assert leftover not in kt, leftover

    # Braces balance once string literals and comments are set aside.
    stripped = _strip_kotlin_strings_and_comments(kt)
    assert stripped.count("{") == stripped.count("}")
    assert stripped.count("(") == stripped.count(")")

    assert kt.startswith("package com.example.a\n")
    assert ("installSplashScreen" in kt) is splash
    assert ("setDecorFitsSystemWindows" in kt) is edge


def _strip_kotlin_strings_and_comments(source: str) -> str:
    """Remove string literals and (nesting) block/line comments, so
    brace counting only sees code. Kotlin block comments nest, which is
    why a stray `/*` inside a KDoc would swallow the rest of the file."""
    out: list[str] = []
    i, n = 0, len(source)
    depth = 0
    while i < n:
        two = source[i : i + 2]
        if depth:
            if two == "/*":
                depth += 1
                i += 2
            elif two == "*/":
                depth -= 1
                i += 2
            else:
                i += 1
        elif two == "/*":
            depth = 1
            i += 2
        elif two == "//":
            while i < n and source[i] != "\n":
                i += 1
        elif source[i] == '"':
            i += 1
            while i < n and source[i] != '"':
                i += 2 if source[i] == "\\" else 1
            i += 1
        else:
            out.append(source[i])
            i += 1
    assert depth == 0, "unterminated block comment in generated Kotlin"
    return "".join(out)


def test_kotlin_stripper_handles_nested_comments():
    assert _strip_kotlin_strings_and_comments("a /* x /* y */ z */ b") == "a  b"
    with pytest.raises(AssertionError):
        _strip_kotlin_strings_and_comments("a /* x /* y */ b")


def test_scaffold_readme_documents_the_new_behavior(tmp_path):
    readme = (_scaffold(tmp_path) / "README.md").read_text()

    assert "allow_navigation" in readme
    assert "INTERNET" in readme
