"""
`production` template for `arklight new` -- see docs/Foundational/DESIGN-NOTES.md,
"v0.004: CLI scaffolding (`arklight new`)", and `arklight new
--explain-architecture` (the guide this layout implements).

Mirrors a proven multi-file layout for sites that outgrow a single
`site.py`: `site.py` + `components/` + `pages/` + `content/` +
`assets/`, plus fixes for the real gotchas that shape hit in practice:

- `site.py` registers every route with a real `@site.page("/route")`
  decorator (never the equivalent call form), since static discovery
  (`arklight.parser.discover`) only recognizes the decorator -- and,
  specifically, only recognizes it in the *entry* file's own source.
  That's why the decorators themselves live in `site.py`, wrapping a
  plain content-building function imported from `pages/`, rather than
  living in `pages/home.py` directly.
- `components/__init__.py` / `pages/__init__.py` / `content/__init__.py`
  are present up front so the package-shaped layout imports cleanly
  from line one.
- `pages/*.py` import `components.*` and `content.*` with ordinary
  absolute imports. That only resolves if the project directory is on
  `sys.path`, which `arklight.parser.loader.load_site` now guarantees
  regardless of how `arklight` was invoked (console script or
  otherwise) -- see that module for the fix.
- `components/nav.py` uses the optional `@component(...)` decorator
  (checked `active` prop, build-time validation), while
  `components/footer.py` stays a plain function -- both work with zero
  setup, and the guide is explicit that you mix them freely. This gives
  a new project one live example of each, side by side.
- `assets/icon.svg` is both the page favicon and what `arklight pwa
  --icon assets/icon.svg:any` points at, so making the scaffolded site
  installable needs no extra files -- see the README's PWA section.
- A top-level `assets/` folder is copied into the build output
  automatically by `arklight build` (no manual `cp -r` step to forget
  or to document here).
- `tests/test_site.py` builds the real site into a temp directory, so a
  broken import, a misspelled component, or a missing required prop
  fails in milliseconds via `pytest`, not only when you next run
  `arklight build` yourself.
"""

from __future__ import annotations

from arklight.cli.templates._common import ARKLIGHT_CONFIG_PY


def build(name: str) -> dict[str, str]:
    """Return {relative_path: contents} for a fresh `production` project called `name`."""
    title = repr(name)
    return {
        "site.py": _SITE_PY,
        "components/__init__.py": _COMPONENTS_INIT_PY,
        "components/nav.py": _COMPONENTS_NAV_PY,
        "components/footer.py": _COMPONENTS_FOOTER_PY,
        "pages/__init__.py": _PAGES_INIT_PY,
        "pages/home.py": _PAGES_HOME_PY,
        "pages/about.py": _PAGES_ABOUT_PY,
        "content/__init__.py": _CONTENT_INIT_PY,
        "content/site_content.py": _CONTENT_SITE_CONTENT_PY.format(title=title),
        "assets/icon.svg": _ASSETS_ICON_SVG,
        "tests/test_site.py": _TESTS_SITE_PY,
        "arklight.config.py": ARKLIGHT_CONFIG_PY,
        ".gitignore": _GITIGNORE,
        "README.md": _README_MD.format(name=name),
    }


_SITE_PY = '''\
# include <stdlib.ARKlight>

from pages.about import about
from pages.home import home

site = Site()


# Real @site.page(...) decorators live here, not in pages/*.py --
# static discovery (arklight.parser.discover) only looks at the entry
# file's own source, so this is the one place routes must be declared.
# Each function below just delegates to the actual page-content
# function in pages/, which is free to import components/ and
# content/ however it likes.


@site.page("/")
def home_page():
    return home()


@site.page("/about")
def about_page():
    return about()
'''

_COMPONENTS_INIT_PY = '''\
"""Reusable pieces shared across pages.

Two kinds live side by side here on purpose -- pick whichever a given
piece needs, and mix them freely:

- a plain function (`footer.py`) -- ordinary Python composition, zero
  setup;
- a registered `@component(...)` (`nav.py`) -- a checked props
  contract and build-time validation instead of a raw `TypeError` if
  it's misused. See docs/Foundational/USER-DEFINED-COMPONENTS.md.
"""
'''

_COMPONENTS_NAV_PY = '''\
# include <stdlib.ARKlight>


@component(props={"active": Prop(default=None)})
def NavBar(active=None):
    """The shared nav bar. `active` is one of "home"/"about" -- pass it
    from each page so the current link gets highlighted."""
    return Container(
        Link("Home", href="/", class_name="active" if active == "home" else None),
        Link("About", href="/about", class_name="active" if active == "about" else None),
        class_name="nav",
    )
'''

_COMPONENTS_FOOTER_PY = '''\
# include <stdlib.ARKlight>

from content.site_content import FOOTER_TEXT


def footer():
    """A plain-function component: no registration needed."""
    return Footer(Text(FOOTER_TEXT, class_name="muted"))
'''

_PAGES_INIT_PY = '''\
"""One module per route. Each exposes a plain function that returns a
`Page(...)` -- the real `@site.page(...)` decorators live in site.py,
which imports these and wires them up (see site.py for why)."""
'''

_PAGES_HOME_PY = '''\
# include <stdlib.ARKlight>

from components.footer import footer
from components.nav import NavBar
from content.site_content import DESCRIPTION, FAVICON, TAGLINE, TITLE


def home():
    return Page(
        NavBar(active="home"),
        Heading(TITLE),
        Text(TAGLINE, class_name="muted"),
        footer(),
        title=TITLE,
        description=DESCRIPTION,
        favicon=FAVICON,
    )
'''

_PAGES_ABOUT_PY = '''\
# include <stdlib.ARKlight>

from components.footer import footer
from components.nav import NavBar
from content.site_content import DESCRIPTION, FAVICON, TITLE


def about():
    return Page(
        NavBar(active="about"),
        Heading("About", level=2),
        Text(f"Say something about {TITLE} here."),
        Link("Back home", href="/"),
        footer(),
        title="About",
        description=DESCRIPTION,
        favicon=FAVICON,
    )
'''

_CONTENT_INIT_PY = '''\
"""Copy/text constants, kept separate from markup so pages/ stays
readable and content can be edited without touching component code."""
'''

_CONTENT_SITE_CONTENT_PY = '''\
TITLE = {title}
TAGLINE = "Build websites with Python."
DESCRIPTION = "A site built with ARKlight."
FOOTER_TEXT = "Built with ARKlight."

# Page favicon -- also the icon `arklight pwa` registers (see README.md).
FAVICON = "assets/icon.svg"
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
misspelled component, a missing required prop, or an undeclared state
name fails here in milliseconds instead of at deploy time. Add a route
to site.py -> add its output file to ROUTES.
"""

from pathlib import Path

import pytest

from arklight.compiler.pipeline import build

SITE = Path(__file__).resolve().parent.parent / "site.py"

# route -> the file `arklight build` writes for it
ROUTES = {"/": "index.html", "/about": "about.html"}


@pytest.fixture(scope="module")
def built(tmp_path_factory):
    out_dir = tmp_path_factory.mktemp("ARK")
    build(SITE, out_dir)
    return out_dir


@pytest.mark.parametrize("output_file", ROUTES.values())
def test_every_route_builds(built, output_file):
    assert (built / output_file).exists()


def test_pages_share_the_nav_and_footer(built):
    for output_file in ROUTES.values():
        html = (built / output_file).read_text(encoding="utf-8")
        assert 'class="nav"' in html
        assert "<footer" in html


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

An ARKlight site, scaffolded with `arklight new {name} --template production`.

## Layout

```
site.py               routes -- @site.page(...) decorators live here
components/
  nav.py                 a registered @component (checked "active" prop)
  footer.py              a plain function -- both work, mix freely
pages/                 one module per route, returns Page(...)
content/               copy/text constants, kept out of the markup
assets/                icon, images, fonts -- copied into the build
tests/                 build smoke tests (pytest)
arklight.config.py     optional project settings, all commented out
```

Run `arklight new --explain-architecture` for the reasoning behind
this shape and how to extend it.

## Build it

```
arklight build site.py -o ARK
```

This writes `ARK/index.html`, `ARK/about.html`, `ARK/styles.css`, and
`ARK/arklight.js`, then opens `ARK/index.html` in your default browser
(pass `--no-open` to skip that). Anything in `assets/` is copied into
`ARK/assets/` automatically -- no manual copy step.

While editing, `arklight live-streaming --subscribe site.py` rebuilds
and reloads on every save.

## Test it

```
pip install pytest
pytest
```

`tests/test_site.py` builds the real site, so a broken import, a
misspelled component, or a missing required prop fails there.

## Adding a page

1. Add `pages/<name>.py` with a function that returns `Page(...)`
   (copy `pages/about.py` as a starting point).
2. In `site.py`, import it and add a decorated wrapper:

   ```python
   from pages.<name> import <name>

   @site.page("/<route>")
   def <name>_page():
       return <name>()
   ```
3. Add the route to `ROUTES` in `tests/test_site.py`.

The decorator has to live in `site.py` itself -- ARKlight discovers
routes by statically scanning the entry file's own source, not any
file it imports.

## Make it installable (PWA)

```
arklight build site.py -o ARK
arklight pwa ARK --name "{name}" --icon assets/icon.svg:any
```

Re-run `arklight pwa` after every `arklight build`.
'''

