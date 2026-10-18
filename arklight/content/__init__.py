"""
Markdown-as-content machinery (`docs/Proposals/MARKDOWN-CONTENT-PROPOSAL.md`,
staged in `docs/Implementation/MARKDOWN-CONTENT-ADDENDUM.md`).

This package is the home for each landing-order stage (`M1`-`M7`) as it
ships:

- `arklight.content.frontmatter` -- Stage M1, the front matter parser.
- `arklight.content.markdown` -- Stage M2, the Markdown-to-IR parser.
- `arklight.content.discovery` -- Stage M3, `content/` discovery and
  route synthesis. This is the first stage wired into
  `arklight.compiler.pipeline`: an early step, before the entry file's
  AST scan, that turns `.md` files under `content/` into pages.

A project with no `.md` files under `content/` -- every existing
`simple`/`production` project -- never triggers any of it.
"""

from __future__ import annotations
