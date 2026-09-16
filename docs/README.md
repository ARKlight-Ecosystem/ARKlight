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
| [`ARCHITECTURE.md`](Foundational/ARCHITECTURE.md) | High-level system design: how source is parsed, compiled to IR, and rendered by a backend. |
| [`CONFIGURABILITY.md`](Foundational/CONFIGURABILITY.md) | The "reachability rule" — which fixed internal values should grow into a per-site kwarg/CLI flag vs. stay a constant. (For the `arklight.config.py` project-settings file itself, see the README's "Configuration" section.) |
| [`DEPLOYMENT-CLI.md`](Foundational/DEPLOYMENT-CLI.md) | The `arklight` CLI: build/deploy workflows and commands. |
| [`DESIGN-NOTES.md`](Foundational/DESIGN-NOTES.md) | Rationale and trade-offs behind key design decisions. |
| [`EXPERIMENTAL-APIS.md`](Foundational/EXPERIMENTAL-APIS.md) | APIs that are unstable or opt-in (`experimental.py`), and their stability guarantees. |
| [`SYSTEM-DESIGN-AGREEMENTS.md`](Foundational/SYSTEM-DESIGN-AGREEMENTS.md) | The "compiler first, runtime last" design agreement: which work the compiler must own vs. delegate to the target runtime, when the compiler may specialize per-target, and the four-question architecture decision rule for judging any new feature against it. |
| [`USER-DEFINED-COMPONENTS.md`](Foundational/USER-DEFINED-COMPONENTS.md) | User-defined, reusable components (v0.060, shipped in full) -- props, default styling, macro/registry modes, component-owned state, and scope boundaries. |

### [`docs/Backends/`](Backends/README.md) — working reference

Design/staging docs for individual output backends. **Working
reference only** — removed once the work they describe is finished
and captured in the changelog or a Foundational doc.

| File | Covers |
| --- | --- |
| [`ANDROID-BACKEND-IMPLEMENTATION.md`](Backends/ANDROID-BACKEND-IMPLEMENTATION.md) | Staged implementation plan for the Android packaging backend. |
| [`ARKLIGHT_DESKTOP_BACKEND_PROPOSAL.md`](Backends/ARKLIGHT_DESKTOP_BACKEND_PROPOSAL.md) | Proposal for a purpose-built native desktop host/packager (replacing Neutralino.js as the canonical desktop backend). |
| [`NEUTRALINO-INTEGRATION.md`](Backends/NEUTRALINO-INTEGRATION.md) | Neutralino desktop-app integration (current desktop backend). |

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
| [`ARKLIGHT-ASSISTANT-CLI-PROPOSAL.md`](<Proposals/ARKLIGHT-ASSISTANT-CLI-PROPOSAL.md>) | Proposal for an `arklight assistant` subcommand: a read-only, doc-grounded CLI companion ("Raeliana") behind `--wake-up-raeliana`, plus a separate opt-in `--activate-memory` flag for cross-session recall. **Accepted -- implementation deferred to v0.090+.** |
| [`PROJECT-KNOWELEDGE-PROPOSAL.md`](<Proposals/PROJECT-KNOWELEDGE-PROPOSAL.md>) | Proposal for a compiler-owned `.arklight/` project-local knowledge directory: providers/facts/observations model, Git as the first provider, persistence across builds. **Accepted -- staged in `docs/Implementation/PROJECT-KNOWLEDGE-ADDENDUM.md` as `v0.071`-`v0.078`.** |
| [`SEARCH-RETRIEVE-DOC-PROPOSAL.md`](<Proposals/SEARCH-RETRIEVE-DOC-PROPOSAL.md>) | Proposal for `arklight search --retrieve-doc`: a doc-tree retrieval mode on the existing `search` subcommand, printing the root or a folder's `README.md` index and, with `--file NAME`, one file's full contents. |

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