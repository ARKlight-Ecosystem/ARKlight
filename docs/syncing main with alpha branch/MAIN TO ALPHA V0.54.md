# Main → Alpha (v0.054) Sync Plan -- ✅ COMPLETE

**Status: all stages (0-9) done.** `main`'s code and Foundational docs
are caught up to `alpha`'s v0.054-equivalent state. Verified directly
against the working tree, not just this plan's checklist: `main`'s
`pyproject.toml` is at `version = "0.54.0"`; `arklight/backend/js/`
carries `htmx.py`, `vdom.py`, the full `runtime/` and `derivations/`
module sets; the CSS and HTML backends carry their split modules
(`at_rules.py`, `selectors.py`, `attrs.py`, `head_meta.py`,
`page_render.py`, `routing.py`, `tag_map.py`, etc.); `arklight/search/`
exists in full; `cli/live_streaming.py` and `cli/cctv.py` are present;
and every test file named in Stages 2-6 below (`test_vdom_4.py`
through `test_vdom_8.py`, `test_htmx_3/4/5.py`, `test_refactor_0.py`,
`test_css_backend.py`/`test_css_selectors.py`/
`test_css_structural_addendum.py`/`test_responsive_style.py`,
`test_html_attrs.py`/`test_html_head_meta.py`/`test_html_page_render.py`/
`test_html_routing.py`/`test_html_tag_map.py`, the `test_search*.py`
suite, `test_live_streaming.py`, `test_event_modifiers.py`) exists in
`main`'s `tests/`. The Stage 8 Android-exclusion checklist below is
fully satisfied -- no `arklight/backend/android/`, no
`arklight/cli/android.py`, no Android wiring in `cli/main.py`, no
`"android"` in `config.py`'s `_KNOWN_SECTIONS`, no `test_android.py`,
and zero `arklight android …` mentions in `main`'s `README.md`.

**Goal:** bring `main`'s code and Foundational docs in line with `alpha`
at its current v0.054-equivalent state (reactive-core JS backend, CSS
rewrite, search engine, live-streaming/CCTV, etc.), **excluding the
Android backend/CLI entirely**, while keeping `alpha`'s
`Backends/`, `Far Future Concern/`, and `new js backend proposal/`
doc folders as alpha-only working references (not ported to `main`).

Each stage below produces a reviewable patch before anything touches
`main` for real. No stage assumes the previous one has been merged
upstream — they're generated against a fixed snapshot of both
branches and can be rebased if `alpha` or `main` move.

## Ground truth this plan is based on

Diff taken between `main` (`f3eaf95`) and `alpha` (`c4a75f4`):

- 132 files changed, +32,101 / −2,294 lines total.
- `arklight/`: 67 files differ — 49 net-new, 18 modified. **Zero
  main-only files** — `main`'s code is a strict subset of `alpha`'s,
  so this is a one-directional catch-up, not a three-way merge.
- `tests/`: same shape — 0 main-only test files.
- Root docs (`README.md`, `CHANGELOG.md`, `PROGRESS.md`) and
  `pyproject.toml` all differ; `alpha` is ahead on all of them.
- Android is cleanly isolated: 2 backend files + 1 CLI file, wired in
  through ~29 lines in `cli/main.py` and 3 lines in `config.py`. No
  other subsystem imports or depends on it.

## Stage 0 — Foundational docs sync ✅ done

Patch already generated (`stage0-docs-sync.patch`). Replaced `main`'s
flat `docs/ARCHITECTURE.md` / `docs/DESIGN-NOTES.md` with byte-identical
copies of `alpha`'s `docs/Foundational/*.md` (6 files + README), and
repointed every internal link in `README.md` / `PROGRESS.md` /
`CHANGELOG.md` to the new path. Verified every resulting link resolves.

## Stages 1–7 — code, in dependency order ✅ done

Each stage below is scoped to land and pass its own tests before the
next starts, mirroring the order the features actually landed in
`alpha` so later stages can assume earlier ones are already in place.

### Stage 1 — Shared plumbing ✅ done

The 18 files modified on both branches that everything else builds on
top of, ported first so later stages apply cleanly:

`arklight/__init__.py`, `api.py`, `ast/nodes.py`, `backend/base.py`,
`compiler/pipeline.py`, `ir/build.py`, `ir/schema.py`, `ir/validate.py`,
`packer/bundle.py`, `packer/seal.py`, `pwa.py`,
`cli/templates/{__init__,production,simple}.py`.

Plus new, foundational-but-standalone modules other stages depend on:
`arklight/config.py` (site-config plumbing — **ported minus its
`"android"` entry in `_KNOWN_SECTIONS` and the accompanying comment**),
`arklight/experimental.py` (the experimental-API gate used by later
stages).

*Risk:* low-medium. No new user-facing behavior by itself, but touches
files everything else depends on, so this is where import-order or
signature-mismatch problems would surface first.

### Stage 2 — CSS backend rewrite ✅ done

New: `backend/css/{at_rules,base_stylesheet,custom_styles,
design_tokens,selectors}.py`. Modified: `backend/css/render.py`.
Corresponds to alpha's v0.048 milestone (`@media` + `<head>`
extension). Test files: `test_css_backend.py`, `test_css_selectors.py`,
`test_css_structural_addendum.py`, `test_responsive_style.py`.

*Risk:* low. Self-contained backend, no Android touchpoints.

### Stage 3 — HTML backend refactor ✅ done

New: `backend/html/{attrs,head_meta,page_render,routing,tag_map}.py`.
Modified: `backend/html/render.py`. This is the `html-2`…`html-6`
staging alpha itself used (see the now-deleted `REFACTOR-INDEX.md`,
preserved in the Stage-0-adjacent backup if you want the original
staging rationale). Test files: `test_html_attrs.py`,
`test_html_head_meta.py`, `test_html_page_render.py`,
`test_html_routing.py`, `test_html_tag_map.py`,
`test_html_backend.py` (expanded).

*Risk:* low-medium. Pure extraction/refactor per alpha's own docs, but
touches the most heavily-used render path in the codebase.

### Stage 4 — JS backend: HTMX + reactive core (vdom) ✅ done

New: `backend/js/{htmx,vdom}.py`, `backend/js/runtime/{__init__,
bindings,dispatch,model,nav,notify,repeat,show,state,watch}.py`,
`backend/js/derivations/{__init__,compare,count,format,join,multiply,
sum}.py`. Modified: `backend/js/render.py`. This is the largest single
stage — alpha's `refactor-0` + `htmx-1..5` + `vdom-4..8` combined
(computed state, watch effects, two-way binding, list rendering,
show/hide, event modifiers, `localStorage` persistence).

Test files: `test_refactor_0.py`, `test_htmx_{3,4,5}.py`,
`test_vdom_{4,5,6,7,8}.py`, `test_event_modifiers.py`,
`test_js_backend.py` / `test_js_error_handling.py` (expanded),
`test_stateful_js_vocabulary_addendum.py` (expanded).

*Risk:* medium-high. Largest surface area, most interdependent internal
stages (each `vdom-*`/`htmx-*` stage in alpha explicitly depended on
the previous one landing first — see dependency column of the old
`REFACTOR-INDEX.md` table). Recommend porting `refactor-0` → `htmx-1`
→ `htmx-2` → `htmx-3` → `htmx-4` → `htmx-5` → `vdom-4` → … → `vdom-8`
as sub-steps within this stage rather than one large diff, so a
regression is traceable to a specific sub-stage.

### Stage 5 — Search engine ✅ done

New: `arklight/search/{__init__,_tokenize,endpoint,engine,feedback,
graph,knowledge,ranking,retrieval,stats}.py`, `cli/search.py`. Test
files: `test_search*.py` (8 files), `test_search_endpoint.py`,
`test_search_engine_facade.py`.

*Risk:* low. Fully independent subsystem, no shared-file overlap with
Stages 2–4 beyond the Stage-1 plumbing.

### Stage 6 — Live-streaming, CCTV, upgrade, scaffold extras ✅ done

New: `cli/live_streaming.py`, `cli/cctv.py`, `cli/upgrade.py`,
`cli/templates/_common.py`. Modified: `cli/scaffold.py` (test-only
diff, per earlier `tests/test_scaffold.py` delta). Wires into
`config.py`'s `_KNOWN_SECTIONS` (the `"live_streaming"` entry — keep
this, only `"android"` is excluded) and `cli/main.py`.

Test files: `test_live_streaming.py`, `test_config.py`
(new), `test_cli.py` (expanded).

*Risk:* low-medium. Independent features, but this is also where
`cli/main.py` gets its non-Android wiring — see the Android-exclusion
checklist below for exactly what to leave out of that file.

### Stage 7 — Root metadata ✅ done

`pyproject.toml` version bump (`0.42.3` → alpha's current version),
`.gitignore` diff (3 lines).

*Risk:* trivial.

## Stage 8 — Android-exclusion pass (verification, not new work) ✅ done, all checks pass

Not a porting stage — a checklist run after Stages 1–7 to confirm
Android never made it in:

- [x] `arklight/backend/android/` does not exist in `main`.
- [x] `arklight/cli/android.py` does not exist in `main`.
- [x] `cli/main.py` has no `from arklight.cli import android` / `from
      arklight.cli.android import AndroidError`, no `android_parser`
      subcommand block, no `_cmd_android_scaffold`. Verified: no
      "android" string appears anywhere in `cli/main.py`.
- [x] `config.py`'s `_KNOWN_SECTIONS` contains `"live_streaming"` but
      not `"android"`; the adjacent comment referencing
      `arklight.cli.android` is removed. Verified:
      `_KNOWN_SECTIONS = {"live_streaming"}`.
- [x] `tests/test_android.py` is not carried over.
- [x] `README.md`'s user-facing usage section has no `arklight
      android …` examples (the 5 mentions found in `alpha`'s
      `README.md`). Verified: zero matches in `main`'s `README.md`.
- [x] `CHANGELOG.md` / `PROGRESS.md` retain their historical Android
      prose as-is (55 / 16 mentions) — these are narrative records of
      what happened on `alpha`, not `main`'s feature surface, so they
      are **not** scrubbed.

## Stage 9 — Full verification ✅ done

- Run `main`'s full test suite (all ported + pre-existing tests)
  together — first real point where cross-stage interaction bugs would
  show up.
- Diff `main`'s final `arklight/` tree against `alpha`'s minus the
  Android exclusions above — should be empty except deliberate
  differences (version string, any Android wiring lines).
- Spot-check that every doc cross-reference in `README.md` /
  `PROGRESS.md` / `CHANGELOG.md` that got touched during the code
  stages still resolves (same check as Stage 0, extended to code-doc
  links introduced in Stages 1–7).

## What's deliberately out of scope

- `docs/Backends/`, `docs/Far Future Concern/`, `docs/new js backend
  proposal/` stay `alpha`-only working references. Not copied to
  `main` at any stage.
- No attempt to reconcile `alpha`'s own stale README links (7 of 9
  doc-links in `alpha`'s `README.md` still point to the pre-move flat
  doc paths) — flagged separately, fixed only if asked.

## Sequencing notes

- Stages 1–7 are listed in dependency order but Stages 2, 3, and 5 have
  no cross-dependencies on each other — they could be reordered or
  done in parallel if that's preferred. Stage 4 should not start before
  Stage 3 (the HTML/JS `attrs.py` split affects the HTMX attribute
  work). Stage 6 has no hard dependency on 2–5 beyond Stage 1.
- Each stage's patch will include only that stage's files plus any
  test files that exercise them, so each one is independently
  reviewable and revertible.
