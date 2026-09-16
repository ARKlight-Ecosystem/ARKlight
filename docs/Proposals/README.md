# Proposals

## Overview

Speculative, not-yet-accepted design proposals -- ideas put forward
for review that no maintainer has committed to yet. A file lands here
when someone has done the legwork of an audit or a design sketch, but
before any decision has been made to build it, stage it, or reject
it.

## Why this is separate from `docs/Foundational/`

`docs/Foundational/` is explicitly the **permanent design record** --
"not deletable," updated in place as the project evolves, describing
decisions that have already been made and are in force today (see
`Foundational/README.md`). Everything in there is *settled*: it
explains why ARKlight already works the way it does.

Proposals are the opposite state: **unsettled**. A proposal describes
something that does *not* exist yet, may never be built as written,
and could be rejected outright once a maintainer looks at it. Filing
these next to `ARCHITECTURE.md`/`DESIGN-NOTES.md` would blur that
line -- a reader landing in `Foundational/` should be able to trust
that everything there reflects the project as it actually is, without
having to first work out which files are aspirational. Keeping
proposals in their own folder means:

- **`Foundational/`'s "permanent, not deletable" guarantee stays
  true.** A rejected proposal can simply be deleted or archived
  without that guarantee having to bend for it.
- **A proposal's status is legible from its location, not just its
  header.** Any file under `Proposals/` is, by construction, not yet
  decided -- no need to re-litigate that in every file.
- **Acceptance has a visible move, not just a label change.** When a
  proposal is accepted and built, the natural step is to move its
  content (or a rewritten version of it) into `Foundational/` (if
  it's a permanent design decision) or into `Backends/`/wherever the
  in-progress staging doc for that work lives -- the same "graduate
  out once decided" pattern `docs/README.md` already uses for
  `docs/new js backend proposal/` and `docs/Far Future Concern/`.
  `Proposals/` is one level earlier than either of those: those two
  folders hold work that's already been picked up as a direction;
  this folder holds ideas that haven't been picked up as anything
  yet.

In short: **`Foundational/` = what ARKlight is. `Backends/`/`new js
backend proposal/` = work already underway or an active fork in the
road. `Proposals/` = ideas waiting for either of those to happen to
them, or for rejection.**

## What belongs here

- Audits that end in a recommendation ("here's what's missing, here's
  what it would take to add it").
- New-feature or new-registry-entry proposals not yet scheduled
  against a version-history milestone.
- Anything explicitly framed as "proposal" that isn't already a
  staging doc for approved, in-progress work (those belong in
  `docs/Backends/` alongside `ARKLIGHT_DESKTOP_BACKEND_PROPOSAL.md`,
  which itself started as this kind of document).

## What doesn't

- Decisions already made and in force -- those belong in
  `docs/Foundational/`.
- Work actively being built or staged -- those belong in
  `docs/Backends/` or wherever the relevant in-progress doc lives.
- Version-by-version shipped-feature summaries -- those belong in
  `docs/version history/`.

## Index

| File | Covers |
| --- | --- |
| [`JS-VOCABULARY-EXPANSION-PROPOSAL.md`](JS-VOCABULARY-EXPANSION-PROPOSAL.md) | Proposal to expand the client-side JS vocabulary: the already-designed-but-unshipped trivial gaps, small new runtime primitives, an exhaustive catalog of scalar math/string/list derivations and predicates (both JS's own built-ins and cross-language "batteries included" idioms from Python/Rust/C++ standard libraries), and the larger IR-node-sized gaps (client-side data fetch, reorderable lists, sort/filter, file-upload preview) plus the out-of-scope bucket that conflicts with ARKlight's no-`eval` non-goal. |
| [`URL-STATE-AS-PRIMITIVE-PROPOSAL.md`](URL-STATE-AS-PRIMITIVE-PROPOSAL.md) | Proposal for a `State(..., query=...)` primitive extending the existing `persist=True` mechanism to cover URL query parameters -- reading, coercing, fail-open defaults, write-back via `history.replaceState`, a `popstate` listener, and an opt-in push-history modifier -- and settles which of three navigation architectures a query-param change should trigger. |
| [`ARKLIGHT-ASSISTANT-CLI-PROPOSAL.md`](ARKLIGHT-ASSISTANT-CLI-PROPOSAL.md) | Proposal for an `arklight assistant` subcommand: a read-only, doc-grounded CLI companion ("Raeliana") woken with `--wake-up-raeliana`, plus a separate, opt-in, off-by-default `--activate-memory` flag for cross-session recall, staged as two independent capabilities. |

## Contributing

If you add a new proposal, add a row for it in the table above. When
a proposal is accepted, move its content to the appropriate permanent
or staging location and remove it from here (or leave a one-line
pointer if useful history).
