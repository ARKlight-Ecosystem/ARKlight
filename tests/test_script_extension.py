"""
Tests for `arklight.backend.script_extension.ScriptExtension` -- the
class-based successor to `site.raw_postprocess(fn)` for injecting
hand-written JS alongside `arklight.js`. See
docs/Foundational/EXPERIMENTAL-APIS.md and
arklight/backend/script_extension.py.
"""

from __future__ import annotations

import shutil
import warnings

import pytest

from arklight import Site
from arklight.backend.js.render import SCRIPT_PATH
from arklight.backend.script_extension import (
    REQUIRED_MARKER,
    ScriptExtension,
    ScriptExtensionError,
    check_js_syntax,
    register,
)


class _Plain(ScriptExtension):
    script = "<script>console.log('hi')</script>"


class _BareJS(ScriptExtension):
    script = "console.log('bare')"


class _Templated(ScriptExtension):
    script = "<template><div/></template><script>x = 1</script>"


class _Styled(ScriptExtension):
    script = "<script>x = 1</script><style>.x{color:red}</style>"


class _Empty(ScriptExtension):
    script = "<script>   </script>"


class _Computed(ScriptExtension):
    def render_script(self) -> str:
        return "<script>const computed = true;</script>"


def test_lower_strips_script_wrapper():
    assert _Plain().lower() == "console.log('hi')"


def test_lower_accepts_bare_js_with_no_wrapper():
    assert _BareJS().lower() == "console.log('bare')"


def test_lower_uses_render_script_override():
    assert _Computed().lower() == "const computed = true;"


def test_lower_rejects_template_block():
    with pytest.raises(ScriptExtensionError):
        _Templated().lower()


def test_lower_rejects_style_block():
    with pytest.raises(ScriptExtensionError):
        _Styled().lower()


def test_lower_rejects_empty_script():
    with pytest.raises(ScriptExtensionError):
        _Empty().lower()


def test_register_accepts_class_or_instance():
    site = Site(name="Test")
    instance = register(site, _Plain)
    assert isinstance(instance, _Plain)

    site2 = Site(name="Test2")
    same_instance = register(site2, _Plain())
    assert isinstance(same_instance, _Plain)


def test_register_rejects_non_script_extension():
    site = Site(name="Test")
    with pytest.raises(TypeError):
        register(site, object)
    with pytest.raises(TypeError):
        register(site, "not an extension")


def test_register_records_experimental_usage():
    site = Site(name="Test")
    register(site, _Plain)
    assert len(site.experimental_usages) == 1
    assert site.experimental_usages[0].feature_id == "script-extension"
    assert site.experimental_usages[0].component == "_Plain"


def test_register_wires_through_raw_postprocessors():
    site = Site(name="Test")
    register(site, _Plain)
    assert len(site.raw_postprocessors) == 1

    output_files = site.raw_postprocessors[0]({})
    assert SCRIPT_PATH in output_files
    assert "console.log('hi')" in output_files[SCRIPT_PATH]
    assert "_Plain" in output_files[SCRIPT_PATH]


def test_register_appends_to_existing_script_output():
    site = Site(name="Test")
    register(site, _Plain)
    output_files = {SCRIPT_PATH: "// existing runtime\n"}
    output_files = site.raw_postprocessors[0](output_files)
    assert "// existing runtime" in output_files[SCRIPT_PATH]
    assert "console.log('hi')" in output_files[SCRIPT_PATH]


def test_site_register_script_extension_method():
    site = Site(name="Test")
    instance = site.register_script_extension(_Plain)
    assert isinstance(instance, _Plain)
    assert len(site.raw_postprocessors) == 1
    assert len(site.experimental_usages) == 1


def _load_module(tmp_path, filename: str, source: str):
    import importlib.util
    import sys

    module_path = tmp_path / filename
    module_path.write_text(source)
    spec = importlib.util.spec_from_file_location(module_path.stem, module_path)
    module = importlib.util.module_from_spec(spec)
    # A normally `import`ed module is registered in sys.modules under
    # its own name automatically -- inspect.getsourcefile relies on
    # that registration to resolve a class back to its file, so do
    # the same here to match real-world import behavior.
    sys.modules[module_path.stem] = module
    spec.loader.exec_module(module)
    return module


def test_missing_marker_warns_but_does_not_block(tmp_path):
    # A real file on disk, deliberately with no marker anywhere in
    # it -- inspect.getsource needs a real file to scan, which
    # classes defined inline in this test module don't reliably give
    # under every test runner, so the marker check is exercised
    # end-to-end via a small file written to tmp_path instead.
    module = _load_module(
        tmp_path,
        "unmarked_mod.py",
        "from arklight.backend.script_extension import ScriptExtension\n"
        "\n"
        "class Unmarked(ScriptExtension):\n"
        "    script = \"<script>console.log('unmarked')</script>\"\n",
    )

    site = Site(name="Test")
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        register(site, module.Unmarked)
    # The warning message itself always quotes REQUIRED_MARKER (it's
    # telling you what to add), so the real signal is that a warning
    # fired at all -- not a substring search over its text.
    marker_warnings = [w for w in caught if "does not contain the required" in str(w.message)]
    assert len(marker_warnings) == 1
    # Not blocked: the extension is still wired up.
    assert len(site.raw_postprocessors) == 1


def test_marker_present_in_source_suppresses_warning(tmp_path):
    module = _load_module(
        tmp_path,
        "marked_mod.py",
        "from arklight.backend.script_extension import ScriptExtension\n"
        "\n"
        "#include <expapilib.ARKlight>\n"
        "class Marked(ScriptExtension):\n"
        "    script = \"<script>console.log('marked')</script>\"\n",
    )

    site = Site(name="Test")
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        register(site, module.Marked)
    assert not [w for w in caught if "does not contain the required" in str(w.message)]


# ---------------------------------------------------------------------------
# `node --check` syntax gate
# ---------------------------------------------------------------------------

needs_node = pytest.mark.skipif(shutil.which("node") is None, reason="node not on PATH")


class _BrokenSyntax(ScriptExtension):
    script = "<script>function broken( {\n  console.log('oops');\n</script>"


class _Opaque(ScriptExtension):
    script = "<script>const clash = 1;</script>"


@needs_node
def test_check_js_syntax_accepts_valid_js():
    assert check_js_syntax("const a = 1;\nconsole.log(a);\n", label="t") is True


@needs_node
def test_check_js_syntax_rejects_invalid_js_and_names_the_label():
    with pytest.raises(ScriptExtensionError) as exc:
        check_js_syntax("function (", label="MyExt.script")
    assert "MyExt.script" in str(exc.value)
    assert "SyntaxError" in str(exc.value)
    # the throwaway temp path must not leak into the message
    assert "arklight-node-check-" not in str(exc.value)
    # nor Node's internal stack frames / version footer
    assert "node:internal" not in str(exc.value)
    assert "Node.js v" not in str(exc.value)


@needs_node
def test_register_fails_fast_on_syntax_error():
    site = Site(name="Test")
    with pytest.raises(ScriptExtensionError) as exc:
        register(site, _BrokenSyntax)
    assert "_BrokenSyntax" in str(exc.value)
    # nothing half-registered
    assert site.raw_postprocessors == []
    assert site.experimental_usages == []


@needs_node
def test_compile_step_catches_a_fragment_that_breaks_the_combined_file():
    # `const clash` parses fine alone but is a redeclaration once appended
    # after a runtime that already declares it at top level.
    site = Site(name="Test")
    register(site, _Opaque)
    with pytest.raises(ScriptExtensionError) as exc:
        site.raw_postprocessors[0]({SCRIPT_PATH: "const clash = 0;\n"})
    assert SCRIPT_PATH in str(exc.value)
    assert "_Opaque" in str(exc.value)


@needs_node
def test_compile_step_reports_a_broken_runtime_rather_than_swallowing_it():
    site = Site(name="Test")
    register(site, _Plain)
    with pytest.raises(ScriptExtensionError):
        site.raw_postprocessors[0]({SCRIPT_PATH: "function ("})


def test_missing_node_warns_but_does_not_block(monkeypatch):
    monkeypatch.setattr(shutil, "which", lambda _name: None)
    site = Site(name="Test")
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        register(site, _BrokenSyntax)  # would raise if node were found
    assert any("syntax was NOT checked" in str(w.message) for w in caught)
    assert len(site.raw_postprocessors) == 1
    out = site.raw_postprocessors[0]({})
    assert "function broken(" in out[SCRIPT_PATH]


def test_check_syntax_false_opts_out(monkeypatch):
    def _boom(*_a, **_k):
        raise AssertionError("node must not be invoked when check_syntax is False")

    monkeypatch.setattr("arklight.backend.script_extension.subprocess.run", _boom)

    class _OptOut(_BrokenSyntax):
        check_syntax = False

    site = Site(name="Test")
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        register(site, _OptOut)
    assert not any("syntax was NOT checked" in str(w.message) for w in caught)
    site.raw_postprocessors[0]({})  # combined check is skipped too


# ---------------------------------------------------------------------------
# Classic-script grammar (why this is not literally `node --check`).
#
# `node --check s.js` parses via lib/internal/main/check_syntax.js, which
# picks CommonJS or ESM and compiles CJS as a function body. arklight.js is
# loaded by a browser as a plain classic <script>, so each of these passes
# `node --check` but is a fatal SyntaxError in the page.
# ---------------------------------------------------------------------------

_FATAL_IN_BROWSER_BUT_PASSES_NODE_CHECK = {
    "export": "export const a = 1;",
    "import": "import x from 'y';",
    "top-level await": "await fetch('/x');",
    "top-level return": "if (!window.ok) { return; }",
    "new.target": "console.log(new.target);",
}


@needs_node
@pytest.mark.parametrize("src", _FATAL_IN_BROWSER_BUT_PASSES_NODE_CHECK.values(), ids=list(_FATAL_IN_BROWSER_BUT_PASSES_NODE_CHECK))
def test_rejects_syntax_that_node_check_accepts_but_a_browser_script_does_not(src):
    with pytest.raises(ScriptExtensionError):
        check_js_syntax(src, label="t")


@needs_node
@pytest.mark.parametrize("src", ["with (Math) { var y = PI; }", "var await = 1;"], ids=["with", "var-await"])
def test_accepts_valid_sloppy_classic_script_that_a_module_goal_would_reject(src):
    assert check_js_syntax(src, label="t") is True


@needs_node
def test_syntax_check_parses_but_never_executes_the_script():
    # If this ran, the throw would surface as a non-SyntaxError failure.
    assert check_js_syntax("throw new Error('must not run'); process.exit(3);", label="t") is True
