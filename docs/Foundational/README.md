# Foundational

## Overview

The core reading for understanding how ARKlight works and why it's
built the way it is: architecture, design rationale, configurability
rules, the CLI, and the experimental-API policy. This is reference
material for the project as a whole, not a record of a single
in-flight task.

**These docs are not deletable.** Unlike the working-reference docs
elsewhere in `docs/`, files in this folder are the permanent design
record for ARKlight. They get updated as the project evolves, but a
file in this folder should never simply be deleted once its "purpose"
is fulfilled — there is no expiry condition for foundational design
knowledge.

## Index

| File | Covers |
| --- | --- |
| [`WHAT-ARKLIGHT-IS.md`](WHAT-ARKLIGHT-IS.md) | The project's own definition of itself -- a compiler framework, not a static-site generator, frontend framework, or UI framework -- verified against the `alpha` source, with an explicit account of which familiar label each part of ARKlight resembles and why none of them describe the whole thing. Opens with "The Goal": comparable-to-frontend-framework DX while enforcing ARKlight's own philosophy, for two named audiences -- the Python Community and the Education Community. |
| [`V1-DEFINITION.md`](V1-DEFINITION.md) | What `v1.0 -- Stable compiler` (`ARCHITECTURE.md`'s Milestones table) concretely means: deterministic, fails-loudly, no-breaking-vocabulary-changes reliability for the Web Developing parts of the compiler only -- explicitly not the native packaging backends, not experimental/opt-in features, and not ARKlight Component Collections. Also documents "capability fix" as a recognized patch category and the evidence trail it leaves toward `v1.0`. |
| [`ARCHITECTURE.md`](ARCHITECTURE.md) | High-level system design: how source is parsed, compiled to IR, and rendered by a backend. |
| [`CONFIGURABILITY.md`](CONFIGURABILITY.md) | The "reachability rule" — which fixed internal values should grow into a per-site kwarg/CLI flag vs. stay a constant. |
| [`CLI-REFERENCE.md`](CLI-REFERENCE.md) | The implemented, shipped `arklight` subcommands (`build`, `pack`, `unpack`, `search`, `new`, `pwa`, `live-streaming`) -- the single canonical CLI reference. |
| [`AUTHORING-GUIDE.md`](AUTHORING-GUIDE.md) | The full public component/behavior/state API: routing, head metadata, layout, styling, behaviors, the component vocabulary, the ARK Bundle format, and `arklight.config.py`. |
| [`DEPLOYMENT-CLI.md`](DEPLOYMENT-CLI.md) | **Design only, not implemented.** The planned `arklight deploy` subcommand: a thin wrapper intended to delegate to a hosting provider's own CLI (Cloudflare Workers/Wrangler by default) rather than reimplementing provider deployment logic. |
| [`DESIGN-NOTES.md`](DESIGN-NOTES.md) | Rationale and trade-offs behind key design decisions. |
| [`EXPERIMENTAL-APIS.md`](EXPERIMENTAL-APIS.md) | APIs that are unstable or opt-in (`experimental.py`), and their stability guarantees. |
| [`SYSTEM-DESIGN-AGREEMENTS.md`](SYSTEM-DESIGN-AGREEMENTS.md) | The "compiler first, runtime last" design agreement: which work the compiler must own vs. delegate to the target runtime, when the compiler may specialize per-target, and the four-question architecture decision rule for judging any new feature against it. |
| [`USER-DEFINED-COMPONENTS.md`](USER-DEFINED-COMPONENTS.md) | Design for user-defined, reusable components (v0.060). |
| [`PLATFORM-APIS.md`](PLATFORM-APIS.md) | Settled design record for the platform API interface layer (`PlatformAPI.notify`/`.clipboard_write`, `v0.065`): terminology, the compiler-owns-interface/backend-owns-implementation architecture, Web-as-default, native-implementations-are-earned, and the explicit boundary against the pre-existing `copy` behavior. |
| [`ACC-CAPABILITIES.md`](ACC-CAPABILITIES.md) | Settled design record for `arklight/capabilities.py`, the ACC (ARKlight Component Collections) capability-discovery hook: the `arklight.capabilities` entry-point contract, diagnostics, API, its one current caller (`compiler/sbom.py`), and status against ACC's own five-stage implementation ladder (Stage 1 landed here; Stages 2-5 tracked in the separate ACC repository). |
