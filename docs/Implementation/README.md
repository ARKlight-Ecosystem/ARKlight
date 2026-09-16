# Implementation

## Overview

Staged implementation plans for proposals that have already been
**accepted** -- turned from "should we?" into "here's the landing
order." A file here is a trackable stage ladder for work that's
going to happen, the same role `docs/Backends/ANDROID-BACKEND-IMPLEMENTATION.md`
already plays for the Android backend, generalized to a top-level
folder so non-backend accepted work (starting with the JS vocabulary
addendum below) has an equivalent home instead of being wedged into
`Backends/` or left informally in `PROGRESS.md`.

## Why this is separate from `docs/Proposals/` and `docs/Foundational/`

Three different states of a piece of design work, three different
folders:

- **`docs/Proposals/`** -- *unsettled*. Nobody has decided yet.
- **`docs/Implementation/`** (here) -- *accepted, not yet (fully)
  built*. A maintainer has looked at the proposal and said "yes, in
  this order" -- what's left is turning each staged rung into actual
  commits, the same way `v0.054` landed as 8 tracked `vdom-N` stages
  and `v0.060` landed as 5 tracked `stage0`-`stage4` stages before
  either got rolled up into a single `docs/version history/` entry.
- **`docs/Foundational/`** -- *settled and shipped*. Once every stage
  in a ladder here is actually done and its outcome is captured in
  `docs/version history/`/`CHANGELOG.md`, anything that's a permanent
  design decision (not just a shipped feature) graduates into
  `Foundational/`; anything that's just "here's what stage N added"
  stays as history, and the file here can be trimmed or removed.

Keeping "accepted, staged, in-flight" separate from both endpoints
means a reader can tell at a glance whether a document describes an
idea awaiting a decision, a decision awaiting execution, or a
decision already executed -- without reading the whole file to find
out which.

## What belongs here

- A staged rung-by-rung implementation ladder for a proposal a
  maintainer has accepted, in the same spirit as
  `ANDROID-BACKEND-IMPLEMENTATION.md`/`DESKTOP-BACKEND-IMPLEMENTATION.md`
  -- but for accepted work that isn't specifically a packaging
  backend, so it doesn't naturally belong under `docs/Backends/`.

## What doesn't

- An idea nobody has committed to yet -- that's `docs/Proposals/`.
- A backend-specific staged plan -- those stay in `docs/Backends/`
  alongside that backend's own proposal doc, for locality.
- A permanent design decision already shipped -- that's
  `docs/Foundational/`, or a plain `docs/version history/` entry if
  it's just a feature summary rather than a design rationale.

## Index

| File | Covers |
| --- | --- |
| [`JS-VOCABULARY-ADDENDUM-v0.070.md`](JS-VOCABULARY-ADDENDUM-v0.070.md) | Staged, ten-rung (`v0.061`-`v0.070`) implementation ladder for the philosophy-compliant parts of `docs/Proposals/JS-VOCABULARY-EXPANSION-PROPOSAL.md` (Tier 1, Tier 2, and the exhaustive §6 scalar catalog) -- easiest additions first, the two entries needing an explicit design exception last. |
| [`PROJECT-KNOWLEDGE-ADDENDUM.md`](PROJECT-KNOWLEDGE-ADDENDUM.md) | Staged, eight-rung (`v0.071`-`v0.078`) implementation ladder for the accepted `docs/Proposals/PROJECT-KNOWELEDGE-PROPOSAL.md` -- `.arklight/` directory foundation first, future-provider open slot last. Follows the proposal's own §19 \"Suggested order\" exactly, one version per stage. |

## Contributing

If a proposal under `docs/Proposals/` gets accepted, write its stage
ladder here rather than jumping straight to code -- add a row to the
Index table above when you do. Once every stage in a ladder here has
actually shipped, roll it up the same way `v0.054.md`/`v0.060.md`
roll up their staging sub-releases, and trim or remove the file here.
