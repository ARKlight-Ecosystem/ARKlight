"""
`markdown-simple` template for `arklight new --template markdown-simple`.

Stage M5 of the Markdown-as-first-class-content landing order
(`docs/Implementation/MARKDOWN-CONTENT-ADDENDUM.md`). Mirrors
`simple.py`'s "zero-thinking path" promise, but for Markdown: every
page is a plain `.md` file under `content/`, discovered automatically
at build time (`arklight.content.discovery`, Stage M3) -- `site.py`
itself registers no `@site.page(...)` routes at all. That is legitimate
exactly because Markdown content exists next to it:
`arklight.parser.discover` is only called with `require_pages=False`
when `arklight.content.discovery.discover_content` already found at
least one non-draft `.md` file (`arklight/compiler/pipeline.py`), so a
`site.py` with no decorators here is not a special case -- it is the
same rule every project already follows, just satisfied a different
way.
"""

from __future__ import annotations

from arklight.cli.templates._common import ARKLIGHT_CONFIG_PY


def build(name: str) -> dict[str, str]:
    """Return {relative_path: contents} for a fresh `markdown-simple` project called `name`."""
    return {
        "site.py": _SITE_PY,
        "content/index.md": _CONTENT_INDEX_MD.format(title=name),
        "content/about.md": _CONTENT_ABOUT_MD,
        "arklight.config.py": ARKLIGHT_CONFIG_PY,
        "README.md": _README_MD.format(name=name),
    }


_SITE_PY = '''\
# include <stdlib.ARKlight>

# Every page in this project comes from content/*.md -- there is
# nothing to register by hand here. Add a new page by adding a new
# .md file under content/; its route is derived from its path
# (content/guide.md -> /guide, content/index.md -> /) unless a
# `route:` line in its own front matter says otherwise. See
# content/index.md and content/about.md for the front matter shape.

site = Site()
'''

_CONTENT_INDEX_MD = '''\
---
title: {title}
description: Build websites with Python.
---

# {title}

Build websites with Python.

[About](/about)
'''

_CONTENT_ABOUT_MD = '''\
---
title: About
---

## About

Say something about your project here.

[Back home](/)
'''

_README_MD = '''\
# {name}

An ARKlight site, scaffolded with `arklight new {name} --template markdown-simple`.

## Build it

```
arklight build site.py -o ARK
```

This writes `ARK/index.html`, `ARK/about.html`, `ARK/styles.css`, and
`ARK/arklight.js`, then opens `ARK/index.html` in your default browser
(pass `--no-open` to skip that).

## Next steps

- Edit the Markdown files under `content/` -- that's the whole site.
  Each one becomes a page; its route comes from its path
  (`content/guide.md` -> `/guide`, `content/index.md` -> `/`) unless
  its own front matter sets `route: /somewhere-else`.
- Front matter is optional. When present it's a `---`-delimited block
  at the top of the file setting `title`, `description`, `route`
  and/or `draft` (`true` excludes the page from the build entirely) --
  see `content/index.md`/`content/about.md` for the shape. An
  unrecognized key, or a block that opens but never closes, fails the
  build with a diagnostic naming the file and line.
- Standard Markdown is supported: headings, **bold**/*italic*, links,
  images, lists, fenced code blocks, blockquotes, tables, and `---`
  rules. A broken local link or image fails the build with the same
  diagnostic a Python-authored page would get -- never a silent dead
  link.
- Add an `assets/` folder next to `site.py` (images, fonts, favicons,
  ...) and `arklight build` copies it into the output directory
  automatically; reference them from Markdown with a relative path
  (`![logo](./logo.png)` or `![logo](assets/logo.png)`).
- Two Markdown files resolving to the same route, or a Markdown route
  that collides with a hand-written `@site.page(...)`, is a build
  error naming both sources -- never a silent "last one wins."
- Want to mix hand-written Python pages in with Markdown content?
  `arklight new <name> --template markdown-production` scaffolds a
  `components/` / `pages/` / `content/` layout that does both.
'''
