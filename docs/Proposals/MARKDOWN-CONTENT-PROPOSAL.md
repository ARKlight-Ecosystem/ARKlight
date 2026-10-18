# Markdown as First-Class Content

## Status

**Proposal -- not yet accepted, not yet staged.** Per
`docs/Proposals/README.md`'s own definition, this describes something
that does not exist yet, may never be built as written, and could be
rejected outright. Nothing below is implemented; every path named here
is a *target*, not a change already made.

**Origin:** a `site.py` sketch pitching Markdown pages discovered from
a `content/` directory, written to the same `@site.page(...)` mental
model ARKlight already uses, with header/footer/nav/theme "built in"
and no styling configuration required by default.

## What is already settled (context, not part of this proposal)

- **Discovery is AST-only and entry-file-only.** `arklight.parser.
  discover` parses the entry file's source with `ast.parse`, before
  any user code runs, and looks for `Site()` and literal
  `@<site_var>.page("/route")` decorator shapes (see the
  `arklight-skill-collections` gotchas #2 and #3). Nothing about
  *filesystem* discovery -- scanning `content/` for `.md` files -- exists
  today; every route currently comes from a decorator in the entry
  file itself.
- **The IR already has the vocabulary this needs.** `arklight.api`
  exposes `Heading`, `Text`, `Strong`, `Em`, `Link`, `Image`, `Picture`,
  `List`/`Item`, `OrderedList`, `Pre`, `Code`, `Blockquote`,
  `HorizontalRule`, `Table`/`TableHead`/`TableBody`/`TableRow`/
  `TableHeaderCell`/`TableCell`, `Video`, `Audio`, and the semantic
  shell pieces (`Header`, `Footer`, `Nav`, `Main`, `Article`,
  `Section`) as plain `node("...")` wrappers over `ARKNode` (see
  `arklight.ast.nodes`), validated against `arklight.ir.schema.SCHEMA`.
  Every construct this proposal needs to render already has a
  destination node; none of it requires a new component.
- **A Markdown parser already exists in this tree.**
  `arklight/cli/mdrender.py` is a vendored, dependency-free Markdown
  reader, written because ARKlight ships zero runtime dependencies on
  principle (no `[project.dependencies]` in `pyproject.toml`, per that
  module's own docstring). It already handles ATX headings, bold/
  italic, inline code, fenced code blocks, blockquotes, bullet/
  numbered lists, horizontal rules, links, and pipe tables -- today it
  reflows all of that to ANSI terminal text for `arklight search
  --retrieve-doc`, not to IR nodes. The *parsing* half of this
  proposal is substantially "point that recognizer at
  `arklight.ir.components` instead of at an ANSI string buffer," not
  "write a Markdown parser from nothing."
- **`arklight new` already has a two-template split.** `arklight.cli.
  scaffold` turns one of `arklight.cli.templates.TEMPLATES`
  (`simple`, `production`, defined in `arklight/cli/templates/
  simple.py` and `production.py`) into a written project directory.
  Adding layouts to this proposal is extending an existing registry,
  not inventing scaffolding from scratch.
- **The compiler pipeline has named stages already**, per
  `arklight/compiler/pipeline.py`'s own module docstring:
  `Python Source -> Python AST -> ... -> IR -> backends`. `arklight.
  compiler.asset_check` and `arklight.compiler.link_check` already
  validate local references and report unresolved ones; `arklight.ir.
  validate` is the only place IR-shape errors are raised today.

## The proposal, as stated

Add Markdown as a first-class authoring format. Markdown content
compiles to static HTML through ARKlight's existing compiler pipeline
-- the same `IR -> backends` stage every `Page(...)`-returning Python
function already goes through -- without requiring the author to write
Python components, HTML, or CSS for an ordinary content page.

### Project layouts

A new `markdown` family alongside the existing `simple`/`production`
split in `arklight.cli.templates.TEMPLATES`, with two layouts of its
own:

- **`markdown-simple`**: `site.py`, `content/`, `assets/`.
- **`markdown-production`**: `site.py`, `components/`, `pages/`,
  `content/`, `assets/`.

Both share one content frontend and one compiler pipeline -- there is
no second build path. `simple` and `production` are unchanged; a
project that never puts anything under `content/` never touches any of
this.

### Authoring

Markdown files live under `content/`. `site.py` keeps doing what it
already does: site identity, navigation, footer, and presentation are
still ordinary `Site(...)` configuration, exactly like today.

What's new is a discovery step that walks `content/` for `.md` files
and derives a route and a nav-label default for each one from its path
(`content/guide.md` -> `/guide`, `content/index.md` -> `/`), the same
way `arklight.parser.discover` derives today's routes from decorator
syntax -- except this scan runs against the filesystem, at build time,
not against the entry file's AST. Precedence, high to low:

1. Explicit `site.py` configuration for that route.
2. The document's own front matter.
3. The filename-derived default.

Optional YAML-ish front matter at the top of a file sets `title`,
`description`, `route` (an override for the filename-derived one), and
`draft` (excluded from the build when true):

```markdown
---
title: Getting Started
route: /guide
draft: false
---

# Getting Started
...
```

### Markdown support

Standard constructs, each mapped onto an existing IR node -- no new
schema entries for any of these:

| Markdown | IR node(s) |
| --- | --- |
| `#` ... `######` | `Heading(level=1..6)` |
| paragraph | `Text` |
| `**bold**`, `*italic*` | `Strong`, `Em` |
| `[text](url)` | `Link` |
| `- item` / `1. item` | `List`/`Item`, `OrderedList`/`Item` |
| `![alt](src)` | `Image` (local `src` resolved against `assets/`) |
| ` ```lang `  fenced block | `Pre(Code(...))` |
| `> quote` | `Blockquote` |
| `\| a \| b \|` tables | `Table`/`TableHead`/`TableBody`/`TableRow`/`TableHeaderCell`/`TableCell` |
| `---` | `HorizontalRule` |

Local references (a relative image `src`, a relative link `href`) are
resolved during the build against `assets/` and the discovered route
table, through the same `asset_check`/`link_check` machinery that
already walks Python-authored pages -- a broken Markdown image
reference should fail the build exactly the way
`Link(href="/typo")` already does, not silently emit a dead link.
Missing assets, invalid front matter, and duplicate routes (two
sources claiming the same path -- a Markdown file and a `@site.page`
decorator, or two Markdown files after front-matter overrides) are
diagnostics, not warnings: actionable, with a file and a line where
that's meaningful, the same register the table in the skill's
"Debugging checklist" is written in.

### Compilation

```
Markdown (content/*.md)
    -> Parse (recognizer extracted/adapted from arklight.cli.mdrender)
    -> ARKNode tree, built from arklight.api's existing components
    -> arklight.ir (the same schema + validate + normalize + build stages every page already goes through)
    -> arklight.backend (html/css/js, unchanged)
    -> Static output
```

No separate HTML renderer, no duplicate compiler pipeline, no
browser-side Markdown runtime. Parsing happens once, at build time, on
the machine running `arklight build` -- the output is static HTML like
everything else ARKlight produces, and a visitor's browser never sees
Markdown source or a Markdown parser. Where `mdrender.py`'s current
recognizer is reusable as-is (headings, emphasis, fenced code, lists,
links, tables, rules) it is adapted rather than rewritten; the IR
schema is extended only where Markdown needs something the ANSI
renderer never had to represent (front matter, in particular, which
has no terminal-rendering analog).

### Presentation

Three built-in presets, selected in `site.py`, no custom CSS required
for any of them:

- **`light`**: clean, general-purpose presentation -- ARKlight's
  existing default stylesheet posture (`arklight.backend.css.
  base_stylesheet.BASE_CSS_BODY`), tuned for a content site rather
  than restyled from scratch.
- **`dark`**: modeled directly on the palette `arklight/cli/
  mdrender.py` already ships for ANSI terminal output, not a new color
  story -- the same warm clay/terracotta accent on a neutral dark
  ground: `#cc785c` (the module's heading-1 / bullet / table-header
  clay, `\x1b[38;2;204;120;92m`) as the primary accent and link color,
  `#c4946b` (heading-2 warm tan) and `#a69780` (heading-3 muted taupe,
  also the blockquote color) for secondary text, `#d6a373` for inline
  code, `#828282` for table borders/rules, against a near-black,
  warm-tinted background rather than a pure `#000` -- so a reader who
  knows ARKlight's docs from the terminal sees the same palette on the
  web.
- **`reading`**: warm colors, a restrained interface, and typography
  sized for long-form content (a narrower measure, larger line-height)
  -- its own design, not modeled on anything that exists today.

All three share one semantic structure and ARKlight's existing
intrinsic layout system (`arklight/backend/css`) -- no second layout
engine, no preset-specific breakpoint rules. Navigation, the page
shell, and the footer derive from `site.py` configuration and the
discovered `content/` tree, exactly as `nav()` is hand-written in
today's `simple` template (`arklight/cli/templates/simple.py`) --
except generated rather than hand-written, with the same places open
for a user to override the generated default.

### Constraints

- Existing Python authoring and compiler behavior is unchanged. A
  `simple`/`production` project with no `content/` directory never
  invokes any of this.
- No Node.js or npm -- consistent with `mdrender.py`'s own
  zero-runtime-dependency rule.
- Markdown is content, never executable source -- no inline script
  execution, no arbitrary HTML passthrough by default.
- A raw-HTML security policy is defined and enforced: raw HTML blocks
  embedded in a Markdown file (an explicit non-goal to render as
  arbitrary trusted HTML) are either stripped, escaped, or routed
  through a narrow allow-listed subset -- which of the three is an open
  question below, not settled by this proposal.
- Builds stay deterministic; routes and local references are
  validated the same way Python-authored pages already are.
- Advanced customization stays inside existing ARKlight APIs
  (`Site(...)` kwargs, `site.style(...)`/`site.style_selector(...)`,
  the registered experimental features in `arklight/experimental.py`)
  -- no new escape hatch invented just for Markdown.
- **User-defined styling is out of scope for this version.** The three
  presets are the whole surface this proposal promises: no per-site
  custom CSS injection point for Markdown content, no preset
  extension API, no fourth preset. That is a later proposal's problem,
  not this one's -- scope creep here is the thing most likely to sink
  it.

## Acceptance criteria

1. Both layouts (`markdown-simple`, `markdown-production`) build
   successfully from a fresh `arklight new` scaffold.
2. Markdown pages compile through the existing `IR -> backend`
   pipeline -- no second renderer runs in production output.
3. Every construct in the Markdown-support table above renders
   correctly.
4. Navigation, footer, and preset are configurable through `site.py`.
5. All three presets (`light`, `dark`, `reading`) work with zero
   custom CSS.
6. Local assets (images, fenced-block-adjacent files) resolve
   correctly in generated output, and a missing one fails the build
   with an actionable diagnostic.
7. Invalid content -- bad front matter, a duplicate route, a missing
   asset -- produces a diagnostic, not a silent gap or a crash with a
   bare traceback.
8. Existing Python-authored `simple`/`production` projects are
   unaffected: no behavior change with no `content/` directory
   present.

## Open questions

**Q1. Where does filesystem discovery live relative to
`arklight.parser.discover`?** Today's discovery is AST-only, against
the entry file, before user code runs (gotcha #3 territory). Scanning
`content/` is a different kind of discovery -- against the filesystem,
and it has to happen *before* IR build but doesn't need `ast.parse` at
all. Does it become a sibling stage in `arklight/compiler/pipeline.py`,
or a preprocessing step that runs before `load_site` and hands
`discover` a synthesized set of pages?

**Q2. What exactly triggers Markdown discovery?** Presence of a
`content/` directory next to `site.py`, an explicit
`site.markdown_dir(...)`-style call, or something declared in
`arklight.config.py`? The sketch that prompted this proposal used
bare `@site.markdown("/route")` decorators mapping routes to specific
files -- that's a third option (explicit per-file registration, no
directory scan at all) worth weighing against directory discovery:
explicit registration keeps `discover`'s "AST-only, entry-file-only"
invariant perfectly intact at the cost of writing one line per page,
exactly the manual step this proposal is otherwise trying to remove.

**Q3. Front matter format.** "YAML-ish" is a placeholder, not a
decision -- full YAML pulls in a parser this project has deliberately
avoided everywhere else (`mdrender.py`'s own stated reason for not
taking a Markdown dependency applies here too). A restricted
`key: value` subset, parsed with the standard library, is the more
consistent choice; whether it is permissive enough for real use needs
checking against whatever front matter actual users write.

**Q4. The raw-HTML security policy's actual shape.** "Define and
enforce" is a constraint, not a design. Three real options: strip raw
HTML entirely, escape it to visible text, or allow a narrow tag
allow-list (closer to what GitHub-flavored Markdown does). This
interacts with ARKlight's no-`eval`/no-arbitrary-JS stance
(`docs/Foundational/`, the experimental-features table in the
`arklight-skill-collections` skill) closely enough that it probably
needs its own short decision record rather than a paragraph buried
here.

**Q5. `dark`'s exact ground color.** The accent and text colors above
come directly off `mdrender.py`'s `_HEADING_COLORS`/`_CODE_COLOR`/
etc. The background itself has no terminal analog (a terminal's
background is whatever the user's terminal theme already is) --
"near-black, warm-tinted" is a placeholder description, not a chosen
hex value, and should be picked to keep the clay/tan/taupe accents at
a comfortable contrast ratio rather than copied from the terminal
palette by accident.

**Q6. Duplicate-route collision between a Markdown page and a
`@site.page(...)` route.** Build error, or does one take precedence?
Given `discover`'s existing "no pages registered" / collision-shaped
errors, an error is the more consistent answer, but this proposal
doesn't settle it.

**Q7. `production`'s `pages/` vs. `content/`.** `markdown-production`
lists both `pages/` (presumably Python-authored pages, per today's
`production` template) and `content/` (Markdown). Is mixing the two
in one project the intended steady state, or is `markdown-production`
meant for Markdown-only projects that happen to want the
`components/`-split layout? If mixed, Q6's collision rule is load-
bearing, not an edge case.

## If accepted -- a sketch, not a commitment

- A Markdown-to-IR module, built by extracting and adapting
  `arklight/cli/mdrender.py`'s recognizers to target
  `arklight.ir.components`/`arklight.api` node construction instead of
  ANSI strings -- `mdrender.py` itself stays as-is for
  `arklight search --retrieve-doc`, which still wants terminal output,
  not IR.
- Front-matter parsing, kept inside the Python standard library per
  Q3.
- A discovery step per Q1/Q2's answer, feeding synthesized pages into
  the same `IR -> backend` stages every page already goes through.
- `markdown-simple`/`markdown-production` entries in
  `arklight.cli.templates.TEMPLATES`, following `simple.py`/
  `production.py`'s existing `build(name) -> dict[str, str]` shape.
- `light`/`dark`/`reading` as preset stylesheets layered on
  `arklight.backend.css`'s existing intrinsic layout system -- no new
  layout engine, no breakpoint rules beyond what already exists.
- The raw-HTML policy from Q4, enforced in whichever IR-build stage
  ends up owning it, with a short decision record of its own.
- `AUTHORING-GUIDE.md` and tests, following the pattern the Markdown-
  support proposal pointed at for the preamble work. Nothing staged;
  this would graduate to `docs/Foundational/`/`docs/Implementation/`
  only once accepted, per `docs/Proposals/README.md`'s own graduation
  path.

## Not in scope

- User-defined/custom styling for Markdown content, or a fourth preset
  -- explicitly deferred, not promised by this version (see
  Constraints).
- MDX, embedded component invocation inside Markdown, or any authoring
  mode that makes Markdown executable -- Markdown stays content, never
  source, per the Constraints above.
- Changes to `simple`/`production` (the existing, non-Markdown
  templates) beyond the registry gaining two new siblings.
- A general raw-HTML-passthrough escape hatch beyond whatever Q4
  settles on.
