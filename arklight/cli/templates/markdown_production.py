"""
`markdown-production` template for `arklight new --template markdown-production`.

Stage M5 of the Markdown-as-first-class-content landing order
(`docs/Implementation/MARKDOWN-CONTENT-ADDENDUM.md`), answering the
parent proposal's **Q7** ("is mixing Python-authored pages and
Markdown content in one project the intended steady state?") with
"yes": this layout scaffolds one Python-authored page (`/`, via
`pages/home.py`, sharing `components/nav.py`/`components/footer.py`
with `production`) side by side with Markdown-authored content
(`content/about.md`, `content/guide.md`). Nothing here invents a
second way to mix the two -- a `.md` file's route is still derived
the exact same way `markdown-simple`'s is, and a route collision
between a Markdown file and a `@site.page(...)` function is still the
Stage M3 build error, naming both sources, that keeps mixing safe
rather than ambiguous (`arklight.content.discovery.
ContentCollisionError`, via `check_python_route_collisions`).

Layout: `site.py`, `components/`, `pages/`, `content/`, `assets/` --
exactly the five pieces named for this template in the addendum.

Stage M8 of the same addendum adds one more file to `components/`:
`markdown_style.py`, pure documentation (not imported, not wired into
the build) listing the `ark-md-*` style-hook classes Stage M6 already
attaches to every Markdown block automatically, and the default
styling ARKlight already ships for them. This template is the one
that gets it specifically *because* it already scaffolds a
`components/` folder for the Python-authored side -- see that file's
own docstring, and `markdown_simple.py`'s module docstring for why
`markdown-simple` does not get an equivalent file.
"""

from __future__ import annotations

from arklight.cli.templates._common import ARKLIGHT_CONFIG_PY


def build(name: str) -> dict[str, str]:
    """Return {relative_path: contents} for a fresh `markdown-production` project called `name`."""
    title = repr(name)
    return {
        "site.py": _SITE_PY,
        "components/__init__.py": _COMPONENTS_INIT_PY,
        "components/nav.py": _COMPONENTS_NAV_PY,
        "components/footer.py": _COMPONENTS_FOOTER_PY,
        # Stage M8 (docs/Implementation/MARKDOWN-CONTENT-ADDENDUM.md):
        # this template is the one that gets this file, specifically
        # because it already scaffolds a components/ folder --
        # `markdown-simple` has nowhere equivalent to put it, so the
        # same default styling reaches it silently instead (see that
        # template's own comment). Not imported by site.py, not wired
        # into the build -- Stage M6's hooks and default CSS are
        # already applied unconditionally by the compiler; this file
        # is purely "make what's available visible."
        "components/markdown_style.py": _COMPONENTS_MARKDOWN_STYLE_PY,
        "pages/__init__.py": _PAGES_INIT_PY,
        "pages/home.py": _PAGES_HOME_PY.format(title=title),
        "content/about.md": _CONTENT_ABOUT_MD,
        "content/guide.md": _CONTENT_GUIDE_MD,
        "assets/icon.svg": _ASSETS_ICON_SVG,
        "tests/test_site.py": _TESTS_SITE_PY,
        "arklight.config.py": ARKLIGHT_CONFIG_PY,
        ".gitignore": _GITIGNORE,
        "README.md": _README_MD.format(name=name),
    }


_SITE_PY = '''\
# include <stdlib.ARKlight>

from pages.home import home

site = Site()


# The real @site.page(...) decorator lives here, not in pages/home.py
# -- static discovery (arklight.parser.discover) only looks at the
# entry file's own source. "/about" and "/guide" are NOT registered
# here on purpose: they come from content/about.md and content/guide.md
# instead, discovered at build time
# (arklight.content.discovery.discover_content). Registering a route
# here that a Markdown file under content/ already claims is a build
# error naming both sources, not a silent override -- see
# content/about.md's comment and the README's "Adding a page" section.


@site.page("/")
def home_page():
    return home()
'''

_COMPONENTS_INIT_PY = '''\
"""Reusable pieces shared across pages. Both Python-authored pages
(pages/home.py) and Markdown-authored content (content/*.md) exist in
this project; these components back the Python-authored side only --
a Markdown page's own body renders through `arklight.content.markdown`
instead, with no nav/footer wrapper of its own yet."""
'''

_COMPONENTS_NAV_PY = '''\
# include <stdlib.ARKlight>


@component(props={"active": Prop(default=None)})
def NavBar(active=None):
    """The shared nav bar for Python-authored pages. `active` is one
    of "home"/"about"/"guide" -- pass it from each page so the current
    link gets highlighted. "/about" and "/guide" below point at
    Markdown-authored pages (content/about.md, content/guide.md);
    NavBar does not care which authoring format backs a route."""
    return Container(
        Link("Home", href="/", class_name="active" if active == "home" else None),
        Link("About", href="/about", class_name="active" if active == "about" else None),
        Link("Guide", href="/guide", class_name="active" if active == "guide" else None),
        class_name="nav",
    )
'''

_COMPONENTS_FOOTER_PY = '''\
# include <stdlib.ARKlight>


def footer():
    """A plain-function component: no registration needed."""
    return Footer(Text("Built with ARKlight.", class_name="muted"))
'''

_COMPONENTS_MARKDOWN_STYLE_PY = '''\
"""
Reference only -- not imported anywhere, not required for anything to
work. content/*.md already renders styled without this file; it exists
purely so the classes ARKlight's Markdown pipeline uses are visible
somewhere in this project, the same way components/nav.py and
components/footer.py make the Python-authored side's pieces visible.

Every block a content/*.md file produces gets one of these classes
automatically (arklight.content.markdown, Stage M6 of
docs/Implementation/MARKDOWN-CONTENT-ADDENDUM.md) -- nothing to write,
nothing to opt into:

    ark-md-h1 .. ark-md-h6    headings (each also gets a slugged id=,
                              for [text](#fragment) anchor links)
    ark-md-p                  paragraphs
    ark-md-list               ark-md-ordered-list    ark-md-item
    ark-md-pre                ark-md-code-block
    ark-md-blockquote         ark-md-hr               ark-md-img
    ark-md-table  ark-md-thead  ark-md-tbody  ark-md-tr
    ark-md-th  ark-md-td
    ark-md-strong  ark-md-em  ark-md-code  ark-md-link
        (inline markup normally reached via a descendant selector off
        the paragraph/cell/blockquote class above -- these three exist
        for the rare case where a whole paragraph is just one of them,
        e.g. a line that is only "**bold**")

ARKlight ships default styling for all of them already
(arklight/backend/css/markdown_defaults.py) -- that's what content/
about.md and content/guide.md look like out of the box, with nothing
written here.

THEMING: `Site(markdown_theme=...)` picks one of three built-in
presets wholesale, no site.style_selector(...) needed at all
(arklight/backend/css/markdown_presets.py):

    "light"    ARKlight's stock bright/indigo default -- what you get
               today even without setting markdown_theme at all.
    "dark"     A near-black, warm-tinted background (#16140f) with
               the exact clay/tan/taupe accent palette ARKlight's own
               `arklight search` CLI already renders Markdown in at
               the terminal (arklight/cli/mdrender.py) -- one-to-one
               with that ANSI color scheme, not a separate invention.
    "reading"  A pale amber/parchment background with dark warm ink
               and a narrower measure + taller line-height for long-
               form reading comfort -- its own design, not modeled on
               light or dark.

Set it in site.py:

    site = Site(markdown_theme="reading")

DISCLAIMER: beyond picking one of those three named presets, this is
still default styling only, for now. There is no dedicated, supported
way yet to hand-tune a preset's individual colors, or to swap in a
*fourth*, fully custom Markdown theme -- only the same
allow_redefine=True escape hatch every other built-in utility class
(.card, .nav, ...) already has, since these classes are reserved the
same protected way. Uncomment and edit whichever line below you want
to try, on top of whichever markdown_theme (if any) you picked above:

    # site.style_selector(
    #     "ark-md-h1",
    #     {"color": "#cc785c"},
    #     allow_redefine=True,
    # )

Add that call (with your own `site = Site()` import) wherever site.py
already calls other site.*(...) setup, not here -- this module is
documentation, not wiring.
"""
'''

_PAGES_INIT_PY = '''\
"""One module per Python-authored route. Each exposes a plain function
that returns a `Page(...)` -- the real `@site.page(...)` decorator
lives in site.py, which imports this and wires it up (see site.py for
why). Markdown-authored routes (content/*.md) have no module here at
all; they are discovered directly from content/."""
'''

_PAGES_HOME_PY = '''\
# include <stdlib.ARKlight>

from components.footer import footer
from components.nav import NavBar


def home():
    return Page(
        NavBar(active="home"),
        Heading({title}),
        Text("Build websites with Python.", class_name="muted"),
        footer(),
        title={title},
        description="A site built with ARKlight.",
        favicon="assets/icon.svg",
    )
'''

_CONTENT_ABOUT_MD = '''\
---
title: About
description: A site built with ARKlight.
---

## About

Say something about your project here. This page is authored in
Markdown (`content/about.md`) -- no Python, no HTML, no CSS needed --
and routed to `/about` automatically because its filename derives
that route.

A route this file claims can never also be registered with
`@site.page("/about")` in `site.py`: that is a build error naming
both sources, not a silent "last one wins." That's what makes it safe
to mix Python-authored pages (`pages/home.py`, at `/`) and
Markdown-authored ones (this file, at `/about`) in the same project.

[Back home](/)
'''

_CONTENT_GUIDE_MD = '''\
---
title: Guide
---

## Guide

A second Markdown-authored page (`content/guide.md`, routed to
`/guide`), showing a few more constructs:

- Lists, like this one.
- **Bold**, *italic*, and `inline code`.
- A fenced code block:

```
arklight build site.py -o ARK
```

> A blockquote, for good measure.

[Back home](/) -- [About](/about)
'''

_ASSETS_ICON_SVG = '''\
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512" role="img" aria-label="Site icon">
  <rect width="512" height="512" rx="96" fill="#1f2937"/>
  <circle cx="256" cy="256" r="120" fill="none" stroke="#f9fafb" stroke-width="36"/>
  <circle cx="256" cy="256" r="32" fill="#f9fafb"/>
</svg>
'''

_TESTS_SITE_PY = '''\
"""Build smoke tests. Run with `pytest` (`pip install pytest` first).

They build the real site into a temp directory, so a broken import, a
misspelled component, a missing required prop, or a Markdown file that
collides with a Python route fails here in milliseconds instead of at
deploy time. Add a Python-authored page to site.py, or a new
content/*.md file -> add its output file to ROUTES.
"""

from pathlib import Path

import pytest

from arklight.compiler.pipeline import build

SITE = Path(__file__).resolve().parent.parent / "site.py"

# route -> the file `arklight build` writes for it. "/" is
# Python-authored (pages/home.py); "/about" and "/guide" are
# Markdown-authored (content/about.md, content/guide.md) -- both kinds
# build through the same pipeline and end up in the same mapping here.
ROUTES = {"/": "index.html", "/about": "about.html", "/guide": "guide.html"}


@pytest.fixture(scope="module")
def built(tmp_path_factory):
    out_dir = tmp_path_factory.mktemp("ARK")
    build(SITE, out_dir)
    return out_dir


@pytest.mark.parametrize("output_file", ROUTES.values())
def test_every_route_builds(built, output_file):
    assert (built / output_file).exists()


def test_python_authored_page_has_the_nav_and_footer(built):
    html = (built / "index.html").read_text(encoding="utf-8")
    assert 'class="nav"' in html
    assert "<footer" in html


def test_markdown_authored_pages_render_their_content(built):
    about_html = (built / "about.html").read_text(encoding="utf-8")
    guide_html = (built / "guide.html").read_text(encoding="utf-8")
    assert "About" in about_html
    assert "Guide" in guide_html


def test_assets_are_copied_into_the_build(built):
    assert (built / "assets" / "icon.svg").exists()
'''

_GITIGNORE = '''\
# Build output (`arklight build site.py -o ARK`)
ARK/

__pycache__/
*.pyc
.pytest_cache/
.venv/
'''

_README_MD = '''\
# {name}

An ARKlight site, scaffolded with `arklight new {name} --template markdown-production`.

## Layout

```
site.py               routes -- the one @site.page(...) decorator lives here
components/
  nav.py                 a registered @component (checked "active" prop)
  footer.py               a plain function -- both work, mix freely
  markdown_style.py       reference only -- the ark-md-* classes content/*.md
                          already gets styled with, see its own docstring
pages/
  home.py                 Python-authored: the "/" route
content/
  about.md                Markdown-authored: routed to "/about" automatically
  guide.md                Markdown-authored: routed to "/guide" automatically
assets/                  icon, images, fonts -- copied into the build
tests/                   build smoke tests (pytest)
arklight.config.py       optional project settings, all commented out
```

This layout mixes both authoring formats on purpose: `/` is a
Python-authored page (`pages/home.py`, sharing `components/nav.py`/
`components/footer.py`), while `/about` and `/guide` are
Markdown-authored (`content/about.md`, `content/guide.md`) -- no
Python, HTML, or CSS needed for either. Both go through the exact same
`arklight build`; nothing about the output tells them apart.

## Build it

```
arklight build site.py -o ARK
```

This writes `ARK/index.html`, `ARK/about.html`, `ARK/guide.html`,
`ARK/styles.css`, and `ARK/arklight.js`, then opens `ARK/index.html`
in your default browser (pass `--no-open` to skip that). Anything in
`assets/` is copied into `ARK/assets/` automatically.

While editing, `arklight live-streaming --subscribe site.py` rebuilds
and reloads on every save.

## Test it

```
pip install pytest
pytest
```

`tests/test_site.py` builds the real site, so a broken import, a
misspelled component, a missing required prop, or a route collision
between a Markdown file and `@site.page(...)` fails there.

## Adding a page

**Markdown-authored** (the usual way for an ordinary content page):
add a new file under `content/` -- its route is derived from its path
(`content/pricing.md` -> `/pricing`) unless its own front matter sets
`route: /somewhere-else`. Nothing else to wire up; `arklight build`
discovers it automatically. Add its output file to `ROUTES` in
`tests/test_site.py`.

**Python-authored** (for a page that needs real logic, state, or a
component the Markdown mapping table does not cover):

1. Add `pages/<name>.py` with a function that returns `Page(...)`
   (copy `pages/home.py` as a starting point).
2. In `site.py`, import it and add a decorated wrapper:

   ```python
   from pages.<name> import <name>

   @site.page("/<route>")
   def <name>_page():
       return <name>()
   ```
3. Add the route to `ROUTES` in `tests/test_site.py`.

Either way, a route claimed twice -- by two Markdown files, or by a
Markdown file and a `@site.page(...)` function -- is a build error
naming both sources, never a silent "last one wins."

## Make it installable (PWA)

```
arklight build site.py -o ARK
arklight pwa ARK --name "{name}" --icon assets/icon.svg:any
```

Re-run `arklight pwa` after every `arklight build`.
'''
