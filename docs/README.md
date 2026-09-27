# ARKlight Documentation

This folder is the documentation index for ARKlight on `main`. Start
here, then follow the links below into the subfolders for the topic
you need.

## Folder Guide

### [`docs/Foundational/`](Foundational/README.md) — permanent

The core reading for understanding how ARKlight works and why it's
built the way it is. **Not deletable** — this is the permanent design
record for the project, updated in place rather than removed. Kept
identical to `alpha`'s copy of the same files (see that folder's own
`README.md` for the full index and descriptions) except where a link
would point at a file that only exists on `alpha` — those are written
as full `github.com/.../blob/alpha/...` URLs instead of relative
paths, since a relative `../Proposals/...` link from a file living in
`main`'s tree can't resolve to a folder `main` doesn't carry.

| File | Covers |
| --- | --- |
| [`WHAT-ARKLIGHT-IS.md`](Foundational/WHAT-ARKLIGHT-IS.md) | The project's own definition of itself -- a compiler framework, not a static-site generator, frontend framework, or UI framework. |
| [`PITCH.md`](Foundational/PITCH.md) | An informal, conversational pitch for what ARKlight is and why it exists. |
| [`V1-DEFINITION.md`](Foundational/V1-DEFINITION.md) | What `v1.0 -- Stable compiler` concretely means, and its scope boundary (Web Developing parts of the compiler only -- not native backends, not experimental features, not ACC). |
| [`ARCHITECTURE.md`](Foundational/ARCHITECTURE.md) | High-level system design: how source is parsed, compiled to IR, and rendered by a backend. |
| [`CONFIGURABILITY.md`](Foundational/CONFIGURABILITY.md) | The "reachability rule" — which fixed internal values should grow into a per-site kwarg/CLI flag vs. stay a constant. |
| [`CLI-REFERENCE.md`](Foundational/CLI-REFERENCE.md) | The full `arklight` CLI reference. Explicitly flags which subcommands are alpha-only so far (`android`, `desktop`, `deploy` -- not yet on `main`, see the note below). |
| [`GETTING-STARTED.md`](Foundational/GETTING-STARTED.md) | Install, the annotated repository layout, and the `pytest` workflow. |
| [`AUTHORING-GUIDE.md`](Foundational/AUTHORING-GUIDE.md) | The full public component/behavior/state API reference. |
| [`DEPLOYMENT-CLI.md`](Foundational/DEPLOYMENT-CLI.md) | `arklight deploy`: spec and provider boundary. Alpha-only so far -- see the note below. |
| [`DESIGN-NOTES.md`](Foundational/DESIGN-NOTES.md) | Rationale and trade-offs behind key design decisions, plus graduated design records of fully-shipped proposals. |
| [`EXPERIMENTAL-APIS.md`](Foundational/EXPERIMENTAL-APIS.md) | APIs that are unstable or opt-in (`experimental.py`), and their stability guarantees. |
| [`SYSTEM-DESIGN-AGREEMENTS.md`](Foundational/SYSTEM-DESIGN-AGREEMENTS.md) | The "compiler first, runtime last" design agreement. |
| [`USER-DEFINED-COMPONENTS.md`](Foundational/USER-DEFINED-COMPONENTS.md) | User-defined, reusable components (v0.060, shipped in full). |
| [`PLATFORM-APIS.md`](Foundational/PLATFORM-APIS.md) | Settled design record for the platform API interface layer (`v0.065`). |
| [`ACC-CAPABILITIES.md`](Foundational/ACC-CAPABILITIES.md) | Settled design record for `arklight/capabilities.py`, the ACC capability-discovery hook. |
| [`PROVIDER-SDK.md`](Foundational/PROVIDER-SDK.md) | Settled design record for `Provider` (`v0.065`-`v0.070`, six-rung ladder, fully shipped). |

### [`docs/version history/`](<version history/README.md>) — permanent

The user-facing overview of each released `main` version. `main` bundles
each sync from `alpha` into one dated release file here rather than
carrying `alpha`'s per-rung file granularity — see that folder's own
`README.md` for why the two branches' directories intentionally differ.

## Android, Desktop, and `deploy`: alpha-only, not yet on `main`

`alpha` has shipped full Android and Desktop packaging backends plus
an `arklight deploy` subcommand. None of the three have landed on
`main` yet -- Android and Desktop need more time before they're ready
to carry over, and `deploy` hasn't been brought over separately. The
Foundational docs above are otherwise kept identical to `alpha`'s copy
(including their own descriptions of those three subcommands, since
the docs describe the whole project rather than only `main`'s subset)
-- `CLI-REFERENCE.md` and `DEPLOYMENT-CLI.md` each say so explicitly
in their own text, so there's no separate `main`-only rewrite to keep
in sync.

## A note on `alpha`'s other doc folders

`alpha` also carries `docs/Backends/`, `docs/Far Future Concern/`,
`docs/Implementation/`, `docs/Proposals/`, and `docs/reference/`.
Those are deliberately **not** ported to `main`: they're working
references and staging docs tied to `alpha`'s in-progress or
speculative work, cleared out or graduated once a decision is made
rather than kept as permanent documentation. `main` only carries
`Foundational/` and `version history/`, which are the two folders
`alpha`'s own `docs/README.md` calls permanent.

## Contributing to the Docs

If you add a new doc file, add a row for it in the relevant table
above so this index stays accurate.
