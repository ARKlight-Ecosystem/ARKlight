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
| [`MAIN TO ALPHA V0.070.md`](<MAIN TO ALPHA V0.070.md>) | **Current plan.** The v0.070 catch-up: ten JS-vocabulary rungs, user-defined components, the full `Provider` SDK, Platform API IR, the Rei narrator, search/knowledge additions, compiler hardening, the standing Android exclusion, and a new Desktop-backend exclusion decision. **Target moved from the `0df63e7` milestone boundary to `alpha` HEAD `23ebc24`** (23 commits later): Stages 15-17 cover the htmx/CSP fixes, `PlatformAPI.db` and small deltas; Stages 0, 11, 13, 14 were amended. Filename kept so links do not break. |

## Status

**v0.54 plan:** all stages (0-9) done; its plan doc has been retired (Stage 14) and lives in git history.

**v0.070 plan:** in progress. Target is `alpha` `23ebc24` (2026-09-29), not the `0df63e7` boundary the plan was first written against; the stage rows below marked "Ported" were ported at `0df63e7`, and the delta on their files is carried by Stages 15-17.

| Stage | Scope | Status |
| --- | --- | --- |
| 0 | Foundational docs + version-history sync | Not started -- and grown: now targets `23ebc24`, adding seven Foundational deltas, `CHANGELOG.md`/`PROGRESS.md` through the `db` entries, and an open decision on links into excluded folders (see plan doc's Stage 0 amendment). `APP-SHELL-ADDENDUM.md` deliberately left out (PLANNED, none started). |
| 1 | Shared plumbing | Ported -- not yet import-clean, see plan doc's coupling note; needs Stages 2/4/5 alongside it |
| 2 | User-defined components (`v0.060`) | Ported -- confirmed no new import gaps beyond Stage 1's note |
| 3 | JS vocabulary ladder, 10 rungs (`v0.061`-`v0.070`) | Ported -- confirmed no new import gaps beyond Stage 1's note |
| 4 | `Provider` SDK, 6 stages (`v0.065`-`v0.070`) | Ported -- `import arklight` still fails, but now for exactly the single remaining reason predicted (Stage 5's `arklight.ir.platform_api`), confirming no new import gaps introduced |
| 5 | Platform API IR | Ported -- resolves the `arklight.ir.platform_api` gap Stage 1 predicted. `import arklight` still fails, but for a gap this plan hadn't documented: `ir/__init__.py` (Stage 1) unconditionally imports `arklight.ir.binary` (Stage 9, not yet landed). Not a Stage 5 defect -- pre-existing in the Stage 1 port, just unmasked now that Stage 5's own gap is closed. Flagging here rather than pulling Stage 9 forward. |
| 6 | Rei compiler narrator | Ported -- self-contained, no existing code references `arklight.compiler.rei` yet, so this introduces no new import coupling. `import arklight` still blocked only by the pre-existing Stage 9 `ir.binary` gap noted at Stage 5. `docs/Proposals/REI-LANGUAGE-PROPOSAL.md` deliberately left out (Proposals dir is out of scope). |
| 7 | Search/knowledge-state additions + doc tooling | Ported -- CLI wiring in `cli/main.py` (importing `deploy`/`doc_retrieval`/`mdrender`/`whats_new`) deliberately deferred to Stage 10, per that stage's own scope (`cli/main.py` is listed there, not here); the new modules and their tests stand alone until then. `docs/Implementation/PROJECT-KNOWLEDGE-ADDENDUM.md` deliberately left out per the plan's gray-area note -- no version-history entry yet claims it. `import arklight` still blocked only by the pre-existing Stage 9 `ir.binary` gap; no new coupling from this stage. |
| 8 | URL state, class binding, action-arg runtime | Ported -- all nine modified runtime files diffed carefully (not wholesale) before landing; confirmed the "main-only" lines were only earlier vdom/htmx refactor stages of the same functions, not unique main features, so alpha's versions were taken as-is. **Scope gap found, not in this stage's file list:** `arklight/backend/js/runtime/__init__.py` and `arklight/backend/js/render.py` needed updating too, or the new `action_args.py`/`query.py`/`reveal.py` (and Stage 5's already-landed `PLATFORM_API_FRAGMENTS`, and render.py's provider-config wiring) would sit unwired and non-functional -- neither file is scoped to any single stage in this plan, they're each stages' shared integration point. Checked render.py's full diff against alpha first: confirmed every symbol it newly imports (`ACTION_FRAGMENTS`, `BEHAVIOR_FRAGMENTS`, `DERIVATION_FRAGMENTS`, `PLATFORM_API_FRAGMENTS`, `check_backend_support`) already exists in `main` from Stages 3/5, so no forward-reference to a not-yet-landed stage was pulled in. `docs/Proposals/URL-STATE-AS-PRIMITIVE-PROPOSAL.md` deliberately left out per standing exclusion. `import arklight` still blocked only by the pre-existing Stage 9 `ir.binary` gap. |
| 9 | Compiler hardening & supply-chain tooling | Ported -- `import arklight` finally succeeds (the `ir.binary` gap flagged since Stage 5 is closed) and a real `pip install -e .` + full suite run is now possible for the first time. See notes below. |
| 10 | Live-streaming/CCTV/upgrade maintenance | Ported at `0df63e7` -- `cli/main.py` and `templates/_common.py` landed with all `android`/`desktop` wiring stripped; `test_binary_ir.py`/`test_scaffold.py` taken from alpha, `test_config.py` kept as main's with its one stale `xfail` removed. Full suite: 2716 passed / 15 failed (was 2591 / 86 failed + 1 collection error). Remaining 15: 8 docs-tree tests (Stage 0's link decision) and 7 Stage 8 runtime-registry gaps -- none from this stage. `live_streaming.py`/`main.py` post-boundary changes deferred to Stages 15/17. |
| 11 | Android-exclusion verification pass | Verified clean at Stage 10's tree -- all checklist items hold; the `android sync`/`ArkDb.kt`/`db`-prose items are guarded for the future stages that could reintroduce them. New `tests/test_android_exclusion.py` (9 tests) makes the check re-runnable. Suite: 2725 passed / 15 failed (same 15 as Stage 10). Pre-existing Android prose in main's Foundational docs left to Stage 0. |
| 12 | Desktop-backend exclusion decision | Excluded and verified -- all nine alpha Desktop paths absent, no `desktop` CLI/config wiring, no Desktop change on alpha in the `0df63e7`->`23ebc24` range. Applies the plan's recommended default; the go/no-go on landing it early (Stage 12a) is still the maintainer's. New `tests/test_desktop_exclusion.py` (13 tests). |
| 13 | Root metadata (preserve `apt-repo.yml`) | Ported -- `pyproject.toml` version `0.54.1` -> `0.070.0` (`arklight --version` prints `0.70.0`). `main`'s SPDX `license`/empty `classifiers` and `.gitignore`'s `ARK/` line are `main`-only and deliberately kept; `apt-repo.yml` untouched. New `tests/test_root_metadata.py` (6 tests). Suite: 2744 passed / 15 failed (same 15 as Stages 10-12). |
| 14 | Full verification | **Pre-flight run -- Stages 0, 15, 16, 17 are still outstanding, so this must be re-run once they land.** Diffed `arklight/`, `tests/`, `examples/`, root against `23ebc24`; closed six gaps that earlier stages left behind (Stage 8 `geolocate`/`paste` registries, a stale `test_js_error_handling.py`, stale doc-path comments, missing `test_upgrade.py`, two missed test expansions, the example site's preamble). `MAIN TO ALPHA V0.54.md` retired. Suite: 2763 passed / 8 failed (was 2744 / 15) -- the 8 are all Stage 0's docs-link decision. |
| 15 | htmx under Trusted Types, CSP, `file://` + live-streaming fallbacks (`e9da11d`, `2ed1674`, `3a933df`, `85a8eee`) | Ported -- seven source files and five test files taken from `23ebc24` whole (verified `main`'s copies matched the `0df63e7` boundary first, so the delta was exactly this stage's). Vendored htmx anchors all applied; Node-executed tests ran, none skipped. New `test_htmx_trusted_types.py`, `test_htmx_failure_handling.py`. Suite: 2816 passed / 8 failed (same 8 docs-tree tests as Stage 14). |
| 16 | `PlatformAPI.db`, Web half only (`f719455`, `23ebc24`) | Ported -- `db.py`, `platform_api.py`, `validate.py`, `dispatch.py`, `platform_apis/__init__.py`, and `api.py` taken from `23ebc24`; `api.py` carries Stage 17's collision-guard hunk too (landed once, as planned), with `test_api_style.py`/`test_css_structural_addendum.py`. `db` is `web`-only: `android` support entry, its prose, and the Android assertions in `test_platform_api_db.py` trimmed; `arkDbBridge` hook kept (inert). Suite: 2867 passed / 8 failed. |
| 17 | Small post-v0.070 deltas: custom-class collision guard, `open_in_browser` fix, PWA precache encoding | Partly done -- the `api.py` collision guard and its two tests landed with Stage 16. Still to do: `cli/main.py` `open_in_browser` hunk (+ `test_cli.py`) and `pwa.py` percent-encoding (+ `test_pwa.py`). |

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

**`arklight/capabilities.py` is `alpha`-only, not carried over.**
Mentioned exactly once in this file's own "ground truth" net-new-
subsystems list but never assigned to any stage -- Stage 9's own
`arklight/compiler/sbom.py` imports it directly (`discover_capabilities`,
`CapabilityError`) for its "ACC (ARKlight Component Collections)
packages installed on this machine" section. Per standing policy
(module deliberately excluded from `main`), `sbom.py` and
`tests/test_sbom.py` are landed with that section, its docstring
paragraph, and its two dedicated tests trimmed out; the module doc
notes exactly why the section is absent. Everything else `sbom.py`
does -- the per-build "what did this specific build actually
reference" manifest -- is unaffected and fully covered.

**`CHANNEL = "alpha"` regression, again:** the same one-line bug the
Stage 5 note above says was already fixed had reverted to `"alpha"` by
the time this stage started. Fixed again; if this recurs a third time
it's worth checking why the fix isn't sticking across patch
regeneration.

**Scope gaps found, not in this stage's file list, needed for Stage
9's own new tests to actually pass:**
- `arklight/backend/html/routing.py`, `attrs.py`, and `page_render.py`
  were all badly behind `alpha` -- missing HTML-rendering support for
  `ModelBindSpec`/`PlatformAPIRef`/`on_reveal` (Stages 2/5/8's own
  backing data already existed; only the HTML side was never wired),
  Stage 3's JS-accurate number/predicate formatting, Stage 8's
  `page.media`/`page.query` URL-state attributes, and this stage's own
  CSP meta tag. Checked every new symbol each file imports first --
  all already satisfied by Stages 1/3/5/8 -- before landing all three
  wholesale, same treatment Stage 8 gave `render.py`/`runtime/__init__.py`.
- `arklight/backend/html/render.py` needed the `strict_csp`/
  `trusted_script_origins` passthrough to `_render_page` (this stage),
  and, separately, a still-unwired Stage 2 gap: `resolve_backend_dispatch`
  was never called from anywhere in `main`. Both fixed here since
  `render.py` is Stage 8/9's shared integration point, not owned by
  either stage.
- `arklight/backend/html/head_meta.py` was missing the `_is_external_ref`
  guard around `favicon`/`og_image` resolution (a real bug: a full
  `https://...` URL rendered as `https:/...`, single slash, and a
  protocol-relative `//host/...` URL had its `//` stripped entirely) --
  caught by this stage's own `test_link_check.py`. Also missing Stage
  4's `Provider`-SDK `scripts` head-tag support (already fully landed
  in `ir.validate`/`ir.build`/`experimental.py`; only the HTML render
  side never got updated). Landed wholesale after confirming both gaps'
  backing symbols already exist in `main`.
- `tests/test_pack.py` (pre-existing, not in this stage's list) hardcoded
  a build's output-file set without `sbom.txt` -- a direct, expected
  side effect of this stage's own `sbom.py`. Updated the two assertions
  to match `alpha`'s own already-corrected version of the same test.

**Test coverage intentionally marked `xfail`, not silently dropped or
faked working:** three `test_binary_ir.py` cases exercise the
`--emit-arklight` CLI flag end-to-end, and one `test_config.py` case
exercises `live_streaming`'s config-driven port validation end-to-end
-- both need `cli/main.py`/`cli/live_streaming.py` wiring that's
explicitly Stage 10 scope, not this stage's. Marked `xfail(strict=True)`
with a reason pointing at Stage 10, rather than pulled forward (scope
creep) or left as unexplained red. The underlying modules
(`arklight.ir.binary`, `arklight.config.validate_live_streaming`) are
fully covered and green.

**Newly exposed by this stage, not fixed here -- deferred to Stage 14
("Full verification"), whose own scope already anticipates this:**
with `import arklight` finally working, a real `pip install -e .` +
full suite run was possible for the first time ever on this branch.
Result: 2591 passed, 4 xfailed (see above), 86 failed, plus one file
still failing to *collect*. None of the 86 are caused by this stage's
changes -- each traces to CLI wiring explicitly scoped to Stage 10
(`cli/main.py`, `cli/search.py`, `cli/live_streaming.py`: `test_deploy.py`,
most of `test_search.py`, `test_provider_search.py`,
`test_provider_custom_capability.py`, `test_rei_narrator.py`,
`test_preamble.py`'s one `_stage_logger(mode=...)` case), Stage 0's
not-yet-synced doc content and the standing `docs/Proposals/` exclusion
(`test_doc_citations.py`, `test_doc_links.py`, `test_doc_retrieval.py`),
or pre-existing gaps in already-"ported" JS runtime stages that simply
never had a working `import arklight` to be checked against before now
(`test_js_error_handling.py`'s try/catch-count assertions;
`test_js_vocabulary_v0063.py`/`_v0066.py`'s `paste`/`geolocate` registry
coverage -- the files exist, `BEHAVIOR_MODULES`/similar registries were
never updated to include them). Collection blocker: `test_action_value_from_state.py`
(Stage 8) imports `arklight.cli.search._format_action_spec`, which
doesn't exist until Stage 10. Full triage with exact test names is in
this stage's patch notes; Stage 14's own scope ("Run `main`'s full test
suite together, including every file added or expanded across Stages
1-10") is the right place to close all of these out at once, once
Stage 10 lands.
