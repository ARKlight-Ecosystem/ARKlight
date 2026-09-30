"""
The rest of internal-link resolution: trailing slashes and `?query` on
routes, full-URL `favicon`/`og_image`, `url()` inside inline styles on
nested pages (routing.py), plus the pre-write link gate that halts on
unknown routes and dead `#fragment`s (`arklight.compiler.link_check`).
"""

from pathlib import Path

import pytest

from arklight.backend.html.routing import (
    _match_route,
    _resolve_route_ref,
    _resolve_style_urls,
)
from arklight.compiler.pipeline import CompileError, build

R2P = {"/": "index.html", "/about": "about.html", "/blog/post": "blog/post.html"}


# ---- routing.py: resolution -------------------------------------------------

def test_match_route_accepts_trailing_slash_but_not_case_folding():
    assert _match_route("/about/", R2P) == "/about"
    assert _match_route("/about", R2P) == "/about"
    assert _match_route("/", R2P) == "/"
    assert _match_route("/About", R2P) is None
    assert _match_route("/nope/", R2P) is None


def test_resolve_route_ref_handles_trailing_slash_query_and_fragment():
    kw = dict(current_route="/blog/post", route_to_path=R2P)
    assert _resolve_route_ref("/about/", **kw) == "../about.html"
    assert _resolve_route_ref("/about?x=1", **kw) == "../about.html?x=1"
    assert _resolve_route_ref("/about/?x=1#s", **kw) == "../about.html?x=1#s"
    assert _resolve_route_ref("/nope", **kw) == "/nope"  # unknown: untouched here


def test_style_urls_are_rewritten_per_page_depth():
    css = "background: url(assets/bg.png); border-image: url(#g)"
    assert _resolve_style_urls(css, current_route="/", route_to_path=R2P) == css
    out = _resolve_style_urls(css, current_route="/blog/post", route_to_path=R2P)
    assert out == "background: url(../assets/bg.png); border-image: url(#g)"


def test_style_urls_leave_external_data_and_quotes_alone():
    kw = dict(current_route="/blog/post", route_to_path=R2P)
    assert _resolve_style_urls("x: url(https://e.com/a.png)", **kw) == "x: url(https://e.com/a.png)"
    assert _resolve_style_urls("x: url(data:image/gif;base64,AA)", **kw) == "x: url(data:image/gif;base64,AA)"
    assert _resolve_style_urls("x: url('/assets/a.png')", **kw) == "x: url('../assets/a.png')"


# ---- build-level ------------------------------------------------------------

HEAD = "# include <stdlib.ARKlight>\nsite = Site()\n"


def write(tmp_path: Path, home_body: str, *, about_body: str = 'Heading("About")', extra: str = "") -> Path:
    path = tmp_path / "site.py"
    path.write_text(
        HEAD
        + f'\n@site.page("/")\ndef home():\n    return Page({home_body}, title="Home")\n'
        + f'\n@site.page("/about")\ndef about():\n    return Page({about_body}, title="About")\n'
        + extra
    )
    return path


def test_trailing_slash_and_query_links_build_to_relative_paths(tmp_path):
    site = write(tmp_path, 'Link("a", href="/about/"), Link("b", href="/about?x=1")')
    build(site, tmp_path / "dist")
    html = (tmp_path / "dist" / "index.html").read_text()
    assert 'href="about.html"' in html and 'href="about.html?x=1"' in html


def test_full_url_favicon_and_og_image_are_not_mangled(tmp_path):
    path = tmp_path / "site.py"
    path.write_text(
        HEAD + '\n@site.page("/")\ndef home():\n    return Page(Heading("H"), title="H", '
        'favicon="https://cdn.example.com/f.ico", og_image="//cdn.example.com/og.png")\n'
    )
    build(path, tmp_path / "dist")
    html = (tmp_path / "dist" / "index.html").read_text()
    assert 'href="https://cdn.example.com/f.ico"' in html
    assert 'content="//cdn.example.com/og.png"' in html


def test_inline_style_url_is_rewritten_on_a_nested_page(tmp_path):
    (tmp_path / "assets").mkdir()
    (tmp_path / "assets" / "bg.png").write_text("x")
    path = tmp_path / "site.py"
    path.write_text(
        HEAD + '\n@site.page("/blog/post")\ndef post():\n    return Page('
        'Container(Text("x"), style={"background": "url(assets/bg.png)"}), title="P")\n'
    )
    build(path, tmp_path / "dist")
    html = (tmp_path / "dist" / "blog" / "post.html").read_text()
    assert "url(../assets/bg.png)" in html


# ---- the link gate ----------------------------------------------------------

def test_unknown_route_halts_with_hint_and_writes_nothing(tmp_path, capsys):
    site = write(tmp_path, 'Link("x", href="/abuot")')
    with pytest.raises(CompileError, match="Link check failed"):
        build(site, tmp_path / "dist")
    assert not (tmp_path / "dist").exists()
    err = capsys.readouterr().err
    assert "LINK CHECK FAILED" in err and "/abuot" in err and "Did you mean '/about'?" in err


def test_wrong_case_route_is_reported_with_the_right_case(tmp_path, capsys):
    site = write(tmp_path, 'Link("x", href="/About")')
    with pytest.raises(CompileError):
        build(site, tmp_path / "dist")
    assert "Did you mean '/about'?" in capsys.readouterr().err


def test_dead_fragment_on_another_page_halts(tmp_path, capsys):
    site = write(tmp_path, 'Link("x", href="/about#nope")', about_body='Container(Text("s"), id="s")')
    with pytest.raises(CompileError):
        build(site, tmp_path / "dist")
    err = capsys.readouterr().err
    assert "DEAD-FRAGMENT" in err and "'nope'" in err and "ids there: s" in err


def test_dead_same_page_fragment_halts(tmp_path):
    site = write(tmp_path, 'Link("x", href="#missing")')
    with pytest.raises(CompileError, match="Link check failed"):
        build(site, tmp_path / "dist")


def test_valid_fragments_and_special_hrefs_pass(tmp_path):
    site = write(
        tmp_path,
        'Heading("H", id="h"), Link("1", href="#h"), Link("2", href="#top"), Link("3", href="#"), '
        'Link("4", href="/about#s"), Link("5", href="/about/#s"), Link("6", href="/styles.css"), '
        'Link("7", href="https://example.com"), Link("8", href="mailto:a@b.c"), '
        'Link("9", href="tel:+1"), Link("10", href="//cdn.example.com/x")',
        about_body='Container(Text("s"), id="s")',
    )
    build(site, tmp_path / "dist")


def test_both_gates_report_together(tmp_path, capsys):
    site = write(tmp_path, 'Image(src="assets/gone.png", alt="g"), Link("x", href="/nope")')
    with pytest.raises(CompileError) as exc:
        build(site, tmp_path / "dist")
    err = capsys.readouterr().err
    assert "ASSET CHECK FAILED" in err and "LINK CHECK FAILED" in err
    assert "Asset check failed" in str(exc.value) and "Link check failed" in str(exc.value)


def test_report_survives_a_silent_on_stage(tmp_path, capsys):
    site = write(tmp_path, 'Link("x", href="/nope")')
    with pytest.raises(CompileError):
        build(site, tmp_path / "dist", on_stage=lambda _m: None)
    assert "/nope" in capsys.readouterr().err
