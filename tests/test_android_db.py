"""
Android half of `PlatformAPI.db` (`tests/test_platform_api_db.py` covers
the compiler and Web half): the generated `ArkDb.kt` (SQLite behind a
`WebMessageListener`) and its wiring into `MainActivity.kt`.

Like `tests/test_android_hardening.py`, everything here checks generated
*text* -- no Kotlin toolchain runs in this suite -- so the tests pin the
properties that matter: the bridge is registered before the first load, is
restricted to the app's own origin, is the only JS-to-native channel, and
speaks the same names and wire format as the JavaScript that calls it.
"""

import re

from arklight.backend.android import runtime
from arklight.backend.js.platform_apis.db import JS_FRAGMENT

PACKAGE = "com.example.notes"
JAVA_DIR = "app/src/main/java/com/example/notes"


def _files(**overrides):
    kwargs = dict(
        app_name="Notes",
        package_id=PACKAGE,
        version_name="1.0",
        version_code=1,
        orientation="fullSensor",
        edge_to_edge=False,
        has_custom_icon=False,
        has_splash=False,
    )
    kwargs.update(overrides)
    return runtime.project_files(**kwargs)


def _ark_db() -> str:
    return _files()[f"{JAVA_DIR}/ArkDb.kt"]


def _main_activity() -> str:
    return _files()[f"{JAVA_DIR}/MainActivity.kt"]


def test_scaffold_emits_ark_db_with_the_apps_package():
    source = _ark_db()
    assert source.splitlines()[0] == f"package {PACKAGE}"
    assert "class ArkDb" in source


def test_ark_db_is_sqlite_backed_with_one_kv_table():
    source = _ark_db()
    assert "SQLiteOpenHelper" in source
    assert "CREATE TABLE IF NOT EXISTS kv (key TEXT PRIMARY KEY NOT NULL, value TEXT NOT NULL)" in source
    assert "INSERT OR REPLACE INTO kv" in source
    assert "DELETE FROM kv WHERE key = ?" in source
    assert "SELECT value FROM kv WHERE key = ?" in source
    assert "SELECT key FROM kv" in source


def test_ark_db_never_builds_sql_from_page_supplied_text():
    # Every statement takes its key/value through a `?` binding.
    source = _ark_db()
    for call in re.findall(r"(?:execSQL|rawQuery)\(\s*\"([^\"]*)\"", source):
        if any(word in call for word in ("INSERT", "DELETE", "WHERE")):
            assert "?" in call, call
        assert "+" not in call, call


def test_bridge_uses_a_web_message_listener_restricted_to_one_origin():
    source = _ark_db()
    assert "WebViewCompat.addWebMessageListener" in source
    assert "setOf(allowedOrigin)" in source
    assert "WebViewFeature.WEB_MESSAGE_LISTENER" in source  # feature-checked, false -> IndexedDB fallback
    # The alternative that would expose the object to *every* page the
    # WebView loads (including `android.allow_navigation` hosts).
    # (Matched as a *call*: the KDoc names it while explaining why it isn't used.)
    call = re.compile(r"addJavascriptInterface\s*\(")
    assert not call.search(source)
    assert not call.search(_main_activity())


def test_main_activity_installs_the_bridge_for_the_asset_origin_before_first_load():
    activity = _main_activity()
    install = activity.index("ArkDb(this)")
    first_load = activity.index("webView.loadUrl(SITE_URL)")
    assert install < first_load
    assert f'install(webView, "{runtime._ASSET_ORIGIN}")' in activity


def test_main_activity_releases_the_database_on_destroy():
    activity = _main_activity()
    assert "override fun onDestroy()" in activity
    assert "arkDb?.close()" in activity


def test_requests_run_off_the_main_thread_and_replies_return_on_it():
    source = _ark_db()
    assert "Executors.newSingleThreadExecutor()" in source  # ordered, off the UI thread
    assert "runOnUiThread" in source  # WebView replies belong to the UI thread


def test_database_helper_holds_the_application_context_not_the_activity():
    assert "activity.applicationContext" in _ark_db()


def test_bridge_name_matches_what_the_web_runtime_looks_for():
    kotlin_name = re.search(r'BRIDGE_NAME = "([^"]+)"', _ark_db()).group(1)
    assert f"window.{kotlin_name}" in JS_FRAGMENT


def test_every_op_the_web_runtime_sends_is_handled_natively():
    sent_ops = set(re.findall(r'bridgeCall\("(\w+)"', JS_FRAGMENT))
    handled_ops = set(re.findall(r'^\s+"(\w+)" ->', _ark_db(), flags=re.MULTILINE))
    assert sent_ops == {"set", "get", "delete", "keys"}
    assert sent_ops <= handled_ops


def test_wire_format_field_names_agree_between_js_and_kotlin():
    source = _ark_db()
    for field in ("id", "ok", "result", "error", "op", "key", "value"):
        assert f'"{field}"' in source, field
    for field in ("id", "op", "key", "value"):
        assert f"{field}: " in JS_FRAGMENT  # request object literal in bridgeCall
    for field in ("reply.id", "reply.ok", "reply.result", "reply.error"):
        assert field in JS_FRAGMENT


def test_no_other_native_surface_was_added_to_the_shell():
    # `PlatformAPI.db` is the only JS-to-native channel in the app.
    activity = _main_activity()
    assert "addWebMessageListener" not in activity  # registered inside ArkDb, once
    assert not re.search(r"addJavascriptInterface\s*\(", activity)


def test_ark_db_kotlin_has_no_dollar_or_stray_template_artifacts():
    # Guards the f-string/plain-string boundary in runtime.py: a stray
    # `{{`/`}}` or `$` would compile-break the generated project.
    for text in (_ark_db(), _main_activity()):
        assert "{{" not in text and "}}" not in text
    assert "$" not in _ark_db()


def test_project_without_db_usage_still_gets_the_bridge_but_it_is_lazy():
    # The bridge is always generated (a later `arklight android sync` can
    # add db usage to a site without regenerating the project); it costs
    # nothing until used because SQLiteOpenHelper only creates the file
    # on first `writableDatabase` access, which only a request triggers.
    source = _ark_db()
    assert "helper.writableDatabase" in source
    assert "writableDatabase" not in source.split("fun install")[1].split("fun close")[0]
