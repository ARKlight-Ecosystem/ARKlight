# Version history

## Overview

This directory is the **user-facing** record of ARKlight's `alpha`
milestones -- a short overview of each shipped version's feature set,
meant for someone deciding whether to build against a given point in
`alpha` or looking up what changed, without wading through internal
implementation notes.

It's deliberately separate from the **changelog** and **progress
log**, both of which are internal/dev-facing and live at the repo
root: [`CHANGELOG.md`](../../CHANGELOG.md) is the plain,
Keep-a-Changelog-style version log (exact files touched, rationale for
each decision, what was deliberately deferred and why);
[`PROGRESS.md`](../../PROGRESS.md) is the narrative record of what was
tried, what was rejected, and what broke along the way, kept in
reverse-chronological order -- its Snapshot table at the top is the
fastest way to see what's DONE / IN PROGRESS / PLANNED right now. The
docs in this directory are the distilled, user-facing version of that
history for everyone else.

For the architecture-level roadmap (the numbered `v0.0xx` milestone
table itself, independent of what's landed so far), see
[`docs/Foundational/ARCHITECTURE.md`](../Foundational/ARCHITECTURE.md).

## Why this directory looks different from `main`'s

`main` has its own `docs/version history/` directory, and it is **not**
a copy of this one -- the two branches keep bookkeeping differently on
purpose (see `docs/README.md` and `docs/Foundational/DESIGN-NOTES.md`
for why `alpha` and `main` diverge at all). Two concrete differences
worth knowing before adding a file here:

- **Version numbering.** `main` moved to a `MAJOR.MINOR.PATCH` format
  starting at its `0.54.0` "alpha catch-up" release (see `main`'s
  `docs/version history/v0.54.0.md`) and bundles everything `alpha`
  shipped up to that point into that one release note. `alpha` never
  adopted that format -- it stays on the plain milestone scheme
  `docs/Foundational/ARCHITECTURE.md`'s roadmap table already uses
  (`v0.001`, `v0.0035`, `v0.060`, ...), including this directory's own
  file names.
- **Granularity.** `alpha` ships and tracks individual *sub-stages*
  within a milestone (`vdom-1` through `vdom-8` feeding `v0.054`;
  `v0.060-stage0` opening `v0.060`; the Android/Desktop backends'
  numbered stage ladders) -- see `PROGRESS.md`'s Snapshot table for
  the full list. This directory does **not** add one file per
  sub-stage; a milestone gets a single file here once it (or its
  currently-landed portion) is a coherent, user-facing thing to
  describe, the same "distilled overview, not a line-by-line diff"
  rule `main`'s own README states. Sub-stage detail stays in
  `PROGRESS.md`/`CHANGELOG.md`, where it already lives.

## Index

| Version | Covers |
| --- | --- |
| [`v0.001.md`](./v0.001.md) | Python -> HTML -- the first working compiler pipeline. |
| [`v0.002.md`](./v0.002.md) | CSS -- default stylesheet backend. |
| [`v0.003.md`](./v0.003.md) | JavaScript helpers + two vocabulary addenda -- closed-behavior JS backend. |
| [`v0.0035.md`](./v0.0035.md) | Stateful JS -- `State`/`Bind`/`Action.*` primitives. |
| [`v0.004a.md`](./v0.004a.md) | CLI scaffolding -- `arklight new <n> --template simple\|production`. |
| [`v0.036.md`](./v0.036.md) | ARK Bundle spec v1 -- `arklight pack`. |
| [`v0.037.md`](./v0.037.md) | Sealed ARK Bundles -- encrypted by default, `arklight unpack`. |
| [`v0.041.md`](./v0.041.md) | CLI/pipeline/JS runtime hardening + stateful JS vocabulary addenda I & II. |
| [`v0.042.md`](./v0.042.md) | Extra CSS features -- `Site.style(...)` custom classes, `arklight search`, `arklight --help`. |
| [`v0.0431.md`](./v0.0431.md) | Emergency patch -- build-time warning for unrouted `srcset`/`poster`/`action`/`formaction`. |
| [`v0.048.md`](./v0.048.md) | CSS `@media` queries + structured `<head>`/`<header>` extension. |
| [`v0.054.md`](./v0.054.md) | JS backend capability expansion (reactive core) -- rolls up all 8 `vdom-N` staging sub-stages. |
| [`v0.060-stage0.md`](./v0.060-stage0.md) | User-defined, reusable components -- Stage 0 (registration, Option A macro expansion, experimental Option B selector). Milestone `v0.060` shipped in full, Stages 0-4 -- see `v0.060.md` for the rollup; this file covers only what Stage 0 shipped. |
| [`v0.060.md`](./v0.060.md) | User-defined, reusable components -- full milestone rollup (Stages 0-4: registration/props, typo diagnostics, default styling, per-backend rendering, component-owned state). |

Not yet covered here: `v0.080` (Android) and `v0.100` (Desktop) are
both still IN PROGRESS with no fully-landed user-facing milestone to
summarize yet -- see their own staged-implementation docs
(`docs/Backends/ANDROID-BACKEND-IMPLEMENTATION.md`,
`docs/Backends/DESKTOP-BACKEND-IMPLEMENTATION.md`) and `PROGRESS.md`'s
Snapshot table for their current per-stage status instead.

## Adding a new version

When a milestone (or a milestone's first user-facing-complete stage)
ships, add a new `vX.Y[-stageN].md` file here with a short,
user-facing summary of what shipped -- what a reader would actually
want to know, not a line-by-line diff -- and add a row for it to the
Index table above. The detailed, internal entry still goes in the root
[`CHANGELOG.md`](../../CHANGELOG.md); this directory should never
accumulate changelog-style detail itself. Use the milestone's plain
`alpha` version string as the file name (`v0.060-stage0.md`, not
`v0.60.0.md`) -- see "Why this directory looks different from `main`'s"
above.
