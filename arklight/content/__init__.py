"""
Markdown-as-content machinery. Accepted and shipped in full as a
ten-stage ladder (`M1`-`M10`); the design record is graduated into
`docs/Foundational/DESIGN-NOTES.md` ("Design record: Markdown as
first-class content"), and the stage-by-stage technical history lives
in `CHANGELOG.md`.

This package is the home for each landing-order stage (`M1`-`M10`):

- `arklight.content.frontmatter` -- Stage M1, the front matter parser.
- `arklight.content.markdown` -- Stage M2, the Markdown-to-IR parser.
- `arklight.content.discovery` -- Stage M3, `content/` discovery and
  route synthesis. This is the first stage wired into
  `arklight.compiler.pipeline`: an early step, before the entry file's
  AST scan, that turns `.md` files under `content/` into pages.
- Stage M4 lives inside `arklight.content.markdown` (reference
  resolution: relative `Image`/`Link` paths against `assets/`, links
  between `.md` files to routes) and is driven by `discovery`'s page
  synthesis. The existing `asset_check`/`link_check` then judge those
  references like any other; neither was changed.

A project with no `.md` files under `content/` -- every existing
`simple`/`production` project -- never triggers any of it.
"""

from __future__ import annotations
