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
| [`ARKLIGHT-ASSISTANT-CLI-PROPOSAL.md`](ARKLIGHT-ASSISTANT-CLI-PROPOSAL.md) | Proposal for an `arklight assistant` subcommand: a read-only, doc-grounded CLI companion ("Raeliana") woken with `--wake-up-raeliana`, an exploratory, tool-using companion ("Miko") woken with `--wake-up-miko`, plus a separate, opt-in, off-by-default `--activate-memory` flag for cross-session recall. **Partially accepted, per its appended sequencing amendment:** Miko's doc-only Stage A is staged as `v0.079`, an experimental CLI feature wrapping the already-shipped `v0.064` doc retrieval, permanence undecided until `v0.080` ships; Raeliana's implementation is not authorized -- `--wake-up-raeliana` currently only logs her proposal stage -- until Miko's dogfooding period trips the amendment's trigger condition. |
| [`PROJECT-KNOWELEDGE-PROPOSAL.md`](PROJECT-KNOWELEDGE-PROPOSAL.md) | Proposal for a compiler-owned `.arklight/` project-local knowledge directory: a providers/facts/observations model, Git as the first knowledge provider, and persistence of derived knowledge across builds. **Accepted -- staged as an eight-rung ladder (`v0.071`-`v0.078`) in [`docs/Implementation/PROJECT-KNOWLEDGE-ADDENDUM.md`](../Implementation/PROJECT-KNOWLEDGE-ADDENDUM.md).** |
| [`SEARCH-RETRIEVE-DOC-PROPOSAL.md`](SEARCH-RETRIEVE-DOC-PROPOSAL.md) | Proposal for `arklight search --retrieve-doc`: a doc-tree retrieval mode for the existing `search` subcommand -- bare/`index` prints the root `docs/README.md`, a directory flag (`--foundational`, `--proposals`, ...) prints that folder's own index, and adding `--file NAME` appends one file's full contents, all read-only and unsynthesized. **Accepted -- staged in [`docs/Implementation/SEARCH-RETRIEVE-DOC-ADDENDUM.md`](../Implementation/SEARCH-RETRIEVE-DOC-ADDENDUM.md), sharing `v0.064` with JS vocabulary addendum stage 4.** |
| [`PROVIDER-SDK-PROPOSAL.md`](PROVIDER-SDK-PROPOSAL.md) | Proposal for `Provider`, an experimental, barebones interface for a site to declare it talks to an external service (Firebase, a hand-rolled API, ...) at runtime -- named to avoid colliding with the existing output-target meaning of "backend." ARKlight ships only the closed contract and validates/gates it; no vendor SDK, networking, or auth logic lives in core. **Accepted -- staged as a six-rung ladder (`v0.065`-`v0.070`) in [`docs/Implementation/PROVIDER-SDK-ADDENDUM.md`](../Implementation/PROVIDER-SDK-ADDENDUM.md), interleaved with JS vocabulary addendum stages 5-10.** |
| [`REI-COMPILER-NARRATOR-PROPOSAL.md`](REI-COMPILER-NARRATOR-PROPOSAL.md) | Proposal for Rei, ARKlight's compiler narrator: an opt-in `--narrate` flag on `arklight build` (sibling to `--verbose`/`--debug`) that narrates the same pipeline stages in natural language instead of `[ARKlight] ...` lines, plus a `rei` config section for a project-wide default log mode. Pure Python, deterministic, no JSON, no LLM -- a classic ELIZA implementation is studied as a design reference only, not used at runtime. Deliberately narrower than an earlier, unfiled draft (no event bus, no diagnostic redesign, no `arklight explain <event-id>`). **Accepted -- staged in [`docs/Implementation/REI-COMPILER-NARRATOR-ADDENDUM.md`](../Implementation/REI-COMPILER-NARRATOR-ADDENDUM.md), interleaved into `v0.065` as a third piece alongside JS vocabulary addendum stage 5 and `Provider` stage 1.** |
| [`RUNTIME-ERROR-HANDLING-PROPOSAL.md`](RUNTIME-ERROR-HANDLING-PROPOSAL.md) | Proposal to close the gap left by `CHANGELOG.md`'s `[0.041] -- JS runtime error-handling hardening` pass: five stateful primitives shipped since then (`Computed`, `Repeat`, `Show`, `bind_value`, watchers) with no equivalent audit, several with zero exception handling. Proposes per-element guards matching v0.041's own discipline, a default page-level `error`/`unhandledrejection` boundary, and a closed `ARKLIGHT_ON_ERROR` override hook a site author can supply. |
| [`PLATFORM-API-IR-PROPOSAL.md`](PLATFORM-API-IR-PROPOSAL.md) | Proposal for a **platform API interface layer in the compiler IR**: platform-facing capabilities (notifications, clipboard, filesystem, device info, ...) represented as backend-independent, versioned interfaces the compiler owns, with Web as the default implementation and Android/Desktop earning individual interfaces only once their backend is mature enough to support them. Deliberately framed as an IR/interface layer rather than "a backend," borrows Capacitor's Web-first/native-extension shape without adopting its plugin-runtime model, and draws an explicit line against `Provider` (external-service abstraction) and against any generic native-code escape hatch. **Not yet accepted -- filed as the next capability gap in `docs/Foundational/WHAT-ARKLIGHT-IS.md`'s `v0.0642` revision.** |

## Contributing

If you add a new proposal, add a row for it in the table above. When
a proposal is accepted, move its content to the appropriate permanent
or staging location and remove it from here (or leave a one-line
pointer if useful history).
