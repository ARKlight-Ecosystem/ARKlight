# Markdown Content Addendum: Staged Landing Order

**Status:** PLANNED. Seven stages (`M1`-`M7`), none started, **no
version slots reserved** -- assigned when each stage is actually
scheduled, not here. This file turns the accepted
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

## Stage M1 -- Front matter parser

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
- **Touch points:** new module, no existing file changed.

## Stage M2 -- Markdown-to-IR parser

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

## Stage M3 -- `content/` discovery and route synthesis

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
- **Touch points:** `arklight/compiler/pipeline.py` (new early stage),
  `arklight/parser/discover.py` (unchanged -- consumed, not modified).

## Stage M4 -- Asset and link resolution

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
  `link_check.py` unchanged.

## Stage M5 -- `markdown-simple` / `markdown-production` templates

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
  `production.py` untouched.

## Stage M6 -- `light` / `dark` / `reading` presets

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
- **Touch points:** new stylesheet modules under `arklight/backend/
  css/`; `Site(...)` gains a `markdown_theme="light"|"dark"|"reading"`
  kwarg (naming to be confirmed at implementation time against
  `Site.__init__`'s existing kwarg conventions).

## Stage M7 -- Docs and tests

`AUTHORING-GUIDE.md` gets a Markdown-authoring section; tests follow
`tests/test_persist_global_scope.py`'s pattern -- unit coverage per
stage (front matter, parser, discovery, asset resolution, templates,
presets) plus one end-to-end fixture project exercised through a real
`arklight build`. `CHANGELOG.md` gets one entry per stage as it ships,
same as every other staged ladder in this folder.

- **Exit test:** full test suite green, including the new Markdown
  suite; `AUTHORING-GUIDE.md` reviewed against the shipped behavior of
  M1-M6, not the proposal's original wording.

## Suggested order

M1 → M2 → M3 → M4 → M5 → M6 → M7, in that order: each stage's exit
test depends on the previous one's output (M2 needs M1's front matter,
M3 needs M2's parser, M4 needs M3's discovered pages, M5 needs M2-M4
working end to end to scaffold against, M6 is independent of M1-M5 and
could run in parallel if useful, M7 closes every stage out). No stage
here is scheduled against a version slot yet -- see Status above.
