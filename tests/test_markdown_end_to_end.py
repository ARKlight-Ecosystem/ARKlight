"""Stage M10 (docs/Implementation/MARKDOWN-CONTENT-ADDENDUM.md) end-to-
end coverage: one fixture project that exercises every landed rung of
the Markdown-as-content ladder together -- front matter (M1), the
Markdown-to-IR parser's construct vocabulary (M2), `content/`
discovery and route synthesis (M3), asset/link resolution (M4), the
`markdown-production` template shape (M5), style hooks (M6) under a
preset theme (M7), and the automatic nav/footer/SEO defaults (M9) --
through one real `arklight.compiler.pipeline.build()` call, the way
M10's own exit test describes it. Each rung already has its own
narrow unit suite (`test_frontmatter.py`, `test_markdown.py`,
`test_content_discovery.py`, `test_content_assets.py`,
`test_markdown_templates.py`, `test_markdown_style_hooks.py`,
`test_markdown_presets.py`, `test_seo_backend.py`); this file is the
one place they're all exercised at once, on a project shaped like a
real one an author would actually write -- plus a matching negative
fixture proving the M10-adjacent opt-in gate
(`# include <markdown.ARKlight>`) that this patch adds.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from arklight.compiler.pipeline import CompileError, build


def _write(root: Path, rel: str, text: str) -> Path:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


SITE_PY = """\
# include <stdlib.ARKlight>
# include <markdown.ARKlight>

site = Site(
    name="Fixture Site",
    author="Ada",
    base_url="https://example.com",
    markdown_theme="dark",
)
"""

INDEX_MD = """\
---
title: Home
description: The fixture site's home page.
---

# Welcome

Some **bold**, some *italic*, and some `inline code`.

[About](/about)

![An icon](icon.svg)

- one
- two

| A | B |
| - | - |
| 1 | 2 |
"""

ABOUT_MD = """\
---
title: About
description: What this fixture is for.
---

## About

```
plain fenced block
```

> A quote.

---
"""

DRAFT_MD = """\
---
draft: true
title: Not yet
---

# Should never build
"""


def _fixture_project(root: Path) -> Path:
    site = _write(root, "site.py", SITE_PY)
    _write(root, "content/index.md", INDEX_MD)
    _write(root, "content/about.md", ABOUT_MD)
    _write(root, "content/draft.md", DRAFT_MD)
    _write(root, "assets/icon.svg", "<svg><!-- fixture icon --></svg>")
    return site


def test_full_markdown_fixture_builds_every_rung_at_once(tmp_path):
    site = _fixture_project(tmp_path)
    result = build(site, tmp_path / "ARK")

    routes = {page.route for page in result.ir.pages}
    # M3: discovery + route synthesis; the draft never gets a route.
    assert routes == {"/", "/about"}

    index_html = result.output_files["index.html"]
    about_html = result.output_files["about.html"]

    # M2: construct mapping landed as real markup, not escaped text.
    assert "<strong>bold</strong>" in index_html
    assert "<em>italic</em>" in index_html
    assert "<code>inline code</code>" in index_html
    assert "<table" in index_html

    # M4: the relative image/link resolved and the asset was checked
    # and copied rather than rejected or left dangling.
    assert 'src="icon.svg"' in index_html or "icon.svg" in index_html
    assert (tmp_path / "ARK" / "assets" / "icon.svg").exists()

    # M6: stable ark-md-* class hooks are present on parsed nodes.
    assert "ark-md-h1" in index_html
    assert "ark-md-table" in index_html

    # M7: the dark preset is actually in effect (its CSS, not the
    # plain default stylesheet, is what should be on disk).
    css = result.output_files["styles.css"]
    assert "ark-md-h1" in css

    # M1: front matter description flowed to the <head> (apostrophe
    # HTML-escaped by the attribute renderer, like any other prop).
    assert "content=\"The fixture site&#x27;s home page.\"" in index_html
    assert 'content="What this fixture is for."' in about_html

    # M9: nav (one link per discovered page), footer, and SEO defaults
    # -- site-wide (robots.txt/og-image.svg/author tag) and per-page
    # (canonical link, og:title/og:description).
    assert 'class="nav"' in index_html
    assert 'href="about.html"' in index_html
    assert "og:title" in index_html
    assert "og:description" in index_html
    assert 'rel="canonical"' in index_html
    assert 'name="author" content="Ada"' in index_html
    assert "robots.txt" in result.output_files
    assert "og-image.svg" in result.output_files
    assert "sitemap.xml" in result.output_files  # base_url is set

    # Draft stayed out of the build entirely.
    assert "draft.html" not in result.output_files
    assert "Should never build" not in "".join(result.output_files.values())


def test_same_fixture_without_the_gate_has_no_markdown_pages(tmp_path):
    # Same content/ and assets/, but site.py never opts in -- M10's
    # negative counterpart to the test above, covering the gate added
    # alongside this stage.
    root = tmp_path
    _write(root, "site.py", "# include <stdlib.ARKlight>\n\nsite = Site()\n")
    _write(root, "content/index.md", INDEX_MD)
    _write(root, "content/about.md", ABOUT_MD)
    with pytest.raises(CompileError, match="No pages registered"):
        build(root / "site.py", root / "ARK")
