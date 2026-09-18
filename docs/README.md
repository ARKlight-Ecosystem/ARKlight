# ARKlight Documentation

This folder is the documentation index for ARKlight. Start here, then
follow the links below into the subfolders for the topic you need.

## Philosophy

- **"The browser never executes Python."** (`arklight/__init__.py`) —
  output is plain HTML/CSS/vanilla JS; the compiler is the only thing
  that runs Python.
- **"No eval, no new Function, no string ever executed as code."**
  (`arklight/backend/js/render.py`, `runtime/dispatch.py`, `attrs.py`) —
  the shipped runtime never turns a string into executable code, even
  via a vendored dependency's optional feature.
- **"Fail loudly at build time, not silently in the browser."**
  (`ir/validate.py`, `config.py`, `experimental.py`) — anything wrong
  with a site should raise a `ValidationError` in Python during
  `arklight build`, never manifest as silent broken behavior after
  deployment.
- **"Only ship what's used."** (`js/htmx.py`, `js/render.py`, `attrs.py`)
  — the compiler emits the minimum HTML/CSS/JS a given site's IR
  actually needs; nothing bundled unconditionally.
- **Compiled markup should be honest about what it does** — the project
  repeatedly frames "inspectable, predictable" output as the point of
  compiling to plain HTML at all (`README.md`'s opening description).

## Folder Guide

Each subfolder now has its own `README.md` with a fuller overview and
index — the summaries below are quick pointers, not the source of
truth.

### [`docs/Foundational/`](Foundational/README.md) — permanent

The core reading for understanding how ARKlight works and why it's
built the way it is. **Not deletable** — this is the permanent design
record for the project, updated in place rather than removed.

| File | Covers |
| --- | --- |
| [`WHAT-ARKLIGHT-IS.md`](Foundational/WHAT-ARKLIGHT-IS.md) | The project's own definition of itself, opening with "The Goal" -- comparable-to-frontend-framework DX while enforcing ARKlight's own philosophy, for the Python Community and the Education Community specifically. |
| [`V1-DEFINITION.md`](Foundational/V1-DEFINITION.md) | What `v1.0 -- Stable compiler` concretely means, and its scope boundary: the Web Developing parts of the compiler only -- not native backends, not experimental features, and not ARKlight Component Collections. |
| [`ARCHITECTURE.md`](Foundational/ARCHITECTURE.md) | High-level system design: how source is parsed, compiled to IR, and rendered by a backend. |
| [`CONFIGURABILITY.md`](Foundational/CONFIGURABILITY.md) | The "reachability rule" — which fixed internal values should grow into a per-site kwarg/CLI flag vs. stay a constant. (For the `arklight.config.py` project-settings file itself, see `AUTHORING-GUIDE.md`'s "Configuration" section.) |
| [`CLI-REFERENCE.md`](Foundational/CLI-REFERENCE.md) | The implemented, shipped `arklight` CLI: every subcommand, its flags, and worked examples. |
| [`AUTHORING-GUIDE.md`](Foundational/AUTHORING-GUIDE.md) | The full public component/behavior/state API reference (moved out of the root `README.md`, which keeps only the quickstart). |
| [`DEPLOYMENT-CLI.md`](Foundational/DEPLOYMENT-CLI.md) | **Design only, not implemented.** The planned `arklight deploy` subcommand and its spec. |
| [`DESIGN-NOTES.md`](Foundational/DESIGN-NOTES.md) | Rationale and trade-offs behind key design decisions. |
| [`EXPERIMENTAL-APIS.md`](Foundational/EXPERIMENTAL-APIS.md) | APIs that are unstable or opt-in (`experimental.py`), and their stability guarantees. |
| [`SYSTEM-DESIGN-AGREEMENTS.md`](Foundational/SYSTEM-DESIGN-AGREEMENTS.md) | The "compiler first, runtime last" design agreement: which work the compiler must own vs. delegate to the target runtime, when the compiler may specialize per-target, and the four-question architecture decision rule for judging any new feature against it. |
| [`USER-DEFINED-COMPONENTS.md`](Foundational/USER-DEFINED-COMPONENTS.md) | User-defined, reusable components (v0.060, shipped in full) -- props, default styling, macro/registry modes, component-owned state, and scope boundaries. |
| [`PLATFORM-APIS.md`](Foundational/PLATFORM-APIS.md) | Settled design record for the platform API interface layer (`PlatformAPI.notify`/`.clipboard_write`, `v0.065`): terminology, compiler-owns-interface/backend-owns-implementation, Web-as-default, native-implementations-are-earned. |
| [`ACC-CAPABILITIES.md`](Foundational/ACC-CAPABILITIES.md) | Settled design record for `arklight/capabilities.py`, the ACC (ARKlight Component Collections) capability-discovery hook -- the `arklight.capabilities` entry-point contract, diagnostics, and status against ACC's own five-stage implementation ladder. |

### [`docs/Backends/`](Backends/README.md) — working reference

Design/staging docs for individual output backends. **Working
reference only** — removed once the work they describe is finished
and captured in the changelog or a Foundational doc.

| File | Covers |
| --- | --- |
| [`ANDROID-BACKEND-IMPLEMENTATION.md`](Backends/ANDROID-BACKEND-IMPLEMENTATION.md) | Staged implementation plan for the Android packaging backend. |
| [`DESKTOP-BACKEND-IMPLEMENTATION.md`](Backends/DESKTOP-BACKEND-IMPLEMENTATION.md) | Staged implementation plan for the desktop packaging backend (Linux only so far). |
| [`ARKLIGHT_DESKTOP_BACKEND_PROPOSAL.md`](Backends/ARKLIGHT_DESKTOP_BACKEND_PROPOSAL.md) | Proposal for a purpose-built native desktop host/packager (replacing Neutralino.js as the canonical desktop backend) -- now Stage 1 of `DESKTOP-BACKEND-IMPLEMENTATION.md`. |
| [`NEUTRALINO-INTEGRATION.md`](Backends/NEUTRALINO-INTEGRATION.md) | Neutralino.js desktop-app integration -- superseded plan, kept for reference only. |

### [`docs/Proposals/`](Proposals/README.md) — unsettled

Speculative design proposals not yet reviewed or accepted by a
maintainer — distinct from `Foundational/`'s settled, permanent
record and from `Backends/`'s already-underway staging docs. See the
folder's own README for the full rationale. Removed or graduated
(into `Foundational/` or a staging doc) once a decision is made.

| File | Covers |
| --- | --- |
| [`JS-VOCABULARY-EXPANSION-PROPOSAL.md`](<Proposals/JS-VOCABULARY-EXPANSION-PROPOSAL.md>) | Proposal for the client-side JS vocabulary: trivial gaps, small new primitives, an exhaustive scalar derivation/predicate catalog, and the larger client-side-fetch-sized gaps still open. |
| [`URL-STATE-AS-PRIMITIVE-PROPOSAL.md`](<Proposals/URL-STATE-AS-PRIMITIVE-PROPOSAL.md>) | Proposal for a `State(..., query=...)` primitive extending `persist=True` to cover URL query parameters, including which navigation architecture a query-param change should trigger. |
| [`ARKLIGHT-ASSISTANT-CLI-PROPOSAL.md`](<Proposals/ARKLIGHT-ASSISTANT-CLI-PROPOSAL.md>) | Proposal for an `arklight assistant` subcommand: a read-only, doc-grounded CLI companion ("Raeliana") behind `--wake-up-raeliana`, an exploratory tool-using companion ("Miko") behind `--wake-up-miko`, plus a separate opt-in `--activate-memory` flag for cross-session recall. **Partially accepted:** Miko's doc-only MVP staged as `v0.079`, an experimental CLI feature (permanence decided after `v0.080`); Raeliana not authorized -- `--wake-up-raeliana` only logs her proposal stage until Miko's dogfooding trips the amendment's trigger. |
| [`PROJECT-KNOWELEDGE-PROPOSAL.md`](<Proposals/PROJECT-KNOWELEDGE-PROPOSAL.md>) | Proposal for a compiler-owned `.arklight/` project-local knowledge directory: providers/facts/observations model, Git as the first provider, persistence across builds. **Accepted -- staged in `docs/Implementation/PROJECT-KNOWLEDGE-ADDENDUM.md` as `v0.071`-`v0.078`.** |
| [`SEARCH-RETRIEVE-DOC-PROPOSAL.md`](<Proposals/SEARCH-RETRIEVE-DOC-PROPOSAL.md>) | Proposal for `arklight search --retrieve-doc`: a doc-tree retrieval mode on the existing `search` subcommand, printing the root or a folder's `README.md` index and, with `--file NAME`, one file's full contents. **Accepted -- staged as `v0.064`, alongside JS vocabulary addendum stage 4.** |
| [`PROVIDER-SDK-PROPOSAL.md`](<Proposals/PROVIDER-SDK-PROPOSAL.md>) | Proposal for `Provider`, an experimental interface for a site to declare it talks to an external service (Firebase, a hand-rolled API, ...) at runtime -- ARKlight ships only the closed contract and validates/gates it; no vendor SDK, networking, or auth logic lives in core. **Accepted -- staged as a six-rung ladder, `v0.065`-`v0.070`.** |
| [`REI-COMPILER-NARRATOR-PROPOSAL.md`](<Proposals/REI-COMPILER-NARRATOR-PROPOSAL.md>) | Proposal for Rei, ARKlight's compiler narrator: an opt-in `--narrate` flag on `arklight build` narrating pipeline stages in natural language, plus a `rei` config section for a project-wide default log mode. Pure Python, deterministic, no JSON, no LLM. **Accepted -- interleaved into `v0.065` as a third piece, alongside JS vocabulary addendum stage 5 and `Provider` stage 1.** |
| [`RUNTIME-ERROR-HANDLING-PROPOSAL.md`](<Proposals/RUNTIME-ERROR-HANDLING-PROPOSAL.md>) | Proposal to close the gap left by `CHANGELOG.md`'s `[0.041]` JS runtime error-handling pass -- per-element guards for five stateful primitives shipped since (`Computed`, `Repeat`, `Show`, `bind_value`, watchers), a default page-level `error`/`unhandledrejection` boundary, and a closed `ARKLIGHT_ON_ERROR` override hook. |

### [`docs/Implementation/`](Implementation/README.md) — accepted, staged

Staged, rung-by-rung implementation ladders for proposals a maintainer
has already accepted -- turning "should we?" into "here's the landing
order." Sits between `docs/Proposals/`'s *unsettled* and
`docs/Foundational/`'s *settled and shipped*. See the folder's own
README for the full rationale.

| File | Covers |
| --- | --- |
| [`JS-VOCABULARY-ADDENDUM-v0.070.md`](Implementation/JS-VOCABULARY-ADDENDUM-v0.070.md) | Staged, ten-rung (`v0.061`-`v0.070`) implementation ladder for the philosophy-compliant parts of `docs/Proposals/JS-VOCABULARY-EXPANSION-PROPOSAL.md`. |
| [`PROJECT-KNOWLEDGE-ADDENDUM.md`](Implementation/PROJECT-KNOWLEDGE-ADDENDUM.md) | Staged, eight-rung (`v0.071`-`v0.078`) implementation ladder for the accepted `docs/Proposals/PROJECT-KNOWELEDGE-PROPOSAL.md` -- `.arklight/` foundation through future-provider open slot, one version per stage. |
| [`REI-COMPILER-NARRATOR-ADDENDUM.md`](Implementation/REI-COMPILER-NARRATOR-ADDENDUM.md) | Single-version (`v0.065`) implementation entry for Rei, the compiler narrator -- `--narrate` build flag, `rei` config section, first-compile introduction banner. No ladder; a third piece interleaved into `v0.065`. |

### [`docs/new js backend proposal/`](<new js backend proposal/README.md>) — working reference

Competing proposals under consideration for a redesigned JS backend.
**Working reference only** — removed once a direction is chosen.

| File | Covers |
| --- | --- |
| [`ARCHITECTURE-VDOM.md`](<new js backend proposal/ARCHITECTURE-VDOM.md>) | Proposal using a virtual DOM approach. |
| [`ARCHITECTURE no vdom.md`](<new js backend proposal/ARCHITECTURE no vdom.md>) | Alternative proposal without a virtual DOM. |

### [`docs/Far Future Concern/`](<Far Future Concern/README.md>) — working reference

Speculative/backlog material for backends that aren't a near-term
priority. **Working reference only** — cleared out if a backend is
dropped, or graduated elsewhere if it's picked up.

| File | Covers |
| --- | --- |
| [`kaios-app-design-doc.md`](<Far Future Concern/kaios-app-design-doc.md>) | Design doc for a potential KaiOS app. |
| [`KAIOS-BACKEND-IMPLEMENTATION.md`](<Far Future Concern/KAIOS-BACKEND-IMPLEMENTATION.md>) | Implementation notes for a KaiOS backend. |
| [`WINDOWS-PHONE-BACKEND.md`](<Far Future Concern/WINDOWS-PHONE-BACKEND.md>) | Notes on a (very) speculative Windows Phone backend. |

### [`docs/version history/`](<version history/README.md>) — permanent

The user-facing overview of each shipped `alpha` milestone, separate
from `CHANGELOG.md`/`PROGRESS.md`'s internal/dev-facing detail. See
that folder's own README for the full index and for how it
deliberately differs from `main`'s `docs/version history/` directory.

## Adding a new doc

Every doc file here exists to answer one kind of question, for one
kind of reader, and every fact should live in exactly one of them --
the same normalization rule `docs/version history/README.md` states
for its own directory ("exactly one file per version") applied to the
whole tree. Two checks before writing a new file or a new section:

**1. Does this fact already have a home?** Search for it first
(`grep -r` for the term, or skim the tables above). If it does, link
to that file rather than restating the fact -- copy-pasted facts drift
the moment one copy gets updated and the other doesn't (see
`docs/Foundational/ARCHITECTURE.md`'s "Why this file is short on
prose, long on links" for a worked example of a redundancy this
caused and how it was fixed). This applies to the root `README.md`
too: it's the landing page, not a second copy of anything that has a
canonical home elsewhere -- `README.md`'s own "Status" section is the
template every other section should follow (a two-line pointer, not a
restated table).

**2. Which folder matches this content's *state*?** Each folder below
is one state in the same lifecycle, in order:

| State | Folder | Leaves the folder when... |
| --- | --- | --- |
| Speculative, not proposed as work | `docs/Far Future Concern/` | A backend/idea gets picked up for real -> graduates to `docs/Backends/` or `docs/Proposals/`. |
| Proposed, not yet decided | `docs/Proposals/` | A maintainer accepts or rejects it -> graduates to `docs/Implementation/` (accepted) or is removed (rejected). |
| Accepted, staged, in-flight | `docs/Implementation/` (general work) or `docs/Backends/` (a specific backend's own staging doc, for locality) | Every stage ships -> the outcome is captured in `docs/version history/` + `CHANGELOG.md`/`PROGRESS.md`, and the staging file itself is trimmed or removed. |
| Shipped, user-facing summary | `docs/version history/` | Never -- permanent, one file per version (see that folder's own README). |
| Shipped, permanent design rationale | `docs/Foundational/` | Never -- permanent, updated in place, not deletable. |

If a new file doesn't obviously match one row, it's usually a sign the
content should be a section added to an existing file instead of a
new one -- a folder here is a *state*, not a topic, so "JS vocabulary
notes" isn't itself a reason for a new file if the content is actually
staged-and-in-flight (`docs/Implementation/`) or already-shipped-
rationale (`docs/Foundational/`) material.

**Once you know which file:** add or update the content there, then
add (or update) its row in that folder's own `README.md` index *and*
in the Folder Guide table above -- both, since a reader may land on
either README first. A file with no index row is invisible to anyone
browsing rather than searching.

**The same rule runs in reverse.** When a file's row in the lifecycle
table above says it leaves a folder -- a Proposal accepted or
rejected, an Implementation ladder's every stage shipped, a Backend's
staging doc finished, a Far Future idea dropped or graduated -- and
the file is deleted (or replaced) as a result, that deletion and
removing its index row are one change, not two: the row in that
folder's own `README.md` index *and* the row in this file's own
Folder Guide table above both come out in the same pass that deletes
the file, never left dangling for a later "docs update" commit to find
and remove. A stale row pointing at a file that no longer exists is
exactly as much a drift bug as a missing row for a file that does --
see "Why this section exists" below for what happens when this is
skipped. `docs/Foundational/` and `docs/version history/` are the only
two folders exempt from this, since (per the table above) a file
never leaves either one.

## Why this section exists: do it in one pass, not several

`git log` on this branch currently shows 56 of 204 commits (~27%) are
docs-only follow-ups to something that had already landed -- commit
messages like "Docs update", "New proposal added. index need to be
updated.", "Docs update, fix stale cli references part 1 of 2" /
"part 2 of 2", and "Docs update, finished the remaining clean up.
repo readme aged like fine milk. had to fix that." That pattern is
one feature landing, then two to four separate later commits chasing
down what the first commit should have updated already. Concrete
examples of the kind of drift that caused those follow-ups, found
still sitting in this tree:

- `docs/Implementation/README.md`'s own index lists
  `SEARCH-RETRIEVE-DOC-ADDENDUM.md` and `PROVIDER-SDK-ADDENDUM.md` --
  neither file exists on disk. (The first is a known, documented gap
  -- `docs/Foundational/ARCHITECTURE.md`'s `v0.064` row notes it was
  "never actually filed." The second has no such note; it's simply
  missing.)
- This file's own Folder Guide table for `docs/Implementation/` lists
  2 files; `docs/Implementation/README.md`'s own index lists 4. Same
  folder, two indexes, two different counts -- exactly the "a reader
  may land on either README first" problem the paragraph above this
  one exists to prevent.
- A version slot getting silently double-booked (two or three pieces
  of work assigned the same `v0.0xx` without a note explaining it) is
  the same failure in a different table -- see
  `docs/Proposals/SEARCH-RETRIEVE-DOC-PROPOSAL.md`'s and
  `docs/Proposals/REI-COMPILER-NARRATOR-PROPOSAL.md`'s own
  "version-number note, kept for history" sections for how to handle
  it *with* a note instead of silently.

None of these are hypothetical failure modes -- they're what's
actually in this tree today, left by past passes that stopped before
touching every file a change like this one touches. **A single
accepted-proposal addition (the size of this section's own change)
touches all of the following, in the same pass, not spread across
follow-up commits:**

1. The proposal file itself, `docs/Proposals/<NAME>-PROPOSAL.md`,
   with a Status line and (if the version slot was already
   reserved for something else) a version-number note.
2. Its row in `docs/Proposals/README.md`'s own Index table.
3. Its row in *this* file's Folder Guide table for `docs/Proposals/`.
4. The implementation/staging file,
   `docs/Implementation/<NAME>-ADDENDUM.md` (or the equivalent
   `docs/Backends/` staging doc for a backend-specific piece of work)
   -- created now, in this pass, not left as a promised filename with
   no file behind it.
5. Its row in `docs/Implementation/README.md`'s own Index table.
6. Its row in *this* file's Folder Guide table for
   `docs/Implementation/`.
7. `docs/Foundational/ARCHITECTURE.md`'s Milestones table row for the
   version slot involved, updated to mention the new piece of work if
   it shares a slot with something already there.
8. `PROGRESS.md`'s Snapshot table row for that version.
9. The relevant `docs/version history/vX.md` preview file's status
   note and per-piece section, **if** one already exists for that
   slot (per that directory's own README, no *new* forward-looking
   file should be created there for a version that doesn't already
   have one).

Skipping any of 2/3/5/6 is exactly how one README's index and the
other's index end up disagreeing, the way `docs/Implementation/`'s
two indexes do right now. Skipping 4 while still writing 5/6 is
exactly how `PROVIDER-SDK-ADDENDUM.md`/`SEARCH-RETRIEVE-DOC-ADDENDUM.md`
ended up referenced without existing. The fix in both cases is not a
follow-up commit later -- it's checking this numbered list before
calling a documentation change finished.