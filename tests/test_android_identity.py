"""
Tests for docs/Proposals/ANDROID-IDENTITY-SYSTEM-BAR-SYNC.md section 2:
the Android scaffold derives the app name, the package id and the
system-bar colours from the build directory instead of hard-coding them.

These check the generated project *text* (Kotlin package lines, Gradle
`applicationId`, `themes.xml`/`colors.xml` content, XML well-formedness).
None of it builds with the Android SDK or runs on a device.
"""

import json
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

from arklight.backend.android import runtime
from arklight.cli.android import (
    AndroidError,
    _parse_css_color,
    _slugify_app_name,
    scaffold_project,
)
from arklight.cli.main import main
from arklight.compiler.pipeline import build

_PNG_BYTES = b"\x89PNG\r\n\x1a\n" + b"0" * 64


def make_site(tmp_path: Path, *, name: str | None = None, bg: str | None = None,
              title: str | None = None) -> Path:
    site_args = []
    if name is not None:
        site_args.append(repr(name))
    if bg is not None:
        site_args.append(f"bg={bg!r}")
    page_args = 'Heading("Hi"), Text("Hello.")'
    if title is not None:
        page_args += f", title={title!r}"
    (tmp_path / "site.py").write_text(
        "from arklight import *\n"
        f"site = Site({', '.join(site_args)})\n"
        '@site.page("/")\n'
        "def home():\n"
        f"    return Page({page_args})\n"
    )
    out_dir = tmp_path / "ARK"
    build(tmp_path / "site.py", out_dir)
    return out_dir


def write_config(tmp_path: Path, android_section: str) -> None:
    (tmp_path / "arklight.config.py").write_text(
        f'CONFIG = {{\n    "android": {android_section},\n}}\n'
    )


def inject_head(build_dir: Path, snippet: str) -> None:
    index = build_dir / "index.html"
    index.write_text(index.read_text().replace("</head>", snippet + "\n</head>", 1))


def scaffold(tmp_path: Path, build_dir: Path):
    project_dir = tmp_path / "proj"
    result = scaffold_project(build_dir, output_dir=project_dir)
    return result, project_dir


def res(project_dir: Path, rel: str) -> str:
    return (project_dir / "app/src/main/res" / rel).read_text()


# --------------------------------------------------------------------
# CSS colour parsing
# --------------------------------------------------------------------


@pytest.mark.parametrize(
    "value, expected",
    [
        ("#fff", "#FFFFFF"),
        ("#1a1a2e", "#1A1A2E"),
        ("#1A1A2E", "#1A1A2E"),
        ("#FFFF", "#FFFFFF"),  # 4-digit hex with full alpha
        ("#1a1a2eff", "#1A1A2E"),  # 8-digit hex with full alpha
        ("rgb(26, 26, 46)", "#1A1A2E"),
        ("rgb(26 26 46)", "#1A1A2E"),
        ("rgba(26, 26, 46, 1)", "#1A1A2E"),
        ("rgb(26 26 46 / 100%)", "#1A1A2E"),
        ("rgb(100%, 0%, 0%)", "#FF0000"),
        ("rgb(300, -5, 46)", "#FF002E"),  # clamped
        ("hsl(0, 100%, 50%)", "#FF0000"),
        ("hsl(120deg 100% 25%)", "#008000"),
        ("hsl(240, 100%, 50%)", "#0000FF"),
        ("hsla(0, 0%, 100%, 1)", "#FFFFFF"),
        ("white", "#FFFFFF"),
        ("  WHITE ", "#FFFFFF"),
        ("navy", "#000080"),
        ("orange", "#FFA500"),
        ("#fff !important", "#FFFFFF"),
    ],
)
def test_parse_css_color_understands_opaque_solid_colours(value, expected):
    assert _parse_css_color(value) == expected


@pytest.mark.parametrize(
    "value",
    [
        "",
        "   ",
        "transparent",
        "rebeccapurple",  # a named colour outside the supported set
        "linear-gradient(#fff, #000)",
        "url(bg.png)",
        "var(--brand)",
        "#12",
        "#12345",
        "#ffffff80",  # translucent hex
        "#fff8",
        "rgba(0, 0, 0, 0.5)",
        "rgb(0 0 0 / 50%)",
        "hsla(0, 0%, 0%, 0)",
        "rgb(1, 2)",
        "rgb(a, b, c)",
        "hsl(0, 100%)",
        "color-mix(in srgb, red, blue)",
        None,
        42,
    ],
)
def test_parse_css_color_rejects_everything_else(value):
    assert _parse_css_color(value) is None


# --------------------------------------------------------------------
# Luminance / icon lightness
# --------------------------------------------------------------------


def test_relative_luminance_endpoints():
    assert runtime.relative_luminance("#000000") == pytest.approx(0.0)
    assert runtime.relative_luminance("#FFFFFF") == pytest.approx(1.0)


def test_dark_icons_only_above_the_equal_contrast_point():
    assert runtime.uses_dark_bar_icons("#FFFFFF")
    assert runtime.uses_dark_bar_icons("#FBFDFA")
    assert runtime.uses_dark_bar_icons("#FFFF00")
    assert not runtime.uses_dark_bar_icons("#000000")
    assert not runtime.uses_dark_bar_icons("#1A1A2E")
    assert not runtime.uses_dark_bar_icons("#4F46E5")
    # 0.179 sits between these two greys.
    assert not runtime.uses_dark_bar_icons("#757575")
    assert runtime.uses_dark_bar_icons("#777777")


def test_relative_luminance_rejects_non_hex():
    with pytest.raises(ValueError):
        runtime.relative_luminance("white")


# --------------------------------------------------------------------
# Package-id slugs
# --------------------------------------------------------------------


@pytest.mark.parametrize(
    "name, slug",
    [
        ("Recipe Box", "recipe_box"),
        ("site-name", "site_name"),
        ("ARKlight", "arklight"),
        ("  Hello,   World!  ", "hello_world"),
        ("Café Déjà Vu", "cafe_deja_vu"),
        ("2048", "app_2048"),
        ("3D Viewer", "app_3d_viewer"),
        ("New", "new_app"),
        ("Class", "class_app"),
        ("Fun", "fun_app"),
        ("In", "in_app"),
        ("Object", "object_app"),
        ("日本語", "app"),
        ("!!!", "app"),
        ("", "app"),
        ("A" * 80, "a" * 40),
    ],
)
def test_slugify_app_name(name, slug):
    assert _slugify_app_name(name) == slug


def test_slug_is_never_longer_than_40_and_never_ends_in_underscore():
    for name in ("x" * 39 + " y", "1" * 60, "class " * 20):
        slug = _slugify_app_name(name)
        assert len(slug) <= 40
        assert not slug.endswith("_")


# --------------------------------------------------------------------
# App name resolution
# --------------------------------------------------------------------


def test_named_site_names_the_app_and_derives_the_package_id(tmp_path):
    build_dir = make_site(tmp_path, name="Recipe Box")
    result, project_dir = scaffold(tmp_path, build_dir)

    assert result.app_name == "Recipe Box"
    assert result.app_name_source == "from index.html <title>"
    assert result.package_id == "com.arklight.recipe_box"
    assert result.package_id_source == "derived from app name"
    assert not result.package_id_configured

    assert "Recipe Box" in res(project_dir, "values/strings.xml")
    kt = project_dir / "app/src/main/java/com/arklight/recipe_box/MainActivity.kt"
    assert kt.read_text().startswith("package com.arklight.recipe_box\n")
    gradle = (project_dir / "app/build.gradle.kts").read_text()
    assert 'applicationId = "com.arklight.recipe_box"' in gradle


def test_unnamed_site_keeps_the_old_name_and_package_id(tmp_path):
    build_dir = make_site(tmp_path)  # Site() -> <title>arklight-site</title>
    result, project_dir = scaffold(tmp_path, build_dir)

    assert result.app_name == "ARKlight App"
    assert result.package_id == "com.arklight.app"
    assert (project_dir / "app/src/main/java/com/arklight/app/MainActivity.kt").exists()


def test_page_title_names_the_app_with_entities_decoded_once(tmp_path):
    # The compiler writes `Fish &amp; Chips` into <title>; one decode
    # gives back the text the author wrote.
    build_dir = make_site(tmp_path, name="Ignored", title="Fish & Chips")
    result, project_dir = scaffold(tmp_path, build_dir)

    assert result.app_name == "Fish & Chips"
    assert result.package_id == "com.arklight.fish_chips"
    # XML-escaped again on the way into strings.xml, as before.
    assert "Fish &amp; Chips" in res(project_dir, "values/strings.xml")


def test_entities_are_decoded_once_not_twice(tmp_path):
    # An author who literally wrote "&amp;" gets "&amp;" (compiled to
    # `&amp;amp;`), not a second decode down to "&".
    build_dir = make_site(tmp_path, title="A &amp; B")
    result, _ = scaffold(tmp_path, build_dir)
    assert result.app_name == "A &amp; B"


def test_title_whitespace_is_collapsed(tmp_path):
    build_dir = make_site(tmp_path)
    index = build_dir / "index.html"
    index.write_text(
        index.read_text().replace(
            "<title>arklight-site</title>", "<title>\n   My \t  Notes \n</title>"
        )
    )
    result, _ = scaffold(tmp_path, build_dir)
    assert result.app_name == "My Notes"


def test_title_outside_head_is_ignored(tmp_path):
    build_dir = make_site(tmp_path)
    index = build_dir / "index.html"
    index.write_text(
        index.read_text().replace(
            "<body>", "<body><svg><title>Chart caption</title></svg>", 1
        )
    )
    result, _ = scaffold(tmp_path, build_dir)
    assert result.app_name == "ARKlight App"


def test_title_inside_a_head_comment_is_ignored(tmp_path):
    build_dir = make_site(tmp_path)
    index = build_dir / "index.html"
    index.write_text(
        index.read_text().replace(
            "<title>arklight-site</title>",
            "<!-- <title>Old</title> --><title>arklight-site</title>",
        )
    )
    result, _ = scaffold(tmp_path, build_dir)
    assert result.app_name == "ARKlight App"


def test_pwa_manifest_name_beats_the_title(tmp_path):
    build_dir = make_site(tmp_path, name="Recipe Box")
    (build_dir / "manifest.json").write_text(json.dumps({"name": "Recipe Box Pro"}))
    result, _ = scaffold(tmp_path, build_dir)

    assert result.app_name == "Recipe Box Pro"
    assert result.app_name_source == "from manifest.json name"
    assert result.package_id == "com.arklight.recipe_box_pro"


def test_pwa_manifest_with_the_placeholder_name_falls_through_to_title(tmp_path):
    build_dir = make_site(tmp_path, name="Recipe Box")
    (build_dir / "manifest.json").write_text(json.dumps({"name": "arklight-site"}))
    result, _ = scaffold(tmp_path, build_dir)
    assert result.app_name == "Recipe Box"


def test_malformed_pwa_manifest_falls_through_to_title(tmp_path):
    build_dir = make_site(tmp_path, name="Recipe Box")
    (build_dir / "manifest.json").write_text("{not json")
    result, _ = scaffold(tmp_path, build_dir)
    assert result.app_name == "Recipe Box"


def test_config_app_name_beats_everything_and_still_derives_the_package_id(tmp_path):
    build_dir = make_site(tmp_path, name="Recipe Box")
    (build_dir / "manifest.json").write_text(json.dumps({"name": "From Manifest"}))
    write_config(tmp_path, '{"app_name": "My Cool App!"}')
    result, project_dir = scaffold(tmp_path, build_dir)

    assert result.app_name == "My Cool App!"
    assert result.app_name_source == "from android.app_name in arklight.config.py"
    assert result.package_id == "com.arklight.my_cool_app"
    assert (project_dir / "app/src/main/java/com/arklight/my_cool_app").is_dir()


@pytest.mark.parametrize("bad", ['""', '"   "', "5", "[]"])
def test_config_app_name_must_still_be_a_non_empty_string(tmp_path, bad):
    build_dir = make_site(tmp_path, name="Recipe Box")
    write_config(tmp_path, f'{{"app_name": {bad}}}')
    with pytest.raises(AndroidError, match="android.app_name must be a non-empty string"):
        scaffold(tmp_path, build_dir)


# --------------------------------------------------------------------
# Package id resolution
# --------------------------------------------------------------------


def test_config_package_id_wins_over_a_derived_one(tmp_path):
    build_dir = make_site(tmp_path, name="Recipe Box")
    write_config(tmp_path, '{"package_id": "com.example.cookbook"}')
    result, _ = scaffold(tmp_path, build_dir)

    assert result.app_name == "Recipe Box"
    assert result.package_id == "com.example.cookbook"
    assert result.package_id_configured


def test_config_package_id_is_still_validated(tmp_path):
    build_dir = make_site(tmp_path, name="Recipe Box")
    write_config(tmp_path, '{"package_id": "recipe-box"}')
    with pytest.raises(AndroidError, match="Invalid android.package_id"):
        scaffold(tmp_path, build_dir)


def test_configured_old_default_package_id_keeps_the_old_identity(tmp_path):
    build_dir = make_site(tmp_path, name="Recipe Box")
    write_config(tmp_path, '{"package_id": "com.arklight.app"}')
    result, _ = scaffold(tmp_path, build_dir)
    assert result.package_id == "com.arklight.app"


@pytest.mark.parametrize("name", ["2048", "New", "Class", "日本語", "site-name", "Fun & Games"])
def test_derived_package_ids_are_always_legal(tmp_path, name):
    build_dir = make_site(tmp_path, name=name)
    result, project_dir = scaffold(tmp_path, build_dir)

    segments = result.package_id.split(".")
    assert segments[:2] == ["com", "arklight"]
    last = segments[-1]
    assert last[0].isalpha() and last.replace("_", "").isalnum()
    assert last not in runtime_reserved_words()
    kt = project_dir / f"app/src/main/java/{'/'.join(segments)}/MainActivity.kt"
    assert kt.read_text().startswith(f"package {result.package_id}\n")


def runtime_reserved_words() -> set[str]:
    from arklight.cli.android import _RESERVED_WORDS

    return set(_RESERVED_WORDS)


# --------------------------------------------------------------------
# System bars: resolution
# --------------------------------------------------------------------


def test_auto_reads_the_stylesheet_background(tmp_path):
    build_dir = make_site(tmp_path, name="Dark", bg="#1a1a2e")
    result, project_dir = scaffold(tmp_path, build_dir)

    assert result.system_bar_color == "#1A1A2E"
    assert result.system_bar_source == "from stylesheet --ark-bg"
    assert result.system_bar_note is None
    assert '<color name="ark_site_background">#1A1A2E</color>' in res(
        project_dir, "values/colors.xml"
    )


def test_stock_site_gets_white_bars(tmp_path):
    result, _ = scaffold(tmp_path, make_site(tmp_path))
    assert result.system_bar_color == "#FFFFFF"


def test_theme_color_meta_beats_the_stylesheet(tmp_path):
    build_dir = make_site(tmp_path, bg="#1a1a2e")
    inject_head(build_dir, '<meta name="theme-color" content="#336699">')
    result, _ = scaffold(tmp_path, build_dir)

    assert result.system_bar_color == "#336699"
    assert result.system_bar_source == "from theme-color meta tag"


def test_dark_media_theme_color_is_ignored(tmp_path):
    build_dir = make_site(tmp_path, bg="#1a1a2e")
    inject_head(
        build_dir,
        '<meta name="theme-color" content="#000000" '
        'media="(prefers-color-scheme: dark)">\n'
        '<meta name="theme-color" content="#336699" '
        'media="(prefers-color-scheme: light)">',
    )
    assert scaffold(tmp_path, build_dir)[0].system_bar_color == "#336699"


def test_only_a_dark_media_theme_color_falls_through_to_the_stylesheet(tmp_path):
    build_dir = make_site(tmp_path, bg="#1a1a2e")
    inject_head(
        build_dir,
        '<meta name="theme-color" content="#000000" media="(prefers-color-scheme: dark)">',
    )
    result, _ = scaffold(tmp_path, build_dir)
    assert result.system_bar_color == "#1A1A2E"
    assert result.system_bar_source == "from stylesheet --ark-bg"


def test_ark_bg_in_a_css_comment_or_property_rule_is_not_used(tmp_path):
    build_dir = make_site(tmp_path, bg="#1a1a2e")
    css = build_dir / "styles.css"
    css.write_text(
        "/* :root { --ark-bg: #ff0000; } */\n"
        "@property --ark-bg { syntax: '<color>'; inherits: true; initial-value: #00ff00; }\n"
        ":root { --ark-bg: #123456; }\n"
    )
    assert scaffold(tmp_path, build_dir)[0].system_bar_color == "#123456"


def test_last_root_ark_bg_declaration_wins(tmp_path):
    build_dir = make_site(tmp_path)
    (build_dir / "styles.css").write_text(
        ":root { --ark-bg: #111111; }\n:root { --ark-bg: #222222; }\n"
    )
    assert scaffold(tmp_path, build_dir)[0].system_bar_color == "#222222"


def test_stylesheet_link_outside_the_build_dir_or_external_is_not_read(tmp_path):
    build_dir = make_site(tmp_path)
    (tmp_path / "evil.css").write_text(":root { --ark-bg: #ff0000; }")
    (build_dir / "styles.css").write_text("/* no bg here */")
    inject_head(
        build_dir,
        '<link rel="stylesheet" href="../evil.css">\n'
        '<link rel="stylesheet" href="https://example.com/x.css">',
    )
    result, _ = scaffold(tmp_path, build_dir)
    assert result.system_bar_color is None
    assert "no theme-color meta tag or --ark-bg" in result.system_bar_note


@pytest.mark.parametrize(
    "value",
    [
        "linear-gradient(#fff, #000)",
        "var(--brand)",
        "rgba(0, 0, 0, 0.5)",
        "transparent",
        "rebeccapurple",
    ],
)
def test_auto_falls_back_to_material_and_names_the_value_it_could_not_use(tmp_path, value):
    build_dir = make_site(tmp_path)
    (build_dir / "styles.css").write_text(f":root {{ --ark-bg: {value}; }}")
    result, project_dir = scaffold(tmp_path, build_dir)

    assert result.system_bar_color is None
    assert value in result.system_bar_note
    assert "ark_site_background" not in res(project_dir, "values/colors.xml")
    assert "ark_site_background" not in res(project_dir, "values/themes.xml")


def test_unusable_theme_color_does_not_silently_use_the_stylesheet(tmp_path):
    build_dir = make_site(tmp_path, bg="#1a1a2e")
    inject_head(build_dir, '<meta name="theme-color" content="var(--x)">')
    result, _ = scaffold(tmp_path, build_dir)

    assert result.system_bar_color is None
    assert "var(--x)" in result.system_bar_note
    assert "theme-color meta tag" in result.system_bar_note


def test_auto_with_no_colour_information_falls_back_to_material(tmp_path):
    build_dir = make_site(tmp_path)
    (build_dir / "styles.css").write_text("body { margin: 0; }")
    result, _ = scaffold(tmp_path, build_dir)
    assert result.system_bar_color is None
    assert result.system_bar_note


@pytest.mark.parametrize(
    "value, expected",
    [
        ("#1a1a2e", "#1A1A2E"),
        ("rgb(26, 26, 46)", "#1A1A2E"),
        ("white", "#FFFFFF"),
        ("hsl(0, 100%, 50%)", "#FF0000"),
        ("AUTO", "#FFFFFF"),
    ],
)
def test_config_status_bar_color_accepts_css_colours(tmp_path, value, expected):
    build_dir = make_site(tmp_path)
    write_config(tmp_path, f'{{"status_bar_color": {value!r}}}')
    result, _ = scaffold(tmp_path, build_dir)
    assert result.system_bar_color == expected


def test_config_colour_beats_the_page(tmp_path):
    build_dir = make_site(tmp_path, bg="#1a1a2e")
    inject_head(build_dir, '<meta name="theme-color" content="#336699">')
    write_config(tmp_path, '{"status_bar_color": "#ff8800"}')
    result, _ = scaffold(tmp_path, build_dir)
    assert result.system_bar_color == "#FF8800"
    assert result.system_bar_source == "from android.status_bar_color in arklight.config.py"


@pytest.mark.parametrize(
    "value",
    [
        '"linear-gradient(#fff, #000)"',
        '"var(--x)"',
        '"transparent"',
        '"rgba(0,0,0,.5)"',
        '"rebeccapurple"',
        '"not a colour"',
        '""',
        "5",
        "None",
        "True",
    ],
)
def test_invalid_explicit_status_bar_color_is_a_build_error(tmp_path, value):
    build_dir = make_site(tmp_path)
    write_config(tmp_path, f'{{"status_bar_color": {value}}}')
    with pytest.raises(AndroidError, match="status_bar_color"):
        scaffold(tmp_path, build_dir)


# --------------------------------------------------------------------
# System bars: generated resources
# --------------------------------------------------------------------


def test_site_colour_drives_window_background_bars_and_icons(tmp_path):
    build_dir = make_site(tmp_path, bg="#ffffff")
    _, project_dir = scaffold(tmp_path, build_dir)

    for folder in ("values", "values-night"):
        themes = res(project_dir, f"{folder}/themes.xml")
        assert (
            '<item name="android:windowBackground">@color/ark_site_background</item>' in themes
        )
        assert (
            '<item name="android:statusBarColor" tools:targetApi="21">'
            "@color/ark_site_background</item>" in themes
        )
        assert (
            '<item name="android:navigationBarColor" tools:targetApi="27">'
            "@color/ark_site_background</item>" in themes
        )
        # A white page: dark icons -- in the night theme file too.
        assert '"android:windowLightStatusBar" tools:targetApi="23">true<' in themes
        assert '"android:windowLightNavigationBar" tools:targetApi="27">true<' in themes
        assert "colorSurface</item>\n        <item name=\"android:windowLight" not in themes
        assert '<color name="ark_site_background">#FFFFFF</color>' in res(
            project_dir, f"{folder}/colors.xml"
        )


def test_dark_site_colour_gets_light_icons_in_both_theme_files(tmp_path):
    build_dir = make_site(tmp_path, bg="#1a1a2e")
    _, project_dir = scaffold(tmp_path, build_dir)

    for folder in ("values", "values-night"):
        themes = res(project_dir, f"{folder}/themes.xml")
        assert '"android:windowLightStatusBar" tools:targetApi="23">false<' in themes
        assert '"android:windowLightNavigationBar" tools:targetApi="27">false<' in themes


def test_edge_to_edge_keeps_the_bars_transparent(tmp_path):
    build_dir = make_site(tmp_path, bg="#1a1a2e")
    write_config(tmp_path, '{"edge_to_edge": True}')
    _, project_dir = scaffold(tmp_path, build_dir)

    themes = res(project_dir, "values/themes.xml")
    assert (
        '<item name="android:statusBarColor" tools:targetApi="21">'
        "@android:color/transparent</item>" in themes
    )
    assert (
        '<item name="android:navigationBarColor" tools:targetApi="27">'
        "@android:color/transparent</item>" in themes
    )
    # ...but the window behind them and the icon lightness still follow the site.
    assert "android:windowBackground\">@color/ark_site_background" in themes
    assert '"android:windowLightStatusBar" tools:targetApi="23">false<' in themes


def test_splash_background_follows_the_site_colour(tmp_path):
    build_dir = make_site(tmp_path, bg="#1a1a2e")
    (build_dir / "splash.png").write_bytes(_PNG_BYTES)
    write_config(tmp_path, '{"splash": "splash.png"}')
    _, project_dir = scaffold(tmp_path, build_dir)

    for folder in ("values", "values-night"):
        themes = res(project_dir, f"{folder}/themes.xml")
        assert (
            '<item name="windowSplashScreenBackground">@color/ark_site_background</item>'
            in themes
        )


def test_material_setting_keeps_the_material_theme(tmp_path):
    build_dir = make_site(tmp_path, bg="#1a1a2e")
    (build_dir / "splash.png").write_bytes(_PNG_BYTES)
    write_config(tmp_path, '{"status_bar_color": "material", "splash": "splash.png"}')
    result, project_dir = scaffold(tmp_path, build_dir)

    assert result.system_bar_color is None
    for folder in ("values", "values-night"):
        assert "ark_site_background" not in res(project_dir, f"{folder}/colors.xml")
        themes = res(project_dir, f"{folder}/themes.xml")
        assert "ark_site_background" not in themes
        assert "windowBackground" not in themes
        assert "?attr/colorSurface</item>" in themes
        assert "windowSplashScreenBackground\">@color/md_theme_background" in themes
    # Icon lightness stays tied to day/night, exactly as before.
    assert '"android:windowLightStatusBar" tools:targetApi="23">true<' in res(
        project_dir, "values/themes.xml"
    )
    assert '"android:windowLightStatusBar" tools:targetApi="23">false<' in res(
        project_dir, "values-night/themes.xml"
    )


def test_no_system_bar_colour_leaves_runtime_output_untouched():
    kwargs = {
        "app_name": "A",
        "package_id": "com.example.a",
        "version_name": "1.0.0",
        "version_code": 1,
        "orientation": "portrait",
        "edge_to_edge": False,
        "has_custom_icon": False,
        "has_splash": True,
    }
    assert runtime.project_files(**kwargs) == runtime.project_files(
        **kwargs, system_bar_color=None
    )


def test_project_files_rejects_a_non_hex_system_bar_colour():
    with pytest.raises(ValueError, match="system_bar_color"):
        runtime.project_files(
            app_name="A",
            package_id="com.example.a",
            version_name="1.0.0",
            version_code=1,
            orientation="portrait",
            edge_to_edge=False,
            has_custom_icon=False,
            has_splash=False,
            system_bar_color="white",
        )


@pytest.mark.parametrize("bg", ["#ffffff", "#1a1a2e"])
@pytest.mark.parametrize("edge_to_edge", [False, True])
@pytest.mark.parametrize("splash", [False, True])
def test_every_generated_resource_file_is_well_formed_xml(tmp_path, bg, edge_to_edge, splash):
    build_dir = make_site(tmp_path, name="Fish & Chips <3", bg=bg)
    cfg = {"edge_to_edge": edge_to_edge}
    if splash:
        (build_dir / "splash.png").write_bytes(_PNG_BYTES)
        cfg["splash"] = "splash.png"
    write_config(tmp_path, repr(cfg))
    _, project_dir = scaffold(tmp_path, build_dir)

    xml_files = list((project_dir / "app/src/main").rglob("*.xml"))
    assert xml_files
    for path in xml_files:
        ET.parse(path)  # raises on malformed XML


# --------------------------------------------------------------------
# CLI reporting
# --------------------------------------------------------------------


def test_cli_reports_what_it_decided(tmp_path, capsys, monkeypatch):
    build_dir = make_site(tmp_path, name="Recipe Box", bg="#1a1a2e")
    monkeypatch.chdir(tmp_path)

    rc = main(["android", "scaffold", str(build_dir), "-o", str(tmp_path / "proj")])
    out = capsys.readouterr().out

    assert rc == 0
    assert "'Recipe Box' (com.arklight.recipe_box)" in out
    assert "name:        'Recipe Box' (from index.html <title>)" in out
    assert "package id:  com.arklight.recipe_box (derived from app name)" in out
    assert "system bars: #1A1A2E (from stylesheet --ark-bg)" in out
    assert "a package id you control before publishing" in out


def test_cli_omits_the_package_id_reminder_when_the_id_is_configured(
    tmp_path, capsys, monkeypatch
):
    build_dir = make_site(tmp_path, name="Recipe Box")
    write_config(tmp_path, '{"package_id": "com.example.cookbook"}')
    monkeypatch.chdir(tmp_path)

    rc = main(["android", "scaffold", str(build_dir), "-o", str(tmp_path / "proj")])
    out = capsys.readouterr().out

    assert rc == 0
    assert "package id:  com.example.cookbook (from android.package_id in arklight.config.py)" in out
    assert "package id you control" not in out


def test_cli_says_when_auto_fell_back_to_material(tmp_path, capsys, monkeypatch):
    build_dir = make_site(tmp_path)
    (build_dir / "styles.css").write_text(":root { --ark-bg: linear-gradient(#fff, #000); }")
    monkeypatch.chdir(tmp_path)

    rc = main(["android", "scaffold", str(build_dir), "-o", str(tmp_path / "proj")])
    out = capsys.readouterr().out

    assert rc == 0
    assert "system bars: Material theme colours" in out
    assert "linear-gradient(#fff, #000)" in out


def test_cli_invalid_status_bar_color_fails_with_a_message(tmp_path, capsys, monkeypatch):
    build_dir = make_site(tmp_path)
    write_config(tmp_path, '{"status_bar_color": "var(--x)"}')
    monkeypatch.chdir(tmp_path)

    rc = main(["android", "scaffold", str(build_dir), "-o", str(tmp_path / "proj")])
    err = capsys.readouterr().err

    assert rc == 1
    assert "status_bar_color" in err
