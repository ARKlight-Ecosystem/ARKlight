"""
Tests for runtime policy enforcement -- the default Content-Security-
Policy meta tag (arklight/backend/html/csp.py) and its Site(...)
override kwargs (strict_csp, trusted_script_origins). See csp.py's
module docstring for the full design rationale.
"""

import pytest

from arklight.api import Heading, Page, Site
from arklight.backend.html.csp import _render_csp_meta_tag
from arklight.backend.html.render import HTMLBackend
from arklight.ir.build import build_website_ir
from arklight.ir.normalize import normalize_ark_ast
from arklight.ir.validate import validate_ark_ast


def render(pages: dict, site_name: str = "site", **kwargs):
    normalized = normalize_ark_ast(pages)
    validate_ark_ast(normalized)
    ir = build_website_ir(site_name, normalized, **kwargs)
    return HTMLBackend().render(ir)


# -- csp.py's _render_csp_meta_tag() directly -------------------------------


def test_default_csp_tag_has_no_unsafe_directives():
    tag = _render_csp_meta_tag()
    assert "unsafe-eval" not in tag
    assert "unsafe-inline" not in tag
    assert "script-src &#x27;self&#x27;" in tag or "script-src 'self'" in tag


def test_default_csp_tag_never_touches_style_src():
    # Explicit scope boundary: this policy is about code execution, not
    # styling. style-src must never appear -- restricting it would break
    # the already-documented inline style="..." escape hatch
    # (CONFIGURABILITY.md).
    tag = _render_csp_meta_tag()
    assert "style-src" not in tag


def test_default_csp_tag_never_sets_default_src_or_connect_src():
    # default-src would silently cascade onto every other fetch
    # directive this module hasn't reasoned about; connect-src is
    # redundant with HTMX's own selfRequestsOnly and ARKlight's closed
    # vocabulary having no fetch primitive at all.
    tag = _render_csp_meta_tag()
    assert "default-src" not in tag
    assert "connect-src" not in tag


def test_csp_tag_requires_trusted_types_for_script():
    tag = _render_csp_meta_tag()
    assert "require-trusted-types-for" in tag
    assert "trusted-types" in tag


def test_csp_tag_includes_object_src_none_and_base_uri_self():
    tag = _render_csp_meta_tag()
    assert "object-src &#x27;none&#x27;" in tag or "object-src 'none'" in tag
    assert "base-uri &#x27;self&#x27;" in tag or "base-uri 'self'" in tag


def test_trusted_script_origins_appended_to_script_src():
    tag = _render_csp_meta_tag(["https://www.googletagmanager.com"])
    assert "googletagmanager.com" in tag
    # Still no unsafe- directives just because an origin was added.
    assert "unsafe-eval" not in tag
    assert "unsafe-inline" not in tag


def test_trusted_script_origins_none_or_empty_gives_self_only():
    assert _render_csp_meta_tag(None) == _render_csp_meta_tag([])


# -- End-to-end through the HTML backend -------------------------------------


def test_strict_csp_true_by_default_emits_csp_meta_tag():
    html = render({"/": Page(Heading("Hi"), title="Home")})["index.html"]
    assert '<meta http-equiv="Content-Security-Policy"' in html


def test_csp_meta_tag_comes_right_after_charset():
    html = render({"/": Page(Heading("Hi"), title="Home")})["index.html"]
    head = html.split("<head>", 1)[1].split("</head>", 1)[0]
    tags = [line.strip() for line in head.splitlines() if line.strip()]
    assert tags[0].startswith('<meta charset')
    assert tags[1].startswith('<meta http-equiv="Content-Security-Policy"')


def test_strict_csp_false_emits_no_csp_tag_byte_identical_to_pre_feature():
    # The raw_postprocess escape valve (see EXPERIMENTAL-APIS.md /
    # arklight/experimental.py's raw-postprocess entry): opting out
    # must restore exactly today's (pre-feature) head, nothing partial.
    html = render({"/": Page(Heading("Hi"), title="Home")}, strict_csp=False)["index.html"]
    assert "Content-Security-Policy" not in html
    assert html.count("<meta") == 2  # charset + viewport only


def test_trusted_script_origins_flow_through_to_rendered_html():
    html = render(
        {"/": Page(Heading("Hi"), title="Home")},
        trusted_script_origins=["https://cdn.example.com"],
    )["index.html"]
    assert "cdn.example.com" in html


def test_style_attribute_still_works_unrestricted_alongside_strict_csp():
    # Confirms the explicit scope boundary end to end, not just at the
    # tag-string level: an inline style= prop renders completely
    # normally on a strict_csp=True (default) page.
    html = render({"/": Page(Heading("Hi", style="color: red;"), title="Home")})["index.html"]
    assert 'style="color: red;"' in html
    assert '<meta http-equiv="Content-Security-Policy"' in html


# -- Site(...) validation -----------------------------------------------------


def test_site_strict_csp_defaults_true():
    site = Site()
    assert site.strict_csp is True
    assert site.trusted_script_origins == []


def test_site_strict_csp_false_stored():
    site = Site(strict_csp=False)
    assert site.strict_csp is False


def test_site_trusted_script_origins_stored():
    site = Site(trusted_script_origins=["https://cdn.example.com"])
    assert site.trusted_script_origins == ["https://cdn.example.com"]


def test_site_trusted_script_origins_rejects_non_list():
    with pytest.raises(ValueError):
        Site(trusted_script_origins="https://cdn.example.com")


def test_site_trusted_script_origins_rejects_empty_string_entry():
    with pytest.raises(ValueError):
        Site(trusted_script_origins=["https://cdn.example.com", ""])


def test_site_trusted_script_origins_rejects_non_string_entry():
    with pytest.raises(ValueError):
        Site(trusted_script_origins=[123])
