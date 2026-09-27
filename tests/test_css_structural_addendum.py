import pytest

from arklight.api import CSSSyntaxError, DuplicateStyleNameError, Page, Site, Text
from arklight.backend.css.render import CSSBackend, STYLESHEET_PATH
from arklight.ir.build import build_website_ir
from arklight.ir.normalize import normalize_ark_ast
from arklight.ir.validate import validate_ark_ast


def _render_css(site: Site) -> str:
    ark_ast = site.build_ark_ast()
    normalized = normalize_ark_ast(ark_ast)
    validate_ark_ast(normalized)
    ir = build_website_ir(
        site.name,
        normalized,
        custom_styles=site.custom_styles,
        media_queries=site.custom_media_queries,
        css_var_overrides=site.css_var_overrides,
        lang=site.lang,
        selector_rules=site.selector_rules,
        keyframes=site.custom_keyframes,
        font_faces=site.font_faces,
        container_queries=site.container_queries,
        supports_rules=site.supports_rules,
        page_rules=site.page_rules,
        style_imports=site.style_imports,
    )
    return CSSBackend().render(ir)[STYLESHEET_PATH]


def _new_site() -> Site:
    site = Site()

    @site.page("/")
    def home():
        return Page(Text("hi"))

    return site


# ---------------------------------------------------------------------------
# style_selector
# ---------------------------------------------------------------------------


def test_style_selector_combinator():
    site = _new_site()
    site.style_selector(".a > .b", {"color": "red"})
    css = _render_css(site)
    assert ".a > .b {" in css
    assert "color: red;" in css


def test_style_selector_grouped_selector():
    site = _new_site()
    site.style_selector("h1, h2, h3", {"font-family": "sans-serif"})
    css = _render_css(site)
    assert "h1, h2, h3 {" in css


def test_style_selector_bare_tag_override():
    site = _new_site()
    site.style_selector("blockquote", {"font-style": "italic"})
    css = _render_css(site)
    assert "blockquote {" in css
    assert "font-style: italic;" in css


def test_style_selector_attribute_selector():
    site = _new_site()
    site.style_selector('[data-state="open"] .panel', {"display": "block"})
    css = _render_css(site)
    assert '[data-state="open"] .panel {' in css


def test_style_selector_pseudo_element():
    site = _new_site()
    site.style_selector(".card::before", {"content": '""'})
    css = _render_css(site)
    assert ".card::before {" in css


def test_style_selector_functional_pseudo_classes():
    site = _new_site()
    site.style_selector(".card:not(.disabled)", {"cursor": "pointer"})
    site.style_selector("li:nth-child(2n+1)", {"background": "#eee"})
    site.style_selector(".wrap:has(> .icon)", {"padding-left": "2rem"})
    css = _render_css(site)
    assert ".card:not(.disabled) {" in css
    assert "li:nth-child(2n+1) {" in css
    assert ".wrap:has(> .icon) {" in css


def test_style_selector_nesting_pseudo_class():
    site = _new_site()
    site.style_selector(".panel", {
        "padding": "1rem",
        "&:hover": {"box-shadow": "0 2px 8px rgba(0,0,0,.15)"},
    })
    css = _render_css(site)
    assert ".panel {" in css
    assert ".panel:hover {" in css


def test_style_selector_nesting_descendant_and_combinator():
    site = _new_site()
    site.style_selector(".panel", {
        "& .title": {"font-weight": "bold"},
        "& > img": {"border-radius": "8px"},
    })
    css = _render_css(site)
    assert ".panel .title {" in css
    assert ".panel > img {" in css


def test_style_selector_nesting_requires_single_base_selector():
    site = _new_site()
    with pytest.raises(CSSSyntaxError):
        site.style_selector("h1, h2", {"&:hover": {"color": "red"}})


def test_style_selector_rejects_unknown_tag():
    site = _new_site()
    with pytest.raises(CSSSyntaxError):
        site.style_selector("made-up-tag", {"color": "red"})


def test_style_selector_rejects_pseudo_shorthand():
    site = _new_site()
    with pytest.raises(CSSSyntaxError):
        site.style_selector(".a", {":hover:color": "red"})


def test_style_selector_bare_class_colliding_with_reserved_utility_raises():
    site = _new_site()
    with pytest.raises(DuplicateStyleNameError, match="built-in"):
        site.style_selector(".card", {"background": "#1F2E27"})
    assert site.selector_rules == []


def test_style_selector_bare_class_colliding_with_reserved_utility_allows_redefine():
    site = _new_site()
    site.style_selector(".card", {"background": "#1F2E27"}, allow_redefine=True)
    assert (".card", {"background": "#1F2E27"}) in site.selector_rules


def test_style_selector_grouped_bare_class_colliding_with_reserved_utility_raises():
    site = _new_site()
    with pytest.raises(DuplicateStyleNameError, match="built-in"):
        site.style_selector(".panel, .nav", {"color": "red"})


def test_style_selector_non_bare_selector_is_not_checked_against_reserved_utility():
    # `.card::before` and `.card:not(.disabled)` aren't the bare `.card`
    # shape `style()` itself can emit, so they don't collide with it.
    site = _new_site()
    site.style_selector(".card::before", {"content": '""'})
    site.style_selector(".card:not(.disabled)", {"cursor": "pointer"})
    assert len(site.selector_rules) == 2


def test_style_selector_bare_class_colliding_with_existing_style_raises():
    site = _new_site()
    site.style("brand", {"color": "red"})
    with pytest.raises(DuplicateStyleNameError, match="site.style"):
        site.style_selector(".brand", {"color": "blue"})


def test_style_selector_called_twice_with_same_selector_raises():
    site = _new_site()
    site.style_selector(".panel", {"color": "red"})
    with pytest.raises(DuplicateStyleNameError, match="already registered"):
        site.style_selector(".panel", {"color": "blue"})
    assert site.selector_rules == [(".panel", {"color": "red"})]


def test_style_selector_called_twice_with_allow_redefine_appends():
    site = _new_site()
    site.style_selector(".panel", {"color": "red"})
    site.style_selector(".panel", {"color": "blue"}, allow_redefine=True)
    assert site.selector_rules == [
        (".panel", {"color": "red"}),
        (".panel", {"color": "blue"}),
    ]


# ---------------------------------------------------------------------------
# keyframes
# ---------------------------------------------------------------------------


def test_keyframes_renders_sorted_stops():
    site = _new_site()
    site.keyframes("fade-in", {"100%": {"opacity": "1"}, "0%": {"opacity": "0"}})
    css = _render_css(site)
    assert "@keyframes fade-in {" in css
    zero_idx = css.index("0% {")
    hundred_idx = css.index("100% {")
    assert zero_idx < hundred_idx


def test_keyframes_supports_from_to():
    site = _new_site()
    site.keyframes("fade-in", {"to": {"opacity": "1"}, "from": {"opacity": "0"}})
    css = _render_css(site)
    from_idx = css.index("from {")
    to_idx = css.index("to {")
    assert from_idx < to_idx


def test_keyframes_rejects_bad_stop():
    site = _new_site()
    with pytest.raises(CSSSyntaxError):
        site.keyframes("fade-in", {"halfway": {"opacity": "0.5"}})


def test_keyframes_rejects_bad_name():
    site = _new_site()
    with pytest.raises(ValueError):
        site.keyframes("123-bad", {"from": {"opacity": "0"}})


# ---------------------------------------------------------------------------
# font_face
# ---------------------------------------------------------------------------


def test_font_face_single_url_string():
    site = _new_site()
    site.font_face("Inter", "/assets/inter.woff2")
    css = _render_css(site)
    assert "@font-face {" in css
    assert 'font-family: "Inter";' in css
    assert 'src: url("/assets/inter.woff2");' in css


def test_font_face_multi_format_list_and_descriptors():
    site = _new_site()
    site.font_face(
        "Inter",
        [
            {"url": "/assets/inter.woff2", "format": "woff2"},
            {"url": "/assets/inter.woff", "format": "woff"},
        ],
        font_weight="400 700",
        font_display="swap",
    )
    css = _render_css(site)
    assert 'url("/assets/inter.woff2") format("woff2")' in css
    assert 'url("/assets/inter.woff") format("woff")' in css
    assert "font-weight: 400 700;" in css
    assert "font-display: swap;" in css


def test_font_face_rejects_unsupported_format():
    site = _new_site()
    with pytest.raises(CSSSyntaxError):
        site.font_face("Inter", [{"url": "/x.woff2", "format": "bogus"}])


def test_font_face_rejects_unsafe_family_name():
    site = _new_site()
    with pytest.raises(CSSSyntaxError):
        site.font_face('Evil"; } body { color: red', "/x.woff2")


# ---------------------------------------------------------------------------
# container_query
# ---------------------------------------------------------------------------


def test_container_query_renders_named_container():
    site = _new_site()
    site.container_query("min-width: 400px", ".sidebar .title", {"font-size": "1.5rem"}, name="sidebar")
    css = _render_css(site)
    assert "@container sidebar (min-width: 400px) {" in css
    assert ".sidebar .title {" in css


def test_container_query_without_name():
    site = _new_site()
    site.container_query("min-width: 400px", ".title", {"font-size": "1.5rem"})
    css = _render_css(site)
    assert "@container (min-width: 400px) {" in css


def test_container_query_is_not_flagged_experimental():
    site = _new_site()
    site.container_query("min-width: 400px", ".title", {"font-size": "1.5rem"})
    assert site.experimental_usages == []


# ---------------------------------------------------------------------------
# supports
# ---------------------------------------------------------------------------


def test_supports_renders_feature_query():
    site = _new_site()
    site.supports("display: grid", ".grid-layout", {"display": "grid"})
    css = _render_css(site)
    assert "@supports (display: grid) {" in css
    assert ".grid-layout {" in css


# ---------------------------------------------------------------------------
# page_rule
# ---------------------------------------------------------------------------


def test_page_rule_bare_and_pseudo():
    site = _new_site()
    site.page_rule({"margin": "2cm"})
    site.page_rule({"margin-top": "4cm"}, pseudo="first")
    css = _render_css(site)
    assert "@page {" in css
    assert "@page :first {" in css


def test_page_rule_rejects_unknown_pseudo():
    site = _new_site()
    with pytest.raises(CSSSyntaxError):
        site.page_rule({"margin": "1cm"}, pseudo="weird")


# ---------------------------------------------------------------------------
# import_style
# ---------------------------------------------------------------------------


def test_import_style_renders_first_in_stylesheet():
    site = _new_site()
    site.import_style("https://fonts.googleapis.com/css2?family=Inter")
    css = _render_css(site)
    assert css.strip().split("\n")[1].startswith('@import url("https://fonts.googleapis.com')
    assert css.index("@import") < css.index("Generated by ARKlight")


def test_import_style_rejects_unsafe_url():
    site = _new_site()
    with pytest.raises(CSSSyntaxError):
        site.import_style('evil"; } body { color: red')


def test_import_style_is_flagged_experimental():
    # Unlike container_query (see test_container_query_is_not_flagged_experimental
    # above), an @import URL's contents can't be validated by ARKlight --
    # they're fetched and applied by the browser at request time -- so
    # this goes through the same css-media-queries-style experimental
    # gate (docs/Foundational/EXPERIMENTAL-APIS.md).
    site = _new_site()
    site.import_style("https://fonts.googleapis.com/css2?family=Inter")
    assert len(site.experimental_usages) == 1
    assert site.experimental_usages[0].feature_id == "css-import"
