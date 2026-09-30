# ARKlight Documentation

This folder is the documentation index for ARKlight on `main`. Start
here, then follow the links below into the subfolders for the topic
you need.

## Folder Guide

### [`docs/Foundational/`](Foundational/README.md) — permanent

The core reading for understanding how ARKlight works and why it's
built the way it is. **Not deletable** — this is the permanent design
record for the project, updated in place rather than removed. See that
folder's own `README.md` for the full index and descriptions.

| File | Covers |
| --- | --- |
| [`WHAT-ARKLIGHT-IS.md`](Foundational/WHAT-ARKLIGHT-IS.md) | The project's own definition of itself -- a compiler framework, not a static-site generator, frontend framework, or UI framework. |
| [`PITCH.md`](Foundational/PITCH.md) | An informal, conversational pitch for what ARKlight is and why it exists. |
| [`V1-DEFINITION.md`](Foundational/V1-DEFINITION.md) | What `v1.0 -- Stable compiler` concretely means, and its scope boundary (Web Developing parts of the compiler only -- not native backends, not experimental features). |
| [`ARCHITECTURE.md`](Foundational/ARCHITECTURE.md) | High-level system design: how source is parsed, compiled to IR, and rendered by a backend. |
| [`CONFIGURABILITY.md`](Foundational/CONFIGURABILITY.md) | The "reachability rule" — which fixed internal values should grow into a per-site kwarg/CLI flag vs. stay a constant. |
| [`CLI-REFERENCE.md`](Foundational/CLI-REFERENCE.md) | The full `arklight` CLI reference. |
| [`GETTING-STARTED.md`](Foundational/GETTING-STARTED.md) | Install, the annotated repository layout, and the `pytest` workflow. |
| [`AUTHORING-GUIDE.md`](Foundational/AUTHORING-GUIDE.md) | The full public component/behavior/state API reference. |
| [`DEPLOYMENT-CLI.md`](Foundational/DEPLOYMENT-CLI.md) | `arklight deploy`: spec and provider boundary. |
| [`DESIGN-NOTES.md`](Foundational/DESIGN-NOTES.md) | Rationale and trade-offs behind key design decisions, plus graduated design records of fully-shipped proposals. |
| [`EXPERIMENTAL-APIS.md`](Foundational/EXPERIMENTAL-APIS.md) | APIs that are unstable or opt-in (`experimental.py`), and their stability guarantees. |
| [`SYSTEM-DESIGN-AGREEMENTS.md`](Foundational/SYSTEM-DESIGN-AGREEMENTS.md) | The "compiler first, runtime last" design agreement. |
| [`USER-DEFINED-COMPONENTS.md`](Foundational/USER-DEFINED-COMPONENTS.md) | User-defined, reusable components (v0.060, shipped in full). |
| [`PLATFORM-APIS.md`](Foundational/PLATFORM-APIS.md) | Settled design record for the platform API interface layer (`v0.065`). |
| [`PROVIDER-SDK.md`](Foundational/PROVIDER-SDK.md) | Settled design record for `Provider` (`v0.065`-`v0.070`, six-rung ladder, fully shipped). |

### [`docs/Implementation/`](Implementation/README.md) — working reference

Staged, rung-by-rung landing orders for accepted work (the JS
vocabulary ladder, the Platform API IR, the Rei narrator, search
knowledge-state). Once every stage in a ladder has shipped, its
permanent design decisions graduate into `Foundational/` and the
ladder is trimmed or removed.

### [`docs/version history/`](<version history/README.md>) — permanent

The user-facing overview of each released version, one file per
version on the same `v0.001`-`v0.070` ladder the roadmap in
[`ARCHITECTURE.md`](Foundational/ARCHITECTURE.md) uses.

### [`docs/syncing main with alpha branch/`](<syncing main with alpha branch/README.md>) — temporary

The staged plan for bringing `main` up to date with the
fast-moving development branch. `main` only takes changes once they
are judged stable, so this plan is the catch-up record. It is removed
once the sync is complete.

## Android and Desktop packaging

`arklight android` and `arklight desktop` are not part of `main`.
Android and Desktop packaging need more time before they are ready
to carry over, so the CLI reference and the guides describe only the
subcommands `main` ships (`build`, `pack`, `unpack`, `pwa`, `deploy`,
`new`, `search`, `live-streaming`). The `PlatformAPI` docs still
name Android and Linux Desktop as backends that exist in the roadmap
but implement no capability yet.

## Folders `main` does not carry

`docs/Backends/`, `docs/Far Future Concern/`, `docs/Proposals/`, and
`docs/reference/` are working references and staging docs tied to
in-progress or speculative work, cleared out or graduated once a
decision is made rather than kept as permanent documentation. `main`
carries only the stable, settled docs above.

## Contributing to the Docs

If you add a new doc file, add a row for it in the relevant table
above so this index stays accurate.
