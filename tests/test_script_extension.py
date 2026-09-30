"""
Tests for `arklight.backend.script_extension.ScriptExtension` -- the
class-based successor to `site.raw_postprocess(fn)` for injecting
hand-written JS alongside `arklight.js`. See
docs/Foundational/EXPERIMENTAL-APIS.md and
arklight/backend/script_extension.py.
"""

from __future__ import annotations

import warnings

import pytest

from arklight import Site
from arklight.backend.js.render import SCRIPT_PATH
from arklight.backend.script_extension import (
    REQUIRED_MARKER,
    ScriptExtension,
    ScriptExtensionError,
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
    assert len(caught) == 1
    assert "does not contain the required" in str(caught[0].message)
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
    assert len(caught) == 0
