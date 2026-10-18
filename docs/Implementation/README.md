# Implementation

## Overview

Staged implementation plans for proposals that have already been
**accepted** -- turned from "should we?" into "here's the landing
order." A file here is a trackable stage ladder for work that's
going to happen, the same role `docs/Backends/ANDROID-BACKEND-IMPLEMENTATION.md`
already plays for the Android backend, generalized to a top-level
folder so non-backend accepted work (starting with the JS vocabulary
addendum below) has an equivalent home instead of being wedged into
`Backends/` or left informally in `PROGRESS.md`.

## Why this is separate from `docs/Proposals/` and `docs/Foundational/`

Three different states of a piece of design work, three different
folders:

- **`docs/Proposals/`** -- *unsettled*. Nobody has decided yet.
- **`docs/Implementation/`** (here) -- *accepted, not yet (fully)
  built*. A maintainer has looked at the proposal and said "yes, in
  this order" -- what's left is turning each staged rung into actual
  commits, the same way `v0.054` landed as 8 tracked `vdom-N` stages
  and `v0.060` landed as 5 tracked `stage0`-`stage4` stages before
  either got rolled up into a single `docs/version history/` entry.
- **`docs/Foundational/`** -- *settled and shipped*. Once every stage
  in a ladder here is actually done and its outcome is captured in
  `docs/version history/`/`CHANGELOG.md`, anything that's a permanent
  design decision (not just a shipped feature) graduates into
  `Foundational/`; anything that's just "here's what stage N added"
  stays as history, and the file here can be trimmed or removed.

Keeping "accepted, staged, in-flight" separate from both endpoints
means a reader can tell at a glance whether a document describes an
idea awaiting a decision, a decision awaiting execution, or a
decision already executed -- without reading the whole file to find
out which.

## What belongs here

- A staged rung-by-rung implementation ladder for a proposal a
  maintainer has accepted, in the same spirit as
  `ANDROID-BACKEND-IMPLEMENTATION.md`/`DESKTOP-BACKEND-IMPLEMENTATION.md`
  -- but for accepted work that isn't specifically a packaging
  backend, so it doesn't naturally belong under `docs/Backends/`.

## What doesn't

- An idea nobody has committed to yet -- that's `docs/Proposals/`.
- A backend-specific staged plan -- those stay in `docs/Backends/`
  alongside that backend's own proposal doc, for locality.
- A permanent design decision already shipped -- that's
  `docs/Foundational/`, or a plain `docs/version history/` entry if
  it's just a feature summary rather than a design rationale.

## Index

| File | Covers |
| --- | --- |
| [`MARKDOWN-CONTENT-ADDENDUM.md`](MARKDOWN-CONTENT-ADDENDUM.md) | Seven-stage (`M1`-`M7`, no version slots reserved) ladder for the accepted `docs/Proposals/MARKDOWN-CONTENT-PROPOSAL.md` -- front matter parser, a Markdown-to-IR parser adapted from the already-vendored `arklight/cli/mdrender.py` terminal renderer, `content/`-directory discovery wired in ahead of `arklight.parser.discover`'s existing AST-only scan, asset/link resolution reusing the existing `asset_check`/`link_check` machinery, the `markdown-simple`/`markdown-production` templates, and the `light`/`dark`/`reading` presets (`dark`'s palette and background fixed to `mdrender.py`'s own ANSI colors against `#16140f`). Settles the proposal's raw-HTML policy (escape, not strip or allow-list) and background-color open questions. **IN PROGRESS** -- Stages `M1`-`M5` of 7 (front matter, Markdown-to-IR parser, `content/` discovery, asset/link resolution, `markdown-simple`/`markdown-production` templates) are SHIPPED, unreleased (`alpha`); `M6` (presets) and `M7` (docs/tests rollup) remain PLANNED. |
| [`JS-VOCABULARY-ADDENDUM-v0.070.md`](JS-VOCABULARY-ADDENDUM-v0.070.md) | Staged, ten-rung (`v0.061`-`v0.070`) implementation ladder for the philosophy-compliant parts of `docs/Proposals/JS-VOCABULARY-EXPANSION-PROPOSAL.md` (Tier 1, Tier 2, and the exhaustive §6 scalar catalog) -- easiest additions first, the two entries needing an explicit design exception last. |
| [`PROJECT-KNOWLEDGE-ADDENDUM.md`](PROJECT-KNOWLEDGE-ADDENDUM.md) | Staged, eight-rung (`v0.071`-`v0.078`) implementation ladder for the accepted `docs/Proposals/PROJECT-KNOWELEDGE-PROPOSAL.md` -- `.arklight/` directory foundation first, future-provider open slot last. Follows the proposal's own §19 \"Suggested order\" exactly, one version per stage. |
| [`SEARCH-KNOWLEDGE-STATE-AND-KEYWORDS-ADDENDUM.md`](SEARCH-KNOWLEDGE-STATE-AND-KEYWORDS-ADDENDUM.md) | Capability fix to `arklight.search.knowledge.build_knowledge_base()` and `arklight.cli.search`: adds the `State`/`Bind`/`Computed`/`Watch` reactive-state closed vocabulary and the six other closed, compiler-validated registries to the typo-tolerant search index, closing a gap where both were invisible to `arklight search`. Stage 0 (plan) and Stage 1 (implementation) SHIPPED, unreleased (`alpha`); no `CHANGELOG.md` entry yet. |
| [`PLATFORM-API-IR-ADDENDUM.md`](PLATFORM-API-IR-ADDENDUM.md) | Two-stage implementation ladder for the accepted `docs/Proposals/PLATFORM-API-IR-PROPOSAL.md` -- Stage 1 (`v0.065`, Web reference implementation: architecture plus `notify`/`clipboard_write`) SHIPPED; Stage 2 (Android/Desktop native implementations) PLANNED, unscheduled pending each backend's own maturity. Interleaved as a fourth piece into `v0.065`. |
| [`APP-SHELL-ADDENDUM.md`](APP-SHELL-ADDENDUM.md) | Six-stage (`S1`-`S6`, no version slots reserved) ladder for the accepted `docs/Proposals/APP-SHELL-CAPABILITY-PROPOSAL.md` -- view transitions, key-scoped state-to-DOM updates, `Repeat` item identity, global-scope persistence, link prefetch, and a design-first stage for static-params routes. **PLANNED.** |
| [`REI-LANGUAGE-ADDENDUM.md`](REI-LANGUAGE-ADDENDUM.md) | Staged, four-rung (`v0.081`-`v0.084`) implementation ladder for the accepted `docs/Proposals/REI-LANGUAGE-PROPOSAL.md` -- maturity gate/package skeleton/RNI first, exceptions and Platform-APIs-as-interface last; the Compute stage stays unscheduled, blocked on Open question 3. |
| [`SCRIPT-EXTENSION-SYNTAX-CHECK-BUGFIX.md`](SCRIPT-EXTENSION-SYNTAX-CHECK-BUGFIX.md) | Bug fix: `ScriptExtension` JS was appended to `arklight.js` with no syntax check, so one typo killed the whole runtime. Documents why plain `node --check` is the wrong gate (read from Node's `check_syntax.js`: CommonJS/ESM grammar, not a browser classic script) and the `vm.Script` parse used instead, checked at `register()` and on the combined file at compile time. Implemented, unreleased (`alpha`). |
| [`INPUT-AND-PLATFORM-PRIMITIVES-ADDENDUM-v0.071.md`](INPUT-AND-PLATFORM-PRIMITIVES-ADDENDUM-v0.071.md) | Six-stage (`v0.071`, sharing the slot with `PROJECT-KNOWLEDGE-ADDENDUM.md`) ladder from two independent dogfooding reports: multi-effect `Watch`/`on_click`/`on_reveal`, element- and page-scoped key events, selection as a `State` source plus line/column derivations, and two new Platform API entries (file open/save, confirm dialog). **IN PROGRESS** -- Stage 2 of 6 (`on_key=`, element-scoped key events) and Stage 6 of 6 (`confirm` dialog) are SHIPPED; Stages 1, 3, 4 and 5 remain PLANNED. See `docs/Foundational/CAPABILITY-MATRIX.md` for the full space it was filtered out of. |

## Contributing

If a proposal under `docs/Proposals/` gets accepted, write its stage
ladder here rather than jumping straight to code -- add a row to the
Index table above when you do. Once every stage in a ladder here has
actually shipped, roll it up the same way `v0.054.md`/`v0.060.md`
roll up their staging sub-releases, and trim or remove the file here.
