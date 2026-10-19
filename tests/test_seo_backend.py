"""
Tests for `arklight.backend.seo.SEOBackend` -- Stage M9 pass (see
docs/Foundational/DESIGN-NOTES.md's "Design record: Markdown as
first-class content"): `robots.txt`,
`sitemap.xml`, the default `og-image.svg`, and the `<head>` tags that
wire the image (and, when set, `Site(author=...)`) into every page.

Same two-layer split `tests/test_html_head_meta.py` already uses for
its own backend: narrow unit tests directly against this module's
pure render functions/`SEOBackend` methods, plus a handful of
end-to-end tests through a real `build()` call for the parts (default
`<meta property="og:image">` injection into HTML another backend
rendered) that only make sense wired into a real pipeline run.
"""

from __future__ import annotations

from pathlib import Path

from arklight.backend.seo import (
    SEOBackend,
    _page_loc,
    _render_og_image,
    _render_robots_txt,
    _render_sitemap,
    _relative_from,
)
from arklight.compiler.pipeline import build
from arklight.ir.build import IRNode, IRPage, WebsiteIR


def write_site(tmp_path: Path, source: str) -> Path:
    path = tmp_path / "site.py"
    path.write_text(source)
    return path


SIMPLE_SITE = """
from arklight import *

site = Site(name="Test Site")

@site.page("/")
def home():
    return Page(Heading("Hi"), title="Home")

@site.page("/about")
def about():
    return Page(Heading("About"), title="About")
"""


def _ir(**overrides) -> WebsiteIR:
    pages = overrides.pop(
        "pages",
        [
            IRPage(route="/", root=IRNode(type="Page", props={})),
            IRPage(route="/about", root=IRNode(type="Page", props={})),
        ],
    )
    defaults = {"site_name": "Test Site", "pages": pages}
    defaults.update(overrides)
    return WebsiteIR(**defaults)


# --- robots.txt --------------------------------------------------------


def test_robots_txt_is_always_permissive_with_no_base_url():
    assert _render_robots_txt(base_url=None) == "User-agent: *\nAllow: /\n"


def test_robots_txt_adds_sitemap_line_when_base_url_is_set():
    text = _render_robots_txt(base_url="https://example.com")
    assert text == "User-agent: *\nAllow: /\nSitemap: https://example.com/sitemap.xml\n"


# --- sitemap.xml ---------------------------------------------------------


def test_page_loc_maps_index_html_to_bare_root():
    assert _page_loc("https://example.com", "index.html") == "https://example.com/"


def test_page_loc_keeps_other_routes_as_is():
    assert _page_loc("https://example.com", "about.html") == "https://example.com/about.html"


def test_sitemap_lists_every_page_as_an_absolute_sorted_url():
    ir = _ir(base_url="https://example.com")
    xml = _render_sitemap(ir)
    assert "<loc>https://example.com/</loc>" in xml
    assert "<loc>https://example.com/about.html</loc>" in xml
    # Sorted: "/" (-> trailing-slash root) comes before "/about.html".
    assert xml.index("https://example.com/<") < xml.index("https://example.com/about.html")


def test_sitemap_escapes_special_characters_in_urls():
    pages = [IRPage(route="/a&b", root=IRNode(type="Page", props={}))]
    ir = _ir(base_url="https://example.com", pages=pages)
    xml = _render_sitemap(ir)
    assert "&amp;" in xml
    assert "<loc>https://example.com/a&b" not in xml


def test_backend_skips_sitemap_when_base_url_is_unset():
    ir = _ir(base_url=None)
    files = SEOBackend().render(ir)
    assert "sitemap.xml" not in files
    assert "Sitemap:" not in files["robots.txt"]


def test_backend_generates_sitemap_when_base_url_is_set():
    ir = _ir(base_url="https://example.com")
    files = SEOBackend().render(ir)
    assert "sitemap.xml" in files
    assert "Sitemap: https://example.com/sitemap.xml" in files["robots.txt"]


# --- og-image.svg ----------------------------------------------------------


def test_og_image_is_a_valid_sized_svg_with_the_site_name():
    svg = _render_og_image("My Cool Site", None)
    assert svg.startswith('<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="630"')
    assert ">My Cool Site<" in svg


def test_og_image_includes_byline_only_when_author_is_set():
    without_author = _render_og_image("Site", None)
    with_author = _render_og_image("Site", "Rae")
    assert "by Rae" not in without_author
    assert "by Rae" in with_author


def test_og_image_escapes_site_name_and_author():
    svg = _render_og_image("A & B", "<script>")
    assert "A &amp; B" in svg
    assert "<script>" not in svg
    assert "&lt;script&gt;" in svg


def test_og_image_truncates_a_very_long_site_name():
    svg = _render_og_image("x" * 200, None)
    assert "x" * 200 not in svg
    assert "\u2026" in svg


# --- relative path math ----------------------------------------------------


def test_relative_from_same_directory():
    assert _relative_from("about.html", "og-image.svg") == "og-image.svg"


def test_relative_from_nested_directory():
    assert _relative_from("blog/post.html", "og-image.svg") == "../og-image.svg"


# --- full pipeline: default tag injection -----------------------------


def test_build_generates_robots_and_og_image_by_default(tmp_path):
    site_path = write_site(tmp_path, SIMPLE_SITE)
    result = build(site_path, tmp_path / "dist")

    assert "robots.txt" in result.output_files
    assert "og-image.svg" in result.output_files
    assert "sitemap.xml" not in result.output_files  # no base_url set


def test_build_injects_default_og_image_meta_into_every_page(tmp_path):
    site_path = write_site(tmp_path, SIMPLE_SITE)
    result = build(site_path, tmp_path / "dist")

    index_html = result.output_files["index.html"]
    about_html = result.output_files["about.html"]
    assert '<meta property="og:image" content="og-image.svg">' in index_html
    assert '<meta property="og:image" content="og-image.svg">' in about_html


def test_build_does_not_add_author_meta_when_site_author_is_unset(tmp_path):
    site_path = write_site(tmp_path, SIMPLE_SITE)
    result = build(site_path, tmp_path / "dist")
    assert 'name="author"' not in result.output_files["index.html"]


def test_build_adds_author_meta_and_byline_when_site_author_is_set(tmp_path):
    source = SIMPLE_SITE.replace('Site(name="Test Site")', 'Site(name="Test Site", author="Rae")')
    site_path = write_site(tmp_path, source)
    result = build(site_path, tmp_path / "dist")

    assert '<meta name="author" content="Rae">' in result.output_files["index.html"]
    assert "by Rae" in result.output_files["og-image.svg"]


def test_build_with_base_url_generates_sitemap_with_both_routes(tmp_path):
    source = SIMPLE_SITE.replace(
        'Site(name="Test Site")', 'Site(name="Test Site", base_url="https://example.com")'
    )
    site_path = write_site(tmp_path, source)
    result = build(site_path, tmp_path / "dist")

    sitemap = result.output_files["sitemap.xml"]
    assert "<loc>https://example.com/</loc>" in sitemap
    assert "<loc>https://example.com/about.html</loc>" in sitemap
    assert "Sitemap: https://example.com/sitemap.xml" in result.output_files["robots.txt"]


def test_build_lets_an_explicit_page_og_image_win_over_the_default(tmp_path):
    source = """
from arklight import *

site = Site(name="Test Site")

@site.page("/")
def home():
    return Page(Heading("Hi"), title="Home", og_image="assets/custom.png")
"""
    site_path = write_site(tmp_path, source)
    # `og_image` is a required-asset prop (arklight.compiler.asset_check's
    # `_PAGE_ASSET_PROPS`) -- it has to really exist under `assets/`
    # or the build fails the pre-write asset gate before SEOBackend's
    # injection is even reached.
    assets_dir = tmp_path / "assets"
    assets_dir.mkdir()
    (assets_dir / "custom.png").write_bytes(b"\x89PNG fake")

    result = build(site_path, tmp_path / "dist")

    index_html = result.output_files["index.html"]
    assert index_html.count('property="og:image"') == 1
    assert 'content="assets/custom.png"' in index_html
    assert "og-image.svg" not in index_html


# --- Site() validation ------------------------------------------------------


def test_site_rejects_blank_author(tmp_path):
    import pytest

    from arklight import Site

    with pytest.raises(ValueError):
        Site(name="Test", author="   ")


def test_site_rejects_base_url_with_trailing_slash():
    import pytest

    from arklight import Site

    with pytest.raises(ValueError):
        Site(name="Test", base_url="https://example.com/")


def test_site_rejects_base_url_with_a_path():
    import pytest

    from arklight import Site

    with pytest.raises(ValueError):
        Site(name="Test", base_url="https://example.com/site")


def test_site_accepts_a_bare_origin_base_url():
    from arklight import Site

    site = Site(name="Test", base_url="https://example.com")
    assert site.base_url == "https://example.com"
