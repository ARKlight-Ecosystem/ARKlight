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
| [`ARCHITECTURE.md`](ARCHITECTURE.md) | High-level system design: how source is parsed, compiled to IR, and rendered by a backend. |
| [`CONFIGURABILITY.md`](CONFIGURABILITY.md) | The "reachability rule" — which fixed internal values should grow into a per-site kwarg/CLI flag vs. stay a constant. |
| [`DEPLOYMENT-CLI.md`](DEPLOYMENT-CLI.md) | The `arklight deploy` subcommand: a thin wrapper delegating to a hosting provider's own CLI (Cloudflare Workers/Wrangler by default) rather than reimplementing provider deployment logic. For every other subcommand (`build`, `pack`, `unpack`, `search`, `new`, `pwa`, `live-streaming`), see the root [`README.md`](../../README.md#cli), the single canonical CLI reference. |
| [`DESIGN-NOTES.md`](DESIGN-NOTES.md) | Rationale and trade-offs behind key design decisions. |
| [`EXPERIMENTAL-APIS.md`](EXPERIMENTAL-APIS.md) | APIs that are unstable or opt-in (`experimental.py`), and their stability guarantees. |
| [`USER-DEFINED-COMPONENTS.md`](USER-DEFINED-COMPONENTS.md) | Design for user-defined, reusable components (v0.060). |
