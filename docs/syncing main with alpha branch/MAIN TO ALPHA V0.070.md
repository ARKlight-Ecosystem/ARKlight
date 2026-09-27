# Main → Alpha (v0.070) Sync Plan

**Status: planning.** `main` is currently caught up to `alpha`'s
v0.054-equivalent state (see the now-superseded `MAIN TO ALPHA
V0.54.md`, removed by this plan's Stage 0 once this sync lands). This
document stages the next catch-up: bringing `main` in line with
`alpha` at commit `0df63e7` ("v0.070 is done. now bug fixes will be
focus until main catches up") -- the exact commit `alpha` itself marks
as the v0.070 milestone boundary, not `alpha`'s current `HEAD`
(`f984fc1`, 13 commits further, all post-v0.070 bug fixes per that
commit's own message).

**Goal:** bring `main`'s code and Foundational docs in line with
`alpha` at its v0.070-equivalent state -- ten JS-vocabulary-expansion
rungs (`v0.061`-`v0.070`), user-defined components (`v0.060`), the full
six-stage `Provider` SDK, Platform API IR, the Rei compiler narrator,
search/knowledge-state additions, and assorted compiler hardening --
**excluding the Android backend/CLI entirely** (same standing exclusion
as the v0.054 plan) and, newly, **excluding the Desktop backend**
(introduced on `alpha` mid-range, ahead of `main`'s own roadmap, which
still places a Desktop backend at the later `v0.100` milestone).

Each stage below produces a reviewable patch before anything touches
`main` for real, generated against the fixed `0efdeb2` (`main`) /
`0df63e7` (`alpha`) snapshot pair.

## Ground truth this plan is based on

Diff taken between `main` (`0efdeb2`) and `alpha` (`0df63e7`):

- 338 files changed, +60,394 / −2,632 lines total.
- `arklight/`: net-new subsystems (`provider.py`, `capabilities.py`,
  `script_extension.py`, `ir/platform_api.py`, `ir/binary.py`,
  `ir/js_string.py`/`js_numeric.py`/`js_list.py`/`js_predicate.py`,
  `ir/component_dispatch.py`/`components.py`, `parser/indentation.py`/
  `preamble.py`, `compiler/asset_check.py`/`link_check.py`/
  `overdrive.py`/`sbom.py`, `compiler/rei/`, `backend/js/derivations/`
  (68 new one-per-file derivations), `backend/js/platform_apis/`,
  `backend/html/csp.py`) plus the standing `backend/android/` and the
  newly-appeared `backend/desktop/`.
- **One main-only file**, unlike the v0.054 plan's "zero main-only
  files": `.github/workflows/apt-repo.yml`. This landed on `main` after
  the v0.054 catch-up (the apt/Debian install path documented in
  `main`'s own README) and does **not** exist on `alpha`. Every stage
  below must preserve it -- nothing in this plan touches
  `.github/workflows/`.
- `docs/version history/`: `alpha` has renumbered three files as part
  of the PEP 440 version-format cleanup `main`'s README already
  documents -- `v0.043.md` → `v0.0431.md`, `v0.54.0.md` → `v0.054.md`,
  `v0.070.0.md` → `v0.070.md` -- alongside 21 new version docs
  (`v0.054.md` through `v0.078.md`; this plan only carries the sync
  through `v0.070.md`, leaving `v0.071.md`-`v0.078.md` for the next
  plan once `main` catches up here).
- `docs/Proposals/` (17 files) is new on `alpha` in this range and, like
  `docs/Backends/`, `docs/Far Future Concern/`, and
  `docs/reference/eliza/`, is a working/reference area -- see "What's
  deliberately out of scope" below.
- `tests/`: 0 main-only test files; every new/modified test on `alpha`
  in this range is additive.

## Stage 0 — Foundational docs + version history sync

Port `docs/Foundational/*.md` deltas (7 files modified: authoring
guide, CLI reference, design notes, getting-started, platform APIs,
README, what-arklight-is). Apply the three version-history renames
above and add `docs/version history/v0.054.md` through
`v0.070.md` (21 files) plus the updated `docs/version history/README.md`
index. Sync `README.md`/`CHANGELOG.md`/`PROGRESS.md` narrative content
up through the v0.070 entries, preserving `main`'s own apt-install
section untouched. Retire `MAIN TO ALPHA V0.54.md` from this folder
(superseded) once this plan's Stage 9 verification passes.

*Risk:* low. Documentation-only.

## Stage 1 — Shared plumbing ✅ ported (not yet import-clean -- see note)

Files modified on both branches that later stages build on:
`arklight/__init__.py`, `api.py`, `ast/nodes.py`, `backend/base.py`,
`config.py`, `experimental.py`, `packer/bundle.py`, `pwa.py`,
`parser/loader.py`, `compiler/pipeline.py`, `ir/__init__.py`,
`ir/build.py`, `ir/schema.py`, `ir/validate.py`. `config.py` ports with
its `android`/`desktop` `_KNOWN_SECTIONS`/`_KNOWN_KEYS` entries left
out, per Stages 11-12's standing exclusions.

**Discovered cross-stage coupling (not anticipated when this plan was
first written):** on `alpha`, these 14 files are no longer
self-contained -- porting them verbatim pulls in five imports this
plan had scoped to later stages:

- `arklight/__init__.py`, `api.py`, `compiler/pipeline.py`,
  `ir/build.py` → `arklight.ir.components` (Stage 2)
- `api.py`, `ir/build.py`, `ir/validate.py` → `arklight.provider`
  (Stage 4)
- `ir/validate.py` → `arklight.ir.platform_api` (Stage 5)
- `config.py`, `parser/loader.py` → `arklight.parser.indentation`,
  `arklight.parser.preamble` (Stage 2)

So this patch, on its own, leaves `main` **not import-clean** --
`import arklight` will raise `ModuleNotFoundError` until Stage 2's
`ir/components.py` + `parser/indentation.py` + `parser/preamble.py`,
Stage 4's `provider.py`, and Stage 5's `ir/platform_api.py` land
alongside it. Each of those five files is still reviewed and landed as
part of its own stage below, not folded into this one -- this is a
sequencing note, not a scope change. All 14 files here do parse as
valid Python in isolation (verified), so the patch itself is reviewable
on its own merits even though the tree it produces won't run tests
green until Stages 2/4/5 join it. See the revised "Sequencing notes"
at the end of this document.

*Risk:* low-medium on the diff content itself; the real risk this stage
surfaced is the import coupling above, not the line-level changes.

## Stage 2 — User-defined, reusable components (`v0.060`)

New: `arklight/ir/component_dispatch.py`, `components.py`,
`arklight/parser/indentation.py`, `preamble.py`. Test files:
`test_user_defined_components_stage0.py` through `stage4.py`,
`test_indentation.py`, `test_preamble.py`, `test_preamble_define.py`,
`test_preamble_scope.py`, `test_component_call_diagnostics.py`.

*Risk:* medium. Five internal sub-stages on `alpha`
(stage0-stage4) -- port in that order rather than as one diff, per the
same rationale Stage 4 of the v0.054 plan used for `vdom-*`/`htmx-*`.

## Stage 3 — JS vocabulary expansion ladder, all 10 rungs (`v0.061`-`v0.070`)

The largest stage by file count: 68 new one-file-per-derivation modules
under `arklight/backend/js/derivations/`, plus
`arklight/ir/js_string.py`, `js_numeric.py`, `js_list.py`,
`js_predicate.py` (the build-time mirrors), and the corresponding
`DERIVATION_REGISTRY` lines in `derivations/__init__.py`.

Rungs, in landing order (see each version's own doc for exact scope):
math siblings (`v0.061`) → string casing + comparison predicates
(`v0.062`) → small runtime primitives (`v0.063`) → math derivations
catalog (`v0.064`) → string derivations catalog (`v0.065`) →
predicates catalog (`v0.066`) → list-scalar derivations (`v0.067`) →
cross-language numeric batteries (`v0.068`) → cross-language
formatting/case batteries (`v0.069`) → capstone, `pluralize` +
`random_int` (`v0.070`).

Test files: `test_js_vocabulary_v0061.py` through `v0070.py` (10
files), plus expansions to `test_stateful_js_vocabulary_addendum.py`
and `test_vocabulary_addendum_2.py`.

*Risk:* low per rung, since each is an additive registry-fragment
pattern with no cross-rung dependency -- but port rung-by-rung anyway
so a regression traces to one specific version doc.

## Stage 4 — `Provider` SDK, all 6 stages (`v0.065`-`v0.070`)

New: `arklight/provider.py`. Test files: `test_provider.py`,
`test_provider_custom_capability.py`, `test_provider_search.py`.
Finalizes at stage 6 (`v0.070`) with the closed `PROVIDER_CAPABILITIES`
vocabulary (`auth`/`read`/`write`/`subscribe`) plus the `custom:`
namespaced escape hatch -- settled design record lands in
`docs/Foundational/PROVIDER-SDK.md` (part of Stage 0).

*Risk:* low-medium. Six sub-stages, same rung-by-rung recommendation as
Stage 3.

## Stage 5 — Platform API IR (`v0.065`, stages 1-2)

New: `arklight/ir/platform_api.py`,
`arklight/backend/js/platform_apis/{__init__,clipboard_write,notify}.py`.
Test file: `test_platform_api.py`. Doc:
`docs/Implementation/PLATFORM-API-IR-ADDENDUM.md`.

*Risk:* low. Self-contained, no shared-file overlap beyond Stage 1.

## Stage 6 — Rei compiler narrator (`v0.065`)

New: `arklight/compiler/rei/__init__.py`. Test file:
`test_rei_narrator.py`. Doc: `docs/Implementation/REI-LANGUAGE-ADDENDUM.md`.

*Risk:* low. Opt-in compiler narration layer, no behavior change to the
core pipeline.

## Stage 7 — Search/knowledge-state additions + doc tooling

Modified: `arklight/search/engine.py`, `knowledge.py`. New CLI:
`arklight/cli/deploy.py` (`arklight deploy`, `v0.06515`),
`arklight/cli/doc_retrieval.py` (`arklight search --retrieve-doc`,
`v0.064`), `arklight/cli/mdrender.py`, `arklight/cli/whats_new.py`.
Test files: `test_deploy.py`, `test_doc_retrieval.py`,
`test_doc_links.py`, `test_doc_citations.py`, `test_mdrender.py`,
`test_search_knowledge.py` (expanded), `test_search.py` (expanded).
Docs: `docs/Implementation/SEARCH-KNOWLEDGE-STATE-AND-KEYWORDS-ADDENDUM.md`,
`PROJECT-KNOWLEDGE-ADDENDUM.md`.

*Risk:* low-medium. `arklight deploy` (Wrangler-based) is the one piece
here with an external-service touchpoint -- confirm it degrades cleanly
without network access before marking this stage done.

## Stage 8 — URL state, class binding, action-arg runtime additions

New: `arklight/backend/js/runtime/action_args.py`, `query.py`,
`reveal.py`; modified `bindings.py`, `dispatch.py`, `model.py`,
`nav.py`, `notify.py`, `repeat.py`, `show.py`, `state.py`, `watch.py`.
New action: `arklight/backend/js/actions/geolocate.py`; new behavior:
`arklight/backend/js/behaviors/paste.py`. Test files:
`test_url_query_state.py` (`v0.0641`), `test_class_binding.py`,
`test_action_value_from_state.py`, plus `test_vdom_4.py`-`test_vdom_8.py`
and `test_htmx_3/4/5.py` (all expanded, not new). Doc:
`docs/Proposals/URL-STATE-AS-PRIMITIVE-PROPOSAL.md` (working reference
only -- see scope note below).

*Risk:* medium. Touches the same reactive-core runtime files Stage 4 of
the v0.054 plan already ported once; diff carefully against what's
already in `main` rather than replacing wholesale.

## Stage 9 — Compiler hardening & supply-chain tooling

New: `arklight/compiler/asset_check.py`, `link_check.py`,
`overdrive.py`, `sbom.py`; `arklight/ir/binary.py`;
`arklight/script_extension.py`; `arklight/backend/html/csp.py`. Test
files: `test_asset_check.py`, `test_link_check.py`, `test_overdrive.py`,
`test_sbom.py`, `test_binary_ir.py`, `test_arklight_file_roundtrip.py`,
`test_script_extension.py`, `test_csp.py`, `test_runtime_error_handling.py`,
`test_experimental_apis.py`, `test_devtools_console_reminder.py`,
`test_index_html_normalization.py`, `test_api_style.py`. Plus
already-existing-file test expansions: `test_package_exports.py`,
`test_pipeline_end_to_end.py`, `test_loader.py`, `test_config.py`,
`test_assets.py`, `test_pwa.py`, `tests/conftest.py`.

*Risk:* low-medium. Independent hardening features; `overdrive.py` and
`sbom.py` are the two worth a closer look since they touch build output
directly rather than just validating it.

## Stage 10 — Live-streaming/CCTV/upgrade maintenance updates

Modified only (no new files): `arklight/cli/cctv.py`,
`live_streaming.py`, `upgrade.py`, `scaffold.py`, `search.py`,
`cli/main.py`, `cli/templates/{__init__,_common,production,simple}.py`.
Test file: `test_cctv.py` (expanded).

*Risk:* low. Maintenance deltas on subsystems Stage 6 of the v0.054
plan already landed.

## Stage 11 — Android-exclusion pass (verification, standing policy)

Same exclusion as the v0.054 plan, re-verified against this range's
diff, since `alpha`'s `backend/android/` and `cli/android.py` both
picked up changes since `v0.054`:

- [ ] `arklight/backend/android/` still does not exist in `main`.
- [ ] `arklight/cli/android.py` still does not exist in `main`.
- [ ] `cli/main.py`'s Android wiring is not carried over (re-check: it
      picked up unrelated non-Android changes in this range that
      **do** need porting -- diff line-by-line, don't skip the whole
      file).
- [ ] `config.py`'s `_KNOWN_SECTIONS` still excludes `"android"`.
- [ ] `tests/test_android.py` and the two new
      `test_android_hardening.py` / `test_android_identity.py` files
      are not carried over.
- [ ] `README.md` still has zero `arklight android …` examples.

## Stage 12 — Desktop-backend exclusion (new decision needed)

`backend/desktop/` did not exist at `alpha`'s `v0.054` snapshot -- it
first landed mid-range (`be519fd`, Linux-only, explicitly marked
not-yet-cross-platform in its own commit message) and is new territory
for this plan, not a re-verification of a prior decision.

`main`'s own roadmap (`README.md` "Roadmap" section) currently places
a Desktop backend at the later `v0.100` milestone, after Android
(`v0.080`). Porting it now would put `main` ahead of its own published
roadmap on this one subsystem. Recommend treating it like Android for
this plan -- excluded pending an explicit decision -- rather than
silently deciding either way:

- [ ] Confirm with maintainer whether Desktop should land now or wait
      for its `v0.100` roadmap slot.
- [ ] If excluded: skip `arklight/backend/desktop/`, `cli/desktop.py`,
      `examples/hello_desktop/`, `docs/Backends/
      ARKLIGHT_DESKTOP_BACKEND_PROPOSAL.md` /
      `DESKTOP-BACKEND-IMPLEMENTATION.md`, `tests/test_desktop.py`.
- [ ] If included: treat it as its own Stage 12a with the same
      per-file review this plan gives every other stage, and update
      `main`'s roadmap table to reflect the pulled-forward timeline.

## Stage 13 — Root metadata

`pyproject.toml` version bump (`0.54.1` → `0.070.0` once Stages 0-12
land), `.gitignore` diff. **Do not touch `.github/workflows/
apt-repo.yml`** -- it is `main`-only, per the ground-truth note above.

*Risk:* trivial, aside from the one explicit do-not-touch.

## Stage 14 — Full verification

- Run `main`'s full test suite together, including every file added or
  expanded across Stages 1-10.
- Diff `main`'s final `arklight/` tree against `alpha`'s `0df63e7`
  minus the Android and (if excluded) Desktop exclusions -- should be
  empty except deliberate differences (version string, exclusion
  wiring).
- Re-run the Stage 11 Android checklist and, if applicable, the Stage
  12 Desktop checklist as a final pass, not just once mid-plan.
- Spot-check every doc cross-reference touched in Stages 0-10 still
  resolves.
- Delete `MAIN TO ALPHA V0.54.md` (superseded) and update this folder's
  `README.md` index/status table to point at this file instead.

## What's deliberately out of scope

- `docs/Backends/`, `docs/Far Future Concern/`, `docs/reference/eliza/`,
  and -- newly, in this range -- `docs/Proposals/` (17 files) all stay
  `alpha`-only working references, same policy the v0.054 plan applied
  to the first three. `docs/Proposals/` in particular holds proposals
  in every state from "accepted and already folded into a Foundational
  doc" (e.g. `Provider`'s, per `v0.070`'s own doc) to "still open" --
  don't assume a file's presence there means the feature it describes
  is unported; check the corresponding `docs/version history/*.md`
  entry instead.
- `docs/Implementation/` is a gray area: it holds addenda for features
  *landing in this plan* (`JS-VOCABULARY-ADDENDUM-v0.070.md`,
  `PLATFORM-API-IR-ADDENDUM.md`, `REI-LANGUAGE-ADDENDUM.md`,
  `SEARCH-KNOWLEDGE-STATE-AND-KEYWORDS-ADDENDUM.md`) alongside
  `PROJECT-KNOWLEDGE-ADDENDUM.md`, which isn't clearly tied to a shipped
  version in this range -- port the first four with their matching
  stages above, leave the last one for the next plan unless a
  version-history entry surfaces that claims it.
- `alpha`'s versions `v0.071` through `v0.078` (its current `HEAD`) are
  out of scope for this plan by design -- they're the "bug fixes"
  `0df63e7`'s own commit message defers past the v0.070 boundary. Next
  plan's job, not this one's.

## Sequencing notes

- Stage 1 must land before every other stage -- but, per the coupling
  note in Stage 1 above, it is **not sufficient on its own**:
  `main` will not import successfully until Stage 2's
  `ir/components.py`/`parser/indentation.py`/`parser/preamble.py`,
  Stage 4's `provider.py`, and Stage 5's `ir/platform_api.py` land
  alongside it. Treat Stage 1 plus those five specific files as one
  land-together unit for merge/CI purposes even though they're
  reviewed as separate patches above.
- Stages 2, 5, 6, 7, 9, 10 have no cross-dependencies on each other and
  could run in parallel once Stage 1 is in.
- Stage 3 has no hard dependency beyond Stage 1, but its 10 rungs are
  internally ordered (each rung's version doc references the prior
  one's registry shape).
- Stage 4's 6 stages are internally ordered the same way; Stage 4 and
  Stage 3 don't depend on each other.
- Stage 8 should follow Stage 3 (shares `derivations/__init__.py`
  registry surface) and should be diffed carefully against Stage 4 of
  the v0.054 plan's prior work, not treated as a clean add.
- Stages 11 and 12 are verification/decision passes, not porting work
  -- run them after every code stage above, not just once at the end.
