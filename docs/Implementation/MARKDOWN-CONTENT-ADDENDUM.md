# Markdown Content Addendum: Staged Landing Order

**Status:** IN PROGRESS. Ten stages (`M1`-`M10`); **`M1`-`M9` SHIPPED,
unreleased (`alpha`)**, `M10` PLANNED. **No version slots
reserved** -- assigned when each remaining stage is actually
scheduled, not here. `M6` and `M8` were inserted into the ladder after
`M1`-`M5` shipped, and `M9` (automatic nav/footer/SEO defaults) was
inserted after `M7` shipped (see each stage's own section for why);
the original docs/tests rollup kept its own content but moved down to
`M10` to make room -- this file always reflects the order as shipped,
not as first proposed. `M9`'s own override/opt-out surface (turning
the nav/footer/SEO defaults off or replacing them) is explicitly out
of `M9`'s scope and will ship later as its own follow-up stage, not
tracked by a stage number here yet. This file turns the accepted
[`docs/Proposals/MARKDOWN-CONTENT-PROPOSAL.md`](../Proposals/MARKDOWN-CONTENT-PROPOSAL.md)
into a trackable landing order, the same role
[`APP-SHELL-ADDENDUM.md`](APP-SHELL-ADDENDUM.md) plays for its
proposal. It does not restate the proposal's reasoning; it fixes the
order, the touch points, and the exit test for each rung, and settles
the proposal's open questions one at a time as each stage reaches
them.

## Why this was accepted

ARKlight calls itself a static site generator. A static site generator
that cannot take Markdown as input is missing the one authoring format
most people reach for first when they hear "SSG" -- every rung below
exists to close that specific, narrow gap, not to grow ARKlight's
scope elsewhere.

## Ground truth this ladder starts from

Verified against source on `alpha`, not taken from the proposal text:

| Fact | Where |
| --- | --- |
| Discovery is `ast.parse` on the entry file's own source, before any user code runs; it recognizes `Site()` and literal `@<site_var>.page("/route")` shapes only | `arklight/parser/discover.py` |
| `arklight new` turns one of `arklight.cli.templates.TEMPLATES` into a written project dir; each template module exposes `build(name) -> dict[str, str]` | `arklight/cli/scaffold.py`, `arklight/cli/templates/{simple,production}.py` |
| A vendored, dependency-free Markdown reader already exists and already handles ATX headings, bold/italic, inline code, fenced code blocks, blockquotes, lists, horizontal rules, links, and pipe tables -- today it reflows all of that to ANSI terminal text, not IR nodes | `arklight/cli/mdrender.py` |
| Every IR node this proposal needs already exists as a plain `node("...")` wrapper, validated against `arklight.ir.schema.SCHEMA`: `Heading`, `Text`, `Strong`, `Em`, `Link`, `Image`, `List`/`Item`, `OrderedList`, `Pre`, `Code`, `Blockquote`, `HorizontalRule`, the `Table` family | `arklight/api.py` |
| Local references are already validated at build time; a broken reference is a build-failing diagnostic, not a silent gap | `arklight/compiler/asset_check.py`, `arklight/compiler/link_check.py` |
| `arklight.compiler.pipeline`'s own module docstring names the pipeline's stages explicitly: `Python Source -> Python AST -> ... -> IR -> backends` | `arklight/compiler/pipeline.py` |
| `arklight/backend/css` is ARKlight's one layout system -- intrinsic, no viewport-keyed breakpoints by default (`css-media-queries` is a gated experimental feature, not the default posture) | `arklight/backend/css`, `arklight/experimental.py` |

## Stage M1 -- Front matter parser **(SHIPPED)**

Settles the proposal's **Q3**. A restricted, standard-library-only
`key: value` front matter reader -- not full YAML, consistent with
`mdrender.py`'s own stated reason for never taking a Markdown
dependency. Supports `title`, `description`, `route`, `draft` (bool)
as a fixed, closed key set for this stage; an unrecognized key is a
diagnostic, not a silent no-op.

- **Exit test:** a file with front matter parses to a small
  dataclass; a file with none parses to all-defaults; a malformed
  block (unterminated `---`, an unrecognized key) raises an actionable
  error naming the file and the key.
- **Touch points:** new module, no existing file changed. Shipped as
  `arklight/content/__init__.py`/`arklight/content/frontmatter.py`
  (`KNOWN_KEYS = {"title", "description", "route", "draft"}`, matching
  the closed set above exactly). `tests/test_frontmatter.py`.

## Stage M2 -- Markdown-to-IR parser **(SHIPPED)**

The core of the proposal. Extracts and adapts `mdrender.py`'s existing
recognizers (headings, emphasis, fenced code, lists, links, tables,
rules) to build `ARKNode` trees via `arklight.api`'s existing
components instead of ANSI strings. `mdrender.py` itself is
**untouched** -- `arklight search --retrieve-doc` still wants terminal
output, not IR, so the two consumers get their own thin layer over a
shared recognizer core rather than one trying to serve both.

- Construct mapping is exactly the table already in the proposal
  (`#`→`Heading(level=N)`, `**bold**`→`Strong`, fenced block→
  `Pre(Code(...))`, etc.) -- no new schema entries, per the proposal's
  own constraint.
- **Raw HTML (Q4), settled here:** raw HTML blocks/inline HTML in a
  Markdown source are **escaped to visible text**, not stripped
  silently and not passed through. Escaping (not stripping) was
  chosen specifically so a visitor sees that something was written
  there rather than silently losing content, and so there is no
  allow-list to maintain or keep in sync with ARKlight's no-`eval`
  stance -- the narrowest of the three options the proposal listed,
  revisitable later as its own proposal if real projects need more.
- **Exit test:** one fixture `.md` file exercising every construct in
  the mapping table round-trips to the expected IR tree; a raw
  `<script>` block in the fixture renders as escaped text in output,
  never as a live element.
- **Touch points:** new module (the parser), `arklight/ir/schema.py`
  untouched per the proposal's own "no new schema entries" framing.
  Shipped as `arklight/content/markdown.py` (`parse_markdown(...)`).
  `tests/test_markdown.py`.

## Stage M3 -- `content/` discovery and route synthesis **(SHIPPED)**

Settles **Q1** and **Q2**. Discovery of `.md` files under `content/`
runs as its own step in `arklight/compiler/pipeline.py`, **before**
`arklight.parser.discover`'s existing AST-only scan, not inside it --
`discover`'s "parses the entry file's own source, before any user code
runs" invariant is left completely intact; Markdown discovery is a
filesystem walk that happens first and hands the rest of the pipeline
a synthesized set of pages, the same shape `DiscoveredPage` already
is. Trigger: presence of a `content/` directory next to `site.py` --
no opt-in flag required, since a `content/`-free project never
triggers this step at all (Stage M3's exit test covers that directly).

Route derivation: `content/guide.md` → `/guide`, `content/index.md` →
`/`, overridden by front matter `route`, overridden by explicit
`site.py` configuration for that route -- the precedence order from
the proposal, unchanged.

- **Q6 (duplicate routes), settled here:** a Markdown-derived route
  colliding with a `@site.page(...)` route, or with another
  Markdown-derived route after front-matter overrides, is a build
  error naming both sources -- consistent with `discover`'s existing
  "no pages registered" collision-shaped errors, not a silent
  precedence rule.
- **`draft: true` pages are excluded from the discovered set
  entirely** -- they don't get a route, don't appear in generated
  nav, and don't participate in Q6's collision check.
- **Exit test:** a fixture project with three `content/*.md` files
  (one with a `route` override, one `draft: true`, one colliding with
  a `@site.page` route) produces exactly the two expected pages and
  the one expected collision error.
- **Touch points:** `arklight/compiler/pipeline.py` (new early stage);
  `arklight/content/discovery.py` (new, `discover_content`/
  `synthesize_pages`/`ContentCollisionError`). Corrected from the plan
  above once implemented: `arklight/parser/discover.py` and
  `arklight/parser/loader.py` each gained a `require_pages: bool =
  True` keyword, defaulting to the long-standing behavior and passed
  `False` only when Markdown content was already found under
  `content/` -- `discover`'s AST-only-scan invariant itself is
  unchanged, but the files are no longer byte-for-byte untouched as
  first planned. `tests/test_content_discovery.py`.

## Stage M4 -- Asset and link resolution **(SHIPPED)**

Wires Stage M2's output into the existing validation machinery rather
than writing a second one. A Markdown-sourced `Image`/`Link` node is,
by the time it reaches `arklight.compiler.asset_check`/`link_check`,
indistinguishable from one a Python-authored page produced -- both
walk the same IR tree. The only new work is resolving a Markdown
file's relative paths (`![alt](./diagram.png)`) against `assets/`
during Stage M2's own parse, before the tree is handed off.

- **Exit test:** a missing local image referenced from a Markdown file
  fails the build with the same diagnostic shape
  `Link(href="/typo")` already produces from a Python page; a present
  one resolves and copies through unchanged.
- **Touch points:** Stage M2's parser only; `asset_check.py`/
  `link_check.py` unchanged. Shipped as extensions to
  `arklight/content/markdown.py` (`content_path=` resolution,
  `MarkdownReferenceError`) and `arklight/content/discovery.py`.
  `tests/test_content_assets.py`.

## Stage M5 -- `markdown-simple` / `markdown-production` templates **(SHIPPED)**

Two new entries in `arklight.cli.templates.TEMPLATES`, following
`simple.py`/`production.py`'s existing `build(name) -> dict[str, str]`
contract exactly. `markdown-simple` writes `site.py`, `content/`
(with one `index.md` and one `about.md`, mirroring `simple`'s two
inline pages), and `assets/`. `markdown-production` adds `components/`
and `pages/` alongside `content/`, for a project that mixes
Python-authored pages with Markdown content -- Q7's "mixed is the
intended steady state" answer, with M3's duplicate-route check as the
guard rail that makes mixing safe.

- **Exit test:** both new templates build successfully, unmodified,
  immediately after `arklight new` -- acceptance criterion 1 from the
  proposal, verified directly.
- **Touch points:** `arklight/cli/templates/markdown_simple.py`,
  `arklight/cli/templates/markdown_production.py` (new),
  `arklight/cli/templates/__init__.py` (registry entry). `simple.py`/
  `production.py` untouched, as planned. `tests/test_markdown_templates.py`
  (follows `tests/test_scaffold.py`'s pattern: file-presence checks,
  then a real `arklight build` over the scaffolded output, which is
  this stage's own exit test).

## Stage M6 -- Style hooks on Markdown-sourced nodes **(SHIPPED)**

Inserted after `M1`-`M5` shipped, ahead of the presets stage below
(renumbered to `M7` to make room): the presets stage styles whole
pages via `Site(markdown_theme=...)`, but nothing before this stage
gave a Markdown-authored block anything a *project's own* CSS
(`Site.style(...)`/`Site.style_selector(...)`) could individually
select -- a `Heading`/`Text`/`List`/... parsed out of `content/*.md`
came out of Stage M2 with no `class_name` at all, indistinguishable
from any other `Heading` only by its text. This stage closes that gap
the same way the rest of this ladder closes gaps: by giving Markdown
content the same hooks a Python-authored page already has access to
(`Heading("...", class_name="...", id="...")` has always been legal
`arklight.api` usage), not a new mechanism.

- Every block `arklight.content.markdown.parse_markdown` produces gets
  a stable `class_name` under a fixed `ark-md-*` prefix -- `ark-md-h1`
  .. `ark-md-h6`, `ark-md-p`, `ark-md-list`/`ark-md-ordered-list`/
  `ark-md-item`, `ark-md-pre`/`ark-md-code-block`, `ark-md-blockquote`,
  `ark-md-hr`, `ark-md-img`, the full `ark-md-table`/`ark-md-thead`/
  `ark-md-tbody`/`ark-md-tr`/`ark-md-th`/`ark-md-td` family, and
  `ark-md-strong`/`ark-md-em`/`ark-md-code`/`ark-md-link` for the one
  edge case where a whole paragraph collapses to a single bare inline
  node (`_paragraph_node`, e.g. `**bold**` alone on a line). Every
  `Heading` additionally gets a slugged `id`, unique within the page,
  for `[text](#fragment)` anchor links -- not a styling hook (see the
  next point), just a normal HTML `id`.
- **Why `id`, not a CSS hook:** `arklight.backend.css.selectors`
  (what `Site.style_selector(...)` validates against) has no `#id`
  selector at all, only tag/class/attribute/pseudo -- so every styling
  hook this stage adds is a `class_name`, on purpose, and `id` stays
  scoped to its one existing HTML job.
- **Default styling, shipped as part of this stage, not deferred to
  `M7`:** `arklight.backend.css.markdown_defaults.MARKDOWN_CSS_BODY`
  styles every `ark-md-*` class above, included in the generated
  stylesheet unconditionally (same cascade tier as, and right after,
  `BASE_CSS_BODY`) -- a `content/*.md` file looks reasonable out of the
  box with zero project CSS written, the same posture every other
  built-in component already has. Every `ark-md-*` class is folded into
  `arklight.api.RESERVED_UTILITY_CLASSES` the same protected way
  `.card`/`.nav`/etc. already are, so a plain `site.style("ark-md-h1",
  ...)` collision fails loudly instead of silently merging.
- **Disclaimer (this is the whole of this stage's styling story, for
  now):** this only wires up ARKlight's own *default* styling. There is
  no dedicated, supported way yet to replace it wholesale with a
  project's own Markdown theme -- only the generic
  `allow_redefine=True` escape hatch every reserved utility class
  already has. A first-class Markdown-theming surface is `M7`
  (independent of this stage; SHIPPED as `Site(markdown_theme=
  "light"|"dark"|"reading")` -- see that stage's own section).
- **Not feature parity, settled here:** `content/*.md` is not a
  `Page(...)`-authored page in different syntax. The construct mapping
  table in Stage M2 is the entire Markdown vocabulary this parser
  understands -- no component props, no `State`/`Bind`/`Action`, no
  custom components -- so a Markdown file can only ever produce, and
  this stage can only ever style, what that table expresses. A page
  that needs any of that goes through a `@site.page(...)`-decorated
  function instead, same as always; mixing both in one project is what
  `markdown-production` (Stage M5) is for.
- **Exit test:** `style_hooks=True` tags every construct in Stage M2's
  fixture with its documented class (and every heading with a unique
  slugged `id`); `arklight.content.discovery.synthesize_page` applies
  hooks with no `site.py` opt-in; the generated stylesheet always
  contains `.ark-md-*` rules, whether or not the site has any Markdown
  content; `site.style("ark-md-h1", ...)` raises the existing
  duplicate-utility-class error, and `allow_redefine=True` overrides it.
- **Touch points:** `arklight/content/markdown.py` (`style_hooks:
  bool = False` kwarg on `parse_markdown`, defaulting to off so every
  existing `tests/test_markdown.py` assertion is untouched -- Stage
  M2-M4's own contract does not change); `arklight/content/
  discovery.py` (`synthesize_page` always passes `style_hooks=True`);
  `arklight/backend/css/markdown_defaults.py` (new, sibling to
  `base_stylesheet.py`); `arklight/backend/css/render.py` (wires the
  new module into the cascade); `arklight/api.py`
  (`RESERVED_UTILITY_CLASSES` unioned with the new module's
  `HOOK_CLASS_NAMES`). `tests/test_markdown_style_hooks.py` (new).

## Stage M7 -- `light` / `dark` / `reading` presets **(SHIPPED)**

Three preset stylesheets layered on `arklight/backend/css`'s existing
intrinsic layout system -- no new layout engine, no breakpoint rules
beyond what already exists, per the proposal's own constraint.

- **`light`**: tuned from ARKlight's existing default stylesheet
  posture (`arklight.backend.css.base_stylesheet.BASE_CSS_BODY`), not
  restyled from scratch.
- **`dark`**: the palette is fixed, not a new design decision -- taken
  directly from `mdrender.py`'s own ANSI constants: `#cc785c` primary
  accent/link (heading-1/bullet/table-header clay), `#c4946b`
  secondary (heading-2 tan), `#a69780` tertiary/blockquote (heading-3
  taupe), `#d6a373` inline code, `#828282` table borders/rules.
  **Q5, settled here:** the background is `#16140f` -- a near-black,
  warm-tinted ground (not a pure `#000`) chosen to keep the clay/tan/
  taupe accents at a comfortable contrast ratio against it, confirmed
  at implementation time against WCAG AA for body text.
- **`reading`**: its own design -- a narrower measure, larger
  line-height, warm paper-toned background -- not modeled on anything
  that exists today, per the proposal.
- **Exit test:** a fixture page renders under all three presets with
  zero custom CSS from the project, matching acceptance criterion 5;
  a contrast-ratio check on `dark`'s body text against `#16140f`
  passes AA.
- **Touch points:** `arklight/backend/css/markdown_presets.py` (new
  module, sibling to `base_stylesheet.py`/`markdown_defaults.py`);
  `arklight/backend/css/render.py` (`CSSBackend.render` emits the
  selected preset right after `MARKDOWN_CSS_BODY`); `arklight/ir/
  build.py` (`WebsiteIR.markdown_theme` + `build_website_ir(
  markdown_theme=...)`); `arklight/api.py` (`Site(markdown_theme=
  "light"|"dark"|"reading")` kwarg, validated against `MARKDOWN_
  PRESETS`'s own keys); `arklight/compiler/pipeline.py` (straight
  passthrough into `build_website_ir`). `tests/test_markdown_
  presets.py` is the exit test: the fixture-page-under-all-three-
  presets check, the `dark`/`#16140f` WCAG AA contrast-ratio
  computation, and a check that an unset `markdown_theme` builds
  byte-identical output to every pre-`M7` release.

## Stage M8 -- `markdown-production` style-hook visibility **(SHIPPED)**

Inserted alongside `M6`, same reasoning that moved the presets stage
to `M7`: `M6` ships the hooks and the default styling, but gives an
author no way to *see* what classes exist or that they're already
styled, short of reading `markdown_defaults.py`'s source. `markdown-
production` (Stage M5) already scaffolds a `components/` folder for
its Python-authored side (`components/nav.py`, `components/
footer.py`) -- this stage reuses that existing convention rather than
inventing a new one: "the reason `markdown-production` gets this at
all is that it has a `components/` folder defined at scaffolding time
to put it in."

- `markdown-production`'s `build(name)` writes one more file,
  `components/markdown_style.py`: pure documentation (a module
  docstring, nothing imported or wired into the build) listing every
  `ark-md-*` class from `M6` and the default styling ARKlight already
  ships for it, plus the same `allow_redefine=True` disclaimer `M6`
  states, with a commented-out `site.style_selector(...)` example to
  uncomment and edit.
- **`markdown-simple` deliberately does not get an equivalent file:**
  that template has no `components/` folder at all
  (`site.py`/`content/`/`assets/` is its whole layout) -- there is
  nowhere to put a visibility file without inventing a new top-level
  convention this stage isn't scoped to add. `M6`'s hooks and default
  styling still apply to a `markdown-simple` project exactly as they
  do everywhere else; they're just not surfaced as a file there. This
  is the "simple is implicitly handled by the compiler" half of the
  stage, as opposed to `markdown-production`'s "visible as a
  component" half.
- **Exit test:** `markdown-production`'s scaffolded output contains
  `components/markdown_style.py`; `markdown-simple`'s does not;
  `arklight build` succeeds unmodified for both, same as `M5`'s own
  exit test (this stage adds a file, it does not change build
  behavior).
- **Touch points:** `arklight/cli/templates/markdown_production.py`
  (new file in `build(name)`'s output, module docstring updated);
  `arklight/cli/templates/markdown_simple.py` (module docstring note
  only, no file added). `tests/test_markdown_templates.py` extended.

## Stage M9 -- Automatic nav/footer/SEO defaults **(SHIPPED, unreleased)**

Inserted after `M7` shipped, same reasoning that inserted `M6`/`M8`
into the ladder: a freshly scaffolded Markdown site (`markdown-
simple`/`markdown-production`, Stage M5) still renders with no page
navigation, no footer, and none of the baseline SEO `<head>` surface
(`<meta name="description">`, `<meta property="og:*">`, a canonical
link) unless an author writes that Python themselves -- out of step
with "beginner friendly" and "Flask-like simplicity" for the one
authoring path (Markdown) that's explicitly meant to need the least
Python. This stage's scope is the *default*, free-by-default half of
that gap only; the override surface below is its own, separately
scheduled follow-up.

- **Nav:** synthesized from `arklight.content.discovery`'s already-
  resolved route table (Stage M3) -- one link per discovered page, in
  route order -- rendered with the existing `.nav` utility class
  (`base_stylesheet.BASE_CSS_BODY`), so it picks up whichever
  `markdown_theme` (`M7`) preset, if any, the site selected with no
  extra styling work.
- **Footer:** a minimal, site-name-plus-build-year default footer,
  same "something sensible, not nothing" posture as the nav default
  above -- not configurable copy at this stage, just present instead
  of absent.
- **SEO, per-page `<head>` tags:** per-page `description` already
  flows from Stage M1 front matter into `Page(description=...)`
  today; this stage adds the `<head>` tags that front-matter value
  should have been populating all along (`<meta name="description">`,
  `og:title`/`og:description` mirroring the page's existing
  `title`/`description`, a self-referential canonical link from the
  page's own route) -- no new front-matter keys, just wiring the ones
  `M1` already parses all the way to the rendered `<head>`
  (`arklight/backend/html/head_meta.py`, gated by its own
  `seo_opt_in` check: a page that sets none of this still renders
  exactly as before).
- **SEO, site-wide defaults:** three more pieces a single page's own
  front matter can't carry, since they need the *whole site* (every
  route, the site name, the author) rather than one page's IR node --
  `arklight/backend/seo.py`'s `SEOBackend`, added to
  `arklight.compiler.pipeline.default_backends()`:
  - `robots.txt` -- always generated (`User-agent: * / Allow: /`),
    with a `Sitemap:` line once `sitemap.xml` exists.
  - `sitemap.xml` -- one `<url><loc>` per page route, generated only
    when the new `Site(base_url=...)` is set (sitemap `<loc>` entries
    must be absolute per the sitemap protocol, and there's no way to
    derive a real origin from the build alone -- see `SEOBackend`'s
    own docstring for why a missing `base_url` means "skip it", not
    "guess one").
  - `og-image.svg` -- a generated default Open Graph image (the
    ARKlight mark, the site name, and, if the new `Site(author=...)`
    is set, a byline), GitHub-social-preview-card style. SVG, not a
    raster format, for the same "no image-encoding dependency exists
    in this project" reason `arklight new`'s scaffolded
    `assets/icon.svg` is hand-drawn SVG too -- see `SEOBackend`'s own
    "Why SVG, not PNG" note for the tradeoff that makes (some stricter
    link-unfurlers won't rasterize it) and why it's always overridable
    per page (`Page(og_image=...)` wins whenever a page sets one).
  - A default `<meta property="og:image">` (and, when `Site(author=
    ...)` is set, `<meta name="author">`) is injected into every
    already-rendered page via `SEOBackend.postprocess()` -- deliberately
    *not* routed through `_render_head_meta`'s `seo_opt_in` gate like
    the per-page tags above, since the entire point of a sitewide
    default is reaching pages that set no SEO props of their own, not
    just ones that already opted in.
- **Override, explicitly out of scope for this stage:** none of the
  three defaults above gets an opt-out or a replacement surface yet
  (no `Site(nav=False)`, no custom footer component slot, no per-page
  SEO override beyond what `M1`'s front matter already exposes) --
  **that override surface ships later, as its own follow-up stage**,
  the same "default now, override as a separate, independent landing"
  split `M6`/`M7` already drew between default `.ark-md-*` styling and
  a first-class theming surface. Until that follow-up lands, a project
  that wants different nav/footer/SEO has the same escape hatch every
  other default in this ladder already has: author the page's own
  `Nav`/`Container`/`<head>`-adjacent nodes directly in Python instead
  of relying on Markdown-content synthesis for that page.
- **Exit test:** a fixture Markdown site with two or more discovered
  pages builds, via a real `arklight build`, HTML containing a `.nav`
  block with one link per page and a footer block on every page, plus
  a `<head>` carrying `description`/`og:title`/`og:description`/
  canonical tags sourced from that page's own front matter; a single-
  page fixture still gets a footer and SEO tags but a `.nav` with
  exactly one (self) link, not an empty or omitted block. For the
  site-wide defaults: any build (Markdown-authored or not) produces
  `robots.txt` and `og-image.svg`, every page's `<head>` carries a
  default `<meta property="og:image">`, `sitemap.xml` appears (with a
  matching `Sitemap:` line in `robots.txt`) only when `Site(base_url=
  ...)` is set, and a page with its own `Page(og_image=...)` keeps
  that value instead of the default.
- **Touch points:** `arklight/content/discovery.py` (nav link
  synthesis, reusing the route table `M3` already builds);
  `arklight/compiler/pipeline.py` or `arklight/ir/build.py` (where the
  synthesized nav/footer nodes and `<head>` tags actually get spliced
  into each page's IR -- exact stage to be confirmed at implementation
  time against the pipeline's existing stage boundaries);
  `arklight/backend/html/page_render.py` (new `<head>` tag emission);
  `arklight/backend/seo.py` (new -- `SEOBackend`, the site-wide
  defaults above); `arklight/api.py`/`arklight/ir/build.py`
  (`Site`/`WebsiteIR`'s new `author`/`base_url` fields, `SEOBackend`'s
  own inputs). New test files: `tests/test_seo_backend.py`, same
  naming convention as `tests/test_markdown_presets.py`.

## Stage M10 -- Docs and tests

`AUTHORING-GUIDE.md` gets a Markdown-authoring section; tests follow
`tests/test_persist_global_scope.py`'s pattern -- unit coverage per
stage (front matter, parser, discovery, asset resolution, templates,
style hooks, presets, template visibility, nav/footer/SEO defaults)
plus one end-to-end fixture project exercised through a real `arklight
build`. `CHANGELOG.md` gets one entry per stage as it ships, same as
every other staged ladder in this folder.

- **Exit test:** full test suite green, including the new Markdown
  suite; `AUTHORING-GUIDE.md` reviewed against the shipped behavior of
  `M1`-`M9`, not the proposal's original wording.

## Suggested order

M1 → M2 → M3 → M4 → M5 → M6 → M8 → M7 → M9 → M10, in roughly that
order: each stage's exit test depends on the previous one's output (M2
needs M1's front matter, M3 needs M2's parser, M4 needs M3's
discovered pages, M5 needs M2-M4 working end to end to scaffold
against, M6 needs M2's node shapes and M5's templates to attach hooks
to and scaffold against, M8 needs M5's `markdown-production` template
and M6's hooks to document, M7 is independent of M1-M6/M8 and could in
principle run in parallel, M9 needs M3's route table for nav synthesis
and benefits from M7 already existing so its nav/footer defaults
render sensibly under any preset, M10 closes every stage out). No
stage here is scheduled against a version slot yet -- see Status
above.

`M1`-`M9` have landed on `alpha`, unreleased; full suite green
including the Markdown tests (`tests/test_frontmatter.py`,
`tests/test_markdown.py`, `tests/test_content_discovery.py`,
`tests/test_content_assets.py`, `tests/test_markdown_templates.py`,
`tests/test_markdown_style_hooks.py`, `tests/test_markdown_
presets.py`) and `M9`'s own `tests/test_seo_backend.py`. `M9`'s own
override/opt-out surface is still explicitly deferred past M9 itself,
to be scheduled as its own follow-up now that the default surface has
shipped. `M10` (docs/tests rollup, `CHANGELOG.md`/`AUTHORING-GUIDE.md`)
is next: its own exit test wants the full `M1`-`M9` surface reviewed
in one pass, which can now happen since `M9` is done.
