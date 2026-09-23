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

## This directory does not carry PLANNED entries -- `ARCHITECTURE.md`'s roadmap does

This directory is retrospective only: a file here means a milestone
(or a fully-landed stage of one) actually shipped, full stop. A
not-yet-shipped version being staged or merely proposed already has
its home -- the Milestones table in
[`docs/Foundational/ARCHITECTURE.md`](../Foundational/ARCHITECTURE.md)
carries every version, DONE or PLANNED, and `docs/Implementation/`
(or `docs/Backends/`) carries the rung-by-rung staging ladder once one
exists. Neither of those needs a matching preview file here, and this
directory shouldn't grow one: the same version's status would then
have two places to update instead of one, and a rollup file here --
whose only job is to tell a reader "this shipped, here's what it
does" -- would stop reliably meaning that the moment it's allowed to
also mean "this is planned to eventually do this."

`v0.065.md` through `v0.078.md` currently violate this: each is a
forward-looking, **PLANNED**-marked summary written while staging its
respective implementation ladder, before that stage had started. They
predate this rule rather than following it, and per "This directory
is a set" above they're still a bug worth fixing -- each should be
rewritten to describe actual shipped behavior once its stage lands
(as `v0.061.md`-`v0.063.md` already were once their stages shipped,
and `v0.064.md` now has been for its shipped `--retrieve-doc` half --
see that file's own status note for how a milestone slot with two
independently-staged pieces is handled when only one has shipped),
not carried forward as a pattern. Nothing needs to move to fix this
note itself: the point is that no *new* forward-looking file should
be added here for `v0.080`, `v0.100`, or anything after -- their
roadmap status belongs in `ARCHITECTURE.md`'s Milestones table alone.

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
| [`v0.064.md`](./v0.064.md) | `arklight search --retrieve-doc` -- doc-tree retrieval mode on the existing `search` subcommand. **Shipped.** Also carries JS vocabulary addendum stage 4/10, the math derivations catalog (21 `Derive.*` kinds), which landed later as `0.06509`. |
| [`v0.0641.md`](./v0.0641.md) | Emergency patch -- `State(..., query=..., history=...)`, URL query-parameter state as a primitive. |
| [`v0.065.md`](./v0.065.md) | All four pieces have **shipped**: `Provider`, stage 1/6 (the contract itself -- `Provider.declare(...)`, `Site(provider=...)`, the gated `provider-integration` feature; shipped as `0.06514`), JS vocabulary addendum, stage 5/10 (string derivations catalog, 18 `Derive.*` kinds, shipped as `0.06513`), Rei, the compiler narrator (`arklight build --narrate` + `rei.default_mode`, shipped as `0.06510`) and Platform API IR, stage 1/2 (Web reference implementation -- `PlatformAPI.notify`/`.clipboard_write`) -- see that file's own status note for how this milestone slot's four independently-staged pieces are tracked. |
| [`v0.06515.md`](./v0.06515.md) | `arklight deploy` -- the deployment CLI: builds the site, then hands it to Wrangler to deploy on Cloudflare Workers. Out-of-band, alpha-only so far. |
| [`v0.066.md`](./v0.066.md) | **DONE -- package version `0.066`.** `Provider`, stage 2/6 -- IR/`validate.py` integration: a declared Provider threaded through `WebsiteIR`, closed-vocabulary capability validation at build time. **Shipped as `0.06516`.** JS vocabulary addendum, stage 6/10 -- predicates catalog, 8 new `Predicate.*` kinds (`and_`/`or_`/`not_`, `in_range`, `one_of`, `is_empty`/`is_not_empty`, `is_null`) -- **shipped as `0.06517`**, so both pieces are done. |
| [`v0.067.md`](./v0.067.md) | **DONE -- package version `0.06612`.** `Provider`, stage 3/6 -- JS backend emission: a read-only `window.ARKLIGHT_PROVIDER` config object (name + capabilities) in `arklight.js`, no networking/vendor code generated. **Shipped as `0.06518`.** JS vocabulary addendum, stage 7/10 -- list-scalar derivations catalog, 9 new `Derive.*` kinds (`list_length`, `list_min`/`list_max`/`list_average`, `list_first`/`list_last`, `list_includes`, `list_any`/`list_all`) -- **shipped as `0.06612`**, so both pieces are done. |
| [`v0.068.md`](./v0.068.md) | **PLANNED.** JS vocabulary addendum, stage 8/10 -- cross-language numeric batteries (`lerp`, `midpoint`, saturating arithmetic, `value_or`/`first_present`). Plus `Provider`, stage 4/6 -- an authored external-`<script src>` primitive, resolving the proposal's own §7 open question about how a concrete vendor SDK actually loads. |
| [`v0.069.md`](./v0.069.md) | **PLANNED.** JS vocabulary addendum, stage 9/10 -- cross-language formatting/case batteries (`humanize_*`, `to_ordinal`, case converters). Plus `Provider`, stage 5/6 -- `arklight search` schema-lookup support for a registered Provider's capability contract. |
| [`v0.070.md`](./v0.070.md) | **PLANNED.** JS vocabulary addendum, stage 10/10 (capstone) -- `pluralize` + `random_int`, the two entries needing an explicit design exception. Plus `Provider`, stage 6/6 (capstone) -- finalizing the closed capability enum and documenting the full landed contract. |
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

A version being planned, staged, or merely renumbered is not a reason
to add a file here -- record that in `ARCHITECTURE.md`'s Milestones
table (and a `docs/Implementation/`/`docs/Backends/` ladder, if one
exists) instead, per the rule above. Only when a milestone (or a
milestone's first user-facing-complete stage) actually **ships**, add
a new `vX.Y[-stageN].md` file here with a short,
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
