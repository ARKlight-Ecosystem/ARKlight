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
| [`user-defined-components.md`](Foundational/user-defined-components.md) | Design for user-defined, reusable components (v0.060). |

### [`docs/Backends/`](Backends/README.md) — working reference

Design/staging docs for individual output backends. **Working
reference only** — removed once the work they describe is finished
and captured in the changelog or a Foundational doc.

| File | Covers |
| --- | --- |
| [`ANDROID-BACKEND-IMPLEMENTATION.md`](Backends/ANDROID-BACKEND-IMPLEMENTATION.md) | Staged implementation plan for the Android packaging backend. |
| [`ARKLIGHT_DESKTOP_BACKEND_PROPOSAL.md`](Backends/ARKLIGHT_DESKTOP_BACKEND_PROPOSAL.md) | Proposal for a purpose-built native desktop host/packager (replacing Neutralino.js as the canonical desktop backend). |
| [`NEUTRALINO-INTEGRATION.md`](Backends/NEUTRALINO-INTEGRATION.md) | Neutralino desktop-app integration (current desktop backend). |

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

## Contributing to the Docs

If you add a new doc file, add a row for it in the relevant table
above so this index stays accurate.