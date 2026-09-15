# Syncing main with alpha branch

## Overview

Working area for the effort to bring `main` in line with `alpha`'s
v0.054-equivalent state, excluding the Android backend/CLI entirely.
Each stage is generated as a standalone, reviewable patch rather than
applied directly -- see the plan doc below for the full staging
rationale and the Android-exclusion checklist.

This directory (like `docs/Backends/`, `docs/Far Future Concern/`, and
`docs/new js backend proposal/`) is a **working reference, not
permanent documentation** -- unlike `docs/Foundational/`, it will be
removed once the sync is complete and `main` no longer needs a
tracking doc for a job that's finished.

## Index

| File | Covers |
| --- | --- |
| [`MAIN TO ALPHA V0.54.md`](<MAIN TO ALPHA V0.54.md>) | The full staged plan: ground-truth diff stats, Stage 0-9 scope and dependency order, the Android-exclusion checklist, and what's deliberately left out (alpha's `Backends/`/`Far Future Concern/`/`new js backend proposal/` doc folders). |

## Status

| Stage | Scope | Status |
| --- | --- | --- |
| 0 | Foundational docs sync | Done |
| 1 | Shared plumbing (18 files) + `config.py`/`experimental.py` | Done |
| 2 | CSS backend rewrite | Done |
| 3 | HTML backend refactor | Done |
| 4 | JS backend: HTMX + reactive core (vdom) | Not started |
| 5 | Search engine | Not started |
| 6 | Live-streaming, CCTV, upgrade, scaffold extras | Not started |
| 7 | Root metadata (`pyproject.toml`, `.gitignore`) | Not started |
| 8 | Android-exclusion verification pass | Not started |
| 9 | Full test-suite verification | Not started |

**Known gap until Stage 5 and Stage 6 land:** `arklight` itself now
imports cleanly (Stage 2 satisfied the one top-level import Stage 1
was missing), but the full test suite still can't collect --
`arklight.compiler.pipeline` (Stage 1) imports `arklight.search.engine`
(Stage 5) at module level, and `arklight.cli.templates.production`/
`simple` (Stage 1) import `arklight.cli.templates._common` (Stage 6).
Both are expected and tracked, not regressions from Stage 2.
