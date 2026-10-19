"""
In-package project templates for `arklight new`.

Each template is a callable `name -> dict[relative_path, contents]`
(plain string building, no templating dependency -- consistent with
"no runtime dependencies beyond the build backend"), registered in
`TEMPLATES` below. See docs/Foundational/DESIGN-NOTES.md, "v0.004: CLI scaffolding
(`arklight new`)", for the full design this implements.

- `simple`     -- `templates.simple.build`: a single `site.py`, the
  zero-thinking path from `arklight new my-site` to a working
  `arklight build`.
- `production` -- `templates.production.build`: a `site.py` +
  `components/` + `pages/` + `content/` + `assets/` layout for sites
  that outgrow one file.
- `markdown-simple` -- `templates.markdown_simple.build`: `simple`'s
  zero-thinking promise, but every page is a `.md` file under
  `content/`, discovered automatically at build time
  (`arklight.content.discovery`) instead of a decorated function in
  `site.py`.
- `markdown-production` -- `templates.markdown_production.build`: a
  `site.py` + `components/` + `pages/` + `content/` + `assets/` layout
  that mixes a Python-authored page with Markdown-authored content in
  one project.

(`markdown-simple`/`markdown-production` are Stage M5 of the
Markdown-as-first-class-content ladder -- see
`docs/Foundational/DESIGN-NOTES.md`'s "Design record: Markdown as
first-class content" for the design this pair implements; its
accepted proposal and implementation addendum were retired once the
ladder's ten stages all shipped.)

Every template also writes an `arklight.config.py` (`templates.
_common.ARKLIGHT_CONFIG_PY`) -- fully commented out, so it changes no
behavior by existing, but gives new projects a discoverable, ready-
to-edit spot for project settings from the start, the same "config
file scaffolded up front" convention build tools like Vite ship by
default.
"""

from __future__ import annotations

from typing import Callable

from arklight.cli.templates import markdown_production, markdown_simple, production, simple

TemplateBuilder = Callable[[str], dict[str, str]]

TEMPLATES: dict[str, TemplateBuilder] = {
    "simple": simple.build,
    "production": production.build,
    "markdown-simple": markdown_simple.build,
    "markdown-production": markdown_production.build,
}

__all__ = ["TEMPLATES"]
