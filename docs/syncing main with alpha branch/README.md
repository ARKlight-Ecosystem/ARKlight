# Syncing main with alpha branch

## Overview

Working area for the effort to bring `main` in line with `alpha`,
excluding the Android backend/CLI entirely. Each stage is generated as
a standalone, reviewable patch rather than applied directly -- see the
plan doc below for the full staging rationale and the Android-exclusion
checklist.

This directory (like `docs/Backends/`, `docs/Far Future Concern/`, and
`docs/Proposals/`) is a **working reference, not permanent
documentation** -- unlike `docs/Foundational/`, it will be removed once
the sync is complete and `main` no longer needs a tracking doc for a
job that's finished.

## Index

| File | Covers |
| --- | --- |
| [`MAIN TO ALPHA V0.54.md`](<MAIN TO ALPHA V0.54.md>) | **Complete.** The v0.054 catch-up: ground-truth diff stats, Stage 0-9 scope and dependency order, the Android-exclusion checklist, and what was deliberately left out. Superseded by the plan below; kept for history until this folder's next cleanup pass. |
| [`MAIN TO ALPHA V0.070.md`](<MAIN TO ALPHA V0.070.md>) | **Current plan.** The v0.070 catch-up: ten JS-vocabulary rungs, user-defined components, the full `Provider` SDK, Platform API IR, the Rei narrator, search/knowledge additions, compiler hardening, the standing Android exclusion, and a new Desktop-backend exclusion decision. |

## Status

**v0.54 plan:** all stages (0-9) done -- see that file's own status
note.

**v0.070 plan:** in progress.

| Stage | Scope | Status |
| --- | --- | --- |
| 0 | Foundational docs + version-history sync | Not started (checked: `Foundational/`, version history, and root docs all still differ from alpha's v0.070 commit) |
| 1 | Shared plumbing | Ported -- not yet import-clean, see plan doc's coupling note; needs Stages 2/4/5 alongside it |
| 2 | User-defined components (`v0.060`) | Ported -- confirmed no new import gaps beyond Stage 1's note |
| 3 | JS vocabulary ladder, 10 rungs (`v0.061`-`v0.070`) | Ported -- confirmed no new import gaps beyond Stage 1's note |
| 2 | User-defined components (`v0.060`) | Not started |
| 3 | JS vocabulary ladder, 10 rungs (`v0.061`-`v0.070`) | Not started |
| 4 | `Provider` SDK, 6 stages (`v0.065`-`v0.070`) | Ported -- `import arklight` still fails, but now for exactly the single remaining reason predicted (Stage 5's `arklight.ir.platform_api`), confirming no new import gaps introduced |
| 5 | Platform API IR | Ported -- resolves the `arklight.ir.platform_api` gap Stage 1 predicted. `import arklight` still fails, but for a gap this plan hadn't documented: `ir/__init__.py` (Stage 1) unconditionally imports `arklight.ir.binary` (Stage 9, not yet landed). Not a Stage 5 defect -- pre-existing in the Stage 1 port, just unmasked now that Stage 5's own gap is closed. Flagging here rather than pulling Stage 9 forward. |
| 6 | Rei compiler narrator | Ported -- self-contained, no existing code references `arklight.compiler.rei` yet, so this introduces no new import coupling. `import arklight` still blocked only by the pre-existing Stage 9 `ir.binary` gap noted at Stage 5. `docs/Proposals/REI-LANGUAGE-PROPOSAL.md` deliberately left out (Proposals dir is out of scope). |
| 7 | Search/knowledge-state additions + doc tooling | Ported -- CLI wiring in `cli/main.py` (importing `deploy`/`doc_retrieval`/`mdrender`/`whats_new`) deliberately deferred to Stage 10, per that stage's own scope (`cli/main.py` is listed there, not here); the new modules and their tests stand alone until then. `docs/Implementation/PROJECT-KNOWLEDGE-ADDENDUM.md` deliberately left out per the plan's gray-area note -- no version-history entry yet claims it. `import arklight` still blocked only by the pre-existing Stage 9 `ir.binary` gap; no new coupling from this stage. |
| 8 | URL state, class binding, action-arg runtime | Not started |
| 9 | Compiler hardening & supply-chain tooling | Not started |
| 10 | Live-streaming/CCTV/upgrade maintenance | Not started |
| 11 | Android-exclusion verification pass | Not started |
| 12 | Desktop-backend exclusion decision | Not started |
| 13 | Root metadata (preserve `apt-repo.yml`) | Not started |
| 14 | Full verification | Not started |

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
