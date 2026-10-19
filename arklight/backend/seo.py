"""
SEO Backend.

Stage M9 pass (see docs/Foundational/DESIGN-NOTES.md's "Design record:
Markdown as first-class content"): the
"automatic ... SEO defaults" half of Stage M9 that goes beyond what
`arklight.backend.html.head_meta._render_head_meta` can do from a
single page's own props alone -- `robots.txt`, `sitemap.xml`, and a
generated default `og-image.svg` all need the *whole site* (every
route, the site name, the author), not one page's IR node. That is
exactly the job `Backend.postprocess()` was built for -- see its own
docstring's worked example ("injecting analytics/OG tags computed from
data the HTML backend already rendered"): this is that example, not a
new mechanism. CHANGELOG.md's `[0.043]` entry names "sitemap
generation" directly as the hook's own motivating case.

What this backend adds, always, with no `site.py` opt-in required
(`Site(author=..., base_url=...)`, both optional, are *inputs* this
backend reads if present -- not a flag that turns it on):

- **`robots.txt`**: `User-agent: * / Allow: /`, plus a `Sitemap:` line
  once `sitemap.xml` exists (see below). Always generated.
- **`sitemap.xml`**: one `<url><loc>` per page route, generated *only*
  when `Site(base_url=...)` is set. A sitemap's `<loc>` entries must be
  absolute URLs per the sitemap protocol
  (<https://www.sitemaps.org/protocol.html>) -- there is no way to
  derive a real origin from the build alone (the same reason
  `_render_head_meta`'s own canonical link is root-relative, not
  absolute), so rather than emit an invalid (relative, or made-up)
  sitemap, this backend skips it entirely when `base_url` is unset.
  Same "don't guess, state the limitation" posture
  `arklight.compiler.overdrive` already holds for its own unverifiable
  references.
- **`og-image.svg`**: one site-wide default Open Graph image -- the
  ARKlight mark, the site's name, and (if set) its author, laid out
  the way GitHub's own repo social-preview cards are: a mark, a bold
  title, a smaller byline underneath. SVG, not a raster format --
  see "Why SVG, not PNG" below.
- Per-page `<meta property="og:image">` (pointing at `og-image.svg`,
  resolved relative to that page) and `<meta name="author">` (only if
  `Site(author=...)` is set), injected in `postprocess()` into every
  already-rendered page that doesn't already carry one. An explicit
  `Page(og_image=...)` (`arklight.backend.html.head_meta`) always
  wins -- this only fills a gap an author didn't fill themselves, the
  same "default now, explicit always wins" rule `_render_head_meta`'s
  own `og_title`/`og_description` fallbacks already use. Unlike every
  other `<head>` tag `_render_head_meta` renders, this is *not* gated
  on that function's `seo_opt_in` check -- Stage M9's whole point is
  moving the baseline SEO surface from "only if an author opts in" to
  "on by default", so the default `og:image` reaches every page, not
  just ones that already set `description`/another `og_*` prop.

## Why SVG, not PNG

Every other image-shaped thing ARKlight ships by default (`arklight
new`'s scaffolded `assets/icon.svg`, see
`arklight/cli/templates/production.py`'s `_ASSETS_ICON_SVG`) is a
hand-drawn SVG, for the same reason this is: there is no image-
encoding library anywhere in this dependency-free project, and
drawing to a raster buffer by hand (manual PNG chunks over `zlib`) for
one generated image is a disproportionate amount of machinery for a
*default* a site can always override with
`Page(og_image="assets/your-real-image.png")` once it cares. The
honest tradeoff: a handful of older/stricter link-preview crawlers
don't rasterize an SVG `og:image`, so the default card may not render
everywhere a hand-supplied PNG would. Same category of tradeoff
`arklight/experimental.py`'s `css-media-queries` entry documents -- a
deliberate default, not an oversight -- and why this is *always*
overridable per page, never the only path.

## Why `postprocess()`, not a new IR prop

An explicit `Page(og_image=...)` is already real schema
(`arklight.ir.schema`, read by `_render_head_meta`) -- this backend
deliberately does *not* add a second, IR-level way to set the same
tag. "No `og_image` on this page" is only observable *after*
`HTMLBackend.render()` has already decided what `<head>` to emit,
which is exactly the ordering `Backend.postprocess()` exists for.
Threading a sitewide default through `arklight.ir.build`/
`arklight.ir.validate`/`_render_head_meta` as a new kind of prop would
duplicate logic `_render_head_meta` already owns for no benefit;
string-level injection over the already-finished HTML is the smaller,
more honest change -- and it is why `SEOBackend` stashes what
`postprocess()` needs (`author`, whether `og-image.svg` was actually
produced) on `self` during `render()`: `postprocess(output_files)`
only ever receives the *combined* output dict, never the `WebsiteIR`
itself (see `Backend.postprocess`'s own signature).
"""

from __future__ import annotations

import posixpath
import re
from html import escape

from arklight.backend.base import Backend
from arklight.backend.html.routing import _output_path_for_route
from arklight.ir.build import WebsiteIR

#: Standard Open Graph / Twitter Card image size -- the same 1200x630
#: convention GitHub's own repo social-preview cards and most link
#: unfurlers (Slack, Discord, iMessage, Twitter/X) expect; see
#: <https://ogp.me> and Twitter's "summary card with large image" spec.
_OG_IMAGE_WIDTH = 1200
_OG_IMAGE_HEIGHT = 630
_OG_IMAGE_PATH = "og-image.svg"
_SITEMAP_PATH = "sitemap.xml"
_ROBOTS_PATH = "robots.txt"

# Same two-tone palette `arklight/cli/templates/production.py`'s
# scaffolded `assets/icon.svg` already uses for "the ARKlight mark",
# plus `arklight/cli/mdrender.py`'s own heading-1/accent clay -- reused
# rather than invented fresh, so a site's generated OG image, its
# generated favicon, and ARKlight's own terminal output read as one
# visual identity, not three.
_OG_BG = "#1f2937"
_OG_FG = "#f9fafb"
_OG_ACCENT = "#cc785c"

_AUTHOR_META_RE = re.compile(r'<meta\s+name="author"')
_OG_IMAGE_META_RE = re.compile(r'<meta\s+property="og:image"')

_FONT_STACK = "ui-sans-serif, system-ui, Segoe UI, Helvetica, Arial, sans-serif"


def _arklight_mark(cx: float, cy: float, r: float) -> str:
    """The ARKlight mark: a ring with a filled center -- the same two
    concentric shapes `production.py`'s `_ASSETS_ICON_SVG` draws,
    redrawn here at an arbitrary size/position (instead of a fixed
    0..512 icon viewBox), since the OG image places it inside a much
    wider canvas next to text rather than standing alone."""
    ring_width = r * 0.3
    return (
        f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="none" '
        f'stroke="{_OG_ACCENT}" stroke-width="{ring_width:.1f}"/>'
        f'<circle cx="{cx}" cy="{cy}" r="{r * 0.27:.1f}" fill="{_OG_ACCENT}"/>'
    )


def _truncate(text: str, max_chars: int) -> str:
    """A single-line SVG `<text>` has no wrapping of its own -- rather
    than overflow the canvas (or pull in a font-metrics table this
    zero-dependency project has nothing to supply), a title/byline
    longer than `max_chars` is cut with an ellipsis. Generous limits at
    the call sites below mean this only ever bites a genuinely long
    site name/author."""
    if len(text) <= max_chars:
        return text
    return text[: max_chars - 1].rstrip() + "\u2026"


def _render_og_image(site_name: str, author: str | None) -> str:
    """The default `og-image.svg`: the ARKlight mark, the site's name,
    and (if set) its author -- see this module's docstring for why
    this is SVG and why it's built here rather than as a new IR prop."""
    mark_cx, mark_cy, mark_r = 160.0, _OG_IMAGE_HEIGHT / 2, 90.0
    text_x = mark_cx + mark_r + 80
    title = escape(_truncate(site_name, 28))

    lines = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{_OG_IMAGE_WIDTH}" '
        f'height="{_OG_IMAGE_HEIGHT}" viewBox="0 0 {_OG_IMAGE_WIDTH} {_OG_IMAGE_HEIGHT}" '
        f'role="img" aria-label="{title}">',
        f'  <rect width="{_OG_IMAGE_WIDTH}" height="{_OG_IMAGE_HEIGHT}" fill="{_OG_BG}"/>',
        f"  {_arklight_mark(mark_cx, mark_cy, mark_r)}",
        f'  <text x="{text_x}" y="{mark_cy - 6:.1f}" font-family="{_FONT_STACK}" '
        f'font-size="64" font-weight="700" fill="{_OG_FG}">{title}</text>',
    ]
    if author:
        byline = escape(_truncate(f"by {author}", 40))
        lines.append(
            f'  <text x="{text_x}" y="{mark_cy + 46:.1f}" font-family="{_FONT_STACK}" '
            f'font-size="32" fill="{_OG_FG}" opacity="0.75">{byline}</text>'
        )
    lines.append(
        f'  <text x="{_OG_IMAGE_WIDTH - 48}" y="{_OG_IMAGE_HEIGHT - 40}" '
        f'font-family="{_FONT_STACK}" font-size="24" fill="{_OG_FG}" opacity="0.55" '
        f'text-anchor="end">Built with ARKlight</text>'
    )
    lines.append("</svg>\n")
    return "\n".join(lines)


def _render_robots_txt(*, base_url: str | None) -> str:
    """Always permissive -- ARKlight has no notion of a page that
    shouldn't be indexed (no `Page(draft=...)`-for-Python-pages
    concept, only Markdown's build-time-excluded `draft: true`, which
    never reaches a route or this file at all). A `Sitemap:` line is
    appended only when `sitemap.xml` was actually generated, i.e. only
    when `base_url` is set -- see this module's docstring."""
    lines = ["User-agent: *", "Allow: /"]
    if base_url:
        lines.append(f"Sitemap: {base_url}/{_SITEMAP_PATH}")
    return "\n".join(lines) + "\n"


def _page_loc(base_url: str, output_path: str) -> str:
    """`index.html` maps to the site root (`{base_url}/`), not
    `{base_url}/index.html` -- a crawler and a human both expect the
    bare origin for the home page, and every real deploy host (and
    ARKlight's own route table) treats `/` and `index.html` as the
    same page. Every other route keeps its `.html` suffix, matching
    exactly how `arklight build` actually wrote the file."""
    if output_path == "index.html":
        return f"{base_url}/"
    return f"{base_url}/{output_path}"


def _render_sitemap(ir: WebsiteIR) -> str:
    """One `<url><loc>` per page, sorted so two builds of the same
    site produce byte-identical output (same determinism discipline
    `arklight.content.discovery.discover_content` already documents
    for its own listing)."""
    locs = sorted(
        _page_loc(ir.base_url, _output_path_for_route(page.route)) for page in ir.pages
    )
    entries = "\n".join(
        f"  <url>\n    <loc>{escape(loc, quote=True)}</loc>\n  </url>" for loc in locs
    )
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        f"{entries}\n"
        "</urlset>\n"
    )


def _relative_from(output_path: str, asset_path: str) -> str:
    """Like `arklight.backend.html.routing._relative_asset_path`, but
    taking the current page's own output path directly instead of a
    route + `route_to_path` lookup -- `postprocess()` only ever sees
    flat `{path: contents}` pairs, not the route table `render()`
    already consumed, so there is no route to look up here. Same two
    lines of `posixpath` math either way."""
    current_dir = posixpath.dirname(output_path) or "."
    return posixpath.relpath(asset_path, current_dir)


class SEOBackend(Backend):
    """`robots.txt` + (when `Site(base_url=...)` is set) `sitemap.xml`
    + a default `og-image.svg`, plus the `<head>` tags that wire the
    image (and, when set, `Site(author=...)`) into every page -- see
    this module's docstring for the full design and why each piece is
    shaped the way it is."""

    name = "seo"

    # Set by `render()`, read by `postprocess()` -- see the module
    # docstring's "Why postprocess(), not a new IR prop" section for
    # why this can't just be a second `WebsiteIR` argument.
    _author: str | None = None
    _og_image_generated: bool = False

    def render(self, ir: WebsiteIR) -> dict[str, str]:
        files: dict[str, str] = {
            _ROBOTS_PATH: _render_robots_txt(base_url=ir.base_url),
            _OG_IMAGE_PATH: _render_og_image(ir.site_name, ir.author),
        }
        if ir.base_url:
            files[_SITEMAP_PATH] = _render_sitemap(ir)

        self._author = ir.author
        self._og_image_generated = True
        return files

    def postprocess(self, output_files: dict[str, str]) -> dict[str, str]:
        if not self._og_image_generated or _OG_IMAGE_PATH not in output_files:
            # `render()` never ran against this instance (e.g. a
            # caller assembled `output_files` by hand without this
            # backend's own `render()` contributing to it) -- nothing
            # to link a default `og:image` to, so leave every page
            # exactly as the other backends produced it rather than
            # inject a reference to a file that doesn't exist.
            return output_files

        updated = dict(output_files)
        for path, contents in output_files.items():
            if not path.endswith(".html") or "</head>" not in contents:
                continue

            insertions: list[str] = []
            if self._author and not _AUTHOR_META_RE.search(contents):
                insertions.append(
                    f'  <meta name="author" content="{escape(self._author, quote=True)}">\n'
                )
            if not _OG_IMAGE_META_RE.search(contents):
                og_href = _relative_from(path, _OG_IMAGE_PATH)
                insertions.append(
                    f'  <meta property="og:image" content="{escape(og_href, quote=True)}">\n'
                )

            if insertions:
                updated[path] = contents.replace("</head>", "".join(insertions) + "</head>", 1)

        return updated


__all__ = ["SEOBackend"]
