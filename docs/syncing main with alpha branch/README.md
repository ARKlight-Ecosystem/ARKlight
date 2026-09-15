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
| 4 | JS backend: HTMX + reactive core (vdom) | Done |
| 5 | Search engine | Done |
| 6 | Live-streaming, CCTV, upgrade, scaffold extras | Not started |
| 7 | Root metadata (`pyproject.toml`, `.gitignore`) | Not started |
| 8 | Android-exclusion verification pass | Not started |
| 9 | Full test-suite verification | Not started |

**Known gap until Stage 6 lands:** with Stage 5 in, the full suite runs
714 tests clean (0 failures) under a proper `pip install -e .`. Only 4
files still fail to *collect*: `test_cli.py`, `test_pack.py`,
`test_scaffold.py`, `test_search.py` -- all for the same single reason,
`arklight.cli.templates.production`/`simple` (Stage 1) importing
`arklight.cli.templates._common` (Stage 6, not yet landed). Expected
and tracked, not a regression.

**Bug found and fixed during Stage 5 verification:** `arklight/__init__.py`
(ported verbatim in Stage 1) still had `CHANNEL = "alpha"` -- the
per-branch constant the module's own docstring says should read
`"main"` on this branch. Caught by `test_channel_is_the_static_per_branch_string`
once a real `pip install -e .` (with `ARKLIGHT_ACCEPT_LICENSE=1`) was
run instead of a bare `PYTHONPATH=.` invocation. Fixed as part of this
patch, not deferred -- it's a one-line correction to a file Stage 1
already introduced, not new Stage 5 scope.
