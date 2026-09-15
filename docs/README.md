# ARKlight Documentation

This folder is the documentation index for ARKlight on `main`. Start
here, then follow the links below into the subfolders for the topic
you need.

## Folder Guide

### [`docs/Foundational/`](Foundational/README.md) — permanent

The core reading for understanding how ARKlight works and why it's
built the way it is. **Not deletable** — this is the permanent design
record for the project, updated in place rather than removed.

| File | Covers |
| --- | --- |
| [`ARCHITECTURE.md`](Foundational/ARCHITECTURE.md) | High-level system design: how source is parsed, compiled to IR, and rendered by a backend. |
| [`CONFIGURABILITY.md`](Foundational/CONFIGURABILITY.md) | The "reachability rule" — which fixed internal values should grow into a per-site kwarg/CLI flag vs. stay a constant. |
| [`DEPLOYMENT-CLI.md`](Foundational/DEPLOYMENT-CLI.md) | The `arklight` CLI: build/deploy workflows and commands. |
| [`DESIGN-NOTES.md`](Foundational/DESIGN-NOTES.md) | Rationale and trade-offs behind key design decisions. |
| [`EXPERIMENTAL-APIS.md`](Foundational/EXPERIMENTAL-APIS.md) | APIs that are unstable or opt-in (`experimental.py`), and their stability guarantees. |
| [`user-defined-components.md`](Foundational/user-defined-components.md) | Design for user-defined, reusable components (v0.060). |

## A note on `alpha`'s other doc folders

`alpha` also carries `docs/Backends/`, `docs/Far Future Concern/`, and
`docs/new js backend proposal/`. Those are deliberately **not** ported
to `main`: they're working references tied to `alpha`'s in-progress
staging work, removed once their purpose is fulfilled rather than kept
as permanent documentation. `main` only carries `Foundational/`, which
is kept identical across both branches.

## Contributing to the Docs

If you add a new doc file, add a row for it in the relevant table
above so this index stays accurate.
