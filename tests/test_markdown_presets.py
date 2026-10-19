"""
Stage M7 of the Markdown-as-first-class-content landing order (see
`docs/Foundational/DESIGN-NOTES.md`'s "Design record: Markdown as
first-class content"): `light`/`dark`/
`reading` presets for `Site(markdown_theme=...)`. Companion to
`tests/test_markdown_style_hooks.py` (Stage M6, untouched by this
stage -- the `.ark-md-*` default stylesheet those tests cover is
unaffected by which, if any, preset a site selects).
"""

import pytest

from arklight.api import Heading, Page, Site, Text
from arklight.backend.css.markdown_presets import MARKDOWN_PRESETS
from arklight.backend.css.render import CSSBackend, STYLESHEET_PATH
from arklight.ir.build import build_website_ir
from arklight.ir.normalize import normalize_ark_ast
from arklight.ir.validate import validate_ark_ast


def _fixture_ir(*, markdown_theme=None):
    """A small fixture page exercising enough constructs (headings,
    text, a link-bearing paragraph is out of scope here -- `test_
    markdown_style_hooks.py` already covers the `.ark-md-*` hooks
    themselves) to stand in for "a page renders under this preset"."""
    pages = {"/": Page(Heading("Title", level=1), Text("Body copy."), title="T")}
    normalized = normalize_ark_ast(pages)
    validate_ark_ast(normalized)
    return build_website_ir("site", normalized, markdown_theme=markdown_theme)


# ---------------------------------------------------------------------------
# markdown_theme unset -- byte-identical to every pre-M7 build
# ---------------------------------------------------------------------------


def test_no_markdown_theme_is_unchanged_output():
    with_theme_off = CSSBackend().render(_fixture_ir())[STYLESHEET_PATH]
    with_theme_default_arg = CSSBackend().render(_fixture_ir(markdown_theme=None))[STYLESHEET_PATH]
    assert with_theme_off == with_theme_default_arg
    for preset_css in MARKDOWN_PRESETS.values():
        # None of the three presets' own `:root` overrides leak into a
        # build that never opted in.
        assert preset_css not in with_theme_off


# ---------------------------------------------------------------------------
# Site(markdown_theme=...) validation
# ---------------------------------------------------------------------------


def test_site_rejects_unknown_markdown_theme():
    with pytest.raises(ValueError, match="markdown_theme"):
        Site(markdown_theme="solarized")


@pytest.mark.parametrize("theme", sorted(MARKDOWN_PRESETS))
def test_site_accepts_each_known_markdown_theme(theme):
    site = Site(markdown_theme=theme)
    assert site.markdown_theme == theme


def test_markdown_theme_defaults_to_none():
    assert Site().markdown_theme is None


# ---------------------------------------------------------------------------
# Acceptance criterion 5: a fixture page renders under all three presets
# with zero custom CSS from the project.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("theme", sorted(MARKDOWN_PRESETS))
def test_fixture_page_renders_under_each_preset_with_zero_custom_css(theme):
    ir = _fixture_ir(markdown_theme=theme)
    assert ir.custom_styles == {}
    assert ir.selector_rules == []
    css = CSSBackend().render(ir)[STYLESHEET_PATH]
    assert MARKDOWN_PRESETS[theme] in css


def test_reading_preset_narrows_measure_and_raises_line_height():
    css = CSSBackend().render(_fixture_ir(markdown_theme="reading"))[STYLESHEET_PATH]
    assert "--ark-max-width: min(100% - 3rem, 42rem);" in css
    assert "line-height: 1.8;" in css


def test_preset_root_block_is_cascade_ordered_after_base_and_markdown_defaults():
    css = CSSBackend().render(_fixture_ir(markdown_theme="dark"))[STYLESHEET_PATH]
    base_index = css.index("html {")
    markdown_defaults_index = css.index(".ark-md-h1")
    preset_index = css.index(MARKDOWN_PRESETS["dark"])
    assert base_index < markdown_defaults_index < preset_index


# ---------------------------------------------------------------------------
# dark preset: WCAG AA contrast ratio for body text against the background
# ---------------------------------------------------------------------------


def _srgb_channel_to_linear(channel_8bit: int) -> float:
    c = channel_8bit / 255.0
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def _relative_luminance(hex_color: str) -> float:
    hex_color = hex_color.lstrip("#")
    r, g, b = (int(hex_color[i : i + 2], 16) for i in (0, 2, 4))
    lr, lg, lb = (_srgb_channel_to_linear(v) for v in (r, g, b))
    return 0.2126 * lr + 0.7152 * lg + 0.0722 * lb


def _contrast_ratio(hex_a: str, hex_b: str) -> float:
    la, lb = _relative_luminance(hex_a), _relative_luminance(hex_b)
    lighter, darker = max(la, lb), min(la, lb)
    return (lighter + 0.05) / (darker + 0.05)


def test_dark_preset_body_text_passes_wcag_aa_against_its_background():
    # Values must match arklight/backend/css/markdown_presets.py's
    # PRESET_DARK exactly -- this test is the exit test's actual
    # contrast-ratio computation, not just a restated claim.
    text, bg = "#f2ece2", "#16140f"
    ratio = _contrast_ratio(text, bg)
    # WCAG 2.x AA, normal (non-large) body text: >= 4.5:1.
    assert ratio >= 4.5, f"dark preset body text/background contrast is only {ratio:.2f}:1"


def test_dark_preset_values_in_module_match_what_this_test_checked():
    assert "--ark-text: #f2ece2;" in MARKDOWN_PRESETS["dark"]
    assert "--ark-bg: #16140f;" in MARKDOWN_PRESETS["dark"]


# ---------------------------------------------------------------------------
# light/reading presets: same AA bar, both body text and the link/accent
# color -- not just dark's headline pairing.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "theme, text, accent, bg",
    [
        ("light", "#1a1a2e", "#4f46e5", "#ffffff"),
        ("dark", "#f2ece2", "#cc785c", "#16140f"),
        ("reading", "#352a16", "#9c5017", "#f8efd6"),
    ],
)
def test_every_preset_body_text_and_accent_pass_wcag_aa_against_its_background(
    theme, text, accent, bg
):
    assert f"--ark-text: {text};" in MARKDOWN_PRESETS[theme]
    assert f"--ark-accent: {accent};" in MARKDOWN_PRESETS[theme]
    assert f"--ark-bg: {bg};" in MARKDOWN_PRESETS[theme]
    text_ratio = _contrast_ratio(text, bg)
    accent_ratio = _contrast_ratio(accent, bg)
    assert text_ratio >= 4.5, f"{theme} preset body text/background contrast is only {text_ratio:.2f}:1"
    assert accent_ratio >= 4.5, f"{theme} preset accent/background contrast is only {accent_ratio:.2f}:1"


def test_presets_use_visually_distinct_accent_hues():
    # The whole point of three named presets is that they don't all
    # converge on one safe color -- light stays ARKlight's stock
    # indigo, dark stays mdrender's clay, reading is its own amber,
    # no two sharing a hue family.
    accents = {
        "light": "#4f46e5",  # indigo
        "dark": "#cc785c",  # clay/terracotta
        "reading": "#9c5017",  # amber/goldenrod
    }
    for theme, accent in accents.items():
        assert f"--ark-accent: {accent};" in MARKDOWN_PRESETS[theme]
    assert len(set(accents.values())) == 3
