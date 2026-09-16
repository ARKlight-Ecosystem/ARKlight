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

## This directory is a set: exactly one file per version

At any given time, at most one `.md` file here may exist for a given
version string. A version that hasn't got a coherent, user-facing
thing to describe yet has **no** file -- not a placeholder, not a
partial-stage file held "just in case." When a milestone's first
user-facing-complete stage does earn an interim file (as
`v0.060-stage0.md` did for `v0.060`), that file is a placeholder for
the milestone's version slot, not an addition to it: the moment the
full milestone ships and a rollup file is written, the interim file
is deleted in the same change that adds the rollup, never left
alongside it. Two files describing the same version (an interim stage
file and its own later rollup, or any other duplicate) is always a
bug in this directory, not a valid state -- if you find one, that's
the fix: delete the superseded file, keep the one that's current, and
update the Index table to match.

## A deliberate exception: `v0.064`-`v0.078` are PLANNED, not shipped

Everything above this note is the folder's normal rule: a file here
means a milestone (or a fully-landed stage of one) actually shipped.
`v0.064.md` through `v0.078.md` are a deliberate, marked exception --
each is a forward-looking summary written while staging its respective
implementation ladder, before that stage has started. Each such file
says **PLANNED** at the top for exactly this reason, and each will be
rewritten to describe actual shipped behavior once its stage lands --
until then, treat them as the ladder's user-facing preview, not a
record.

`v0.064.md`-`v0.070.md` were written while staging
[`docs/Implementation/JS-VOCABULARY-ADDENDUM-v0.070.md`](../Implementation/JS-VOCABULARY-ADDENDUM-v0.070.md).
`v0.061.md`-`v0.063.md` were the first three rungs of that same
ladder and have since shipped (see their own files, no longer marked
PLANNED) -- proof the exception is meant to be temporary per-file, not
a standing status for the whole range.

`v0.071.md`-`v0.078.md` were written while staging
[`docs/Implementation/PROJECT-KNOWLEDGE-ADDENDUM.md`](../Implementation/PROJECT-KNOWLEDGE-ADDENDUM.md)
(the eight-rung Project Knowledge ladder). They follow exactly the
same convention.

`v0.080`/`v0.100` below deliberately do **not** get this treatment
yet, because neither has a finished, rung-by-rung staged plan the
way the JS vocabulary addendum and Project Knowledge addendum now do;
once one gets a comparable `docs/Implementation/` (or `docs/Backends/`)
ladder, the same PLANNED-entry treatment can apply to it too.

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
| [`v0.060.md`](./v0.060.md) | User-defined, reusable components -- full milestone rollup (Stages 0-4: registration/props, typo diagnostics, default styling, per-backend rendering, component-owned state). Landed first as an interim `v0.060-stage0.md` covering only Stage 0; once Stages 1-4 shipped and this rollup was written, the interim file was removed per the one-file-per-version rule below. |
| [`v0.061.md`](./v0.061.md) | JS vocabulary addendum, stage 1/10 -- math siblings (`subtract`/`divide`/`min`/`max`). |
| [`v0.062.md`](./v0.062.md) | JS vocabulary addendum, stage 2/10 -- string-casing sibling + comparison `Show` predicates. |
| [`v0.063.md`](./v0.063.md) | JS vocabulary addendum, stage 3/10 -- small new runtime primitives (`reveal`, debounced binding, clipboard paste, geolocation, `matchMedia`). |
| [`v0.064.md`](./v0.064.md) | **PLANNED.** JS vocabulary addendum, stage 4/10 -- math derivations catalog. |
| [`v0.065.md`](./v0.065.md) | **PLANNED.** JS vocabulary addendum, stage 5/10 -- string derivations catalog. |
| [`v0.066.md`](./v0.066.md) | **PLANNED.** JS vocabulary addendum, stage 6/10 -- predicates catalog. |
| [`v0.067.md`](./v0.067.md) | **PLANNED.** JS vocabulary addendum, stage 7/10 -- list-scalar derivations catalog. |
| [`v0.068.md`](./v0.068.md) | **PLANNED.** JS vocabulary addendum, stage 8/10 -- cross-language numeric batteries (`lerp`, `midpoint`, saturating arithmetic, `value_or`/`first_present`). |
| [`v0.069.md`](./v0.069.md) | **PLANNED.** JS vocabulary addendum, stage 9/10 -- cross-language formatting/case batteries (`humanize_*`, `to_ordinal`, case converters). |
| [`v0.070.md`](./v0.070.md) | **PLANNED.** JS vocabulary addendum, stage 10/10 (capstone) -- `pluralize` + `random_int`, the two entries needing an explicit design exception. |
| [`v0.071.md`](./v0.071.md) | **PLANNED.** Project Knowledge, stage 1/8 -- `.arklight/` foundation: detect-or-create the directory, establish the knowledge-format marker, safe read/write helpers. |
| [`v0.072.md`](./v0.072.md) | **PLANNED.** Project Knowledge, stage 2/8 -- internal Project Knowledge context abstraction (providers/facts/observations separation) with no external provider wired in yet. |
| [`v0.073.md`](./v0.073.md) | **PLANNED.** Project Knowledge, stage 3/8 -- Git as the first concrete provider: repository identity, working-tree state, graceful no-`.git/` handling. Read-only; nothing persisted yet. |
| [`v0.074.md`](./v0.074.md) | **PLANNED.** Project Knowledge, stage 4/8 -- persistent project context: write derived Git facts into `.arklight/`, preserve them once `.git/` is gone. |
| [`v0.075.md`](./v0.075.md) | **PLANNED.** Project Knowledge, stage 5/8 -- compiler build history: record build results, associate with source identity, store compiler version and timestamp. |
| [`v0.076.md`](./v0.076.md) | **PLANNED.** Project Knowledge, stage 6/8 -- diagnostics integration: surface compact project knowledge in compiler errors, last-known-good info, verbose detail behind debug flag. |
| [`v0.077.md`](./v0.077.md) | **PLANNED.** Project Knowledge, stage 7/8 -- historical observations: compare build states, identify last-successful and first-failing revisions, correlate repository changes with build transitions. |
| [`v0.078.md`](./v0.078.md) | **PLANNED.** Project Knowledge, stage 8/8 (capstone, open slot) -- reserved for future knowledge providers, added only when a concrete compiler feature actually needs one. |

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
`v0.60.0.md`) -- and remember "This directory is a set" above: if
`vX.Y-stageN.md` is standing in for `vX.Y.md` before the full
milestone lands, delete it and update the Index row in the same
change that later adds the real `vX.Y.md` rollup, rather than leaving
both on disk -- see "Why this directory looks different from `main`'s"
above.
