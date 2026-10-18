"""
Markdown-as-content machinery (`docs/Proposals/MARKDOWN-CONTENT-PROPOSAL.md`,
staged in `docs/Implementation/MARKDOWN-CONTENT-ADDENDUM.md`).

This package is the home for each landing-order stage (`M1`-`M7`) as it
ships -- `arklight.content.frontmatter` is Stage M1. Nothing here is
wired into the compiler pipeline or `arklight`'s public API yet; later
stages do that as they land. Importing this package has no effect on
an existing `simple`/`production` project.
"""

from __future__ import annotations
