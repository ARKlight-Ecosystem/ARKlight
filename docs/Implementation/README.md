# Implementation

## Overview

Staged implementation plans for proposals that have already been
**accepted** -- turned from "should we?" into "here's the landing
order." A file here is a trackable stage ladder for work that's
going to happen (or has just happened), so accepted work has a home
instead of living informally in `PROGRESS.md`.

## Where this sits between an idea and a settled record

Three different states of a piece of design work, three different
places:

- **An open proposal** -- *unsettled*. Nobody has decided yet. Proposals
  are working references and are not carried on `main`.
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

## What belongs here

- A staged rung-by-rung implementation ladder for a proposal a
  maintainer has accepted, for work that shipped on `main` or is about
  to.

## What doesn't

- An idea nobody has committed to yet.
- A permanent design decision already shipped -- that's
  `docs/Foundational/`, or a plain `docs/version history/` entry if
  it's just a feature summary rather than a design rationale.

## Index

| File | Covers |
| --- | --- |
| [`JS-VOCABULARY-ADDENDUM-v0.070.md`](JS-VOCABULARY-ADDENDUM-v0.070.md) | Staged, ten-rung (`v0.061`-`v0.070`) implementation ladder for the philosophy-compliant parts of the JS vocabulary expansion (Tier 1, Tier 2, and the exhaustive scalar catalog) -- easiest additions first, the two entries needing an explicit design exception last. |
| [`SEARCH-KNOWLEDGE-STATE-AND-KEYWORDS-ADDENDUM.md`](SEARCH-KNOWLEDGE-STATE-AND-KEYWORDS-ADDENDUM.md) | Capability fix to `arklight.search.knowledge.build_knowledge_base()` and `arklight.cli.search`: adds the `State`/`Bind`/`Computed`/`Watch` reactive-state closed vocabulary and the six other closed, compiler-validated registries to the typo-tolerant search index, closing a gap where both were invisible to `arklight search`. Stage 0 (plan) and Stage 1 (implementation) SHIPPED. |
| [`PLATFORM-API-IR-ADDENDUM.md`](PLATFORM-API-IR-ADDENDUM.md) | Two-stage implementation ladder for the accepted Platform API IR -- Stage 1 (`v0.065`, Web reference implementation: architecture plus `notify`/`clipboard_write`, later `db`) SHIPPED; Stage 2 (native Android/Desktop implementations) PLANNED, unscheduled pending each backend's own maturity. |
| [`REI-LANGUAGE-ADDENDUM.md`](REI-LANGUAGE-ADDENDUM.md) | Staged, four-rung (`v0.081`-`v0.084`) implementation ladder for the accepted Rei language -- maturity gate/package skeleton/RNI first, exceptions and Platform-APIs-as-interface last; the Compute stage stays unscheduled, blocked on Open question 3. |

## Contributing

When a proposal is accepted, write its stage ladder here rather than
jumping straight to code -- add a row to the Index table above when
you do. Once every stage in a ladder here has actually shipped, roll
it up the same way `v0.054.md`/`v0.060.md` roll up their staging
sub-releases, and trim or remove the file here.
