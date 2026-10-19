"""
`content/` discovery and route synthesis.

Stage M3 of the Markdown-as-first-class-content landing order (see
`docs/Foundational/DESIGN-NOTES.md`'s "Design record: Markdown as
first-class content"), settling that design record's **Q1**, **Q2**
and **Q6**.

**Q1 -- where discovery lives.** This is a filesystem walk, not an AST
scan, and it runs as its own step in `arklight.compiler.pipeline`
*before* `arklight.parser.discover`'s scan of the entry file -- not
inside it. `discover`'s invariant ("parses the entry file's own source,
before any user code runs") is untouched: nothing here reads or
interprets `site.py`. What this module hands the rest of the pipeline
is a list of `ContentPage`s -- the same role `DiscoveredPage` plays for
decorator-registered routes -- which the pipeline turns into ordinary
`Page(...)` nodes (`synthesize_pages`) and merges into the ARK AST next
to the ones `Site.build_ark_ast()` produced.

**Q2 -- what triggers it.** A `.md` file existing under the `content/`
directory next to the site's entry file, *and* the entry file's own
preamble carrying `# include <markdown.ARKlight>`
(`arklight.parser.preamble.includes_markdown_authoring`) -- the same
"mandatory, not a comment" posture `# include <stdlib.ARKlight>` has.
Without that include, `arklight.compiler.pipeline.compile_site_file`
never calls `discover_content` at all; it only checks (via a cheap
directory probe, not a full walk) whether `content/` has `.md` files
nobody opted into, to log a pointer at the missing include rather than
build silently as if they weren't there. Note the trigger, once opted
in, is the *Markdown files*, not the directory: ARKlight's `production`
template already uses `content/` as a plain Python package
(`content/__init__.py`, `content/site_content.py`), and a project like
that has no `.md` files in it, so this step finds nothing and the build
is exactly what it was before this module existed.

**Route derivation**, lowest to highest precedence among the layers
this module owns:

1. the filename-derived default -- `content/guide.md` -> `/guide`,
   `content/index.md` -> `/`, `content/docs/index.md` -> `/docs`,
   `content/docs/setup.md` -> `/docs/setup`;
2. the front matter `route` (Stage M1), which replaces it.

The proposal's top layer, "explicit `site.py` configuration for that
route", has no API to attach to yet -- `Site(...)` has no kwarg that
configures a Markdown-derived route. The one way `site.py` can claim a
route today is registering it with `@site.page(...)`, and per **Q6**
that is a build error rather than a silent override: see
`check_python_route_collisions`.

**Q6 -- duplicate routes.** A Markdown-derived route colliding with
another Markdown-derived route (after front matter overrides) or with
an `@site.page(...)` route is a build error that names both sources.
It is never resolved by silent precedence. `draft: true` pages are
excluded from the discovered set before any of this runs, so a draft
never gets a route, never takes part in a collision check, and is never
built.

Everything is deterministic: files are walked in sorted order and the
returned list is sorted by route.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Mapping

from arklight.api import Footer, Link, Nav, Page
from arklight.content.frontmatter import FrontMatter, parse_front_matter
from arklight.content.markdown import parse_markdown
from arklight.ast.nodes import ARKNode

#: Name of the folder, next to the site's entry file, that is searched
#: for Markdown content. Mirrors `arklight.compiler.pipeline.
#: ASSETS_DIR_NAME`'s "next to site.py" convention.
CONTENT_DIR_NAME = "content"

_MARKDOWN_SUFFIX = ".md"

# What a single URL path segment may contain for a *filename-derived*
# route. Deliberately narrow: a space or other punctuation in a
# filename would otherwise turn silently into an awkward URL. An
# author who wants such a filename sets `route:` in front matter,
# which is the escape hatch the error message points at.
_SAFE_SEGMENT_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._~-]*$")


class ContentError(ValueError):
    """Raised for a problem in how `content/` maps onto routes: an
    unreadable file, an invalid route, or a duplicate route. Always
    names the file(s) involved."""


class ContentCollisionError(ContentError):
    """Raised for Q6: two sources claim the same route. `collisions`
    holds one `(route, first_source, second_source)` tuple per
    colliding route, so a caller can inspect them without parsing the
    message; the message itself lists every one."""

    def __init__(self, collisions: list[tuple[str, str, str]]) -> None:
        self.collisions = collisions
        lines = [
            f"  route {route!r}: {first} and {second}" for route, first, second in collisions
        ]
        noun = "collision" if len(collisions) == 1 else "collisions"
        super().__init__(
            f"Duplicate route {noun} -- two sources claim the same route, and "
            "ARKlight will not pick one silently:\n"
            + "\n".join(lines)
            + "\nGive one of them a different route (a `route:` line in a "
            "Markdown file's front matter, or a different `@site.page(...)` "
            "path), or remove one."
        )


@dataclass(frozen=True)
class ContentPage:
    """One discovered, non-draft Markdown file, with its route
    resolved. `body` is the file's text with the front matter block
    removed -- ready for `arklight.content.markdown.parse_markdown`."""

    source_path: Path
    #: POSIX-style path relative to the site directory, e.g.
    #: `content/guide.md` -- the name diagnostics use for this file.
    relative_path: str
    route: str
    #: Where `route` came from: `"filename"` or `"front matter"`.
    route_source: str
    title: str
    description: str | None
    front_matter: FrontMatter
    body: str

    @property
    def content_path(self) -> str:
        """This file's POSIX path relative to `content/` (`docs/setup.md`)
        -- the key Markdown-to-Markdown links are resolved through."""
        return PurePosixPath(self.relative_path).relative_to(CONTENT_DIR_NAME).as_posix()

    @property
    def source_label(self) -> str:
        return f"{self.relative_path} (route from {self.route_source})"


# ---------------------------------------------------------------------------
# Route derivation
# ---------------------------------------------------------------------------


def _humanize(stem: str) -> str:
    """`getting-started` / `getting_started` -> `Getting Started`."""
    words = re.split(r"[-_\s]+", stem.strip())
    return " ".join(w[:1].upper() + w[1:] for w in words if w)


def _derive_route(relative_to_content: Path, relative_path: str) -> str:
    parts = list(relative_to_content.with_suffix("").parts)
    if parts and parts[-1] == "index":
        parts = parts[:-1]
    for segment in parts:
        if not _SAFE_SEGMENT_RE.match(segment):
            raise ContentError(
                f"{relative_path}: cannot derive a route from the name "
                f"{segment!r} -- a route segment may only contain letters, "
                "digits and . _ ~ - (and must start with a letter or digit). "
                "Rename the file, or set the route explicitly with a "
                "`route:` line in its front matter."
            )
    return "/" + "/".join(parts)


def _validate_front_matter_route(route: str, relative_path: str) -> str:
    def bad(reason: str) -> ContentError:
        return ContentError(
            f"{relative_path}: front matter `route: {route}` is not a valid "
            f"route -- {reason}."
        )

    if not route.startswith("/"):
        raise bad("it must start with '/'")
    if re.search(r"[\s?#\\]", route):
        raise bad("it must not contain whitespace, '?', '#' or backslashes")
    if route == "/":
        return route
    if route.endswith("/"):
        raise bad("it must not end with '/' (write '/guide', not '/guide/')")
    segments = route[1:].split("/")
    if any(s == "" for s in segments):
        raise bad("it must not contain an empty segment ('//')")
    if any(s in (".", "..") for s in segments):
        raise bad("it must not contain '.' or '..' segments")
    return route


def _default_title(content_relative: Path) -> str:
    stem = content_relative.stem
    if stem == "index":
        parent = content_relative.parent.name
        return _humanize(parent) if parent else "Home"
    return _humanize(stem)


# ---------------------------------------------------------------------------
# Discovery
# ---------------------------------------------------------------------------


def _iter_markdown_files(content_dir: Path) -> list[Path]:
    found: list[Path] = []
    for path in content_dir.rglob("*"):
        if path.suffix.lower() != _MARKDOWN_SUFFIX or not path.is_file():
            continue
        # Hidden files/dirs (`.git`, editor droppings like `.#foo.md`)
        # are never content.
        if any(part.startswith(".") for part in path.relative_to(content_dir).parts):
            continue
        found.append(path)
    return sorted(found)


def discover_content(site_dir: str | Path) -> list[ContentPage]:
    """Walk `<site_dir>/content/` for `.md` files and return one
    `ContentPage` per non-draft file, sorted by route.

    Returns `[]` -- touching nothing and raising nothing -- when there
    is no `content/` directory or it holds no Markdown files, which is
    what keeps every existing project's build unchanged.

    Raises `arklight.content.frontmatter.FrontMatterError` for a
    malformed front matter block, and `ContentError` /
    `ContentCollisionError` for an unreadable file, an invalid route,
    or two Markdown files resolving to the same route.
    """
    site_path = Path(site_dir)
    content_dir = site_path / CONTENT_DIR_NAME
    if not content_dir.is_dir():
        return []

    pages: list[ContentPage] = []
    for path in _iter_markdown_files(content_dir):
        relative_path = path.relative_to(site_path).as_posix()
        try:
            # `utf-8-sig` so a BOM from a Windows editor doesn't hide
            # the opening `---` of the front matter block.
            source = path.read_text(encoding="utf-8-sig")
        except (OSError, UnicodeDecodeError) as exc:
            raise ContentError(f"{relative_path}: could not read file: {exc}") from exc

        front_matter, body = parse_front_matter(source, filename=relative_path)
        if front_matter.draft:
            continue

        content_relative = path.relative_to(content_dir)
        if front_matter.route is not None:
            route = _validate_front_matter_route(front_matter.route, relative_path)
            route_source = "front matter"
        else:
            route = _derive_route(content_relative, relative_path)
            route_source = "filename"

        pages.append(
            ContentPage(
                source_path=path,
                relative_path=relative_path,
                route=route,
                route_source=route_source,
                title=front_matter.title
                if front_matter.title is not None
                else _default_title(content_relative),
                description=front_matter.description,
                front_matter=front_matter,
                body=body,
            )
        )

    _check_content_collisions(pages)
    return sorted(pages, key=lambda p: p.route)


def _check_content_collisions(pages: list[ContentPage]) -> None:
    by_route: dict[str, ContentPage] = {}
    collisions: list[tuple[str, str, str]] = []
    for page in pages:  # already in sorted-path order -> stable messages
        earlier = by_route.get(page.route)
        if earlier is None:
            by_route[page.route] = page
        else:
            collisions.append((page.route, earlier.source_label, page.source_label))
    if collisions:
        raise ContentCollisionError(collisions)


def check_python_route_collisions(
    pages: list[ContentPage], python_routes: Mapping[str, str]
) -> None:
    """Q6, second half: raise `ContentCollisionError` if any Markdown
    page's route is also registered by an `@site.page(...)` function.

    `python_routes` maps each Python-registered route to a label for
    where it was declared (e.g. `site.py:12 (about)`); that label is
    what lets the error name both sources.
    """
    collisions = [
        (page.route, page.source_label, python_routes[page.route])
        for page in pages
        if page.route in python_routes
    ]
    if collisions:
        raise ContentCollisionError(collisions)


# ---------------------------------------------------------------------------
# Synthesis
# ---------------------------------------------------------------------------

#: `Site(name=...)`'s own default (`arklight.api.Site.__init__`) --
#: mirrored here as a fallback for `synthesize_page`/`synthesize_pages`
#: callers that don't pass `site_name` explicitly (e.g. direct unit
#: tests), so the default footer never renders an empty site name.
_DEFAULT_SITE_NAME = "arklight-site"


def _build_nav(pages: list[ContentPage]) -> ARKNode:
    """Stage M9 (see docs/Foundational/DESIGN-NOTES.md's "Design
    record: Markdown as first-class content"):
    one `Link` per discovered page, in route order, wrapped in the
    existing `.nav` utility class (`base_stylesheet.BASE_CSS_BODY`) so
    it picks up whichever `markdown_theme` (Stage M7) preset, if any,
    the site selected, with no extra styling work. `pages` is the same
    list for every page on the site (including a single-page site,
    which gets a `.nav` with exactly one self-link rather than an
    empty/omitted block -- M9's own exit test)."""
    return Nav(*(Link(page.title, href=page.route) for page in pages), class_name="nav")


def _build_footer(site_name: str) -> ARKNode:
    """Stage M9: a minimal, site-name-plus-build-year default footer --
    "something sensible, not nothing", same posture as `_build_nav`
    above. Not configurable copy at this stage -- see the addendum's
    M9 section for why the override surface is a separate follow-up."""
    year = datetime.now(timezone.utc).year
    return Footer(f"\u00a9 {year} {site_name}", class_name="footer")


def synthesize_page(
    page: ContentPage,
    page_routes: Mapping[str, str] | None = None,
    *,
    nav_pages: list[ContentPage] | None = None,
    site_name: str | None = None,
) -> ARKNode:
    """Build the `Page(...)` node for one discovered Markdown file:
    the parsed body (Stage M2) as children, the front matter /
    filename-derived title and optional description as props -- the
    same shape a `@site.page` function returns, so everything after
    this point treats it as any other page.

    Local references in the body are resolved (Stage M4) as part of
    that parse; `page_routes` is `{content_path: route}` for every
    non-draft page, which a link to another `.md` file is resolved
    through (see `synthesize_pages`).

    `nav_pages`/`site_name` are Stage M9's nav/footer defaults
    (`_build_nav`/`_build_footer` above): both default to `None`, in
    which case neither is added and this function's output is
    byte-for-byte what it always was -- the shape every existing
    direct caller of `synthesize_page` (unit tests included) already
    relies on. `synthesize_pages` below is the one real caller that
    passes both, for every page it builds.

    Raises `arklight.content.markdown.MarkdownSyntaxError` for a
    construct that opens and never closes, and its subclass
    `MarkdownReferenceError` for a reference that cannot be resolved."""
    props: dict[str, str] = {"title": page.title}
    if page.description is not None:
        props["description"] = page.description
    children = parse_markdown(
        page.body,
        filename=page.relative_path,
        content_path=page.content_path,
        page_routes=page_routes,
        # Stage M6 (see docs/Foundational/DESIGN-NOTES.md's "Design
        # record: Markdown as first-class content"):
        # always on for a real, discovered Markdown page -- this is the
        # "implicitly handled by the compiler" half of that stage, as
        # opposed to Stage M8's `markdown-production` `components/`
        # visibility story. No `site.py` opt-in needed; see
        # `arklight.content.markdown.parse_markdown`'s `style_hooks` kwarg.
        style_hooks=True,
    )
    body: list = list(children)
    if nav_pages is not None:
        body = [_build_nav(nav_pages), *body]
    if site_name is not None:
        body = [*body, _build_footer(site_name)]
    return Page(*body, **props)


def synthesize_pages(
    pages: list[ContentPage], *, site_name: str = _DEFAULT_SITE_NAME
) -> dict[str, ARKNode]:
    """`{route: Page node}` for every discovered page, in route order.
    Builds the `{content_path: route}` table once, from the whole
    (draft-free) set, so a page can link to any other.

    Stage M9: every page returned here also gets the automatic nav
    (one `Link` per discovered page, built from this same `pages`
    list) and footer (`site_name` plus the build year) default --
    `arklight.compiler.pipeline.compile_site_file` passes `site.name`
    through as `site_name`; direct callers that don't care about M9
    (or want the pre-M9 shape) should call `synthesize_page` directly
    instead, which defaults to adding neither."""
    page_routes = {page.content_path: page.route for page in pages}
    return {
        page.route: synthesize_page(page, page_routes, nav_pages=pages, site_name=site_name)
        for page in pages
    }


__all__ = [
    "CONTENT_DIR_NAME",
    "ContentCollisionError",
    "ContentError",
    "ContentPage",
    "check_python_route_collisions",
    "discover_content",
    "synthesize_page",
    "synthesize_pages",
]
