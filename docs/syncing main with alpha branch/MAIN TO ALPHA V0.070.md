# Main → Alpha (v0.070) Sync Plan

**Status: in progress -- target moved.** `main` is currently caught up
to `alpha`'s v0.054-equivalent state (see the now-superseded `MAIN TO
ALPHA V0.54.md`, removed by this plan's Stage 14 once this sync lands).
This document stages the next catch-up.

**Target revision history (read this before trusting any older note in
this file):**

| Revision | Commit | What it is |
| --- | --- | --- |
| Original target | `0df63e7` ("v0.070 is done. now bug fixes will be focus until main catches up") | The v0.070 milestone boundary. Stages 0-13 were written and mostly ported against this. |
| Interim head | `f984fc1` ("Closing known gaps part 13, Sync with main will be initiated") | 13 commits after the boundary. Was the "current HEAD" when this plan was first drafted. |
| **Current target** | **`23ebc24`** (2026-09-29, "Oops, Looks like it deleted the whole commit, instead of just changing the name") | **`alpha` HEAD, 23 commits after the boundary** -- the 13 above plus 10 more (bug fixes, the htmx/CSP work, `PlatformAPI.db`). |

The 23 post-boundary commits touch 47 files (+4,635 / -151). This plan
used to defer them wholesale as "`v0.071`-`v0.078`, next plan's job".
That is withdrawn: the sync now runs to `23ebc24`. Stages 0-14 keep
their numbers and their `0df63e7` ground truth (already-ported stages
are **not** re-opened -- the post-boundary delta on each file is
carried by the new Stages 15-17 instead); Stage 0, 11, 13 and 14 are
amended in place because they are still undone; Stages 15-17 are new.
The file keeps its `V0.070` name so existing links do not break.

**Goal:** bring `main`'s code and Foundational docs in line with
`alpha` at `23ebc24` (the v0.070 milestone plus the 23 commits since) -- ten JS-vocabulary-expansion
rungs (`v0.061`-`v0.070`), user-defined components (`v0.060`), the full
six-stage `Provider` SDK, Platform API IR, the Rei compiler narrator,
search/knowledge-state additions, and assorted compiler hardening --
**excluding the Android backend/CLI entirely** (same standing exclusion
as the v0.054 plan) and, newly, **excluding the Desktop backend**
(introduced on `alpha` mid-range, ahead of `main`'s own roadmap, which
still places a Desktop backend at the later `v0.100` milestone).

Each stage below produces a reviewable patch before anything touches
`main` for real. Stages 0-14 were generated against the `0efdeb2`
(`main`) / `0df63e7` (`alpha`) snapshot pair; Stages 15-17 are
generated against `0df63e7` -> `23ebc24`.

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

### Ground truth added for the `0df63e7` -> `23ebc24` range

Diff taken between `0df63e7` and `23ebc24`: 47 files changed, +4,635 /
-151, in three clusters:

- **"Closing known gaps" series** (`2bc8fc2`-`f984fc1`, 11 commits,
  2026-09-27): mostly docs (`AUTHORING-GUIDE.md` rewritten as a
  user-facing reference, `WHAT-ARKLIGHT-IS.md`, `GETTING-STARTED.md`,
  Foundational `README.md`), plus real but small code: `Site.style`/
  `style_selector`/`media_query` now refuse a bare-class name that
  collides with a built-in utility class (`arklight/api.py`,
  `tests/test_api_style.py`, `tests/test_css_structural_addendum.py`),
  `open_in_browser` in `cli/main.py` now reports a failed launch
  honestly (`tests/test_cli.py`), and `pyproject.toml`'s version moves
  to the `0.MMM.PP` scheme (`0.070` -> `0.070.0`).
- **Bug-fix day, 2026-09-27/28** (`804c7d3`-`2ed1674`): `pwa.py`
  percent-encodes precache paths; htmx no longer dies under the strict
  CSP's Trusted Types (`backend/js/htmx.py`, `backend/html/csp.py`,
  `page_render.py`, `render.py`, `runtime/notify.py`,
  `runtime/__init__.py`); boosted navigation degrades to real
  navigation on `file://` and on failed swaps; live-streaming's injected
  reload script survives `app_shell` boosting (`cli/live_streaming.py`).
  Also `arklight android sync` and Android error handling
  (`cli/android.py`, `backend/android/runtime.py`) -- **excluded**, see
  Stage 11.
- **`PlatformAPI.db`** (`f719455`, `23ebc24`): a new Platform API for
  local key/value storage -- IndexedDB on Web, SQLite on Android
  (`ir/platform_api.py`, `api.py`, `ir/validate.py`,
  `backend/js/platform_apis/db.py`, `runtime/dispatch.py`). The Android
  half (`ArkDb.kt` in `backend/android/runtime.py`) is **excluded**; the
  Web half is in scope.
- Also new on `alpha`: `docs/Implementation/APP-SHELL-ADDENDUM.md`
  (PLANNED ladder, none started) -- left out, see Stage 0.

Android-only files in this range (7, all excluded): `backend/android/
runtime.py`, `cli/android.py`, `docs/Backends/ANDROID-BACKEND-
IMPLEMENTATION.md`, `tests/test_android.py`, `test_android_db.py`,
`test_android_hardening.py`, `test_android_sync.py`. No Desktop files
were touched in this range (`db` is explicitly unimplemented for
Desktop).

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

**Amendment for `23ebc24` (Stage 0 is still undone, so it grows):**

- Foundational deltas since `0df63e7`: `AUTHORING-GUIDE.md` (+219,
  rewritten as a user-facing reference with a component vocabulary
  table and a `Provider` section; its provenance note now points at
  `96ada2c` and says `v0.070.0`), `WHAT-ARKLIGHT-IS.md` (+93),
  `PLATFORM-APIS.md` (+73, the `db` section and status-table row),
  `CLI-REFERENCE.md` (+14, includes `arklight android sync` --
  **trim**, Android is excluded), `DESIGN-NOTES.md` (+7, `db`),
  `GETTING-STARTED.md` (+6), `README.md` (index row for `Provider`).
- `docs/Implementation/PLATFORM-API-IR-ADDENDUM.md` (+15, `db`) rides
  with Stage 16; the Implementation `README.md` gains an
  `APP-SHELL-ADDENDUM.md` row on `alpha` that must **not** be carried
  over, because:
- `docs/Implementation/APP-SHELL-ADDENDUM.md` is **left out**. Its own
  header says PLANNED, six stages, none started, no version slots; it
  turns `docs/Proposals/APP-SHELL-CAPABILITY-PROPOSAL.md` (out of scope)
  into a landing order and no version-history entry claims it. Same
  gray-area rule as `PROJECT-KNOWLEDGE-ADDENDUM.md`.
- `CHANGELOG.md` gains 8 draft entries and `PROGRESS.md` ~195 lines;
  sync them up to `23ebc24`, preserving `main`'s apt-install content.
  Entries that describe Android-only work (`android sync`, `ArkDb.kt`)
  keep their text but must not imply `main` ships it.
- **Decision needed (blocks `test_doc_links.py`/`test_doc_citations.py`):**
  ported Foundational docs cite `docs/Proposals/*`, `docs/Backends/
  ANDROID-*`/`DESKTOP-*` and `docs/version history/v0.065.md`-style
  files that either stay out of scope or are not on `main` yet.
  Either rewrite those links to plain text in the `main` copies, or
  extend the docs-tree tests' allow-list for the excluded folders.
  Stage 9's triage already flagged these tests as Stage 0/Proposals
  fallout; they cannot go green before this is decided.

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

## Stage 2 — User-defined, reusable components (`v0.060`) ✅ ported

New: `arklight/ir/component_dispatch.py`, `components.py`,
`arklight/parser/indentation.py`, `preamble.py`. Test files:
`test_user_defined_components_stage0.py` through `stage4.py`,
`test_indentation.py`, `test_preamble.py`, `test_preamble_define.py`,
`test_preamble_scope.py`, `test_component_call_diagnostics.py`.

Ported as one patch rather than five internal sub-stages: checked each
new file's own imports first (`component_dispatch.py`/`components.py`
resolve to `ast/nodes.py`, `ir/build.py`, `ir/schema.py`, `ir/normalize.py`
-- all already in `main` via Stage 1 or earlier; `preamble.py` resolves
to `components.py` and `indentation.py`, both landing in this same
stage) -- no internal ordering conflict surfaced, so a single diff was
lower-risk than four artificial splits. Verified with `ast.parse` on
all four files.

Confirms the Stage 1 coupling note: `python3 -c "import arklight"`
still fails after this stage, but now for exactly the two reasons that
note predicted -- `arklight.ir.platform_api` (Stage 5) and, once that's
resolved, `arklight.provider` (Stage 4) -- not for anything Stage 2
introduced. No new forward-references found.

*Risk:* low. Confirmed no cross-dependency on Stage 4/5's still-missing
modules beyond what Stage 1 already flagged.

## Stage 3 — JS vocabulary expansion ladder, all 10 rungs (`v0.061`-`v0.070`) ✅ ported

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

Landed as one patch, not rung-by-rung: checked every new file's own
imports first -- the four new `ir/js_*.py` mirrors only reference each
other plus `ir/build.py`'s `_coerce_number` (already in `main` via
Stage 1), and every derivation module resolves against
`derivations/__init__.py`'s own registry, so there was no real
inter-rung ordering risk to preserve by splitting the diff. Verified
with `ast.parse` across all 81 new/modified files, and re-ran
`python3 -c "import arklight"` afterward: it still fails, but for the
exact same single reason as after Stage 2 (`arklight.ir.platform_api`,
Stage 5) -- this stage introduced no new forward-references.

*Risk:* low per rung, since each is an additive registry-fragment
pattern with no cross-rung dependency -- confirmed by the import check
above rather than assumed.

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

## Stage 10 — Live-streaming/CCTV/upgrade maintenance updates ✅ ported (at `0df63e7`)

Modified only (no new files): `arklight/cli/cctv.py`,
`live_streaming.py`, `upgrade.py`, `scaffold.py`, `search.py`,
`cli/main.py`, `cli/templates/{__init__,_common,production,simple}.py`.
Test file: `test_cctv.py` (expanded).

Landed from `0df63e7`, **not** from `23ebc24`: `live_streaming.py` and
`cli/main.py` moved again after the boundary, and their new versions
depend on later stages (`live_streaming.py`'s `app_shell` guard lives
with Stage 15; `main.py`'s `open_in_browser` fix with Stage 17). Taking
them now would pull those stages forward.

Android/Desktop stripping (Stage 11/12 policy applied at port time):

- `cli/main.py`: dropped the `android`/`desktop` imports, `AndroidError`/
  `DesktopError`, the two usage lines in the module docstring,
  `_cmd_android_scaffold`, `_cmd_desktop_scaffold`, `_cmd_desktop_build`,
  and the `android`/`desktop` subparser blocks. Everything else in the
  file's 768-line delta (deploy, doc retrieval, `--narrate`,
  `--emit-arklight`, `whats_new`, `mdrender`) is kept.
- `cli/templates/_common.py`: dropped the commented-out `"android"`/
  `"desktop"` config blocks from the generated `arklight.config.py`.
- Three inert mentions remain and are deliberate: a docstring
  comment in `cli/deploy.py`, a help string in `cli/doc_retrieval.py`,
  and the explanatory comment in `config.py`.

Test-file handling: `test_binary_ir.py` and `test_scaffold.py` taken
from `alpha` as-is (the three Stage 9 `xfail(strict=True)` markers on
`--emit-arklight` had all flipped to XPASS and were failing strictly --
alpha's file has no such markers). `test_config.py` **kept as `main`'s**
because alpha's version tests `android`/`desktop` config keys; only its
one Stage 9 `xfail` marker (`live_streaming` bad-port test) was removed
by hand, since Stage 10 wires that validator up.

Result: full suite went from 2591 passed / 4 xfailed / 86 failed / 1
collection error (end of Stage 9) to **2716 passed / 15 failed**. The 15
that remain, none caused by Stage 10:

- 5 `test_doc_retrieval.py`, 2 `test_doc_citations.py`, 1
  `test_doc_links.py` -- missing `docs/Proposals/README.md` /
  `docs/Backends/README.md` and links into out-of-scope folders; closed
  by Stage 0's link decision.
- 3 `test_js_error_handling.py` (try/catch-count assertions) and 4
  `test_js_vocabulary_v0063.py` (`geolocate`/`paste` registry coverage) --
  the pre-existing Stage 8 runtime-registry gaps noted under Stage 9;
  `BEHAVIOR_MODULES`-style registries still lack the new fragments.
  Belongs to a Stage 8 follow-up, not Stage 10.

*Risk:* low. Maintenance deltas on subsystems Stage 6 of the v0.054
plan already landed.

## Stage 11 — Android-exclusion pass (verification, standing policy) ✅ verified at Stage 10's tree

Same exclusion as the v0.054 plan, re-verified against this range's
diff, since `alpha`'s `backend/android/` and `cli/android.py` both
picked up changes since `v0.054`:

- [x] `arklight/backend/android/` still does not exist in `main`.
- [x] `arklight/cli/android.py` still does not exist in `main`.
- [x] `cli/main.py`'s Android wiring is not carried over (re-check: it
      picked up unrelated non-Android changes in this range that
      **do** need porting -- diff line-by-line, don't skip the whole
      file).
- [x] `config.py`'s `_KNOWN_SECTIONS` still excludes `"android"`.
- [x] `tests/test_android.py` and the two new
      `test_android_hardening.py` / `test_android_identity.py` files
      are not carried over.
- [x] `README.md` still has zero `arklight android …` examples.
- [x] **New for `23ebc24`:** `arklight android sync` (`dd85d0e`) is not
      carried over -- the `sync` subcommand wiring in `cli/main.py`,
      its `CLI-REFERENCE.md` section, and `tests/test_android_sync.py`.
- [x] **New for `23ebc24`:** `ArkDb.kt` generation in
      `backend/android/runtime.py` and `tests/test_android_db.py` are
      not carried over; `ir/platform_api.py`'s `BACKEND_PLATFORM_API_
      SUPPORT` on `main` lists `db` for `web` only (alpha lists `web`
      and `android`) -- see Stage 16.
- [x] **New for `23ebc24`:** docs prose that mentions the Android
      `db` engine (`PLATFORM-APIS.md`, `DESIGN-NOTES.md`,
      `PLATFORM-API-IR-ADDENDUM.md`) is trimmed or marked "not on this
      branch" rather than describing a feature `main` lacks.

**Result (run after Stage 10 landed, `766acd3`):** every item above
holds. What was checked and how:

- `arklight/backend/android/` and `arklight/cli/android.py` do not exist.
- `cli/main.py` and `cli/templates/_common.py` contain zero occurrences
  of "android" (case-insensitive). `arklight android` exits with
  argparse's `invalid choice`; `arklight --help` lists only `build, pack,
  unpack, pwa, deploy, new, search, live-streaming`.
- `config._KNOWN_SECTIONS`/`_KNOWN_KEYS` are `csp, experimental,
  live_streaming, rei` -- no `android`, no `desktop`.
- No `tests/test_android*.py`; no Android/Gradle/Kotlin files anywhere
  in `git ls-files`; `.github/workflows/` holds only the `main`-only
  `apt-repo.yml` and `publish.yml`.
- Root `README.md` has no `arklight android` example. Its two prose
  mentions ("Android excluded throughout", roadmap `v0.080`) are
  accurate for `main` and stay.

**Deliberately left in place (not violations):** the word "android" as
a backend *name* or in prose -- `ir/platform_api.py`'s
`BACKEND_PLATFORM_API_SUPPORT["android"] = frozenset()` and its
`check_backend_support` error path (covered by `test_platform_api.py`),
`register_backend("android")` in `test_user_defined_components_stage3.py`,
docstrings in `api.py`/`provider.py`/`experimental.py`/`render.py`/
`ir/component_dispatch.py`, and the explanatory comment in `config.py`.
These are the shared Platform API IR and component-dispatch
vocabulary, identical on `alpha`, and name a backend without
implementing it. Removing them would diverge `main` from `alpha` for no
exclusion benefit.

**Not part of this stage, still open:** Foundational docs on `main`
(`CLI-REFERENCE.md`, `DESIGN-NOTES.md`, `ARCHITECTURE.md`,
`GETTING-STARTED.md`, `V1-DEFINITION.md`) already describe `arklight
android` and pre-date this sync (`main` at `4609718` has the same
mentions). Stage 0 owns deciding whether to trim them; the `android
sync` section `alpha` added to `CLI-REFERENCE.md` after `0df63e7` must
not be carried over.

**Now enforced by the suite:** `tests/test_android_exclusion.py` (9
tests) turns this checklist into something Stage 14's "re-run as a
final pass" is a `pytest` call rather than a manual grep. Mutation-checked:
creating an empty `arklight/cli/android.py` makes it fail. Full suite
after this stage: 2725 passed / 15 failed (same 15 as after Stage 10;
the 9 new tests all pass).

## Stage 12 — Desktop-backend exclusion ✅ excluded, verified (go/no-go still the maintainer's)

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
- [x] If excluded: skip `arklight/backend/desktop/`, `cli/desktop.py`,
      `examples/hello_desktop/`, `docs/Backends/
      ARKLIGHT_DESKTOP_BACKEND_PROPOSAL.md` /
      `DESKTOP-BACKEND-IMPLEMENTATION.md`, `tests/test_desktop.py`.
- [ ] If included: treat it as its own Stage 12a with the same
      per-file review this plan gives every other stage, and update
      `main`'s roadmap table to reflect the pulled-forward timeline.

**Result (run on `main` at `40f10d4`, Stage 11 upstream):** the "if
excluded" branch was executed and holds. This was already the working
assumption of Stages 1 and 10 (`config.py` never learned a `desktop`
section; `cli/main.py` and `templates/_common.py` were ported with all
Desktop wiring stripped), so this stage's job was to verify it and make
it enforceable, not to remove anything.

- All nine Desktop-only paths `alpha` has at `23ebc24` are absent on
  `main`: `arklight/backend/desktop/{__init__,runtime}.py`,
  `arklight/cli/desktop.py`, `examples/hello_desktop/{.gitignore,
  README.md,arklight.config.py}`, `docs/Backends/ARKLIGHT_DESKTOP_
  BACKEND_PROPOSAL.md`, `docs/Backends/DESKTOP-BACKEND-IMPLEMENTATION.md`,
  `tests/test_desktop.py`.
- `arklight desktop ...` exits with argparse's `invalid choice`;
  `config._KNOWN_SECTIONS` is `csp, experimental, live_streaming, rei`;
  `cli/main.py` and `templates/_common.py` contain no "desktop".
- No Desktop files changed on `alpha` between `0df63e7` and `23ebc24`,
  so nothing in Stages 15-17 can reintroduce this.
- `main`'s roadmap (`README.md`, `ARCHITECTURE.md`) already places the
  Desktop backend at `v0.100`, after Android (`v0.080`); nothing to
  edit there. `.github/workflows/apt-repo.yml` untouched.

**Left in place (not violations):** the shared Platform API IR and
component-dispatch vocabulary that names `desktop` as a backend without
implementing it (`ir/platform_api.py`'s `"desktop": frozenset()`,
`test_platform_api.py`'s `backend_name="desktop"` case, docstrings in
`api.py`/`provider.py`/`render.py`/`component_dispatch.py`), the "phone vs
desktop" CSS/`Show` examples, and two dangling prose references to a
command `main` lacks: `cli/deploy.py`'s docstring ("same reasoning as
`arklight desktop build`'s `make` call") and `cli/doc_retrieval.py`'s
`--backends` help string. Both are byte-identical on `alpha`; reword
them only if you want `main` to stop mentioning the command at all.

**Still open, and only yours to answer:** the first checkbox. The plan
recommended exclusion "pending an explicit decision" and this stage
applied that recommendation; it does not settle whether Desktop lands
early. If you want it in, that is **Stage 12a** -- per-file review of the
nine paths above, `config.py`'s `desktop` section/keys (which must be
added back together with `android`'s, per the comment in `config.py`, or
split deliberately), a `Backend` registration, and a roadmap-table edit
-- and `tests/test_desktop_exclusion.py` must be deleted in that same
change.

**Now enforced by the suite:** `tests/test_desktop_exclusion.py` (13
tests), sibling of Stage 11's guard. Mutation-checked: creating an empty
`arklight/backend/desktop/__init__.py` makes it fail.

## Stage 13 — Root metadata ✅ ported

`pyproject.toml` version bump, `.gitignore` diff. **Do not touch
`.github/workflows/apt-repo.yml`** -- it is `main`-only, per the
ground-truth note above.

**Amendment for `23ebc24`:** the version target is no longer `0.070`.
`alpha` migrated to the `0.MMM.PP` scheme (`f984fc1`), so its version
at `23ebc24` is `0.070.0`. `main` currently reads `0.54.1`, which is
the very leading-zero-loss shape that migration's `CHANGELOG.md` entry
describes (`v0.054` shipped as `0.54.0`). Confirm with the maintainer
whether `main` jumps to `0.070.0` (which `importlib.metadata`
normalizes to `0.70.0` in `arklight --version`) or takes another
number; `tests/test_version.py` and `tests/test_upgrade.py` both read
the version and must be re-run after the bump. Also keep `arklight/
__init__.py`'s `CHANNEL = "main"` (it regressed to `"alpha"` twice
during earlier stages).

*Risk:* trivial, aside from the one explicit do-not-touch and the
version-number decision.

**Result (run on `main` at `4ada548`, Stage 1 upstream):**

- `pyproject.toml` `version`: `0.54.1` -> **`0.070.0`** (alpha's value at
  `23ebc24`). Version-number decision taken as the plan's first option;
  `importlib.metadata` normalizes it, so `arklight --version` prints
  `arklight 0.70.0` and `arklight.__version__` is `0.70.0`.
  `CHANNEL` is still `"main"`. `tests/test_version.py` passes.
  (`tests/test_upgrade.py` does not exist on `main`; the only tests
  reading the version are `test_version.py` and `test_sbom.py`.)
- **Two `pyproject.toml` differences from `alpha` kept on purpose, not
  ported.** `alpha` still has the legacy `license = { text = ... }` plus
  a `License ::` classifier; `main` moved to the SPDX string
  `license = "GPL-3.0-or-later"` with `classifiers = []` in the
  `ed77192` "Workflow update" commit, and nothing in this range
  changes that reasoning. Taking alpha's block would silently undo a
  `main`-only packaging change.
- **`.gitignore` difference kept on purpose, not ported.** The diff is
  one line: `main` has `ARK/`, `alpha` does not. `main` added it in
  Stage 9 (`4609718`) and it never existed on `alpha`, so this is
  `main`-only, not something `alpha` deleted after the fact. Porting
  the diff literally would drop it.
- `.github/workflows/apt-repo.yml` untouched (verified: no diff under
  `.github/`).
- Left as-is deliberately: `docs/Foundational/WHAT-ARKLIGHT-IS.md`
  says the *published* package is `0.54.1`. That stays accurate until
  a release is actually cut from this version; Stage 0 owns that prose.

**Now enforced by the suite:** `tests/test_root_metadata.py` (6 tests):
version scheme and value, installed-metadata normalization, `CHANNEL`,
`apt-repo.yml` present, and the two `main`-only differences above.
Full suite: **2744 passed / 15 failed** -- the same 15 as Stages 10-12
(8 docs-tree tests awaiting Stage 0's link decision, 7 Stage 8 runtime
registry gaps); the 6 new tests all pass.

## Stage 15 — htmx under Trusted Types, CSP, and `file://`/live-streaming fallbacks (new, `0df63e7` -> `23ebc24`) ✅ ported

Commits: `e9da11d`, `2ed1674`, `3a933df`, `85a8eee` (the live-streaming
half). The bug: on `Site(app_shell=True)` every boosted link died under
the strict CSP because htmx's response parse is a Trusted Types sink.

Modified: `arklight/backend/js/htmx.py` (+131: the vendored htmx is now
the byte-for-byte upstream literal plus one anchored Trusted Types
patch, policy `arklight-htmx`; fails at import if a future htmx bump
breaks an anchor), `backend/html/csp.py` (`trusted-types default
arklight-htmx`), `backend/html/page_render.py`, `backend/js/render.py`,
`backend/js/runtime/__init__.py`, `backend/js/runtime/notify.py` (+161:
`wireHtmxErrorHandling` degrades a dead boosted link to one real
navigation; `disableBoostOnFileProtocol()` and the `file://` notice),
and `cli/live_streaming.py` (+34: the injected reload `<script>` gets
`id` + `hx-preserve` when `app_shell` is on, so boosted navigation does
not open a new `EventSource` per click).

Tests: new `test_htmx_trusted_types.py` (392 lines) and
`test_htmx_failure_handling.py` (275 lines); expanded `test_htmx_4.py`,
`test_csp.py`, `test_live_streaming.py`.

*Dependencies:* Stage 8 (`render.py` and `runtime/__init__.py` are its
shared integration files -- diff against what Stage 8 already landed,
do not overwrite wholesale), Stage 9 (`csp.py`). `live_streaming.py`
needs `WebsiteIR.app_shell`, which `main` already has from the htmx-4
stage (verified on `main`'s `ir/build.py`). No Android or Desktop
content in this stage.

*Risk:* medium. Same reactive-core/runtime files as Stage 8, and the
htmx patch is exact-match-anchored, so it needs the vendored htmx
literal on `main` to match `alpha`'s. Checked: both are htmx 2.0.10, so
the anchors should apply; run `test_htmx_trusted_types.py` to confirm.

**Result (run on `main` at `a44525b`, Stage 14 upstream):**

- Before touching anything, confirmed `main`'s copies of the seven source
  files were byte-identical to `alpha@0df63e7` except `htmx.py` and
  `page_render.py`, which differed only in doc-path comments. Only the
  four listed commits touched these files on `alpha`, so the
  `main`-vs-`23ebc24` delta was exactly this stage's delta and nothing
  else -- the files were taken from `23ebc24` whole rather than merged
  hunk by hunk. Stage 8's `render.py`/`runtime/__init__.py` work is
  preserved because `alpha`'s versions already contain it.
- Ported: `backend/js/htmx.py`, `backend/html/csp.py`,
  `backend/html/page_render.py`, `backend/js/render.py`,
  `backend/js/runtime/__init__.py`, `backend/js/runtime/notify.py`,
  `cli/live_streaming.py`. Tests: new `test_htmx_trusted_types.py` (392
  lines) and `test_htmx_failure_handling.py` (275); expanded
  `test_htmx_4.py`, `test_csp.py`, `test_live_streaming.py`.
- The risk flagged above did not materialise: the vendored htmx literal
  matched (2.0.10 both sides), every Trusted Types patch anchor applied,
  and `import arklight` succeeds. Node (`/usr/bin/node`) is present, so
  the Node-executed cases in the two new files ran rather than skipped
  (46 passed, 0 skipped).
- **Android/Desktop:** no imports, wiring or config. The ported files
  mention Android WebView only as prose (why `moveBefore` and Trusted
  Types matter on current Chromium) and one comment cites
  `android/runtime.py` as the behaviour `wireHtmxErrorHandling` mirrors.
  Byte-identical on `alpha`, so left in place under Stage 11's rule
  about prose that names a backend without implementing it. Both
  exclusion guards still pass.
- Suite: **2816 passed / 8 failed** (was 2763 / 8). The same 8
  docs-tree failures as Stage 14 -- Stage 0's link decision. The 53 new
  passes are the stage's tests.
- Stage 14's remaining-diff table: the "htmx / CSP / `file://`" row and
  the five Stage 15 test files are now closed; re-check them on the
  final Stage 14 run.

## Stage 16 — `PlatformAPI.db`, Web half only (new, `f719455`, `23ebc24`) ✅ ported

New: `arklight/backend/js/platform_apis/db.py` (IndexedDB engine, plus
a `window.arkDbBridge` hook that only the excluded Android backend
sets -- keep the hook, it is inert on the Web). Modified:
`arklight/ir/platform_api.py` (`db` registered, `DB_OPERATIONS`,
`BACKEND_PLATFORM_API_SUPPORT` -- **`web` only on `main`**),
`arklight/api.py` (`PlatformAPI.db.set/get/delete/keys`; shares the file
with Stage 17, see below), `arklight/ir/validate.py`
(`_validate_platform_db`, +122), `backend/js/platform_apis/__init__.py`
(+3), `backend/js/runtime/dispatch.py` (the `"platform:"` branch
resolves `Bind(...)` args and passes the page store).

Tests: `test_platform_api_db.py` (544 lines; Node-executed against an
IndexedDB stub and a fake Android bridge -- the fake-bridge cases test
the JS side only and stay). Doc: the `db` parts of `PLATFORM-APIS.md`,
`DESIGN-NOTES.md`, `PLATFORM-API-IR-ADDENDUM.md` ride with Stage 0.

**Not carried over:** `ArkDb.kt` in `backend/android/runtime.py` and
`tests/test_android_db.py` (Stage 11).

*Dependencies:* Stage 5 (`ir/platform_api.py`, `platform_apis/`), Stage
8 (`dispatch.py`), Stage 1 (`validate.py`).

*Risk:* low-medium. New, additive, but `dispatch.py` changes an
existing branch every Platform API call goes through; re-run
`test_platform_api.py` alongside.

**Result (run on `main` at `a44525b` + Stage 15):**

- `main`'s copies of every file here matched `alpha@0df63e7`, so the
  delta against `23ebc24` was exactly this stage's plus Stage 17's
  `api.py` hunk. Per the plan, `api.py` landed **once**, whole, carrying
  both: `PlatformAPI.db` and the custom-class collision guard
  (`RESERVED_UTILITY_CLASSES`, `_bare_class_names`, `allow_redefine=`
  on `Site.style`/`style_selector`/`media_query`). Its two tests,
  `test_api_style.py` and `test_css_structural_addendum.py`, came with
  it, so **Stage 17's `api.py` item is done**; what remains there is
  `cli/main.py`'s `open_in_browser` hunk and `pwa.py`.
- Ported from `23ebc24`: `platform_apis/db.py` (new),
  `platform_apis/__init__.py`, `runtime/dispatch.py`,
  `ir/platform_api.py`, `ir/validate.py` (`_validate_platform_db`),
  `api.py`; tests `test_platform_api_db.py` (new, 544 lines, Node-run).
  `test_platform_api.py` needed no change and passes alongside, as the
  risk note asked.
- **Trimmed for the Android exclusion (the judgment call Stage 14
  flagged):** `BACKEND_PLATFORM_API_SUPPORT["android"]` stays
  `frozenset()`, `db` is `web`-only. The `platform_api.py` module and
  comment prose that credited `ArkDb.kt`, and two `api.py` docstrings
  that said Android implements `db`, were reworded to say the Android
  half lives on `alpha`. In `test_platform_api_db.py` the Android
  support assertions were rewritten to match (`db` rejected for
  `android` with the standard "not implemented by backend" error;
  `--search` reports `implemented by : web`) and the one test about
  Android's *other* capabilities was dropped as meaningless here.
- **Kept on purpose:** `db.py`'s `window.arkDbBridge` hook and the Node
  test that runs it against a fake bridge. The hook is inert on the Web
  and only ever set by the excluded Android backend; the test exercises
  the JS side only. `db.py`'s module docstring still describes the
  Android host in prose, identical to `alpha`.
- Not carried over, as planned: `ArkDb.kt` and `tests/test_android_db.py`.
- Suite: **2867 passed / 8 failed** (was 2816 / 8). Same 8 docs-tree
  failures; both exclusion guards, `test_root_metadata`, and
  `test_version` pass.
- This makes Stage 14's remaining-diff rows for `PlatformAPI.db` and for
  `api.py` closed. `ir/platform_api.py` will still differ from `alpha` on
  purpose (the `android` entry and its prose).

## Stage 17 — Small post-v0.070 deltas (new) ✅ ported

One patch each, all verified independent of Stages 15-16 except `api.py`:

- **`arklight/api.py` -- land once, with Stage 16.** Two unrelated
  changes share the file: `PlatformAPI.db` (Stage 16) and the
  custom-class collision guard (`_bare_class_names`; `Site.style`/
  `style_selector`/`media_query` raise when a bare class name collides
  with a built-in utility class unless `allow_redefine=True`; commits
  `2bc8fc2`, `2fd11e7`, `ce62681`, `028f4e7`). Tests:
  `test_api_style.py`, `test_css_structural_addendum.py` (+67).
- **`arklight/cli/main.py`** (`19c5d0b`): `open_in_browser` returns
  `bool(webbrowser.open(...))` instead of an unconditional `True`.
  Test: `test_cli.py` (+17). Apply as a hunk on top of Stage 10's
  version -- the file's other post-boundary delta, `arklight android
  sync` (`dd85d0e`), is **excluded**.
- **`arklight/pwa.py`** (`804c7d3`): precache paths are percent-encoded
  so one unencodable filename cannot fail `cache.addAll()` and leave the
  service worker stuck. Test: `test_pwa.py` (+22). The same commit's
  `cli/android.py` and `tests/test_android.py` changes are excluded.
- **`pyproject.toml`:** version, handled by Stage 13.

*Risk:* low.

**Result (run on `main` at `33eafae` + Stage 16):**

- **`api.py`:** already landed whole with Stage 16, as planned (collision
  guard, `test_api_style.py`, `test_css_structural_addendum.py`).
- **`pwa.py`** (`804c7d3`): precache paths percent-encoded via
  `quote(p, safe="/")`. Taken from `23ebc24` (the file matched
  `0df63e7` on `main`, so the delta was exactly this commit). Test:
  `test_pwa.py` +22.
- **`cli/main.py`** (`19c5d0b`): applied as a **single-function hunk**,
  not a file copy -- `open_in_browser` now returns
  `bool(webbrowser.open(...))`. Everything else in `alpha`'s `main.py`
  delta is Android/Desktop wiring, which stays out; `git diff` of the
  file against `main` is 10 added / 6 removed lines, all in that one
  function. `arklight android sync` (`dd85d0e`) is not carried over.
- **`test_cli.py` was a bigger gap than the plan said.** The plan lists
  only `+17` for this file, but `main`'s copy was missing **220 lines**
  that `alpha` already had at the `0df63e7` boundary and no earlier
  stage had ported it: the `[Rei]` nudge and config suppression,
  `search --retrieve-doc` (Stage 7 features), design-token breakout
  refusal, the "Did you mean" suggestion for misspelled components, and
  the `arklight deploy site.py` diagnostic. The file was taken whole
  from `23ebc24` and **every added test passes against `main`'s
  existing source**, so no source gap was hiding behind it -- it was
  purely un-synced coverage. No Android or Desktop content in it.
- Suite: **2890 passed / 8 failed** (was 2867 / 8). Same 8 docs-tree
  failures; both exclusion guards, `test_root_metadata`, `test_version`
  pass.
- Code-stage checklist: with this, **Stages 1-13 and 15-17 are ported**.
  The only stages left are **0** (docs/version-history/CHANGELOG/PROGRESS
  sync plus the link decision that owns the last 8 red tests) and
  **14** (re-run after Stage 0).

## Stage 14 — Full verification (runs last -- after Stages 15-17) ⚠️ pre-flight run done, re-run required

- Run `main`'s full test suite together, including every file added or
  expanded across Stages 1-10 and 15-17. Baseline going in: 2716 passed /
  15 failed (end of Stage 10, see that stage's triage).
- Diff `main`'s final `arklight/` tree against `alpha`'s **`23ebc24`**
  (not `0df63e7`) minus the Android and (if excluded) Desktop exclusions -- should be
  empty except deliberate differences (version string, exclusion
  wiring).
- Re-run the Stage 11 Android checklist and, if applicable, the Stage
  12 Desktop checklist as a final pass, not just once mid-plan.
- Spot-check every doc cross-reference touched in Stages 0-10 still
  resolves.
- Delete `MAIN TO ALPHA V0.54.md` (superseded) and update this folder's
  `README.md` index/status table to point at this file instead.

**Result of the pre-flight run (on `main` after Stage 13, `42a3b59`;
diffed against `23ebc24`).** Stage 14 was run *before* Stages 0 and
15-17, at the maintainer's request, so it is a triage, not the final
sign-off this section describes: the diff below cannot be empty until
those four stages land. What it did establish:

*Closed here* -- gaps earlier stages left behind that no later stage
owns, all found by diffing rather than by a failing test alone:

- `arklight/backend/js/actions/__init__.py` and `behaviors/__init__.py`
  (Stage 8): `geolocate.py` and `paste.py` existed but were never added
  to the registries. Taken from `alpha`. Clears the 4
  `test_js_vocabulary_v0063.py` failures.
- `tests/test_js_error_handling.py`: `main`'s copy pre-dated `v0.065`
  (`arkNotify` -> `arkReportError`, third `platform:` branch). Taken from
  `alpha`; clears the 3 `try {` count failures. Together with the row
  above these were the "7 Stage 8 runtime-registry gaps" of Stages 9-13.
- Stale doc paths in comments/docstrings (`docs/DESIGN-NOTES.md`,
  `docs/Backends/...`) in 12 `arklight/` files and 8 test files --
  comment/docstring/string-literal only, taken from `alpha`. The
  paths pointed at files that do not exist on `main`.
- `tests/test_upgrade.py` (new, pre-boundary; covers the PEP 668 retry in
  `cli/upgrade.py`, which Stage 10 had already ported) and the
  `test_html_head_meta.py` / `test_html_page_render.py` expansions
  (`Provider` `scripts` head tags; integral-float `Bind` formatting).
  All three pass against `main`'s code as-is, so no source gap hid
  behind them.
- `examples/hello_site/site.py`: `alpha` uses the preamble
  (`# include <stdlib.ARKlight>`) instead of `from arklight import *`.
  Built both; output is byte-identical, so the preamble system Stage 2
  ported works end to end.
- `MAIN TO ALPHA V0.54.md` deleted and this folder's index updated;
  the two prose mentions in `CHANGELOG.md`/`PROGRESS.md` now say
  "since retired".

*Remaining `arklight/` diff against `23ebc24`, every file attributed*
(34 files before this stage, 20 after -- 12 were doc-path comments
only and 2 were the Stage 8 registries above):

| Bucket | Files | Owner |
| --- | --- | --- |
| Post-`0df63e7` htmx / CSP / `file://` | `backend/js/htmx.py`, `backend/html/csp.py`, `backend/html/page_render.py`, `backend/js/render.py`, `backend/js/runtime/__init__.py`, `runtime/notify.py`, `cli/live_streaming.py` | Stage 15 |
| `PlatformAPI.db` (Web half) | `backend/js/platform_apis/db.py` (new), `platform_apis/__init__.py`, `runtime/dispatch.py`, `ir/platform_api.py`, `ir/validate.py`, `api.py` | Stage 16 |
| Small deltas | `api.py` (collision guard, shared with 16), `pwa.py`, `cli/main.py` (`open_in_browser` hunk only) | Stage 17 |
| Deliberate `main` differences | `__init__.py` (`CHANNEL`), `config.py` + `cli/templates/_common.py` (no `android`/`desktop`), `cli/main.py` (no android/desktop wiring), `compiler/sbom.py` (no ACC section), `capabilities.py` (`alpha`-only, absent) | Stages 1, 9, 10-12 |
| Excluded | `backend/android/`, `backend/desktop/`, `cli/android.py`, `cli/desktop.py` | Stages 11-12 |

Two pieces of `platform_api.py` are Stage 16 *and* need a judgment call
when it lands: `BACKEND_PLATFORM_API_SUPPORT["android"]` must stay
`frozenset()` on `main`, and the docstring that credits Android's
`ArkDb.kt` must be trimmed.

*Remaining test-tree diff:* `test_csp`, `test_htmx_4`,
`test_htmx_failure_handling`, `test_htmx_trusted_types`,
`test_live_streaming` (Stage 15); `test_platform_api_db` (Stage 16);
`test_api_style`, `test_css_structural_addendum`, `test_cli`, `test_pwa`
(Stage 17); `test_capabilities`, `test_sbom`, `test_config`,
`test_version` (deliberate: ACC, Android/Desktop config, `CHANNEL`);
`test_root_metadata` is `main`-only by design.

*Checklists re-run:* `tests/test_android_exclusion.py` (9) and
`tests/test_desktop_exclusion.py` (13) pass. `.github/workflows/`
holds `apt-repo.yml` and `publish.yml`; `apt-repo.yml` is the only file
under `.github/` that differs from `alpha`, as intended.

*Suite:* **2763 passed / 8 failed** (was 2744 / 15). The 8 are the
docs-tree tests -- `test_doc_citations` (2), `test_doc_links` (1),
`test_doc_retrieval` (5) -- blocked on Stage 0's link decision and
`docs/Foundational/` sync (4 files differ: `AUTHORING-GUIDE`,
`CLI-REFERENCE`, `DESIGN-NOTES`, `PLATFORM-APIS`), not on code.

*Not done, because it belongs to other stages:* the doc cross-reference
spot-check (cannot pass until Stage 0), and the final "diff is empty
except deliberate differences" sign-off. **Re-run this stage after
Stages 0, 15, 16 and 17.**

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
- ~~`alpha`'s versions `v0.071` through `v0.078` ... next plan's job.~~
  **Withdrawn.** The post-boundary bug fixes are now in scope through
  `23ebc24` (Stages 15-17). What is still out of scope: anything on
  `alpha` *after* `23ebc24`, and `docs/version history/v0.071.md`-
  `v0.078.md` if they exist there (the Project Knowledge ladder those
  numbers are reserved for has no code in this range).

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
- Stage 15 follows Stage 8 (shared `render.py`/`runtime/__init__.py`)
  and Stage 9 (`csp.py`). Stage 16 follows Stage 5, and lands `api.py`
  together with Stage 17's `api.py` hunk. Stage 17's other pieces are
  independent. Stage 14 runs after all of them.
- Stages 11 and 12 are verification/decision passes, not porting work
  -- run them after every code stage above, not just once at the end.
