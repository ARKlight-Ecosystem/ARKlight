"""
Tests for the devtools mirror of the compile-time experimental-feature
banner (arklight/backend/js/render.py's
`_experimental_console_reminder_js`), its `WebsiteIR.
devtools_console_reminder` / `strict_csp` plumbing through
`compile_site_file`/`build`, and the `arklight.config.py` "experimental"/
"csp" sections that control both from the CLI. See
`arklight/backend/js/render.py`'s and `arklight/config.py`'s comments
for the full design rationale.
"""

from __future__ import annotations

from arklight.api import Heading, Page, Site
from arklight.backend.js.render import JSBackend, _experimental_console_reminder_js
from arklight.compiler.pipeline import compile_site_file
from arklight.experimental import ExperimentalUsage
from arklight.ir.build import build_website_ir
from arklight.ir.normalize import normalize_ark_ast
from arklight.ir.validate import validate_ark_ast


def _ir(pages: dict, **kwargs):
    normalized = normalize_ark_ast(pages)
    validate_ark_ast(normalized)
    return build_website_ir("site", normalized, **kwargs)


# -- _experimental_console_reminder_js() directly ----------------------------


def test_empty_usages_produces_no_js():
    assert _experimental_console_reminder_js([]) == ""


def test_single_usage_emits_console_warn_with_feature_note():
    js = _experimental_console_reminder_js([ExperimentalUsage(feature_id="css-import")])
    assert "console.warn" in js
    assert "css-import" in js
    assert "can't be validated by ARKlight" in js


def test_duplicate_usages_of_same_feature_dedupe_to_one_warning():
    js = _experimental_console_reminder_js(
        [
            ExperimentalUsage(feature_id="css-import"),
            ExperimentalUsage(feature_id="css-import", component="Foo"),
            ExperimentalUsage(feature_id="css-import"),
        ]
    )
    assert js.count("can't be validated by ARKlight") == 1


def test_multiple_distinct_features_each_get_a_warning_first_seen_order():
    js = _experimental_console_reminder_js(
        [
            ExperimentalUsage(feature_id="css-import"),
            ExperimentalUsage(feature_id="raw-postprocess"),
        ]
    )
    assert js.index("css-import") < js.index("raw-postprocess")
    assert "raw-postprocess" in js


def test_reminder_js_never_uses_eval_or_new_function():
    # Same invariant every other fragment in this backend holds (see
    # module docstring): static console.warn strings only.
    js = _experimental_console_reminder_js([ExperimentalUsage(feature_id="css-import")])
    assert "eval(" not in js
    assert "new Function" not in js


def test_reminder_js_guards_console_existence():
    js = _experimental_console_reminder_js([ExperimentalUsage(feature_id="css-import")])
    assert 'typeof console !== "undefined"' in js


# -- End-to-end through JSBackend --------------------------------------------


def test_devtools_console_reminder_true_by_default_emits_warning():
    ir = _ir(
        {"/": Page(Heading("Hi"), title="Home")},
        experimental_usages=[ExperimentalUsage(feature_id="css-import")],
    )
    assert ir.devtools_console_reminder is True
    js = JSBackend().render(ir)["arklight.js"]
    assert "console.warn" in js
    assert "css-import" in js


def test_devtools_console_reminder_false_suppresses_warning():
    ir = _ir(
        {"/": Page(Heading("Hi"), title="Home")},
        experimental_usages=[ExperimentalUsage(feature_id="css-import")],
        devtools_console_reminder=False,
    )
    js = JSBackend().render(ir)["arklight.js"]
    assert "console.warn" not in js
    assert "css-import" not in js


def test_no_experimental_usage_emits_no_console_reminder_block_even_when_enabled():
    ir = _ir({"/": Page(Heading("Hi"), title="Home")})
    assert ir.experimental_usages == []
    js = JSBackend().render(ir)["arklight.js"]
    assert "ARKlight: experimental API" not in js


# -- WebsiteIR / build_website_ir defaults -----------------------------------


def test_website_ir_devtools_console_reminder_defaults_true():
    ir = _ir({"/": Page(Heading("Hi"), title="Home")})
    assert ir.devtools_console_reminder is True


# -- compile_site_file()'s strict_csp_override / devtools_console_reminder ---


def _write_site(tmp_path, body: str = ""):
    site_file = tmp_path / "site.py"
    site_file.write_text(
        "from arklight import *\n"
        "\n"
        "site = Site('demo')\n"
        + body
        + "\n"
        "@site.page('/')\n"
        "def home():\n"
        "    return Page(Heading('Hi'), title='Home')\n",
        encoding="utf-8",
    )
    return site_file


def test_strict_csp_override_none_defers_to_site_file(tmp_path):
    site_file = _write_site(tmp_path)
    ir = compile_site_file(site_file, strict_csp_override=None)
    assert ir.strict_csp is True  # Site()'s own default


def test_strict_csp_override_false_wins_over_site_default_true(tmp_path):
    site_file = _write_site(tmp_path)
    ir = compile_site_file(site_file, strict_csp_override=False)
    assert ir.strict_csp is False


def test_strict_csp_override_true_wins_over_site_file_opt_out(tmp_path):
    site_file = _write_site(tmp_path, "site.strict_csp = False\n")
    # Site() itself doesn't expose reassigning strict_csp post-construction
    # in the public API, so exercise the override the way it matters: a
    # site file that explicitly opted out still gets overridden by the
    # project-wide config when strict_csp_override=True is passed in.
    ir = compile_site_file(site_file, strict_csp_override=True)
    assert ir.strict_csp is True


def test_devtools_console_reminder_passthrough_via_compile_site_file(tmp_path):
    site_file = _write_site(tmp_path)
    ir = compile_site_file(site_file, devtools_console_reminder=False)
    assert ir.devtools_console_reminder is False


# -- arklight.config.py's "experimental"/"csp" sections -----------------------


def test_config_csp_section_known_and_defaults_to_none(tmp_path):
    from arklight.config import load_config, section

    config = load_config(tmp_path)
    csp_cfg = section(config, "csp", {"strict_csp": None})
    assert csp_cfg == {"strict_csp": None}


def test_config_csp_strict_csp_false_read_back(tmp_path):
    from arklight.config import load_config, section

    (tmp_path / "arklight.config.py").write_text(
        'CONFIG = {"csp": {"strict_csp": False}}\n', encoding="utf-8"
    )
    config = load_config(tmp_path)
    csp_cfg = section(config, "csp", {"strict_csp": None})
    assert csp_cfg == {"strict_csp": False}


def test_config_experimental_devtools_console_reminder_default_true(tmp_path):
    from arklight.config import load_config, section

    config = load_config(tmp_path)
    experimental_cfg = section(
        config,
        "experimental",
        {"heavy_reliance_nudge": True, "devtools_console_reminder": True},
    )
    assert experimental_cfg["devtools_console_reminder"] is True


def test_config_experimental_devtools_console_reminder_false_read_back(tmp_path):
    from arklight.config import load_config, section

    (tmp_path / "arklight.config.py").write_text(
        'CONFIG = {"experimental": {"devtools_console_reminder": False}}\n',
        encoding="utf-8",
    )
    config = load_config(tmp_path)
    experimental_cfg = section(
        config,
        "experimental",
        {"heavy_reliance_nudge": True, "devtools_console_reminder": True},
    )
    assert experimental_cfg["devtools_console_reminder"] is False
    # Unset keys in a partially-specified section still fall back to
    # their own default (section()'s "merge over defaults" contract).
    assert experimental_cfg["heavy_reliance_nudge"] is True
