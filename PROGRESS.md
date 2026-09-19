# ARKlight Progress

Living document tracking what's implemented, key decisions made along
the way, and what's queued up next. Update this file at the end of
every work session, not just at milestone boundaries.

Detail sections below are kept in reverse-chronological order (newest
first) and are the narrative record -- what was tried, what was
rejected, what broke. For the plain version history, see
[`CHANGELOG.md`](./CHANGELOG.md); for a short, user-facing overview of
each shipped milestone, see
[`docs/version history/README.md`](./docs/version%20history/README.md);
for the architecture-level roadmap
table, see [`docs/Foundational/ARCHITECTURE.md`](./docs/Foundational/ARCHITECTURE.md).

## Snapshot

| Version  | What                                                       | Status  |
|----------|------------------------------------------------------------|---------|
| v0.001   | Python -> HTML                                              | DONE    |
| v0.002   | CSS (default stylesheet)                                    | DONE    |
| v0.003   | JavaScript helpers + two vocabulary addenda                 | DONE    |
| v0.0035  | Stateful JS (`State`/`Bind`/`Action.*` registries)           | DONE    |
| v0.004a  | CLI scaffolding (`arklight new`)                             | DONE    |
| v0.036   | ARK Bundle spec v1 (`arklight pack`)                         | DONE    |
| v0.037   | Sealed ARK Bundles (encrypted by default, `arklight unpack`) | DONE    |
| v0.041   | CLI/pipeline/JS runtime hardening + stateful JS addenda I/II | DONE    |
| v0.042   | Extra CSS features: custom classes (`Site.style(...)`), `arklight search <name>`, `arklight --help`/bare `arklight` | DONE |
| vdom-1   | Reactive-core vdom staging, Stage 1 of 8: vendored snabbdom bare core swapped into `State`'s re-render pass | DONE |
| vdom-2   | Reactive-core vdom staging, Stage 2 of 8: reactive class binding (`Bind.when(...)`/`bind_class=`) | DONE |
| vdom-3   | Reactive-core vdom staging, Stage 3 of 8: event modifiers (`.with_modifiers(...)`/`.debounce(...)`/`.throttle(...)`) | DONE |
| vdom-4   | Computed/derived state (`Computed`/`Derive.*`/`DERIVATION_REGISTRY`) -- docs/Backends/REFACTOR-INDEX.md row 12 | DONE |
| vdom-5   | Watch effects (`Watch(...)`, reuses the action dispatcher) -- docs/Backends/REFACTOR-INDEX.md row 13 | DONE |
| vdom-6   | Two-way input binding (`bind_value=Bind.model(...)` -> `data-ark-model`) -- docs/Backends/REFACTOR-INDEX.md row 14 | DONE |
| vdom-7   | Per-item list rendering (`Repeat`) + conditional show/hide (`Show`) -- docs/Backends/REFACTOR-INDEX.md row 15 | DONE |
| vdom-8   | `localStorage` persistence for `State(..., persist=True)` -- docs/Backends/REFACTOR-INDEX.md row 16, the last stage of the combined reactive-core refactor | DONE |
| v0.0431  | Emergency patch: build-time warning for unrouted `srcset`/`poster`/`action`/`formaction` | DONE |
| v0.048   | CSS `@media` queries + `<head>`/`<header>` extension (Stage A of 2: `meta`/`links` DONE; Stage B of 2: `responsive_style` + `@media` compilation DONE) | DONE |
| v0.054   | JS backend capability expansion (reactive core parity with Vue 3) -- renumbered from v0.044 now that v0.048 has shipped; all 8 vdom-staging stages above are now DONE | DONE |
| v0.060   | User-defined, reusable components -- renumbered from v0.100     | DONE |
| v0.060-stage0 | User-defined components, Stage 0 of 4: registration API (`component`/`Prop`), props contract, Option A macro expansion pass, cycle/depth guards, experimental `mode="registry"` selector -- `docs/Foundational/USER-DEFINED-COMPONENTS-IMPLEMENTATION.md` | DONE |
| v0.060-stage1 | User-defined components, Stage 1 of 4: `arklight search` typo-suggestion integration for registered user components (`arklight/search/knowledge.py`'s `component_symbol_fact`/`build_knowledge_base(components=...)`) | DONE |
| v0.060-stage2 | User-defined components, Stage 2 of 4: default styling hook (`component(..., default_style={...})`) -- folded into the site's stylesheet under `.{ComponentName}` (only for components a build actually uses) and onto the rendered subtree's own root `class_name`, so a caller doesn't have to pass `class_name=` by hand | DONE |
| v0.060-stage3 | User-defined components, Stage 3 of 4: Option B's real differentiator, per-backend render dispatch (`.register_backend(backend_name)`/`register_backend_render`) -- a `mode="registry"` component's identity survives (via a tagged prop, lifted onto `IRNode.component_origin`) far enough that `HTMLBackend` can supply its own render function for a component, falling back to the shared default when it doesn't; `arklight/ir/component_dispatch.py` (new module) resolves this once per backend, after the shared `WebsiteIR` already exists | DONE |
| v0.060-stage4 | User-defined components, Stage 4 of 4 (final): component-owned state (`component(..., state={...})`/`ComponentState`) -- a component's own local, instance-scoped `State(...)`-equivalent, hoisted onto its owning page under a uniquely-namespaced key per call site (`arklight/ir/components.py`'s `_hoist_component_state`/`_rewrite_component_state_refs`), so `Bind(...)`/`Action.*(...)`/`bind_class=`/`bind_value=` all work exactly like they would against a page-level `State(...)`, with zero changes to Normalization/Validation/any backend | DONE |
| v0.061   | JS vocabulary addendum, stage 1 of 10: math siblings (`Derive.subtract`/`.divide`/`.min`/`.max`) -- `docs/Implementation/JS-VOCABULARY-ADDENDUM-v0.070.md` | DONE |
| v0.062   | JS vocabulary addendum, stage 2 of 10: string-casing siblings + comparison predicates (`Derive.uppercase`/`.trim`, `Predicate.equals`/`.gt`/`.lt`) -- `docs/Implementation/JS-VOCABULARY-ADDENDUM-v0.070.md` | DONE |
| v0.063   | JS vocabulary addendum, stage 3 of 10: `Action.geolocate(name)`, clipboard `paste` behavior, `State(..., media=...)` (`matchMedia`-driven boolean state), `reveal`/`lazy` behavior (`on_reveal=`, `IntersectionObserver`), debounced/throttled `Bind.model(...)` -- `docs/Implementation/JS-VOCABULARY-ADDENDUM-v0.070.md` | DONE |
| v0.064   | `arklight search --retrieve-doc` -- doc-tree retrieval mode (`--foundational`/`--backends`/`--proposals`/`--implementation`/`--js-backend`/`--far-future`/`--version-history`, plus `--file NAME`) on the existing `search` subcommand, fully wired into `arklight/cli/main.py`/`arklight/cli/doc_retrieval.py`; `tests/test_doc_retrieval.py` (48 tests incl. `test_cli.py`) passing. Landed ahead of its own `docs/Implementation/SEARCH-RETRIEVE-DOC-ADDENDUM.md` staging writeup, which was never actually filed -- see `docs/Proposals/SEARCH-RETRIEVE-DOC-PROPOSAL.md` for the accepted proposal this shipped from | DONE |
| v0.0641  | Emergency patch: URL query-parameter state -- `State(..., query="page", history="push")`, extending the existing `persist=`/`media=` precedent: two-way sync with a URL query parameter, typed coercion (`_query_type_tag`, bool checked before int), `history="replace"`/`"push"` write-back via `history.replaceState`/`pushState`, and a new `wireQuerySync` `popstate` listener (`arklight/backend/js/runtime/query.py`) gated by `has_query` -- `docs/Proposals/URL-STATE-AS-PRIMITIVE-PROPOSAL.md`. Out-of-band, numbered inside the v0.064 -> v0.065 gap, same "capability fixes take priority" treatment as `v0.0431`'s bug-fix patch; `tests/test_url_query_state.py` (44 tests) passing | DONE |
| v0.0642  | Docs-only incremental patch: rewrote `docs/Foundational/WHAT-ARKLIGHT-IS.md`'s one-sentence definition (new `docs/Foundational/README.md` index row) so ARKlight is stated as a **compiler framework** rather than leaning on "static-site compiler" as the load-bearing noun -- Section 4 now names, explicitly, that ARKlight is not a static-site generator, not a frontend framework, and not a UI framework, instead of leaving that distinction implied. Filed alongside it: `docs/Proposals/PLATFORM-API-IR-PROPOSAL.md` (new `docs/Proposals/README.md` index row) -- the next capability fix identified against `SYSTEM-DESIGN-AGREEMENTS.md`'s "Compiler First, Runtime Last" rule: a platform API interface layer in the compiler IR (notifications, clipboard, filesystem, device info, ...), Web as the default implementation, Android/Desktop earning individual interfaces only once mature. Proposal filed as **Proposed**, not yet accepted; no code changed this patch. Out-of-band, numbered inside the v0.064 -> v0.065 gap, same slot-sharing precedent as `v0.0431`/`v0.0641` | DONE |
| v0.0643  | Docs-only incremental patch: rewrote `arklight/__init__.py`'s module docstring so it opens with the same **compiler framework** wording `v0.0642` gave `docs/Foundational/WHAT-ARKLIGHT-IS.md`, instead of the older "Python-first compiler for building static websites" framing; quickstart example swapped a stateless `Button` for `State`/`Action.increment` so the closed-vocabulary interactivity primitives are visible on first import. No code changed. Out-of-band, numbered inside the v0.064 -> v0.065 gap, same slot-sharing precedent as `v0.0431`/`v0.0641`/`v0.0642` | DONE |
| v0.0644  | Docs-only incremental patch: added a new "The Goal" section to `docs/Foundational/WHAT-ARKLIGHT-IS.md` -- comparable-to-frontend-framework DX while enforcing ARKlight's own philosophy (`SYSTEM-DESIGN-AGREEMENTS.md`), for two named audiences, the Python Community and the Education Community. Filed alongside it: new `docs/Foundational/V1-DEFINITION.md` -- what `v1.0`/"Stable compiler" (`ARCHITECTURE.md`'s Milestones table) concretely means (deterministic, fails-loudly, no-breaking-vocabulary-change reliability), scoped explicitly to the Web Developing parts of the compiler only, with named exclusions (native backends, CLI conveniences beyond `build`, everything gated by `arklight/experimental.py`, `Provider`/Rei/Project Knowledge/`arklight assistant`, and -- called out specifically -- **ARKlight Component Collections**, a newly-named, not-yet-proposed concept for curated bundles of `@component`-registered content built on `USER-DEFINED-COMPONENTS.md`'s macro-expansion path, whose own release cadence is deliberately independent of the compiler's stability claim). Also documents "capability fix" (first recognized at `v0.0641`) as the mechanism and evidence trail behind `v1.0`'s reliability claim -- each capability fix landed is a checkable step toward the point where that supply runs dry. New index rows in `docs/Foundational/README.md` and `docs/README.md`; `ARCHITECTURE.md`'s `v1.0` milestone row now links to `V1-DEFINITION.md` instead of standing unexplained. Also fixed two pre-existing doc-index drifts noticed while editing `docs/README.md`'s Foundational Folder Guide table: `WHAT-ARKLIGHT-IS.md` and `PLATFORM-APIS.md` were both present in `docs/Foundational/README.md`'s own index but missing from this table, and this row's own predecessor (`v0.0643`) had a literal `\n` instead of a real line break, merging it with the `v0.064-v0.070 (remainder)` row below -- both fixed in this pass. No code changed. Out-of-band, numbered inside the v0.064 -> v0.065 gap, same slot-sharing precedent as `v0.0431`/`v0.0641`/`v0.0642`/`v0.0643` | DONE |
| v0.0645  | Docs-only incremental patch: documented `arklight/capabilities.py` (the ACC capability-discovery hook, landed undocumented at `a4aa6b8`) for the first time anywhere in this doc tree -- new `docs/Foundational/ACC-CAPABILITIES.md` (settled design record: entry-point contract, diagnostics, API, its one current caller `compiler/sbom.py`, status against ACC's own five-stage implementation ladder). Corrects `V1-DEFINITION.md` Section 5's now-stale "no design doc yet, not-yet-proposed concept" framing, since ACC has since become a real repository (`Rae-ARK/ARKlight-Component-Collections`) with its own foundational design doc and a landed Stage 1. New index rows in `docs/Foundational/README.md` and `docs/README.md`; `README.md`'s repository-layout listing gains a `capabilities.py` line (previously missing despite the file existing since `a4aa6b8`). No code changed. Out-of-band, numbered inside the v0.064 -> v0.065 gap, same slot-sharing precedent as `v0.0431`/`v0.0641`/`v0.0642`/`v0.0643`/`v0.0644` | DONE |
| v0.0646  | Docs-only incremental patch: fixed a real self-contradiction in `docs/Foundational/V1-DEFINITION.md` Section 5 -- the "zero special-cased compiler support" bullet, unchanged since `v0.0644`, was left asserting exactly that in the same section `v0.0645` had just amended to say the capability-discovery hook (`arklight/capabilities.py`, compiler-side code by its own docstring's admission) had landed; narrowed the bullet's claim to Collection *content* specifically, with the hook named as the one, already-acknowledged exception. Also adds an explicit reverse rule to `docs/README.md`'s "Adding a new doc" section: deleting a file that leaves the `docs/Proposals/`/`docs/Implementation/`/`docs/Backends/`/`docs/Far Future Concern/` lifecycle and removing its index row (in that folder's own `README.md` *and* this file's Folder Guide table) are one change, not two -- closing the gap the existing rule left (add/update covered, removal wasn't). Also fixed this table's own `v0.0645` row, which had picked up a literal `\n` merging it with the `v0.064-v0.070 (remainder)` row below -- the identical defect `v0.0644`'s own row fixed for `v0.0643` two rows above, recurring. No code changed. Out-of-band, numbered inside the v0.064 -> v0.065 gap, same slot-sharing precedent as `v0.0431`/`v0.0641`-`v0.0645` | DONE |
| v0.0647  | Docs-only incremental patch: rewrote the root `README.md` as a short, Chromium-style landing page -- large logo + `# ARKlight` heading, and every section below the quickstart trimmed to a two-line pointer (the pattern the "Status" section already used, per `docs/README.md`'s "Adding a new doc" rule). The three pieces of content that had no canonical home anywhere else -- the `pip`/Debian-package install instructions, the annotated repository layout, and the `pytest` workflow -- moved verbatim into new `docs/Foundational/GETTING-STARTED.md` rather than staying in the README where they'd drift the way `docs/README.md`'s own "Why this section exists" already documents happened before. `docs/Foundational/ARCHITECTURE.md`'s "Repository" section repointed from `README.md#repository-layout` to `GETTING-STARTED.md#repository-layout`. New index rows in `docs/Foundational/README.md` and `docs/README.md`'s Foundational Folder Guide table. `ARKlight-logo.png` (added at `e0fddb7`, previously unreferenced anywhere) wired into the README for the first time. No code changed. Out-of-band, numbered inside the v0.064 -> v0.065 gap, same slot-sharing precedent as `v0.0431`/`v0.0641`-`v0.0646` | DONE |
| v0.0648  | Docs-only incremental patch, part 2 of `v0.0647`: actually rewrote the root `README.md` (the previous pass had landed the supporting docs but left the README itself untouched, still carrying the full duplicated Install/Repository-layout/Running-tests content `GETTING-STARTED.md` now owns). Root `README.md` is now the landing page `v0.0647` described: centered logo + `# ARKlight Framework` heading (amends `v0.0647`'s row, which said `# ARKlight`), the pitch and quickstart kept, an Install section reduced to the one `pip` command plus a pointer, and every other topic -- CLI, compiler pipeline, authoring API, repository layout, tests, non-goals, backends, proposals, version history -- collapsed into a single `## Documentation` section pointing at `docs/README.md` as the one index, Chromium-`README.md`-style, rather than a separate two-line pointer per topic that would itself need upkeep. Fixed the one link this broke: `docs/Foundational/CLI-REFERENCE.md`'s `README.md#cli` anchor (that heading no longer exists) now points at the Documentation section instead; `docs/Foundational/AUTHORING-GUIDE.md`'s README description updated to match. No code changed. Alpha-branch only. Out-of-band, numbered inside the v0.064 -> v0.065 gap, same slot-sharing precedent as `v0.0431`/`v0.0641`-`v0.0647` | DONE |
| v0.0649  | Docs-only incremental patch, part 3 of `v0.0647`: moved the root `README.md`'s inline site-example code block (`Page(Heading(...), Text(...), Button(...))` + `arklight build`/output lines) into a new "Example" section in `docs/Foundational/GETTING-STARTED.md`, between Install and Repository layout. The root README was the one place still restating actual component-API surface -- exactly the kind of content that drifts as the API grows, unlike a fixed `pip install -e .` command or a pointer link. Root `README.md`'s Install section now reads pitch, one install command, one pointer -- nothing left in it that the component API, CLI, or repository layout could make stale. Updated `GETTING-STARTED.md`'s own intro line (\"pitch and quickstart\" -> \"pitch\", since the quickstart moved here) and its repository-layout comment on `examples/hello_site/` (previously \"Example site matching the root README\", now stale since the README no longer holds an example to match; repointed at this doc's new Example section instead). No code changed. Alpha-branch only. Out-of-band, numbered inside the v0.064 -> v0.065 gap, same slot-sharing precedent as `v0.0431`/`v0.0641`-`v0.0648` | DONE |
| v0.0650  | Capability fix: preamble directives -- `# include <stdlib.ARKlight>` / `# include <acc.<dotted.module.path>>` / `# define <alias> -> <target>`, reserved-shape comments ARKlight's own loader parses and resolves itself (`arklight/parser/preamble.py`, new module), replacing reliance on raw `from X import *` for the step that gets vocabulary names into a site file's namespace. Fixes the one namespace-binding step the compiler's existing "fail loudly, no silent winner" doctrine (`DuplicateComponentError`, `CapabilityError`) didn't yet cover: two includes disagreeing on a name now raise `PreambleCollisionError` naming both sources, instead of Python's own star-import silently keeping whichever ran last. `arklight/parser/loader.py` wires the resolved bindings in before `exec`; new "Preamble directives" section in `docs/Foundational/AUTHORING-GUIDE.md`. `from arklight import *` keeps working unchanged -- purely additive. `tests/test_preamble.py` (18 tests); full suite 1425 passed. `0.0641` -> `0.0650` version bump. Out-of-band, numbered inside the v0.064 -> v0.065 gap, same "capability fixes take priority" treatment as `v0.0431`/`v0.0641` | DONE |
| v0.06501 | Capability fix follow-up to `v0.0650`: `from arklight import *` retired (still works; every build logs a notice naming file/line and the `# include <stdlib.ARKlight>` replacement); the two things the preamble couldn't see now fail loudly -- a site file rebinding a name its own preamble bound (`def`/assignment/import/star import, checked after `exec`), and a user `@component` named like a built-in, which silently replaced every built-in of that name (`register_component` now refuses it unless `allow_redefine=True`); `# define` split the way the rest of the compiler is -- applied in normalization (a rename), raised in validation, plus a new duplicate-define check. `arklight/parser/preamble.py`/`loader.py`, `arklight/ir/components.py`; scaffolds/example/docs moved to the preamble syntax. `tests/test_preamble.py` 18 -> 43; full suite 1454 passed. `0.0650` -> `0.06501`; roadmap `v0.065` untouched. Out-of-band, same slot-sharing precedent as `v0.0650` | DONE |
| v0.06502 | Capability fix follow-up to `v0.06501`: `# define` is now C's `#define` (name replaced by text, token-based, per file, one pass; no longer an alias between included objects), the preamble is read in **every** Python file ARKlight takes in (project modules via an import hook scoped to the site directory; `arklight.config.py`) instead of the site file only, and `# include <stdlib.ARKlight>` is the whole public API (`CSSSyntaxError`, `DuplicateStyleNameError`, `ComponentError`, `DuplicateComponentError` added to `__all__`, with a structural test). Preamble parser is now a directive registry; `# use` is reserved and refused, with `docs/Proposals/USE-PREAMBLE-PROPOSAL.md` (discussion, **not accepted**). `arklight/parser/preamble.py`/`loader.py`, `arklight/config.py`; production scaffold migrated. Collision-picking `# define` removed (behavior change, in `CHANGELOG.md`). Tests: `test_preamble_define.py` +41, `test_preamble_scope.py` +18, 11 obsolete removed; full suite 1502 passed. `0.06501` -> `0.06502`; roadmap `v0.065` untouched. Out-of-band, same slot-sharing precedent | DONE |
| v0.06503 | Capability fix: live-input -> action-value -- `Bind("name")` accepted as `Action.set`/`Action.append`'s `value` (`{"__state__": name}` marker, opt-in per argument via `ActionSpec.state_args`, build-time validated, resolved by `resolveActionArgs` at dispatch time), so `[type a task] [Add]` is expressible with `bind_value=Bind.model(...)` + `Watch(..., then=Action.reset(...))`. Issue-register #7; `docs/Proposals/ACTION-VALUE-FROM-STATE-PROPOSAL.md`. Also fixes a raw `TypeError` on `Action.append(name, Bind(...))`. `tests/test_action_value_from_state.py` (31 tests); full suite 1538 passed. `0.06502` -> `0.06503`; roadmap `v0.065` untouched. Out-of-band, same slot-sharing precedent | DONE |
| v0.06504 **(draft -- version slot unconfirmed)** | Bug fix: `trusted_script_origins` CSP directive injection -- `_render_csp_meta_tag` spliced entries verbatim into `script-src`; `'unsafe-inline'`/`'unsafe-eval'` (quoted or not) and directive-breaking characters (`;`, whitespace) now raise a build-time `ValueError` at `Site.__init__` instead of silently reaching the emitted CSP. `docs/Proposals/CSP-TRUSTED-ORIGIN-INJECTION-BUGFIX.md`. Landed in code (`arklight/api.py`, `tests/test_csp.py`) without a version bump or this row -- added retroactively during a docs-consistency pass; a maintainer should confirm the slot and pyproject bump | DONE (code) / DRAFT (record) |
| v0.064-v0.070 (remainder) | JS vocabulary addendum, stages 4-10 of 10 (math/string/list-scalar derivation catalogs, predicates catalog, cross-language "batteries included" numeric/formatting idioms, capstone `pluralize`/`random_int`) -- `docs/Implementation/JS-VOCABULARY-ADDENDUM-v0.070.md`; per-stage `docs/version history/` previews marked PLANNED until each lands. `v0.065`-`v0.070` additionally carry `Provider`'s six-stage ladder (`docs/Implementation/PROVIDER-SDK-ADDENDUM.md`), one stage per version -- accepted, independent piece of work sharing this range's milestone slots | PLANNED |
| v0.065 (interleaved third piece) | Rei, the compiler narrator -- `--narrate` flag on `arklight build` (sibling to `--verbose`/`--debug`) narrating pipeline stages in natural language, plus a `rei` config section (`default_mode`) for a project-wide default log mode -- `docs/Implementation/REI-COMPILER-NARRATOR-ADDENDUM.md`. One version, no ladder; accepted and interleaved into `v0.065` after the other two pieces above were already reserved there, same "make room for one more" precedent as `v0.041`/`v0.064` | PLANNED |
| v0.065 (interleaved fourth piece) | Platform API IR, stage 1 of 2: Web reference implementation -- `PlatformAPI.notify(...)`/`PlatformAPI.clipboard_write(...)` on `on_click=`, compiler-owned interface registry (`arklight.ir.platform_api`), validation, HTML attribute compilation, Web JS fragments + click-dispatch wiring, and `check_backend_support` actually enforced during a build -- `docs/Implementation/PLATFORM-API-IR-ADDENDUM.md`, accepted from `docs/Proposals/PLATFORM-API-IR-PROPOSAL.md`. Stage 2 (Android/Desktop native implementations) stays unscheduled, gated on each backend's own maturity. Interleaved into `v0.065` as a fourth piece, same "make room for one more" precedent as Rei above | DONE |
| v0.071-v0.078 | Project Knowledge, stages 1-8 of 8: compiler-owned `.arklight/` project-local knowledge directory (foundation, internal providers/facts/observations abstraction, Git as first provider, persistent project context, compiler build history, diagnostics integration, historical observations, future-provider open slot) -- `docs/Implementation/PROJECT-KNOWLEDGE-ADDENDUM.md` | PLANNED |
| v0.079   | `arklight assistant` -- Miko MVP, Stage A of `docs/Proposals/ARKLIGHT-ASSISTANT-CLI-PROPOSAL.md`'s sequencing amendment: `--wake-up-miko` wraps the already-shipped `v0.064` `arklight search --retrieve-doc` in-process as her one sanctioned tool, no `.arklight/`/Project Knowledge access. Experimental CLI feature (same gated, loudly-labeled-provisional posture as `docs/Foundational/EXPERIMENTAL-APIS.md`'s build-time escape hatches); permanence undecided until `v0.080` ships. `--wake-up-raeliana` is a stub that logs Raeliana's current proposal stage rather than launching an assistant -- her implementation stays unauthorized until Stage A's dogfooding period trips the amendment's fabrication/inconsistency trigger | PLANNED |
| v0.080   | Android backend (`arklight android` -- `androidx.webkit.WebViewAssetLoader` packaging, evolving the existing `ARKlight-Viewer-for-Android-Devices` app into the runtime) -- renumbered from v0.100; Stages 0-4 of the staged CLI ladder done (CI build/smoke-test/release-build), Stages 5/6/7 (the local-toolchain counterparts) not started | IN PROGRESS |
| v0.100   | Desktop backend (`arklight desktop` packaging) -- renumbered from v0.080; Stages 1-4 (`arklight desktop scaffold`, Linux-only GTK3/WebKit2GTK native host; CI build/smoke-test/packaging) done, Stages 5-7 (the local-toolchain counterparts) not started | IN PROGRESS |
| v1.0     | Stable compiler                                              | PLANNED |

### Planned, not yet scheduled to a version

- **User-defined functions.** Next up after `v0.060` (user-defined
  *components*) finishes its staged ladder -- distinct from
  components: reusable *logic* a project can register and have the
  compiler treat as a first-class name (parallel to how `Derive.*`/
  `Action.*` are each a closed, described vocabulary rather than an
  arbitrary expression string), as opposed to reusable *markup*. No
  design doc yet -- noted here only so the direction isn't lost before
  one exists. Not to be confused with a page function
  (`@site.page("/")`) or a component's own `render_fn`, both of which
  are already "user-defined functions" in the plain Python sense.

Design-sketched in `docs/DESIGN-NOTES.md`, explicitly waiting on a
go-ahead before implementation starts on any of these:

- **KaiOS backend.** Design complete --
  `docs/Far Future Concern/KAIOS-BACKEND-IMPLEMENTATION.md` (plus the
  constraint-gathering doc in the same directory,
  `kaios-app-design-doc.md`) -- but pulled back out of the numbered
  roadmap (it briefly held `v0.120`, assigned in the same reshuffle
  that produced `v0.060`/`v0.080`/`v0.100` above -- see
  `docs/ARCHITECTURE.md`'s "Renumbered" note for that history, and the
  amendment immediately below it for this reversal). No committed
  version number or scheduled slot -- the same "Far Future Concern"
  tier `docs/Far Future Concern/WINDOWS-PHONE-BACKEND.md`'s Windows
  Phone/UWP backend already sits at: a written, plausible design with
  no roadmap commitment behind it.

## v0.079 -- `arklight assistant` Miko MVP, Stage A (PLANNED)

Opens the `arklight assistant` subcommand described in
`docs/Proposals/ARKLIGHT-ASSISTANT-CLI-PROPOSAL.md`, built to the
order its appended "Sequencing Amendment: Miko First, Raeliana On
Trigger" argues for and its "Maintainer Decision" section accepts:
Miko before Raeliana, doc-only before Project Knowledge, and nothing
built that a dogfooding period hasn't earned yet.

`--wake-up-miko` gets exactly one sanctioned tool: an in-process
wrapper around `arklight/cli/doc_retrieval.py`'s retrieval function --
the same primitive `v0.064` already shipped for `arklight search
--retrieve-doc` -- called directly rather than shelled out to via
`subprocess`, so a multi-tool-call REPL turn doesn't pay a fork/exec
tax per lookup. No `.arklight/` access of any kind: Project Knowledge
(`v0.071`-`v0.078`) isn't finished, and wiring Miko to a
still-in-flight knowledge system would tangle "is the assistant
useful" together with "is Project Knowledge returning the right
things" into one unreadable experiment.

Shipped as an **experimental CLI feature** -- gated and labeled
provisional the same way `docs/Foundational/EXPERIMENTAL-APIS.md`
already treats build-time escape hatches that step outside ARKlight's
settled default surface, even though the mechanism here is a CLI
notice rather than that file's `arklight/experimental.py` registry
(this is a dev-time CLI convenience, not compiled output, so it isn't
added to that registry). Whether `arklight assistant` earns a
permanent, unflagged spot in the CLI is explicitly not decided by this
milestone; that's revisited once `v0.080` (Android backend) ships,
alongside whatever Stage B's dogfooding log says about Raeliana.

`--wake-up-raeliana` ships too, but only as a status stub: since her
Stage C trigger (a fabrication or inconsistency failure Miko produces
on a query plain doc retrieval could have answered) hasn't had a
chance to fire yet, the flag prints her current stage per the
proposal instead of launching a matching engine that would pre-empt
the experiment. See the base proposal's Maintainer Decision section
for the exact wording.

Design complete; implementation not started.

## v0.06503 -- Capability fix: live-input -> action-value (DONE)

Out-of-band, same slot-sharing precedent as `v0.0650`-`v0.06502`; numbered
`0.0650` plus decimals, roadmap `v0.065` untouched. Picked from the issue
register (#7) as the one open item it labels a *capability* gap.

**Reproduced first:** `Action.append("tasks", Bind("draft"))` passed
Validation and then raised `TypeError: Object of type ARKNode is not JSON
serializable` in the HTML backend.

**Decisions.** Spelling is `Bind("draft")` in an argument position (no new
name; `Bind`'s docstring already promised "wherever a literal value is
accepted"). Wire shape is a plain dict, `{"__state__": name}`, not a
dataclass, because dataclasses nested in `ActionRef.args` lose their tag in
`.arklight` encoding (the known `ItemIndexRef` gap). Opt-in per argument
(`ActionSpec.state_args`) and only `set`/`append`'s `value`: `increment`'s
delta from an input would string-concatenate. Resolution is at dispatch
time and returns a fresh object. The resolver is inlined in both
dispatchers rather than a new top-level function because existing
Node-driven tests evaluate `WIRE_WATCHERS_JS` standalone, and
`test_htmx_3` forbids `forEach` in the interceptor body (hence a `for`
loop).

**Verified.** 31 new tests, two of them Node-driven against the real
fragments (mutation-checked: disabling resolution fails both). One-off
jsdom run of a fully built site: add, add again, input cleared by the
`Watch`, debounced click reading the value at fire time. jsdom prints
XPath errors from vendored HTMX; they also occur on a literal-only page.

**Not done, on purpose:** `Bind` nested inside list/dict arguments;
Enter-to-submit; numeric actions reading state (`increment`'s `delta` from
a numeric `State` would be safe, but is not distinguishable from an
input-bound string, since `State`s are untyped to the compiler).

## v0.06502 -- Capability fix follow-up: `# define` fixed, preamble everywhere, stdlib complete (DONE)

Out-of-band, same slot-sharing precedent as `v0.0650`/`v0.06501`;
numbered `0.0650` plus decimals, roadmap `v0.065` untouched.

**`# define`.** `v0.06501` made it an alias between included objects --
a second way to bind names, next to the one directive that exists for
that. It is now what the word says, lifted from C: the left name is
replaced by the right text before the file runs, nothing is bound.
Implemented on tokens (`tokenize`), not regex, so strings, comments and
f-strings are never touched and `Btn` never matches `Btn2`; f-string
contents are skipped explicitly so behavior is identical on Python
3.10-3.13 (3.12 tokenizes f-strings into real NAME tokens, earlier
versions do not). One pass, no rescan, with a validation rule making the
missing rescan loud instead of surprising. The loader now discovers and
executes the define-applied source; every substitution is one line, so
line numbers still match. A post-substitution parse check turns "syntax
error in code I never wrote" into an error naming the defines in effect.

**Every Python file.** Reproduced first (`NameError: name 'Page' is not
defined` in a scaffolded `pages/home.py`). An import hook
(`sys.meta_path`, front) swaps the loader only for modules whose source
is inside the site file's directory and runs the shared `run_source`
step; everything else falls through to Python. Installed for the
duration of `load_site`, removed in `finally`. `arklight.config.py` uses
the same step. The site directory is now on `sys.path` before the
preamble resolves, so project-local ACC modules can be included.
Third-party ACC packages are deliberately outside the boundary.

**Stdlib.** Four names missing from `__all__`; added, and a structural
test compares `arklight.api`'s public names to `__all__` so it cannot
drift again.

**Directive registry, `use` reserved.** One recogniser + one handler per
directive; `# use <...>` refused with a pointer to the proposal, which
records the maintainer's stated thinking and seven open questions and
decides none of them.

**Removed, on purpose:** the collision-picking form of `# define`. No
directive resolves an include collision now (proposal Q5).

**Tests:** `test_preamble_define.py` (41) and `test_preamble_scope.py`
(18) added; 11 alias-semantics tests removed. Hook disabled -> the
project-module tests fail. Full suite: 1502 passed.

**Not done, on purpose:** `# use`/`UI.ARKlight`/`UX.ARKlight` (proposal
only); ACC packages installed outside the project; retiring
`from arklight import *` beyond the existing notice.

## v0.06501 -- Capability fix follow-up: the preamble's blind spots (DONE)

Bug-fix follow-up to `v0.0650`, out-of-band, same slot-sharing
precedent. Numbered as the in-progress roadmap version (`v0.065`)
extended by extra decimals -- `0.0650` plus two -- so it never touches
the version itself. Still a **capability fix**: `v0.0650` closed "how
names get into a site file", but three things it was meant to cover
stayed invisible to the compiler.

**Retired, not removed.** `from arklight import *` keeps working, but
each build now logs one notice per occurrence (file:line, and the
`# include <stdlib.ARKlight>` line to use instead) through the
pipeline's existing stage logger, in the always-print form the CLI
already had for experimental-API banners. `load_site` gained an
optional `on_notice` callback rather than printing, matching how every
other stage reports. Deliberately scoped to the site file: the
preamble is only ever read from the entry file, so `pages/*.py` /
`components/*.py` in the production scaffold cannot adopt the new
syntax and are not nagged about it.

**Names the compiler couldn't see.** (a) The file's own definitions:
the preamble binds names before `exec`, so a later `def Button`, an
assignment, an import or a leftover star import silently won, and
nothing earlier could notice. The fix compares the finished
namespace to what the preamble bound, by identity -- which catches
every way of rebinding, including ones no static scan can -- and only
then reads the AST to say where. (b) User components: reproduced
before fixing -- `@component() def Button` replaced every `Button(...)`
in the site, ARKlight's own included, because `expand_ark_ast` checks
`COMPONENT_REGISTRY` before the schema. `arklight search` had already
decided the opposite ("built-ins always win"), so the compiler and its
own search disagreed. Now refused at registration unless
`allow_redefine=True`, the opt-in the earlier registration-collision
fix introduced; `@component` records that choice on the callable it
returns so the namespace check treats an opted-in override as
deliberate.

**`# define`, and where it belongs.** A define is "replace the left
name with the right one": canonicalization, so it is *applied* in
normalization. Normalization never raises -- it records what it
couldn't apply -- and validation is the single place that fails,
mirroring the compiler's own Normalization -> Validation order. This
also let one missing check land cleanly: two `# define`s giving one
alias two targets was a silent last-one-wins, now a collision. Kept as
a preamble-local pair rather than folded into `ir/normalize.py`/
`ir/validate.py`, because those run over the ARK AST *after* `exec`,
while names have to be bound *before* it -- the ARK AST only holds
already-resolved node types, so a post-`exec` pass can no longer see
an alias.

**Boundary, stated and pinned.** The preamble is recognised comments
above the file's contents only. A directive-shaped comment between
statements or at the end of the file is an ordinary comment.

**Tests:** `tests/test_preamble.py` 18 -> 43;
`test_user_defined_components_stage0.py` +4. Each new behaviour was
mutation-checked (disabled -> its tests fail). Three older tests
adjusted for the intended behaviour change, listed in `CHANGELOG.md`'s
`[0.06501]`. Full suite: 1454 passed.

**Not done, on purpose:** preamble support in *imported* modules
(`pages/`, `components/`) -- would need an import hook; a separate
capability fix if wanted.

## v0.0650 -- Capability fix: preamble directives (DONE)

Out-of-band alpha maintenance release, same slot-sharing precedent as
`v0.0431`/`v0.0641`-`v0.0649`. Treated as a **capability fix**, the
category `v0.0641` first recognized: not a broken promise, but a
missing piece whose absence has no ceiling on what it costs everything
built against this compiler until it's closed.

The gap: a site file's `from arklight import *` -- and the identical
pattern against any other vocabulary source, ACC included -- relies
entirely on Python's own star-import semantics to get names into the
module namespace. Python's rule for two statements binding the same
name is unconditional "last one wins": no diagnostic, no record of
which source lost, nothing pointing back at either import. That is the
exact "silently resolved by picking a winner" antipattern this
compiler's own registries already refuse everywhere else --
`register_component`/`register_backend_render`
(`DuplicateComponentError`) and ACC capability identities
(`CapabilityError`), both hardened by the `[Unreleased] --
Registration collisions now fail loudly instead of overwriting
silently` `CHANGELOG.md` entry well before this patch. But neither of
those guards the *first* step, getting names bound into the namespace
to begin with -- that step still ran on raw Python import semantics,
with zero ARKlight involvement, until now.

**What shipped:** `# include <label>` and `# define <alias> ->
<target>`, written as reserved-shape comments before a site file's
first executable statement. ARKlight's own loader (not Python's
import machinery) parses and resolves these, and binds the result
into the module namespace before the rest of the file runs.
`# include <stdlib.ARKlight>` binds `arklight.__all__` -- identical to
what `from arklight import *` already provides, just resolved by
ARKlight itself instead of by Python's star-import statement.
`# include <acc.<dotted.module.path>>` imports a real module and
binds its own `__all__`; a module with no `__all__` raises rather than
guessing which of its names are vocabulary (the same "no implicit
trust beyond one documented contract" stance
`arklight/capabilities.py` already takes for ACC capability
registration). If two includes bind the same name to two different
objects, `PreambleCollisionError` names every source involved and
raises at load time. `# define <alias> -> <target>` resolves a
collision explicitly (or just adds a local alias): a bare target must
be unambiguous across everything included so far, a dotted target
(`<include-label>.<name>`) picks one specific include's copy.

Deliberately additive, not a breaking change: `from arklight import
*` keeps working exactly as before, since this module only ever acts
on comments matching the two directive shapes above -- a site that
never adopts `# include`/`# define` is completely unaffected. That is
also the intended migration path, documented in
`docs/Foundational/AUTHORING-GUIDE.md`'s new "Preamble directives"
section rather than as a breaking-change announcement.

**Implementation:** `arklight/parser/preamble.py` (new module) --
`resolve_preamble` (the entry point `load_site` calls),
`PreambleError`/`PreambleCollisionError`, `_leading_comment_lines` (a
`tokenize`-based preamble scanner: walks `COMMENT` tokens up to the
first token belonging to an actual statement, the same "preamble ends
where code starts" boundary a C preprocessor's directives respect),
`_resolve_include_source` (the `stdlib.ARKlight`/`acc.*` label
dispatch), `_resolve_define_target` (bare vs. dotted `# define`
resolution, with its own unknown-label/unknown-name diagnostics).
`arklight/parser/loader.py` -- `load_site` calls `resolve_preamble`
right after `discover()` succeeds, binds the result into
`module.__dict__` before `exec`, and wraps `PreambleError` as
`SiteLoadError` like every other load-time failure this function
already surfaces.

**Tests:** `tests/test_preamble.py` (new, 18 tests) -- stdlib include
resolution against the real `arklight.__all__`; `acc.` include
resolution against fake modules registered into `sys.modules` for the
test (missing-module and missing-`__all__` failure modes covered
separately); two includes agreeing on a name (no collision, since it's
the same object) vs. disagreeing (raises `PreambleCollisionError`);
`# define` disambiguation, both bare and dotted, plus its own
unknown-include-label and unknown-name-on-a-known-include failure
modes; and integration through `load_site` -- binding without any raw
star-import present at all, wrapping a collision as `SiteLoadError`,
and confirming a site written the old way (`from arklight import *`,
no directives) still loads unchanged. Full suite: 1425 passed, no
regressions.

`0.0641` -> `0.0650` version bump (`pyproject.toml`) -- the docs-only
patches numbered in between (`v0.0642`-`v0.0649`) didn't bump it, per
each of their own "no code changed" entries above.

## v0.0641 -- Emergency patch: URL query-parameter state (DONE)

Out-of-band alpha maintenance release, numbered inside the v0.064 ->
v0.065 gap rather than waiting for whichever of those two versions'
own numbered work (JS vocabulary stage 4/10; JS vocabulary stage 5/10
plus `Provider` stage 1/6) finishes first -- same treatment as
`v0.0431`'s bug-fix patch, extended to a second category this project
now recognizes explicitly: a **capability fix**, not a bug fix, but
handled with at least the same priority. `v0.0431` existed because
`ROUTE_AWARE_ATTRS` silently broke a contract the HTML backend had
already made (route-shaped `srcset`/`poster`/`action`/`formaction`
values 404ing outside the domain root) -- a violation of something the
compiler already claimed to do. This patch is the other half of that
same "stop and fix it now, not later" posture: not a broken promise,
but a missing one -- ARKlight shipping no authored answer at all for
something every other reactive primitive in this vocabulary implies it
should have. A gap that blocks real, better use of the compiler is, if
anything, the higher-priority case to interrupt numbered work for: a
contract violation caps how *wrong* the tool can be, but a capability
gap caps how *useful* it can be, and the latter has no ceiling on how
much it's costing every site built against this compiler until it's
closed. Numbered milestone work resumes at whichever of `v0.065`'s
pieces was in flight, unaffected by this patch landing in between.

Accepted from `docs/Proposals/URL-STATE-AS-PRIMITIVE-PROPOSAL.md`.
Confirmed by the proposal's own exhaustive grep of `arklight/` for
`location.search`/`URLSearchParams`: ARKlight had no authored
primitive for reading, writing, or reacting to URL query parameters at
all, and -- unlike dynamic routes, nested layouts, or metadata -- this
is a gap the static-compilation model genuinely can't dissolve.
`/products?page=2` and `/products?page=3` resolve to the same file at
the static-file-server level; the compiler never sees the query
string, and the space of possible query values is unbounded, so
"generate one file per value" was never on the table.

`State(name, initial, query=..., history=...)` extends the existing
`persist=True`/`media=` precedent rather than inventing a fourth
parallel mechanism: same "override on init from an external source,
keep writing after that" shape, just sourced from
`URLSearchParams(location.search)`/`history.replaceState`/`pushState`
instead of `localStorage`/`matchMedia`. `query=` names the query-string
key (validated against `_LEGAL_QUERY_KEY_RE` at build time -- an
unencodable key would otherwise mis-round-trip through
`URLSearchParams` silently, in the browser, with nothing pointing back
at the `State(...)` declaration that caused it). `history=` (`"push"`,
the opt-in; `"replace"`, the unmarked default) controls whether a
change gets a real back-button-worthy history entry or silently
replaces the current one -- deliberately its own small registry
(`arklight.ir.schema.KNOWN_QUERY_HISTORY_MODES`), not folded into
`MODIFIER_REGISTRY`, since it's a per-`State`-declaration property with
no event of its own, not a per-event dispatch/timing token.

The one genuinely new runtime surface this adds: nothing shipped by
ARKlight listened for `popstate` before this, since there's no SPA
router. `wireQuerySync` (`arklight/backend/js/runtime/query.py`, new
file, kept separate from `state.py` for exactly that reason) is
registered once, from the existing `DOMContentLoaded` handler, gated
behind `has_query` the same "only ship what's used" way `has_reveal`
already gates `wireReveal`; it re-reads whichever page's
`data-ark-query`/`data-ark-state` attributes are on screen *right now*
rather than closing over a fixed manifest, so it stays correct across
an `app_shell`-boosted navigation to a different page. The read/
coerce/write-back half, by contrast, is folded directly into
`STATE_CORE_JS`'s `initState()` unconditionally (present on every
stateful page, a no-op when a page declares no `query=` state) -- same
split `persist=`/`media=` already established between "always present"
core behavior and "only shipped when used" wiring.

Deliberately never a real navigation: `State`/`Computed`/`Derive`/every
`Action` in this vocabulary are synchronous, in-memory primitives with
no network/navigation step anywhere in them, and the compiler-rendered
document is invariant to the query string in the first place (static
file resolution strips it before ARKlight's output is even in the
picture). So a query-tracked `State` update always stays a
`history.replaceState`/`pushState` call, never a full reload or an
`hx-boost` swap of a document that would, by construction, be
byte-for-byte identical to the one already on screen. A
before/after-URL equality check in the write-back subscriber also
makes a `popstate`-driven `store.set(...)` round-trip a no-op --
`wireQuerySync` never re-pushes/re-replaces the URL it just navigated
*to*, with no separate "am I currently handling a popstate" flag
needed.

Tests: `tests/test_url_query_state.py` (new, 44 tests) -- API prop
defaults/round-trip and independence from `persist=`/`media=`;
`KNOWN_QUERY_HISTORY_MODES`; Validation (legal/illegal query keys,
non-string `query`, known/unknown `history` modes, `history=` without
`query=`, plain `State(...)` left untouched); IR build (`IRPage.query`
tuples, `_query_type_tag`'s bool-before-int ordering, declaration
order across multiple query-tracked keys, independence from
`persist`/`media` lists); HTML render (`data-ark-query` presence/
absence, marker-vs-`<body>` placement under `app_shell`); JS render
(`data-ark-query`/`coerceQueryValue`/`serializeQueryValue` always
present whenever any page has state, `wireQuerySync` gated strictly by
`has_query` and shipped only once across multiple pages); and a
Node.js integration suite (mirroring `test_vdom_7.py`'s/
`test_js_vocabulary_v0063.py`'s precedent of checking the shipped
runtime fragments against a real JS engine, not just compiled-output
string assertions) exercising the actual `createState`/`initState`/
`wireQuerySync` fragments together: URL-override-on-init, fallback to
`initial` on a missing or malformed query value, `push`-vs-`replace`
write-back, and a `popstate` round-trip both with the param present
and falling back to the server-rendered default when it's absent from
the URL. Full suite: 1297 passed, no regressions.

Version bumped `0.063` -> `0.0641` (`pyproject.toml`) so `arklight
--version` and build-output banners reflect the patch -- noting, for
the record, that `v0.064`'s own `--retrieve-doc` piece landed without
a version bump of its own (`pyproject.toml` was still `0.063` going
into this patch despite `v0.064` being marked DONE in the Snapshot
table above); this bump covers both, same as any other pre-existing
inconsistency this project's docs flag in place rather than silently
paper over.

## v0.0642 -- Docs-only incremental patch: definition rewrite + Platform API IR proposal (DONE)

Out-of-band, numbered inside the same v0.064 -> v0.065 gap as
`v0.0431`/`v0.0641`, but a different kind of patch than either of
those two: not a bug fix, not a capability fix, a **docs-only**
correction to how the project describes itself, filed together with
the design proposal that correction points at.

**What changed, part one -- the definition.**
`docs/Foundational/WHAT-ARKLIGHT-IS.md` previously opened with "a
Python-authored, closed-vocabulary static-site compiler" as its
one-sentence definition, current as of `v0.063`. That wording made
"static-site compiler" the load-bearing noun, which reads as a
synonym for "static-site generator" even though Section 4 of the same
document already argued ARKlight isn't one. This patch rewrites
Section 1 so the load-bearing noun is **compiler framework**, and
extends Section 4 ("What ARKlight deliberately is not") with three
explicit bullets -- not a static-site generator, not a frontend
framework, not a UI framework -- instead of leaving readers to infer
the distinction from the rest of the document. Section 5's comparison
table preamble is reworded to match: ARKlight is compared against the
*nearest* tool on each axis precisely because, by this document's own
definition, there isn't a peer in its own category yet. Added to
`docs/Foundational/README.md`'s index (it wasn't listed there before
this patch, despite already existing in the doc tree under a version
that predates this repository's own `v0.001`-onward history -- filed
here rather than backdated).

**What changed, part two -- the proposal.** New
`docs/Proposals/PLATFORM-API-IR-PROPOSAL.md`: a platform API interface
layer for the compiler IR. Platform-facing capabilities (notifications,
clipboard, filesystem, device info, ...) are represented as
backend-independent, versioned interfaces the *compiler* owns; Web is
the default implementation; Android and Linux Desktop earn individual
interfaces only once their own backend is mature enough to support
them (deliberately not granted the whole catalogue just because a
WebView shell already works). Framed explicitly as an interface layer
in the IR rather than "a backend" -- the same terminology discipline
`docs/Foundational/SYSTEM-DESIGN-AGREEMENTS.md` already applies
elsewhere ("Compiler First, Runtime Last": the compiler owns the
semantic interface, the target owns the implementation). Borrows
Capacitor's Web-first/native-extension shape as an architectural
reference (Section 17 of the proposal) without adopting its
plugin-runtime model, and explicitly rules out any
`execute_native(...)`/`call_android(...)`-shaped generic native escape
hatch (Section 15) -- the same non-goal
`docs/Foundational/WHAT-ARKLIGHT-IS.md` Section 4 already states about
ARKlight as a whole. Section 25 of the proposal draws the line against
`Provider` (accepted, staged `v0.065`-`v0.070`): `Provider` is
external-service abstraction, Platform API is execution-platform
abstraction, neither absorbs the other. Added to
`docs/Proposals/README.md`'s index.

**Status:** the proposal is filed as **Proposed**, not accepted. This
patch names it as the project's next capability-fix candidate (per the
prompting that produced this patch) but does not itself commit to
building it, does not reserve a version-history slot for it, and
changes no compiler code. Acceptance, staging, and a milestone slot
are a separate, later decision -- same posture `docs/Proposals/
README.md` already describes for every other filed-but-undecided
proposal in that folder.

## v0.0643 -- Docs-only incremental patch: package docstring refresh (DONE)

Out-of-band, numbered inside the same v0.064 -> v0.065 gap as
`v0.0431`/`v0.0641`/`v0.0642`. Docs-only: no compiler code changed.

`arklight/__init__.py`'s module docstring still opened with "a
Python-first compiler for building static websites" -- the exact
"static-site compiler" framing `v0.0642` deliberately moved away from
in `docs/Foundational/WHAT-ARKLIGHT-IS.md`, left un-synced in the one
other place the project describes itself in that same sentence shape.
This patch brings the docstring in line: it now opens with **compiler
framework** (static site plus optional wrapped native/PWA targets, own
batteries-included workflow), and the quickstart example underneath it
now shows `State("count", 0)` and `Button(..., on_click=Action.
increment("count"))` instead of a stateless `Button` with no handler --
so `from arklight import *`'s own docstring demonstrates the
closed-vocabulary interactivity primitives (`State`, `Action.*`,
`Derive.*`, `Predicate.*`, `Watch`) rather than only markup. The
closing line, `"The browser never executes Python."`, is unchanged --
`docs/README.md`'s Philosophy section cites it by file reference, and
it remains accurate.

No other file quotes the docstring's opening sentence verbatim, so no
further doc was out of sync with it.

## v0.0644 -- Docs-only incremental patch: "The Goal" + `V1-DEFINITION.md` (DONE)

Out-of-band, numbered inside the same v0.064 -> v0.065 gap as
`v0.0431`/`v0.0641`/`v0.0642`/`v0.0643`. Docs-only: no compiler code
changed.

**What changed, part one -- "The Goal."**
`docs/Foundational/WHAT-ARKLIGHT-IS.md` gains a new, unnumbered "The
Goal" section, placed right after the document's opening grounding
note and before Section 1 (deliberately unnumbered rather than
inserted as a new Section 2, so Sections 2-7's existing numbers --
and, specifically, `docs/Proposals/PLATFORM-API-IR-PROPOSAL.md`'s two
existing references to "Section 4" -- stay valid without a
renumbering pass). The section states the DX bar ARKlight is aiming
for (comparable to React/Vue/Svelte's authoring ergonomics) alongside
the constraint it refuses to trade away to get there
(`SYSTEM-DESIGN-AGREEMENTS.md`'s "Compiler First, Runtime Last"), and
names the two audiences the project is actually building for -- the
Python Community and the Education Community -- rather than
"developers" in the abstract. `docs/Foundational/README.md`'s and
`docs/README.md`'s index rows for `WHAT-ARKLIGHT-IS.md` both updated
to mention it. The doc's own "Current as of `v0.0642`" marker is
bumped to `v0.0644`, since this patch is now the latest thing that
touched it (it had drifted -- `v0.0643` shipped after `v0.0642` without
this file's marker being bumped to match; caught and fixed in this
same pass rather than left for a later one).

**What changed, part two -- `V1-DEFINITION.md`.** New
`docs/Foundational/V1-DEFINITION.md`, filed as a direct follow-on from
"The Goal" (which raises "what does stable actually mean" without
answering it). Defines `v1.0`/"Stable compiler"
(`ARCHITECTURE.md`'s Milestones table has carried this as a bare
one-line `PLANNED` row since that table's inception) concretely:
deterministic output, fails-loudly-at-build-time with no known
exceptions in scope, no breaking changes to the closed vocabulary
without a deprecation path, and a developer who stops thinking about
the compiler entirely. Scoped explicitly to **the Web Developing
parts only** -- parsing/AST, Normalization/Validation, the Website IR,
and the HTML/CSS/JS backends, i.e. everything `arklight build` itself
exercises -- with named exclusions: the Android and Desktop packaging
backends (both still `IN PROGRESS`, earning their own maturity
independently), CLI conveniences beyond `build`, everything gated by
`arklight/experimental.py`, and `Provider`/Rei/Project
Knowledge/`arklight assistant` (all explicitly experimental or staged,
not "the compiler"). Names **ARKlight Component Collections** for the
first time anywhere in this doc tree -- a not-yet-proposed concept for
curated, distributable bundles of `@component`-registered content
built on `USER-DEFINED-COMPONENTS.md`'s existing macro-expansion path
(an "Education" collection of quiz/flashcard components; a "Starter
UI" collection of buttons/cards/form patterns) -- and states plainly
why it's out of scope: it's content built *on* the compiler via a
path the compiler already supports unmodified, its release cadence
and curation quality are editorial judgments independent of whether
`arklight build` behaved correctly, and it is expected to keep
churning well past `v1.0`. Flagged explicitly as a scope note, not a
proposal -- a real Collections feature (registry, distribution,
versioning policy) would still need its own `docs/Proposals/` entry
before any of it is real, per `docs/README.md`'s own document
lifecycle rule.

Also documents **"capability fix"** -- first recognized at `v0.0641`,
named again when `v0.0642` filed the Platform API IR proposal as the
category's second instance -- as more than a bookkeeping label: it's
the actual mechanism (and, cumulatively, the evidence) behind `v1.0`'s
reliability claim. Each capability fix landed closes one specific way
`arklight build` could otherwise surprise, block, or under-serve a
real site, ahead of the numbered schedule rather than on it;
`V1-DEFINITION.md` Section 2 frames `v1.0` itself as the point where
that supply of open capability fixes (and bug fixes) for the in-scope
surface runs dry, not a milestone that arrives independent of that
track record.

**Housekeeping caught in the same pass** (per `docs/README.md`'s own
"do it in one pass, not several" rule -- noticed while editing the
files this patch already had open, not chased down separately
afterward):

- `ARCHITECTURE.md`'s `v1.0` Milestones-table row, previously a bare
  `Stable compiler` label with nothing to click through to, now links
  to `V1-DEFINITION.md`.
- `docs/README.md`'s Foundational Folder Guide table was missing rows
  for both `WHAT-ARKLIGHT-IS.md` and `PLATFORM-APIS.md`, even though
  both already had rows in `docs/Foundational/README.md`'s own index
  -- exactly the "a reader may land on either README first" drift
  `docs/README.md` itself warns about. Both rows added here, alongside
  the two new rows this patch needed anyway.
- This file's own `v0.0643` Snapshot-table row had a literal `\n`
  instead of a real line break, merging it onto one line with the
  `v0.064-v0.070 (remainder)` row below it. Fixed.
- A stray, leftover `<<<<<<< HEAD` merge-conflict marker was sitting
  directly above the `v0.0643` narrative section header, just below.
  Removed -- it wasn't part of any real conflict still in progress.

## v0.0645 -- Docs-only incremental patch: `ACC-CAPABILITIES.md` (DONE)

Out-of-band, numbered inside the same v0.064 -> v0.065 gap as
`v0.0431`/`v0.0641`/`v0.0642`/`v0.0643`/`v0.0644`. Docs-only: no
compiler code changed.

**What was missing.** `a4aa6b8` ("Separating concerns and letting ACC
carry some burden") landed two things in the same commit:
`arklight/ir/binary.py` (the `.arklight` binary IR format) and
`arklight/capabilities.py` (the ACC capability-discovery hook). Only
the first got a docs update in that commit --
`docs/Foundational/ARCHITECTURE.md` gained a full "Binary IR" section
and `docs/Foundational/CLI-REFERENCE.md` documented
`--emit-arklight`. `capabilities.py` shipped with a thorough module
docstring and `tests/test_capabilities.py` (9/9 passing) but no entry
anywhere in `docs/`, `README.md`'s repository layout, `PROGRESS.md`,
or `CHANGELOG.md` -- exactly the kind of drift
`docs/README.md`'s own "why this section exists" postmortem warns
about, just not yet caught there.

**What changed.** New
[`docs/Foundational/ACC-CAPABILITIES.md`](docs/Foundational/ACC-CAPABILITIES.md):
the settled design record for the module -- the `arklight.capabilities`
entry-point contract, the `Capability`/`CapabilityError` API,
`compiler/sbom.py` as its one current caller (an ACC capability
appears in a build's SBOM as its own SPDX entry, whether or not that
build's IR uses it), and an explicit statement that nothing in the
compiler pipeline itself consumes a discovered capability during a
build yet. Also includes a status table cross-referencing ACC's own
`docs/design/IMPLEMENTATION-LADDER.md`: Stage 1 (this hook) landed
here; Stages 2-5 (package skeleton, `@acc/prism`, `@acc/common`,
installability) remain unstarted, tracked in ACC's own repository, not
this one.

`docs/Foundational/V1-DEFINITION.md` Section 5 corrected: its original
"no design doc yet -- defined here for the first time" framing for
ARKlight Component Collections is now false -- ACC is a real
repository (`Rae-ARK/ARKlight-Component-Collections`) with its own
`docs/design/acc-foundational-design.md`, and one piece of its ladder
has already shipped in `alpha`. The section's core exclusion argument
(a Collection is content built on the compiler via the existing
User-Defined Components macro-expansion path, versioned and curated on
its own schedule, never implying anything about `v1.0`'s stability
claim) is unchanged and still holds -- corrected the stale framing
around it, not the boundary itself. Also notes, explicitly, that the
capability-discovery hook is the one landed exception to "a real ACC
feature needs its own `docs/Proposals/` entry first": it was proposed
against `alpha` from ACC's side, not this repo's own Proposals folder,
which is why no such entry exists for it -- named so this patch's own
gap-closing isn't later mistaken for license to skip `docs/Proposals/`
on anything else. Doc's own "Current as of" marker bumped from
`v0.0644` to `v0.0645`.

New index rows in `docs/Foundational/README.md` and `docs/README.md`
(Foundational Folder Guide table) for `ACC-CAPABILITIES.md`, per
`docs/README.md`'s own numbered "one pass, not several" checklist.
Root `README.md`'s repository-layout listing gains a `capabilities.py`
line under `arklight/` -- previously absent despite the file existing
since `a4aa6b8`, the same class of gap `v0.0644` found and fixed for
`WHAT-ARKLIGHT-IS.md`/`PLATFORM-APIS.md` in `docs/README.md`'s own
table.

## v0.0646 -- Docs-only incremental patch: `V1-DEFINITION.md` self-contradiction fix + doc-removal rule (DONE)

Out-of-band, numbered inside the same v0.064 -> v0.065 gap as
`v0.0431`/`v0.0641`-`v0.0645`. Docs-only: no compiler code changed.

**What was wrong.** `v0.0645` amended `V1-DEFINITION.md` Section 5's
opening paragraph to say the ACC capability-discovery hook had landed
in `alpha` as `arklight/capabilities.py`, compiler-side code by its
own docstring's account -- but left that section's first bullet
("It is content built on the compiler, not code inside it ... with
zero special-cased compiler support") completely unchanged. The two
statements sit two paragraphs apart in the same section and directly
contradict each other: one says special-cased compiler-side code for
ACC exists and names the file; the other says there is zero
special-cased compiler support. A reader hitting the bullet right
after the opening paragraph would reasonably read it as ARKlight
either forgetting what it had just said, or silently reversing it.

**The fix.** Narrowed the bullet's claim to what it actually meant --
a Collection's own *content* compiles through the existing
`USER-DEFINED-COMPONENTS.md` macro-expansion path with zero
special-cased support -- and named the capability-discovery hook
in-line as the one, already-acknowledged exception, rather than
leaving it to silently contradict a claim two paragraphs above it.
The section's underlying argument (a Collection's *content* still
touches none of `arklight/parser/`, `arklight/ir/`, or any backend
listed in Section 3) is unchanged; only the absolute "zero
special-cased compiler support" phrasing needed scoping.

**Also fixed, same pass** (per `docs/README.md`'s own "do it in one
pass, not several" rule):

- `docs/README.md`'s "Adding a new doc" section only ever described
  what to do when a file is *added* or *updated* -- add/update its row
  in that folder's own index and in this file's Folder Guide table.
  It never said what to do when a file already covered by that
  lifecycle table is *removed* (a rejected Proposal, a finished
  Implementation ladder, a completed Backend staging doc, a
  dropped Far Future idea). Added an explicit reverse rule: deleting
  such a file and removing its index row(s) -- in that folder's own
  `README.md` index and in `docs/README.md`'s own Folder Guide table
  -- are one change, not two, exactly mirroring the existing
  add/update rule. `docs/Foundational/` and `docs/version history/`
  are named as the two exemptions, since neither folder ever loses a
  file.
- This file's own `v0.0645` Snapshot-table row had picked up a literal
  `\n` merging it with the `v0.064-v0.070 (remainder)` row below it --
  the identical defect `v0.0644`'s own row previously found and fixed
  for `v0.0643`, recurring one row later. Fixed; the two rows are
  separate lines again.

## v0.065 (interleaved fourth piece) -- Platform API IR, stage 1 of 2: Web reference implementation (DONE)

The proposal `v0.0642` filed as merely a capability-fix candidate is
now **accepted**, staged as a two-rung ladder in the new
`docs/Implementation/PLATFORM-API-IR-ADDENDUM.md`, and this session
ships the first rung end to end -- interleaved into `v0.065`'s already
crowded slot as a fourth piece, same "make room for one more"
precedent Rei's own addition to that slot already set.

**What shipped:** `PlatformAPI.notify(title, body=None)` and
`PlatformAPI.clipboard_write(text)` (`arklight/api.py`), each building
a `PlatformAPIRef` (`arklight/ast/nodes.py`) for `on_click=`, the same
authoring shape `Action.*(...)`/`ActionRef` already established. A
compiler-owned interface registry (`arklight/ir/platform_api.py`, new
module) describes each capability's arguments/permissions and which
backends currently implement it (`web`: both starter capabilities;
`android`/`desktop`: neither yet), independent of any backend's actual
implementation -- the split the proposal argues for throughout ("the
compiler defines the interface, each backend supplies its own
implementation"). Validation (`arklight/ir/validate.py`) catches an
unknown capability or an unexpected keyword argument at build time,
before any backend sees the reference at all. HTML compilation
(`arklight/backend/html/attrs.py`) reuses the same
`data-ark-on-click="<prefix>:<n>"` attribute slot `ActionRef` already
established, with a new `"platform:"` prefix. The Web backend's own
implementation (`arklight/backend/js/platform_apis/`, new package)
mirrors the existing `actions`/`behaviors` per-capability-fragment
pattern exactly -- one module per capability, only shipped when a
site's IR actually references it -- dispatched through a new
`"platform:"` branch in the click interceptor
(`arklight/backend/js/runtime/dispatch.py`), itself dispatching into a
new `platformApis` object `arklight/backend/js/render.py` assembles
with the same "only ship what's used" discipline `actions`/
`behaviors`/`derivations` already follow. `check_backend_support`
(previously defined but called from nowhere) now actually runs during
`_build_runtime_js`, failing the build with a named-capability
diagnostic if a site's IR references a capability the selected backend
doesn't implement -- today only reachable by deliberately narrowing
`web`'s own support set in a test, since `web` implements everything
currently registered.

**Also settled, not just implemented:** the boundary between
`PlatformAPI.clipboard_write` and the pre-existing `copy` named
behavior (`v0.063`) -- both call `navigator.clipboard.writeText` on
the Web backend, but answer different authoring questions ("copy
whatever's currently in this other element" vs. "copy this exact,
already-known string"). Recorded permanently in the new
`docs/Foundational/PLATFORM-APIS.md`, alongside the terminology,
architecture model, and Web-default/native-earns-later decisions the
accepted proposal argues for. `docs/Foundational/WHAT-ARKLIGHT-IS.md`'s
own "filed this revision, not yet accepted" note about this proposal
is updated to reflect acceptance and Stage 1 shipping.

**Tests:** `tests/test_platform_api.py` (new, 18 tests) -- API factory
return values, validation errors, HTML attribute compilation, JS
"only ship what's used" discipline (neither/one/both capabilities),
click-interceptor dispatch wiring, the no-`eval`/`new Function`
invariant, and `check_backend_support` actually firing both
standalone and from inside `JSBackend.render()`. Two pre-existing
tests (`tests/test_htmx_3.py`,
`tests/test_js_error_handling.py`) that hard-coded "the click
interceptor has exactly two dispatch branches" were updated to expect
three, the same way those tests were themselves updated when `htmx-5`
went from one shared guard to two per-branch guards. Full suite: 1313
passed (2 pre-existing, unrelated `test_version.py` failures from a
bare non-`pip install`ed checkout, present before this stage too), no
regressions.

**Stage 2 (Android/Desktop native implementations)** stays PLANNED and
deliberately unscheduled -- gated on each backend's own maturity per
the proposal's Section 6/22, not on a fixed version number. See
`docs/Implementation/PLATFORM-API-IR-ADDENDUM.md`.

## v0.061 -- JS vocabulary addendum, stage 1 of 10: math siblings (DONE)

Opens the JS vocabulary expansion ladder staged in
`docs/Implementation/JS-VOCABULARY-ADDENDUM-v0.070.md` -- the first
and cheapest rung, four missing math siblings of the existing `sum`/
`multiply` derivations: `Derive.subtract`, `Derive.divide`,
`Derive.min`, `Derive.max`. Each is a pure registry-fragment addition
in the pattern the ladder doc promises: one new `arklight/backend/js/
derivations/<name>.py` (`NAME` + `JS_FRAGMENT`) plus one
`DERIVATION_REGISTRY` line in `arklight/ir/schema.py`, one
`_evaluate_derivation` branch in `arklight/ir/build.py`, and one
`Derive.*` static method in `arklight/api.py` -- never a change to
Validation's arity-check *logic* (the existing `DerivationSpec.
min_names`/`max_names` fields already cover the new values) or any
backend's generation logic.

`subtract`/`divide` aren't associative the way `sum`/`multiply` are,
so both need `min_names=2`: `names[0]` is the starting value and
every later name applies against it in declared order. `divide`
mirrors JavaScript's own `x / 0` float semantics (`Infinity`/`NaN`,
never a thrown error) on the Python build-time-evaluation side too,
rather than letting Python's `/` raise `ZeroDivisionError` -- keeps
the server-rendered `Bind(...)` text and the client recompute in
agreement even at this edge case, the same "never disagree" contract
`sum.py`'s own docstring already holds. `min`/`max` are associative
like `sum`, so `min_names=1` is enough.

Tests: `tests/test_js_vocabulary_v0061.py` (19 tests, new) -- API,
validation (arity), IR-build initial-value evaluation (including the
divide-by-zero/`Infinity` case), HTML pre-fill, JS fragment shipping
(only the used kind ships, once), and a Node.js end-to-end check that
the shipped runtime fragment's recompute agrees with the build-time
initial value. Full suite: 1144 passed (2 pre-existing, unrelated
`test_version.py` failures -- package metadata lookup fails in a bare
source checkout, reproduces identically on `origin/alpha` before this
change), no regressions.

## v0.062 -- JS vocabulary addendum, stage 2 of 10: string casing + comparison predicates (DONE)

Second rung of the JS vocabulary expansion ladder staged in
`docs/Implementation/JS-VOCABULARY-ADDENDUM-v0.070.md` -- the last of
the genuinely one-hour additions, plus the `Show` comparison
predicates that were already speced but never wired up.

`Derive.uppercase`/`Derive.trim` are the missing string-casing
siblings of `Derive.join`/`Derive.format`, single-value transforms
with the same fixed arity as `Derive.count`: one new
`arklight/backend/js/derivations/<name>.py` (`NAME` + `JS_FRAGMENT`)
each, one `DERIVATION_REGISTRY` line (`min_names=1, max_names=1`),
one `_evaluate_derivation` branch (`str.upper()`/`str.strip()`), and
one `Derive.*` static method -- the exact same registry-fragment
pattern `v0.061` used.

`Predicate.equals`/`.gt`/`.lt` fill the `PREDICATE_REGISTRY` gap
`docs/Proposals/JS-VOCABULARY-EXPANSION-PROPOSAL.md` flagged: the
predicates were already speced alongside `Derive.compare`'s
`eq/ne/gt/lt/gte/lte` op set, but only `truthy`/`falsy` had ever
shipped. Each new kind takes exactly two names (`PredicateSpec(names=2)`)
and gets its own `_evaluate_predicate` branch
(`arklight/backend/html/page_render.py`, build-time) and its own
`arkEvalPredicate` case (`arklight/backend/js/runtime/show.py`,
client-side), so a page's server-rendered initial `hidden` state and
every subsequent client recompute agree -- no changes needed to
Validation's arity-check *logic*, just an updated error message
listing the new predicate kinds.

Tests: `tests/test_js_vocabulary_v0062.py` (new) -- API,
`PREDICATE_REGISTRY` coverage, validation (arity), IR-build
initial-value evaluation (including non-string coercion for
`uppercase`), HTML `Bind(...)` pre-fill and `Show(...)` `hidden`
attribute against the new predicates, JS fragment/`arkEvalPredicate`
shipping, and Node.js end-to-end parity checks. Full suite: 1170
passed, no regressions.

## v0.063 -- JS vocabulary addendum, stage 3 of 10: small new runtime primitives (DONE)

Third rung of the JS vocabulary expansion ladder staged in
`docs/Implementation/JS-VOCABULARY-ADDENDUM-v0.070.md` -- five small
runtime primitives, each extending `arklight/backend/js/runtime/*.py`
without a new IR node. Landed across two passes: an earlier,
incomplete one already shipped `Action.geolocate`'s JS fragment and
`Bind.model(..., debounce=...)`/`.throttle(...)` before stopping
mid-stage (a "Work on v0.063 is not done yet" commit); this pass
finished the remaining wiring (`Action.geolocate` itself never had an
`ACTION_REGISTRY` entry or an `arklight/api.py` static method yet)
and the other three primitives.

`Action.geolocate(name)` is a one-shot, argument-less action --
`navigator.geolocation.getCurrentPosition` writes `{lat, lng}` into
`State(name)` once the browser's permission prompt resolves.
Asynchronous, unlike every other action so far: the dispatcher's
existing "fire and forget" `action(store, key, args)` call already
made this safe without any dispatcher changes.

Clipboard **paste** (`on_click="paste"`) mirrors `copy.py` closely --
same `behavior_target` selector, same clipboard-availability guard,
reading instead of writing. Writing into an `Input`/`Textarea` also
dispatches a real `input` event, so an element that also carries
`bind_value=Bind.model(...)` picks the pasted text up into state too,
for free.

`State(..., media="(min-width: 768px)")` is the third kind of
`State(...)` declaration with a second, non-`Action.*(...)` writer
(after `persist=True`): `IRPage.media` carries `(name, query)` pairs
through the IR exactly the shape `IRPage.persist` already
established, `data-ark-media` rides along `data-ark-persist` on the
same hydration marker, and `initState()` overrides the initial value
with `matchMedia(query).matches` before the store is created, then
attaches one `MediaQueryList` "change" listener per declared media
key.

`reveal`/`lazy` (`on_reveal="reveal"`, `IntersectionObserver`) needed
an actual design decision, flagged when this stage was originally
planned: every existing named behavior is click-triggered, wired
through `wireClickInterceptor`'s delegated `click` listener, but a
reveal-on-scroll-into-view effect has no click to hook. Reusing
`on_click=`'s prop/registry for a mechanism that isn't click-triggered
at all would silently misbehave the moment a site tried to combine
the two on one element -- so `on_reveal=` got its own prop, its own
small registry (`arklight.ir.schema.REVEAL_REGISTRY`/
`KNOWN_REVEAL_BEHAVIORS`), and its own mount-time wiring pass
(`wireReveal`, `arklight/backend/js/runtime/reveal.py`) called from
`arkInitPage()` -- first load and, on an `app_shell` site, after every
boosted swap -- rather than one more entry in the click-dispatched
`behaviors` object. One kind so far: `reveal` adds `toggle_class`
(default `"is-visible"`, reusing `toggle`/`dismiss`'s existing
attribute/default) to the element itself the first time it enters the
viewport, then stops observing it.

While making sure `from arklight import *` actually reached this
stage's own new names, found (and fixed) that it didn't reach several
*older* ones either: `Repeat`, `RepeatItem`, `Show`, `Predicate`,
`PredicateRef`, `ItemIndexRef`, `ClassBindSpec`, `ModelBindSpec` were
all defined in `arklight/api.py`/`arklight/ast/nodes.py` but missing
from `arklight/api.py`'s own `__all__` and from
`arklight/__init__.py`'s import/`__all__` list entirely -- reachable
via `arklight.api.Repeat` etc., but not via the wildcard import users
are told to use. Same class of gap `tests/test_package_exports.py`
already caught once before, for the v0.003 second vocabulary
addendum; fixed the same way, plus a regression test in
`tests/test_js_vocabulary_v0063.py` this time so it can't quietly
regress a third time.

Every new `window.*` access in this stage (`window.matchMedia`,
`"IntersectionObserver" in window`) is guarded with `typeof window
!== "undefined"` rather than a bare reference -- needed for
`tests/test_vdom_8.py`'s existing Node.js harness (a hand-built
`document`/`localStorage` stub with no `window` global) to keep
passing once `initState()`'s JS grew a `window.matchMedia` branch;
caught by running the full suite before considering this stage done,
not by inspection.

Tests: `tests/test_js_vocabulary_v0063.py` (new, 36 tests) --
`Action.geolocate`/`ACTION_REGISTRY` coverage and validation against
undeclared state; `paste`'s registry coverage, `behavior_target`
requirement, and HTML/JS output; `media=`'s IR round-trip, validation,
and HTML/JS output; `on_reveal=`'s validation (notably that it does
*not* require `behavior_target`, unlike `on_click`) and that
`wireReveal()` ships/runs independent of `has_state`; `Bind.model(...,
debounce=...)`/`.throttle(...)`; a combined test exercising all five
primitives on one page; `from arklight import *`/`from arklight.api
import *` wildcard-export regression tests; and a Node.js check of the
shipped `wireReveal` fragment. Full suite: 1204 passed (2
pre-existing, unrelated `test_version.py` failures in a bare,
non-`pip install`ed checkout -- present before this stage too), no
regressions.

## v0.060-stage0 -- User-defined components, Stage 0 of 4 (DONE)

Opens the `v0.060` milestone: promotes a plain Python render function
into a real, named node type via `component(...)`, per the **hybrid**
design `docs/Foundational/USER-DEFINED-COMPONENTS-IMPLEMENTATION.md`
pins down (Option A -- macro expansion -- as the default and the only
mode with distinct behavior yet; Option B -- registry-based late
binding -- selectable today via `mode="registry"` as an explicit
EXPERIMENTAL opt-in, not yet a different rendering outcome).

- **`arklight/ir/components.py`** (new) -- `Prop` (a component's
  per-prop declaration: optional `type`, optional `default`, required
  when no default is given), `ComponentSpec` (name/render_fn/props/mode,
  validates `mode` against a closed `{"macro", "registry"}` vocabulary
  at construction), `COMPONENT_REGISTRY` (a plain module-level dict,
  last-registration-wins, same rule `Site.style(...)` already uses),
  `register_component(...)`, and the expansion pass itself:
  `expand_node`/`expand_child`/`expand_ark_ast`. The hybrid dispatch
  lives in `_render_once` as a literal `if spec.mode == "macro": ...
  elif spec.mode == "registry": ...` ladder -- both branches currently
  do the same thing (see the implementation doc for why that's
  deliberate at this stage). Cycle detection via a stack of in-progress
  component type names (mirrors `validate.py` check #13's
  `Computed`/`Derive` self-reference guard) plus a
  `MAX_COMPONENT_EXPANSION_DEPTH = 64` ceiling as cheap insurance
  alongside it. `ComponentError` is the one exception type for every
  failure mode here (missing/unknown/mistyped prop, cycle, depth
  ceiling, invalid `mode`).
- **`arklight/api.py`** -- `component(*, props=None, mode="macro")`
  decorator: registers the render function, returns a marker-node
  factory with the same call shape a built-in's `node("...")`-produced
  factory has, so `NavBar(active="home")` reads identically to
  `Heading("...")` at the call site even though it's building a marker
  instead of a final node. Re-exported (`component`, `Prop`) from
  `arklight/__init__.py` alongside every built-in.
- **`arklight/compiler/pipeline.py`** -- new stage,
  `"Expanding user-defined components..."`, between
  `site.build_ark_ast()` and `normalize_ark_ast(...)` --
  `expand_ark_ast(...)` runs before Normalization ever sees the tree,
  exactly as Option A's design requires. A `ComponentError` here is
  wrapped into the same `CompileError` every other pipeline-stage
  failure already produces. No changes anywhere else in the pipeline,
  `arklight/ir/schema.py`, `tag_map.py`, or any backend -- the "zero
  changes required downstream" property Option A promised held in
  practice, not just on paper.
- **No children slot on a component call this stage** -- only keyword
  props, matching every example in the original design doc; a
  component that needs to accept nested content takes it as a prop
  value (`Card(body=Container(...))`), the same way it would take any
  other `ARKNode`-valued prop.
- **Tests:** `tests/test_user_defined_components_stage0.py` (17 tests,
  new) -- registration, marker-factory shape, macro expansion
  (including nested/recursive component-in-component cases), props
  contract (missing/unknown/mistyped), cycle detection (direct and
  indirect/mutual), the depth ceiling's non-cyclical-deep-chain
  negative case, and confirming an expanded tree passes
  Normalization/Validation completely unchanged. Also updated two
  existing `tests/test_pipeline_end_to_end.py` stage-order assertions
  to include the new `"Expanding user-defined components..."` line.
  Full suite: 1057 passed, no regressions.
- **Not done this stage** (see the implementation doc's staged
  ladder): `arklight search` typo-suggestion integration for user
  component names (Stage 1), a default-styling registration hook
  (Stage 2), Option B's actual per-backend rendering differentiator
  (Stage 3), and component-owned reactive state (Stage 4, blocked on
  nothing further from `v0.054`'s side but a materially separate
  problem in its own right).



Closes docs/Backends/REFACTOR-INDEX.md row 15, the last of the
"content" reactive-core stages -- unlike `Computed`/`Watch`, `Repeat`
and `Show` are real renderable content that stays exactly where it's
placed in the tree.

- **`arklight/api.py`** -- `Repeat(name, *, template)` calls `template`
  once at compile time; the current item is referenced inside it via
  `RepeatItem.value()`/`RepeatItem.index()`, never passed in directly
  (there's no such thing at compile time). `Show(predicate, *children)`
  takes a `Predicate.truthy(name)`/`Predicate.falsy(name)` reference,
  a closed vocabulary the same way `Derive.*` is for `Computed(...)`.
- **`arklight/ast/nodes.py`** -- new `PredicateRef`/`ItemIndexRef`
  dataclasses, same "small structured object, not a string" shape as
  `DerivationRef`.
- **`arklight/ir/schema.py`/`validate.py`** -- `PREDICATE_REGISTRY`
  (`truthy`/`falsy`); dedicated recursive validators
  (`_validate_repeat_template`, `_validate_show_declaration`) rather
  than the page-scoped-declaration path `Watch` uses, since both stay
  in the tree and recurse into ordinary children.
- **`arklight/backend/html/page_render.py`** -- `_render_repeat` emits
  the *actual current* items as full markup (a JS-disabled visitor
  sees the real list) plus a JSON `data-ark-repeat-template` spec for
  the client to build new items from later; `_render_show` always
  renders its children, toggling the native `hidden` attribute rather
  than omitting markup.
- **`arklight/backend/js/runtime/repeat.py`/`show.py`** (new) --
  `renderRepeat` routes through the vendored snabbdom `patch()`, keyed
  by each item's own value (not index, so a removal doesn't cause
  every later item to be misdiagnosed as changed); its first call per
  container "adopts" the server-rendered DOM into a matching vnode
  tree instead of patching, since the vendored core has no dedicated
  hydration pass and would otherwise duplicate every item. `renderShow`
  deliberately does **not** route through `patch()` -- the same missing
  hydration pass makes a vnode-swap toggle either leave stale content
  next to an empty vnode or destroy the anchor element outright on the
  first real toggle -- so it uses `hidden` instead. Both ship only on
  pages that actually use them (`has_repeat`/`has_show` in
  `render.py`'s `_collect_usage`).
- **Tests:** `tests/test_vdom_7.py` (21 tests, new). Full suite: 970
  passed, no regressions.

## vdom-6 -- Two-way input binding (DONE)

Closes docs/Backends/REFACTOR-INDEX.md row 14. `bind_value=` gives an
`Input` a two-way binding to a `State(...)` name -- state writes into
the element's `value` (same pre-fill/re-render pattern `bind_class=`
already uses), and the element's own `input` events write back into
state, so a bound field stays in sync in both directions without an
explicit `on_click=`/`Action.*` wire-up for every keystroke.

- **`arklight/api.py`** -- `Bind.model(name)` is a thin, explicit
  spelling for "this is a two-way reference" (`bind_value=` also
  accepts a plain string directly, same as `bind_class=`'s relationship
  to `ClassBindSpec`). Only a `State(...)` name is a valid target --
  mirrors `Action.*(...)`'s own restriction, since a `Computed(...)`
  has no independent value of its own for user input to write back
  into.
- **`arklight/ir/validate.py`** -- `_validate_model_bind` enforces that
  restriction: `bind_value` must be a non-empty string naming a
  `State(...)` declared on the page, not a `Computed(...)` name.
- **`arklight/backend/html/attrs.py`** -- pre-fills `value=` from the
  page's initial state (same as `bind_class=`'s initial-render
  pre-fill), unless an explicit `value=` prop is already given (that
  wins), and compiles `bind_value=` to a `data-ark-model="name"`
  attribute for the runtime to key off.
- **`arklight/backend/js/runtime/model.py`** (new) --
  `renderModelBindings(store)` is one more `store.subscribe` render
  pass alongside `renderBindings`/`renderClassBindings`: writes
  `store.get(key)` into the element's `.value` whenever state changes
  from *any* source, comparing against the element's current `.value`
  first so a user's own keystroke doesn't get its cursor position
  reset. `wireModelBinding(getStore)` is one delegated `input` listener
  on `document` (event delegation via `Element.closest()`, same
  pattern `wireClickInterceptor` uses for `click`), taking a
  zero-argument getter for the same "registered exactly once, must
  survive an `app_shell` boosted navigation without a stale closure"
  reason `wireClickInterceptor` documents.
- **`arklight/backend/js/render.py`** -- `_collect_usage` now also
  reports `has_model_binding`; both new fragments are only shipped on
  a page that actually declares `bind_value=` somewhere, same
  "only ship what's used" discipline `WIRE_WATCHERS_JS` already
  follows.
- Deliberately not routed through the vendored snabbdom core -- same
  reasoning `renderClassBindings` already documents for `bind_class`:
  `.value` is DOM element state, not a vnode's own rendered children,
  so there's nothing for `patch()` to diff.
- Test coverage: `tests/test_vdom_6.py` (new) -- API, Validation, HTML
  backend, JS backend, and two Node-subprocess end-to-end checks that
  the shipped `renderModelBindings`/`wireModelBinding` fragments
  actually sync state -> value and value -> state.

**Note:** the commit that landed this was mistitled "Vdom 5" (it's
`vdom-6` throughout the code/docstrings and in
`docs/Backends/REFACTOR-INDEX.md` row 14) -- flagging here so it isn't
missed by anyone grepping history for "vdom-6".

## vdom-4 -- Computed/derived state (DONE)

Closes out the row started in the prior session ("Continuing the
combined refactor. Vdom-4 computed && derived stage started"), which
landed the Python side only (`arklight.api.Computed`/`Derive.*`,
`ast.nodes.DerivationRef`, `ir.schema.DERIVATION_REGISTRY`,
`ir.validate`'s cross-declaration/cycle checks, `ir.build`'s
dependency-ordered `IRPage.computed`/`computed_initial` extraction,
and `backend.html.page_render`'s `data-ark-computed` marker). This
session finishes the JS runtime half docs/Backends/REFACTOR-INDEX.md
row 12 calls for:

- **New `arklight/backend/js/derivations/` package**, mirroring
  `actions/`/`behaviors/`: one `NAME`/`JS_FRAGMENT` sibling module per
  `Derive.*` kind (`sum.py`, `multiply.py`, `join.py`, `count.py`,
  `format.py`, `compare.py`), each a small `kind: function (state,
  names, args) { ... }` fragment kind-for-kind matching
  `arklight.ir.build._evaluate_derivation`'s build-time semantics, so
  a page's server-rendered `Bind(...)` text never disagrees with what
  the client recomputes after the first state change. Verified this
  agreement directly (Node evaluation of the shipped `multiply`
  fragment against the build-time-evaluated initial value) rather than
  only asserting it by construction.
- **`runtime/state.py`**: `createState(initial, computed)` gains a
  second, optional parameter -- the same dependency-ordered `(name,
  spec)` pairs `IRPage.computed` carries, JSON-round-tripped as plain
  2-element arrays. A new `recomputeAll()` closure walks that list in
  the order `arklight.ir.build._topological_order_computed` already
  sorted at build time (the client never re-derives that ordering
  itself), looks each entry's `kind` up in the `derivations` object,
  and writes the result straight into `state` under the `Computed(...)`'s
  own `name` -- so it's readable through the exact same `store.get(key)`
  every `Bind(...)`/`renderBindings` call already uses, no separate
  lookup path. Runs once at construction and again at the end of every
  `set`/`reset`, *before* that call's subscriber notification, so a
  subscriber never sees a stale computed value. `initState()` reads
  the sibling `data-ark-computed` attribute the same way it already
  reads `data-ark-state` and passes it through.
- **`render.py`**: `_collect_usage` now also returns which derivation
  kinds are referenced and whether any page declares `Computed(...)`
  at all; a new `_derivations_object_js` (mirrors
  `_actions_object_js`/`_behaviors_object_js` exactly) ships only the
  fragments a site's IR actually uses, spliced in right after the
  vendored snabbdom core -- always inside the existing `if has_state:`
  branch, since every `Computed(...)` dependency chain bottoms out at
  a real `State(...)` (enforced by Validation), so `has_computed`
  never needs its own top-level branch.
- **`tests/test_vdom_4.py`** (29 tests, per the project's one-file-per-
  stage discipline): API, Validation (cross-declaration checks, cycle
  detection, arity, unknown kind/op, the `Computed(...)` name being
  bindable but never a valid `Action.*(...)` target), IR build
  (dependency-ordered `computed`, chained `computed_initial`
  evaluation), HTML backend (`data-ark-computed` emission,
  `data-ark-state` staying mutable-only, prefilled `Bind(...)` text),
  JS backend (only-used-kinds shipping, recompute-before-notify
  ordering, `initState()` reading the new attribute), and one
  Node-subprocess parity check against the build-time value.
- Two pre-existing `tests/test_refactor_0.py` assertions hardcoded
  `createState`'s old single-argument signature
  (`"function createState(initial)"`); updated to the new
  `createState(initial, computed)` shape rather than left broken.
  Full suite: 899 passed, no other regressions.

Not part of this stage (see `vdom-5`/`vdom-6`/`vdom-7`/`vdom-8` in
docs/Backends/REFACTOR-INDEX.md, all still "Not started"): watch
effects, two-way input binding, per-item list rendering/conditional
show-hide, `localStorage` persistence.

## vdom-5 -- Watch effects (DONE)

Closes the "when X changes, also do Y" side-effect gap `Computed(...)`
deliberately leaves open (a `Computed(...)` only ever *derives* a
value -- it can't dispatch an `Action.*(...)` of its own). New API:

```python
State("celsius", 0)
State("fahrenheit", 32)
Watch("celsius", then=Action.set("fahrenheit", ...))
```

Same seven-additive-sub-systems shape docs/Foundational/DESIGN-NOTES.md
lays out for this whole vdom-staging arc: a `Watch(...)` API function
(`arklight/api.py`), no new registry this time (a `Watch(...)`'s
`then=` is just an `ActionRef`, validated by the exact same
`_validate_action`/`ACTION_REGISTRY` machinery `on_click=` already
uses), and one new runtime fragment
(`arklight/backend/js/runtime/watch.py`).

- **`arklight/api.py`**: `Watch(name, *, then)` -- a page-scoped
  declaration, same shape as `Computed(...)`: must be a direct child
  of `Page(...)`, compiled into the IR rather than reaching any
  backend as a component.
- **`arklight/ir/validate.py`**: `_validate_watch_declaration` --
  `parent_is_page` check (mirrors `_validate_computed_declaration`),
  `name` checked against the page's bindable set the same way
  `_validate_bind` checks a `Bind(...)`'s name (so a `Watch(...)` can
  observe a `State(...)` *or* a `Computed(...)`), and `then` handed
  straight to the existing `_validate_action` (so `then` can only ever
  target a real `State(...)`, the same restriction `on_click=
  Action.*(...)` already has -- a `Computed(...)` has nothing of its
  own to mutate).
- **`arklight/ir/build.py`**: new `IRPage.watch` field --
  declaration-ordered (no dependency graph to sort, unlike `computed`)
  list of `{"name": ..., "then": {...}}` dicts, `_extract_page_state`
  pulling `Watch(...)` nodes out of a page's children the same way it
  already pulls `State(...)`/`Computed(...)`, and a new
  `_action_ref_to_spec` helper (`ActionRef` -> plain dict, the same
  role `_derivation_ref_to_spec` plays for `DerivationRef`).
- **`arklight/backend/html/page_render.py`**: a sibling
  `data-ark-watch` JSON attribute, same marker/`<body>`-attribute
  duality `data-ark-state`/`data-ark-computed` already use -- a page
  can only ever have `page.watch` non-empty when `page.state` is too
  (enforced transitively by Validation), so it's always safe on the
  same element.
- **`arklight/backend/js/runtime/watch.py`** (new): `wireWatchers(store,
  specs)` -- snapshots each watched name's current value, then adds
  one more `store.subscribe` listener alongside `renderBindings`/
  `renderClassBindings` (wired from `initState()`, `runtime/state.py`,
  guarded with `typeof wireWatchers === "function"` since the fragment
  only ships on a page that actually declares `Watch(...)`). On each
  notification, re-reads every watched name and, for any that
  changed, updates the snapshot *before* dispatching that watch's
  `then` action through the exact same `actions[...]` object
  `wireClickInterceptor` already reads -- no new dispatch mechanism,
  confirming this stage's own "verify against whatever htmx-3 leaves
  that dispatcher looking like" note. Updating the snapshot before
  dispatch keeps a self-referential `Watch(...)` (the "clamp a value
  back into range" case) a small, bounded number of reentrant passes
  rather than an infinite loop, even though `store.set` itself always
  notifies regardless of whether the value actually changed -- see
  `tests/test_vdom_5.py`'s Node-subprocess coverage for the exact
  bound.
- **`arklight/backend/js/render.py`**: `_collect_usage` now returns
  `used_on_click_actions` separately from the broader `used_actions`
  (which folds in every `Watch(...)`'s `then.action` too) -- `
  needs_click_interceptor` stays keyed off the narrower set (a watch
  effect never involves a click), while a new `needs_actions_object`
  (`needs_click_interceptor or has_watch`) decides whether the
  `actions` dispatch object itself ships, so a watch-only page (no
  `on_click=`/named behavior anywhere) gets `actions` without an
  unused click interceptor tagging along.
- **`tests/test_vdom_5.py`** (24 tests, mirroring `test_vdom_4.py`'s
  per-stage discipline): API, Validation (bindable-name/`then`-target
  checks, unknown action, invalid modifier, `Computed(...)` rejected as
  a `then` target), IR build (declaration order, plain-dict `ActionRef`
  mirror, `Watch(...)` never reaching page children), HTML backend
  (`data-ark-watch` emission + round-trip), JS backend (fragment only
  ships when needed, `actions`-without-click-interceptor on a
  watch-only page, dedup against an unrelated `on_click=` action,
  guarded `wireWatchers` call site), and two Node-subprocess checks:
  one confirming `wireWatchers` actually dispatches the watched action
  on a real change, one confirming a self-referential watch settles in
  a small, fixed number of reentrant passes rather than hanging. Full
  suite: 931 passed (plus 2 pre-existing, unrelated
  `test_version.py` failures from this sandbox's `arklight` package
  not being `pip install`-ed -- not introduced by this stage), no
  regressions.

Not part of this stage (see `vdom-6`/`vdom-7`/`vdom-8` in
docs/Backends/REFACTOR-INDEX.md, all still "Not started"): two-way
input binding, per-item list rendering/conditional show-hide,
`localStorage` persistence. Also deliberately out of scope, noted here
so it isn't rediscovered later: `Watch(...)`'s `then=` accepts the
same `.with_modifiers(...)`/`.debounce(...)`/`.throttle(...)` shape
`on_click=Action.*(...)` does (Validation doesn't special-case it
away), but `wireWatchers` never reads `spec.then.modifiers` -- those
tokens exist to coalesce rapid *clicks* on one element, which has no
equivalent for a state-change subscription that already only fires
once per actual value change, so any modifiers present on a
`Watch(...)`'s `then` are silently inert rather than rejected at
Validation time. Worth a follow-up Validation check (reject
modifiers on a `Watch(...)`'s `then` outright) if that silent-inert
behavior ever surprises someone in practice.

## v0.048 -- Stage B: `responsive_style` + `@media` compilation (DONE)

Landed independently of Stage A, per the split `docs/DESIGN-NOTES.md`
("v0.048: CSS media queries + `<head>` extension") called for -- Stage
B depends on nothing from Stage A (a different node prop, a different
backend path).

**Shipped:** an optional `responsive_style: dict[str, dict[str, str]]`
prop any component may carry, e.g. `Container(responsive_style=
{"(max-width: 600px)": {"display": "none"}})`. Each key is the full
media-condition text a site author wants inside `@media <here> { ... }`
(so it may already carry its own parens, or be a compound condition
like `"screen and (max-width: 600px)"`); each value is a normal
CSS-property dict, using the same `_`->`-` property-name convention the
existing inline `style={...}` prop already does (this prop is
documented as extending that convention, not `Site.style()`'s literal-
property-name one).

Four pipeline stages touched, same discipline as every other prop this
project has added:

- `arklight/ir/validate.py` -- `_validate_responsive_style` checks the
  prop is a non-empty `dict[str, dict[str, str-or-number]]` with
  non-empty condition/property keys, so a malformed entry fails loudly
  at build time instead of silently producing broken generated CSS.
- `arklight/ir/build.py` -- a new `_ResponsiveStyleCollector` walks the
  tree alongside `_ark_node_to_ir_node`, assigning each
  `responsive_style`-carrying node a deterministic, site-wide-unique
  generated class (`arkgen-1`, `arkgen-2`, ... in build order: pages in
  dict order, depth-first per page), stripping `responsive_style` out
  of the node's own IR props (it isn't a real HTML attribute -- leaving
  it in would've round-tripped into a meaningless `data-responsive-style`
  attribute the same way any unknown prop does), and folding the
  generated class into `class_name`. `WebsiteIR` gained a
  `responsive_rules` field: `(condition, generated_class, {prop:
  value})` triples, in registration order. `build_website_ir` gained an
  optional `on_warning` callback so the inline "[EXPERIMENTAL FEATURE
  ACTIVE]" banner can print at its actual detection point -- unlike
  `site.media_query(...)` (an author-time `Site` method call, already
  known before IR build starts), a `responsive_style` prop is only
  discovered by walking the tree, so it needed its own detection point
  rather than reusing `site.experimental_usages`' pre-build loop.
- `arklight/backend/css/custom_styles.py` -- a new
  `render_responsive_styles` sibling to `render_media_queries`, but
  deliberately *not* the same function: `render_media_queries` always
  wraps `site.media_query(condition, ...)`'s bare condition in parens
  (`@media ({condition}) {{`); `render_responsive_styles` inserts the
  key verbatim (`@media {condition} {{`), since the design doc's own
  example key already includes the parens (`"(max-width: 600px)"`) --
  wrapping it again would emit `@media ((max-width: 600px))`, which is
  invalid, and would make a compound condition like `"screen and
  (max-width: 600px)"` impossible to express at all.
- `arklight/backend/css/render.py` -- `CSSBackend.render` appends
  `render_responsive_styles(ir.responsive_rules)` absolute last in the
  cascade (after the existing `site.media_query(...)` blocks), so a
  per-node override always wins against a sitewide one -- though in
  practice the two can never target the same class, since `arkgen-N`
  names are never author-chosen.

**Experimental gating (docs/EXPERIMENTAL-APIS.md updated):**
`responsive_style` is a second entry point into the *same*
`css-media-queries` feature gate `site.media_query(...)` already uses,
not a new feature id -- both compile to a viewport-keyed `@media` block
and both step outside the intrinsic layout model the same way, so both
print the same inline banner and end-of-build summary block. The
feature's `legacy_note` text was generalized (it used to read
"predates ARKlight's intrinsic layout model," which was accurate for
`site.media_query(...)` alone but not for a brand-new prop shipping in
the same release) to describe both authoring surfaces without implying
`responsive_style` itself is legacy.

**26 new tests** (`tests/test_responsive_style.py`, plus one added each
to `tests/test_experimental_apis.py` and
`tests/test_pipeline_end_to_end.py`): validation (well-formed input,
every malformed shape), IR build (class generation, ordering, class-
name merging with an existing `class_name`, multiple conditions on one
node sharing one class, the experimental-usage record), CSS rendering
(verbatim condition insertion, compound conditions, underscore-to-
dash conversion, cascade position), and a full `compile_site_file`/
`build()` round trip confirming `responsive_style` never leaks into
the rendered HTML as a raw attribute. 532 tests total, all passing.

**Explicitly not touched by this patch:** Stage A (`meta`/`links` on
`Page(...)`) remained not-yet-implemented as of this patch -- tracked
separately, unaffected by Stage B landing first. (Since landed -- see
"v0.048 -- Stage A" below.)

## v0.048 -- Stage A: structured `<head>` extension (DONE)

Started ahead of v0.044 (now renumbered v0.054, see the top of this
file's Snapshot table) in the previously announced roadmap order
(README/ARCHITECTURE said v0.044 next); v0.048 was picked up first
instead. Design unchanged from `docs/DESIGN-NOTES.md` ("v0.048: CSS
media queries + `<head>` extension") -- landed as two independent
stages so each was reviewable/testable on its own. With this stage
done, both halves of v0.048 have now shipped and the milestone as a
whole moves to DONE.

**Shipped:** `Page(...)` gains two more optional, *structured*
extension points -- `meta: dict[str, str] | None` (name/content pairs,
each rendered as `<meta name="..." content="...">`) and `links:
list[dict[str, str]] | None` (each dict is attribute name -> value,
rendered as a single `<link ...>` tag -- for preconnect, webfonts, or
extra icon sizes beyond the existing `favicon`). No raw HTML-injection
escape hatch -- same "no arbitrary strings" boundary every other
extension point in the project holds (`responsive_style` above,
`Site.style()`, `on_click`'s closed behavior/action registries).

Two pipeline stages touched:

- `arklight/ir/validate.py` -- a new `_validate_page_head_extensions`,
  called only for `Page` nodes (these two props are read exclusively
  off `page.root`, matching `favicon`/`description`/`og_*`'s existing
  page-only convention). `meta` must be a non-empty `dict[str, str]`;
  `links` must be a non-empty `list[dict[str, str]]` where every entry
  carries a `rel` attribute -- a malformed entry fails loudly at build
  time rather than silently producing broken `<head>` output.
- `arklight/backend/html/render.py` -- `_render_head_meta` gained two
  more opt-in blocks after the existing `description`/`favicon`/`og_*`
  tags: `meta` entries render as `<meta name=... content=...>` in
  dict-iteration order; `links` entries render verbatim (attribute
  dict -> `<link ...>` tag). Deliberately **not** run through
  `_relative_asset_path` the way `favicon`/`og_image` are -- unlike
  those two (always a local build asset), a `links` entry is at least
  as likely to point at an external origin (`rel="preconnect"` to a
  webfont host) as a local one, and there's no reliable way to tell
  which from the shape of the dict alone. A site author who wants a
  route-relative `<link>` (e.g. an extra icon size) supplies the
  already-correct relative path themselves, same as any other
  external-facing prop this backend doesn't rewrite.

**10 new tests** (`tests/test_html_backend.py`): rendering (single
entry, multiple entries in insertion order, arbitrary link attributes,
multiple `<link>` tags), HTML escaping for both props, the
"page that sets neither renders unchanged" byte-for-byte guarantee
(extending the existing `test_page_without_head_meta_props_renders_
unchanged` coverage), and validation errors for an empty `meta` dict
and a `links` entry missing `rel`. 541 tests total, all passing.

**Stage B (`responsive_style` + `@media` compilation)** shipped
earlier, independently, per the entry above.

## v0.0431 -- Emergency patch: unrouted-reference build warning (DONE)

Out-of-band alpha maintenance release, numbered inside the v0.043 ->
v0.0438 gap rather than waiting for v0.044. Triggered by an external
audit of the HTML backend that found `ROUTE_AWARE_ATTRS = {"href",
"src"}` doesn't cover `srcset` (`Picture`/`PictureSource`), `poster`
(`Video`), or `action`/`formaction` (`Form`) -- all four sit in
`PASSTHROUGH_ATTRS` and are emitted verbatim, so a route-shaped value
(`/assets/preview.png`) works when served from `/` and silently 404s
the moment the site is deployed from a subdirectory or opened via
`file://`. Same failure shape as the already-fixed `href`/`src` case,
just never extended to the newer attrs when they were added.

**Shipped:** detection only, not the fix. `arklight.backend.html.render`
now calls `warnings.warn(...)` (build continues; nothing fails) whenever
one of those four attributes gets a value `_is_internal_route_ref`
recognizes as route-shaped -- `srcset` is split on `,` and each URL
checked individually, since it's a list of `url descriptor` pairs, not
a single value. The message names the node type, attribute, and value,
states this is a known alpha limitation, and points at this patch
series. One file touched (`arklight/backend/html/render.py`); no
page-facing API change; all 293 existing tests still pass (one,
`test_form_elements_render_with_form_attrs`, now also emits the new
warning, which is expected -- it was already hitting this exact gap).

**Checked, not touched:** the audit's other claimed gap -- an unknown
`on_click` value (a typo like `"dismis"`) silently round-tripping into
harmless-looking `data-ark-on-click="dismis"` output -- does not
reproduce on this branch. `arklight/ir/validate.py`'s
`_validate_behavior_props` already raises `ValidationError` for any
`on_click` not in `KNOWN_BEHAVIORS`. No change made where there was
nothing to fix.

**Left open at the time.** Three more items from the same audit --
`<html lang="en">` hardcoded with no `Site`/`Page` override, the
`--ark-max-width` CSS variable unreachable from any public API, and
every `--ark-*` custom property being an untyped string substitution
(no `@property`, so a bad value like `--ark-max-width: 75re;` fails
silently) -- had **no code path a site author could hit at the time**,
since no prop existed yet that would let them trigger the gap. Status
since: `--ark-max-width` was fixed by the CSS backend refactor
(`docs/CONTAINER-WIDTH-BUG.md`); `<html lang="en">` was fixed by
`Site(lang=...)`/`Page(lang=...)`/`arklight build --lang` (see
`CHANGELOG.md`'s `[0.0434]`); untyped `--ark-*` custom properties
remains open. These were noted as "tracked against the CSS/HTML
backend refactor in `docs/DESIGN-NOTES.md`" -- no such section was
ever written there; the design doc is now `docs/HTML-BACKEND-REFACTOR.md`
(HTML side) and `docs/CSS-BACKEND-REFACTOR.md` (CSS side, landed).

**Real fix (route-rewriting `srcset`/`poster`/`action`/`formaction`
the way `href`/`src` already are) is not in this patch** -- it needs
`srcset`'s comma-separated list split and rejoined per-URL, and a
decision on whether `action`/`formaction` should warn-and-skip instead
of rewrite (a form action is at least as likely to be an external API
endpoint as an internal route). Tracked as a follow-up, not v0.0431's
job -- this release is the safety net, not the repair. Now designed
(not yet implemented) in `docs/HTML-BACKEND-REFACTOR.md`'s reachability
audit, as part of that refactor's `routing.py` module.

Version bumped `0.043` -> `0.0431` (`pyproject.toml`,
`arklight/__init__.py`) so `arklight --version` and build-output banners
reflect the patch.



Documentation-only session: wrote up the full design in
`docs/DESIGN-NOTES.md` ("v0.0438: Android backend"), added the
milestone row + Future-backend note to `docs/ARCHITECTURE.md`, and
this snapshot/narrative entry. No code written -- matches every other
PLANNING section's "design complete, implementation not started"
convention. Deliberately not mentioned in `README.md` for the same
reason no other unbuilt PLANNING item is.

Key decisions, in brief (full reasoning in `docs/DESIGN-NOTES.md`):

- **Why `androidx.webkit.WebViewAssetLoader`**, not a solo-maintainer
  WebView-wrapper library: it's a Jetpack/AndroidX artifact, so the
  maintenance-risk axis (who keeps this working) is Google's AndroidX
  release train, not one person's side project. Also solves a real
  problem plain `file://` loading has: opaque/null origin, unreliable
  `localStorage`/`fetch()` behavior.
- **The build toolchain (JDK, Android SDK, Gradle/AGP, network) is
  unavoidable**, even for the smallest possible version of this
  feature -- `WebViewAssetLoader` only exists as compiled bytecode
  inside an APK, there's no "just drop in a .js-equivalent file" path.
  An earlier, too-optimistic take assumed a template-only path could
  avoid this entirely; corrected in the design doc. What *does* stay
  genuinely zero-dependency: generating the Kotlin/Gradle project
  files themselves is pure templating, same as every other backend.
- **`subprocess` is the only tool needed** to shell out to the
  generated project's `./gradlew`, not PyJNIus/JPype (JNI bridges --
  solve a different problem, calling into live JVM objects) or Jython
  (a separate Python implementation entirely). No new third-party
  dependency on ARKlight's own side, same discipline as the ARK
  Bundle sealing code (stdlib `hmac`/`hashlib`/`secrets` only).
- **Graceful failure with no JDK present**: `subprocess` against a
  missing `java`/`gradlew` raises `FileNotFoundError`/`OSError`, not a
  Java-flavored error -- caught explicitly (not left to the v0.041
  catch-all) with a clear "install a JDK" message rather than a raw
  traceback.
- **A 4-stage CLI ladder** (`arklight android scaffold` ->
  `build` -> `build --install` -> `build --release`) so the user
  decides how far to go -- e.g. someone who only wants the generated
  project to open in Android Studio themselves never needs a JDK on
  *this* machine at all.
- **Cross-reference correction**: the actual dependency isn't on
  `v0.044` (none of its planned sub-systems care what origin a page
  is served from) -- it's specifically on the vdom-staging **Stage
  8** (`localStorage` persistence), because `localStorage` is scoped
  per-origin, and only a real, stable origin (which
  `WebViewAssetLoader` provides and `file://` doesn't) makes that
  persistence reliable inside a packaged app. That's why this section
  is placed right after Stage 8 in `docs/DESIGN-NOTES.md`, not after
  `v0.044`.
- Explicitly out of scope for now: iOS/`WKWebView` (different
  toolchain, own future design), any native-plugin/JS-bridge layer
  beyond asset serving, and Play Store signing/publishing automation.

**Stage 0 (Viewer-repo promotion) and Stage 1 (`arklight android
scaffold`) since shipped** -- see `CHANGELOG.md` for both. Stage 1's
scaffold reads app identity from `arklight.config.py`'s `"android"`
section and produces a buildable, if generically branded, project
even with no config at all.

**Stage 2a (GitHub Actions CI build) also shipped**, splitting the
design doc's original single "Stage 2" in two: 2a ships a GitHub
Actions workflow as part of every scaffolded project, building a
debug APK on GitHub-hosted runners with no local JDK/Android SDK
required; 2b (shelling out to a *local* Gradle install) keeps the
original Stage 2 scope and stays not-yet-implemented. Rationale in
`docs/Backends/ANDROID-BACKEND-IMPLEMENTATION.md`'s "Why split Stage 2
into 2a/2b" note -- in short, CI build verification doesn't actually
need the local-machine toolchain the original single stage assumed
every rung of the ladder needed, so splitting it off let that half
ship immediately instead of waiting on 2b's `subprocess`/JDK-detection
work.

**Stage 3a (CI install + launch smoke test) shipped too**, same split
applied one rung up: the same workflow file gained a second job that
downloads 2a's APK, boots a throwaway emulator on the runner, and
fails if the app crashes on launch -- real regression coverage beyond
"does it compile," still with zero local toolchain. 3b (`adb install`
onto a device the user has actually connected) keeps the original
Stage 3 scope, now depending on 2b instead, and stays not-yet-started.
Rationale in the same doc's "Why split Stage 3 into 3a/3b" note.

**Stage 4 (CI release build) shipped, and the whole ladder's
letter-suffixed numbering was retired.** The same workflow file gained
a third, independent job, `assemble-release`, building a release APK
via `gradle assembleRelease` on GitHub-hosted runners -- optionally
signed from `RELEASE_KEYSTORE_BASE64`/`RELEASE_KEYSTORE_PASSWORD`/
`RELEASE_KEY_ALIAS`/`RELEASE_KEY_PASSWORD` repo secrets if configured,
unsigned otherwise, same "gracefully degrade, don't fail" shape the
JDK-detection handling already established elsewhere in this ladder.
With all three CI-only stages (build, smoke test, release build) now
shipped well ahead of any of their local-machine counterparts, the
`2a`/`2b`/`3a`/`3b`/`4a`/`4b` naming this section describes above was
retired in favor of plain sequential numbers: the CI stages above are
now Stages 2/3/4, and the not-yet-started local counterparts (`arklight
android build`, `--install`, `--release`) are now Stages 5/6/7. See
`docs/Backends/ANDROID-BACKEND-IMPLEMENTATION.md`'s "Numbering" note
and `CHANGELOG.md` for the full reasoning and implementation details.

## Reactive-core vdom staging -- Stage 1: vdom core integration (DONE)

Separate initiative from `v0.044` below, not a `v0.0XX`-numbered
milestone -- it's staged work on the *mechanism* under `State`/`Bind`,
tracked as "Stage 1 of 8" in `docs/DESIGN-NOTES.md` ("Reactive-core
vdom staging"). Vendored snabbdom 3.6.4's bare core (`init`, `h`,
`vnode`, `htmlDomApi`; none of its optional modules) into the new
`arklight/backend/js/vdom.py`, MIT-attributed, and swapped the state
runtime's `renderBindings` pass from a raw `el.textContent = ...`
assignment to a real vdom `patch()` call. Verified with the full
existing test suite (unchanged, 260 passed) plus a live jsdom smoke
test confirming the same DOM node is reused (no remount) across
repeated state updates. No page-facing API change; pages without
`State(...)` still ship none of the vendored code.

Chose to vendor only the four core files (`init`/`h`/`vnode`/
`htmldomapi`), not any of snabbdom's optional modules
(`attributes`/`class`/`dataset`/`eventlisteners`/`props`/`style`) --
those add capability this stage doesn't need yet (Stage 2, reactive
class binding, will want a minimal hand-written class-diff instead of
pulling in the whole `classModule`, to keep with the closed-registry
discipline the rest of the JS backend already follows). Next queued:
Stage 2 (reactive class binding), then Stages 3-7 (the rest of
`v0.044`'s sub-systems, built against this vdom instead of the old
textContent pass), then Stage 8 (`localStorage` persistence for
`State`).

## Reactive-core vdom staging -- Stage 2: reactive class binding (DONE)

`Bind.when("active", "is-active")` (a `ClassBindSpec`, mirroring
`ActionRef`'s shape) plus a `bind_class=` prop, validated the same way
`Bind`/`Action.*` already are (unknown `state` target, or an empty
`class_name`, both fail the build). HTML backend pre-fills the class
at build time from `State`'s initial value, same as `Bind`'s text
already does, so the page is correct with JS disabled. 10 new tests in
`tests/test_class_binding.py`; full suite (270) green.

Decided *against* routing this through Stage 1's vendored vdom, even
though that was the original plan sketched when Stage 1 landed: the
bare core has no class module, and encoding the class into an
element's vdom selector would make `patch()`'s `sameVnode` check see a
different vnode on every toggle and remount the element -- silently
dropping any `on_click` listener already wired to it. Went with a
small, separate, hand-written `renderClassBindings` pass
(`el.classList.toggle(...)`) instead -- correct, and more honest about
what a *bare* vdom core actually covers than stretching it to do
something it wasn't built for. Next queued: Stage 3 (event modifiers).

## Reactive-core vdom staging -- Stage 3: event modifiers (DONE)

`Action.set("saved", True).debounce(300)` / `Action.remove("items",
0).with_modifiers("prevent", "stop", "once")` -- new builder methods
on `ActionRef` (`arklight/ast/nodes.py`) attach `prevent`/`stop`/
`once`/`debounce:<ms>`/`throttle:<ms>` tokens, drawn from a new
closed `MODIFIER_REGISTRY` (`arklight/ir/schema.py`), the same
registry discipline `ACTION_REGISTRY`/`BEHAVIOR_REGISTRY` already
established. Validation (`arklight/ir/validate.py`) rejects unknown
modifier names and enforces that `debounce`/`throttle` carry a
positive integer value while `prevent`/`stop`/`once` don't take one.

The HTML backend renders the modifiers as a single
`data-ark-modifiers="prevent,debounce:300"` attribute on the element
(omitted entirely when an `ActionRef` has no modifiers attached, same
only-ship-what's-used discipline as everywhere else). The JS runtime
adds one small wrapper, `arkApplyModifiers`, that reads that attribute
once per element and wraps the action dispatcher with `stop`/`once`
short-circuiting plus debounce/throttle timing -- `prevent` itself is
already honored unconditionally by the existing click listener's
`event.preventDefault()`, so `.with_modifiers("prevent")` is really
documenting intent rather than changing runtime behavior. Named
behaviors (`on_click="toggle"`, etc.) have no modifier-attaching API
yet -- deliberately out of scope for this stage, which only touches
`ActionRef`-based `on_click`.

17 new tests (`tests/test_event_modifiers.py`). No change to
`State`/`Bind`/existing `Action.*` behavior, and this stage does not
route through Stage 1's vendored vdom `patch()` -- modifiers are a
dispatch-timing concern on the listener itself, not a DOM-diffing
concern. Next queued: Stages 4-7 (computed/derived state, watch
effects, two-way input binding, per-item list rendering, conditional
show/hide -- the remaining `v0.044` sub-systems), then Stage 8
(`localStorage` persistence for `State`).

## v0.054 -- JS backend capability expansion: reactive core parity with Vue 3 (PLANNED)

Renumbered from v0.044 now that v0.048 (CSS `@media` + `<head>`
extension, picked up first out of announced order) has shipped in
full -- see the Snapshot table at the top of this file. Design and
scope are unchanged.

Requested by the maintainer: bring "most of Vue 3's JS capabilities"
into the JS backend -- computed/derived state, watchers, two-way
input binding, per-item list rendering, conditional show/hide, event
modifiers, reactive class binding. Full design writeup in
[`docs/Foundational/DESIGN-NOTES.md`](./docs/Foundational/DESIGN-NOTES.md) ("v0.044: JS backend
capability expansion -- reactive core parity with Vue 3"). Design
complete; implementation not started.

Explicit scope boundary carried over from the maintainer's own framing
and enforced throughout the design: **anything achievable in CSS or
HTML stays in the CSS/HTML backends.** This milestone only ever adds
*reactivity* (state changing, and the DOM reflecting that change) --
never new visual/structural vocabulary, which already has its own
dedicated pipelines and its own milestones (`v0.048` for CSS, the two
vocabulary addenda for HTML). Where a feature sounds like both (e.g.
"conditional rendering"), the JS side only decides *whether/what*
renders; *how it looks* is still 100% CSS the author already
controls.

- [x] **Computed/derived state** (`Computed(name, deps=(...),
      derive=Derive.sum(...))` etc.) -- a closed `DERIVATION_REGISTRY`
      (`Derive.sum`, `Derive.join`, `Derive.count`, `Derive.format`,
      `Derive.compare`), same registry discipline as
      `ACTION_REGISTRY`. **Landed as `vdom-4`** (docs/Backends/
      REFACTOR-INDEX.md row 12) -- see the dedicated narrative section
      below and `tests/test_vdom_4.py`. The rest of this milestone's
      sub-systems (watch effects onward) remain not implemented.
- [ ] **Watch effects** (`Watch("state_key", then=Action.xxx(...))`
      declared on `Page(...)`) -- state-change-triggered side effects
      reusing the existing action dispatcher, just triggered by
      `store.set` instead of only by click. Not implemented yet.
- [ ] **Two-way input binding** (`Input(..., bind_value="field")` ->
      `data-ark-model`) -- the `v-model` equivalent; wires
      `input`/`change` back into `store.set`. Not implemented yet.
- [ ] **Per-item list rendering** (`Repeat(state_name, template=fn)`)
      -- the `v-for` equivalent and the single biggest lift here,
      already flagged as the real remaining gap back in the
      `v0.0035` addendum II writeup ("comma-joined display is a
      stopgap, not the end state"). Needs a new IR node carrying a
      template sub-tree, plus a fixed `<template>`-clone-per-item
      runtime function. Not implemented yet.
- [ ] **Conditional show/hide** (`Show(Predicate.truthy("flag"),
      children)`) -- the `v-show`/`v-if` equivalent, driven by a
      closed `PREDICATE_REGISTRY` (`truthy`, `equals`, `gt`, `lt`),
      never a raw boolean expression. Not implemented yet.
- [ ] **Event modifiers** (`prevent`, `stop`, `once`,
      `debounce:<ms>`, `throttle:<ms>`) -- one small dispatcher
      wrapper via a closed `MODIFIER_REGISTRY`, not per-action
      duplication. Not implemented yet.
- [ ] **Reactive class binding** (`class_name=Bind.class_if("is_open",
      "expanded")`) -- toggles an *existing* CSS class (defined by
      the CSS backend/`Site.style`, not by this milestone) based on
      state. This is the "later `class_name=Bind(...)` for
      conditional classes" note left open back in the original
      `v0.0035` design section. Not implemented yet.
- [ ] Generalize the reactive core (`createState`/`renderBindings`/
      the action dispatcher in `arklight/backend/js/render.py`) into
      a real dependency graph (state key -> {computed keys, watchers,
      bound elements, repeat blocks, show-if predicates} depending on
      it), so one `store.set` triggers only what actually depends on
      that key. Not implemented yet.

**Explicitly out of scope for v0.044** (tracked here so it doesn't get
assumed-in-scope later, same convention this file already uses for
`v0.048`):

- Any real JS/template-expression evaluator, `eval`, or `new
  Function` -- permanent non-goal, not just deferred. Vue 3's own
  breadth comes partly from a real expression evaluator in its
  compiled render functions; this milestone gets comparable coverage
  of *common patterns* through a breadth of closed, named primitives
  instead, which is a real and permanent capability ceiling worth
  being honest about, not a temporary gap.
- Component props/slots/`provide`/`inject`/composition-API-style
  reuse -- that's `v0.010` (components), which hasn't started; this
  milestone doesn't assume or get ahead of it.
- CSS transitions/animations/`@keyframes` for the `Show` toggle --
  that's `v0.048`'s (and beyond) territory; `Show` only flips an
  attribute/class, never defines how a change looks.
- New HTML component types or semantic vocabulary -- that's the HTML
  backend/schema's job (the two vocabulary addenda), not this one.
- Lifecycle hooks (`onMounted`/`onUpdated`) -- no concrete forcing use
  case yet; deferred rather than added speculatively.
- Alternate framework backends (Vue/Svelte codegen) -- still `v0.100`,
  still blocked on the same state/event-semantics prerequisite
  `docs/DESIGN-NOTES.md` already names, which this milestone is a
  step towards but does not itself complete.

## v0.041 -- JS runtime error-handling hardening (DONE)

**Status: DONE**, version number not yet assigned. Follow-up to "CLI &
pipeline error-handling hardening" directly below -- that pass covered
the Python/CLI side and explicitly deferred the generated client-side
`arklight.js` runtime, which had **zero** `try`/`catch` anywhere in it
(confirmed by reading `arklight/backend/js/render.py` and every
behavior/action fragment directly). Full detail in `CHANGELOG.md`
("JS runtime error-handling hardening"). Short version:

- [x] New `arkNotify(message)` helper (`arklight/backend/js/render.py`)
      -- small, self-contained, inline-styled on-page notice, shipped
      only when a site actually uses a behavior or declares
      `State(...)` (same "only ship what's used" discipline as the
      rest of this runtime). Gives end users a visible signal instead
      of a console-only error nobody but a developer would ever see.
      Wrapped in its own `try`/`catch` so the notifier itself can
      never throw.
- [x] `initState()`'s `JSON.parse` is now guarded -- previously a
      malformed `data-ark-state` attribute threw inside the
      `DOMContentLoaded` handler and silently aborted `wireActions()`
      (and anything scheduled after it) for the whole page.
- [x] `wireActions()` and `wireBehaviors()` now guard each element's
      setup *and* its click dispatch independently -- previously one
      malformed element (bad JSON in `data-ark-action-args`, or a
      behavior/action throwing at click time) could abort the
      `forEach` loop for every other element on the page, not just the
      one at fault.
- [x] The `copy` behavior's clipboard promise
      (`arklight/backend/js/behaviors/copy.py`) now has a `.catch()`
      -- previously an unhandled rejection, notable because
      `arklight build --open` opens sites as `file://` URLs by
      default, exactly where clipboard permissions are likeliest to be
      denied.
- [x] `tests/test_js_error_handling.py` -- 8 new tests (212 total, all
      passing).

Deliberately left out: `renderBindings()` and `highlightActiveNavLink()`
have no plausible runtime failure mode given their inputs
(`store.get(key)` returning `undefined` just renders as the text
"undefined", not a throw; the nav-highlight loop only ever touches
`<a>` elements' own `.href`), so no guard was added to either.

## v0.041 -- CLI & pipeline error-handling hardening (DONE)

**Status: DONE**, version number not yet assigned. Prompted by a UX
audit comparing the CLI's error handling against how the generated
client-side JS runtime handles (or rather, doesn't handle) failures.
Full detail in `CHANGELOG.md` ("CLI & pipeline error-handling
hardening"). Short version:

- [x] `arklight/cli/main.py::main()` -- top-level `try/except` around
      subcommand dispatch. Every subcommand already caught its own
      typed error (`CompileError`/`PackError`/`PWAError`/
      `ScaffoldError`); anything outside those known, anticipated
      failure modes previously escaped as a raw traceback, which
      directly contradicted the CLI module docstring's own stated
      goal. Now prints a clear "outside ARKlight's known, handled
      failure modes" message and exits `1`.
- [x] `arklight/compiler/pipeline.py::build()` -- the output-file
      write loop and the `_copy_assets()` call are now each guarded
      with `try/except OSError`, reporting exactly how many files
      wrote successfully before a failure (permissions, disk full, a
      network drive dropping mid-write) rather than leaving a silently
      partial output directory that looks the same as a complete one.
- [x] `_cmd_pack` -- prints a runtime warning when `--passphrase` is
      passed on the command line (shell history / process-listing
      exposure), rather than leaving that risk documented only in
      `--help` text.
- [x] Fixed a real, pre-existing bug found while making the change
      above: `_cmd_pwa` was defined twice in `arklight/cli/main.py`
      (identical bodies, second silently shadowed the first). Removed
      the duplicate.
- [x] Fixed a version drift recurrence: `pyproject.toml` said `0.1.0`
      while `arklight/__init__.py` already said `0.038` -- same class
      of bug as the one fixed during the "v0.003 addendum" pass below,
      just recurred for a later version jump and went uncaught.

Deliberately out of scope for this pass, tracked as separate follow-up
work: the generated client-side `arklight.js` runtime has an
analogous gap -- zero `try`/`catch` anywhere in
`arklight/backend/js/render.py`'s output, an unhandled clipboard-
promise rejection in the `copy` behavior (`.writeText().then(...)`
with no `.catch()`, notable since `arklight build --open` opens sites
as `file://` URLs by default -- exactly where clipboard permissions
are likeliest to fail), and a single malformed
`data-ark-action-args` attribute able to abort `wireActions()`'s
`forEach` for every *other* element on the page, not just the bad one.

**Update:** this follow-up is now done -- see the "JS runtime
error-handling hardening" milestone directly above.

## v0.042 -- Extra CSS features: custom classes, `arklight search`, `arklight --help` (DONE)

**Status: DONE**, shipped and bumped to `0.42.0`. This entry was
missing from PROGRESS.md even though the code shipped and
`CHANGELOG.md` already has the full writeup ("[0.042] -- Extra CSS
features: custom classes, `arklight search`, `arklight --help`") --
docs are being brought back in sync with the code here, same situation
as the `v0.0035` entry below. Full design context in
`docs/DESIGN-NOTES.md` ("v0.042: extra CSS features"). Goal was
cutting boilerplate/nesting in the styling API and closing two
long-open CLI discoverability gaps -- not new `@media`/`<head>`
capability (that's `v0.048`).

- [x] **`Site.style(name, rules)`** (`arklight/api.py`) -- registers a
      real, named, reusable CSS class from a plain
      `{css-property: value}` dict; `class_name="name"` anywhere in
      the site then picks up the rules from the generated stylesheet
      instead of repeating a `style={...}` dict on every node that
      needs it. Validated at registration time (safe single class
      identifier; non-empty rules dict). Re-registering the same name
      overwrites it (last call wins).
- [x] **`WebsiteIR.custom_styles`** (`arklight/ir/build.py`) threads
      `Site.custom_styles` through `build_website_ir()`.
- [x] **`CSSBackend`** (`arklight/backend/css/custom_styles.py`, new
      module split out of `render.py`) renders `ir.custom_styles` as
      `.name { prop: value; }` blocks, sorted for deterministic
      output, appended after the fixed base stylesheet so custom
      classes can override base rules by cascade order. Custom classes
      and the fixed base utility classes (`.nav`, `.card`, `.stack`,
      ...) share the same `class_name=` mechanism -- nothing new
      needed on the HTML backend side.
- [x] **`arklight search <name>`** (`arklight/search/`,
      `arklight/cli/search.py`, `arklight/cli/main.py`) -- read-only
      schema lookup against `arklight.ir.schema.SCHEMA`: required
      props, whether children are allowed, and whether the component
      is a `Bind(...)`-able target. Exact match (case-insensitive)
      wins outright; otherwise falls back to typo-tolerant "did you
      mean" suggestions. No external dependency, no new data format,
      no compiler-pipeline changes. Does not currently search the base
      stylesheet's utility class names, only component schema --
      possible follow-up, not scoped for this pass.
- [x] **`arklight --help` / bare `arklight`** (`arklight/cli/main.py`)
      -- `--help` already worked via argparse's built-in flag;
      running bare `arklight` (no subcommand) used to print argparse's
      terser "error: the following arguments are required: command"
      instead of full help. Subparsers are no longer `required=True`;
      a bare `arklight` now prints full help and exits `0`.
- [x] Fixed a real version-drift bug from the published PyPI release:
      `pyproject.toml`'s version and `arklight.__version__` disagreed.
      `arklight/__init__.py` no longer hardcodes a second copy --
      `__version__` reads back from the installed package's own
      metadata (`importlib.metadata.version("arklight")`), so
      `pyproject.toml` is the single source of truth. Also moved off
      the old two/three-digit milestone-number-as-decimal scheme to a
      proper three-part `MAJOR.MINOR.PATCH` string (the old scheme was
      a real PEP 440 hazard: `0.100` normalizes to `0.1`, which would
      have sorted below `0.048`'s `0.48`).
- Test coverage: `tests/test_api_style.py` (new),
  `tests/test_css_backend.py` (extended),
  `tests/test_pipeline_end_to_end.py` (extended), `tests/test_search.py`
  (new), `tests/test_cli.py` (extended), `tests/test_version.py` (new,
  locks `__version__` to installed package metadata).

## v0.0035 -- Stateful JS (DONE)

**Status: DONE.** This entry was missing from PROGRESS.md/CHANGELOG.md
even though the code shipped -- `pyproject.toml` and
`arklight/__init__.py` both already read `0.0035`, and the README
"Status" section already described this milestone in the present
tense. Docs are being brought back in sync with the code here rather
than the other way around; nothing described below required new
implementation work.

### What's implemented

- [x] `KNOWN_BEHAVIORS` (a flat `frozenset`) replaced by
      `BEHAVIOR_REGISTRY: dict[str, BehaviorSpec]`
      (`arklight/ir/schema.py`) -- `KNOWN_BEHAVIORS` stays as a derived
      `frozenset(BEHAVIOR_REGISTRY)` so Validation's existing check
      didn't need to change shape.
- [x] `arklight/backend/js/behaviors/` -- one file per behavior
      (`toggle.py`, `scroll_to.py`, `copy.py`, `dismiss.py`), each a
      `JS_FRAGMENT` string; `JSBackend.render()` concatenates only the
      fragments a given site's IR actually references.
- [x] `arklight/backend/js/actions/` -- one file per closed action
      (`set.py`, `increment.py`, `toggle_bool.py`), driven by a new
      `ACTION_REGISTRY` (same registry pattern as behaviors), so a
      future `Action.append_to_list`/etc. is a new registry entry, not
      a `JSBackend` rewrite.
- [x] New API in `arklight/api.py`: `State(name, initial)` (declares
      page-scoped reactive state, stored on the IR's `Page` node),
      `Bind(name)` (references a declared `State(...)` wherever a
      literal prop value is accepted today, e.g. `Text(Bind("count"))`),
      and `Action.set`/`Action.increment`/`Action.toggle_bool`
      (structured `ActionRef` objects for `on_click=`, never an
      arbitrary JS/Python string).
- [x] Validation extended: every `Bind(...)`/`Action.*(...)` must
      reference a `State(...)` actually declared on that page, same
      "catch it at compile time" guarantee the rest of Validation
      already provides.
- [x] `JSBackend` emits, only for pages that declare `state`, a small
      fixed reactive core (`createState` closure, `data-ark-bind`
      re-render wiring, an action dispatcher walking
      `ACTION_REGISTRY`) -- still no `eval`, no `new Function`, no
      string ever executed as code.
- [x] `tests/test_stateful_js.py` -- 14 tests covering the new API,
      validation, and generated runtime (130 tests total, all
      passing).

### Deliberate design choices worth remembering later

- Explicit scope boundary honored: this milestone added **capability,
  not vocabulary** -- no new named behaviors, just the registry
  refactor plus the `State`/`Bind`/`Action` primitives, exactly as
  scoped in `docs/DESIGN-NOTES.md` ("v0.0035: stateful JS --
  capability, not vocabulary").
- This is the reactivity/IR-state milestone `docs/DESIGN-NOTES.md`
  named as the real prerequisite for v0.100 (alternate backends) to
  mean more than static HTML wearing a different file extension --
  worth revisiting that section before scoping v0.100 for real.

## v0.003 -- JavaScript helpers (DONE)

**Status: DONE.** Also folded in a round of research (Alpine.js/htmx,
Reflex, Mitosis) and a written positioning/design-notes doc, per
request, before committing to the JS design.

### Research performed

- Compared Alpine.js/htmx's "attributes describe behavior, a small
  shipped runtime does the rest, no build step" model against Reflex's
  "Python state class + live WebSocket backend" model. Reflex requires
  a running Python server and compiles the *frontend* to React while
  keeping state/logic server-side -- fundamentally incompatible with
  ARKlight being a static, backend-independent compiler with no runtime
  Python anywhere. Alpine/htmx's model -- ship a tiny fixed runtime,
  describe behavior via HTML attributes -- is the correct fit and is
  what v0.003 follows.
- Looked at Mitosis (Builder.io) as prior art for "one authoring layer,
  many framework backends" (the v0.100 vision). Confirmed the Backend
  interface is already shaped correctly for this, but that ARKlight's
  IR (`type/props/children`, no state or event semantics) isn't yet --
  see `docs/DESIGN-NOTES.md` for the full reasoning. This is now an
  explicit, named gap in the roadmap rather than an implicit one.
- Wrote up honest positioning against htpy/FastHTML (mature Python
  "no template language" tools; FastHTML already has an HTMX-based JS
  story) and against the Svelte comparison (structurally similar small
  beginning, but Svelte's breakout came from a genuinely new technical
  insight solving an acutely-felt problem, not just "started small").
  Captured in `docs/DESIGN-NOTES.md`.

### What's implemented

- [x] `KNOWN_BEHAVIORS` added to the shared schema
      (`arklight/ir/schema.py`) -- a closed, documented set of
      client-side behavior names (`toggle`, `scroll-to`). Closed
      deliberately: components accept a fixed behavior *name*, never
      an arbitrary JS string, keeping "the browser never executes
      Python" true in spirit (nothing runs that ARKlight didn't ship)
      and "one obvious way" true in practice.
- [x] Validation stage extended: any node with `on_click` must name a
      known behavior and must carry a `behavior_target` (CSS selector)
      prop, or the build fails with a specific message -- same
      "catch it at compile time, not silently in the browser"
      guarantee the rest of Validation already provides.
- [x] `JSBackend` (`arklight/backend/js/render.py`) -- generates a
      single static `arklight.js`: a `behaviors` dispatch object
      (`toggle`, `scroll-to`), a `DOMContentLoaded` wiring pass over
      `[data-ark-on-click]` elements, and automatic current-page nav
      link highlighting (`is-active` on any `.nav a` matching the
      current URL) with zero props required.
- [x] HTML backend updated: `on_click`/`behavior_target`/`toggle_class`
      props render as `data-ark-on-click` / `data-ark-target` /
      `data-ark-toggle-class` (not real HTML attributes), and every
      page now includes `<script src="...arklight.js" defer></script>`
      with the same relative-path resolution styles.css already gets.
- [x] **Renamed the behavior-selector prop to `behavior_target`,
      not `target`**, specifically because `target` is already a real
      HTML attribute (`<a target="_blank">`) and reusing it would have
      been a silent footgun the moment someone wanted both on one
      element. Caught and fixed before shipping, not after.
- [x] CSS backend: added `.nav a.is-active` styling and a `.hidden`
      utility class (`display: none`) that pairs with `toggle_class`
      for the common "hidden by default, revealed by a button" pattern.
- [x] `default_backends()` now returns `[HTMLBackend(), CSSBackend(),
      JSBackend()]`.
- [x] Example site updated: the shared `nav()` gets automatic active-
      link highlighting for free, and the home page gained a real
      "Show details" button using `on_click="toggle"` -- a working
      interactive element with no hand-written JavaScript anywhere in
      the example.
- [x] `docs/DESIGN-NOTES.md` added: styling ceiling (`style=`'s real ceiling
      is no pseudo-classes/`@media`/`@keyframes`/custom fonts, all of
      which need a `<head>` hook `Page` doesn't expose yet), audience
      positioning, the Svelte-comparison writeup, the Mitosis-reframe
      writeup (state/event semantics as the real blocker for v0.100),
      and why compile-time validation is a sharper AI-assisted-coding
      advantage than "Python is popular" alone.
- [x] 9 new tests (66 total, all passing): JS backend output content,
      behavior-prop validation (valid/unknown/missing target), HTML
      rendering of `data-ark-*` attributes and the script tag.
- [x] **Verified interactively with Playwright**, not just by reading
      generated HTML: served the built example over a local HTTP
      server, loaded it in real headless Chromium, confirmed the nav
      link for the current page gets `is-active`, confirmed
      `#more-details` starts hidden, clicked the "Show details" button,
      and confirmed it becomes visible. Screenshotted the result.

### Verification performed

```bash
arklight build examples/hello_site/site.py -o /tmp/dist_v3 --no-open
python3 -m http.server 8934 --directory /tmp/dist_v3 &
python3 -c "<playwright script: goto, check .is-active, click 'Show details', assert #more-details visible>"
# -> home link class: 'is-active' / about link class: '' (on index.html)
# -> details visible before click: False / after click: True
python3 -m pytest -q
# -> 66 passed
```

### Deliberate design choices worth remembering later

- **Closed behavior vocabulary, not arbitrary JS.** The obvious
  "easier" path would have been an `on_click="alert(1)"`-style raw JS
  string prop. Rejected because it reopens exactly the door "the
  browser never executes Python" is meant to keep shut (arbitrary
  code, just JS instead of Python), breaks Validation's ability to
  catch mistakes at compile time (a typo in a JS string isn't
  checkable), and turns every site into a slightly different JS
  dialect -- the opposite of "one obvious way."
- **`behavior_target` instead of `target`** to avoid colliding with the
  real HTML anchor `target` attribute. Small, but exactly the kind of
  naming collision that's cheap to avoid now and expensive once sites
  depend on it.
- **Static, constant `arklight.js` for v0.003**, mirroring the CSS
  backend's v0.002 scope cut: `JSBackend.render(ir)` doesn't yet
  inspect which behaviors a given site actually uses. A future pass
  emitting only the referenced behaviors is a natural, non-breaking
  follow-up.

## v0.002 -- CSS (DONE)

**Status: DONE.** Along with real CSS support, this pass also fixed
three "wrinkles" reported after v0.001 landed: the CLI didn't open
anything in a browser, the example site's nav links were broken once
you actually clicked them, and the example looked unstyled.

### What's implemented

- [x] `CSSBackend` (`arklight/backend/css/render.py`) -- a second
      backend that runs over the same Website IR as the HTML backend
      and contributes `styles.css`: a single default stylesheet
      (typography, spacing, buttons, links, nav/card utility classes)
      so a freshly generated site looks intentional with zero CSS
      written by the user. This is the literal "Backend Interface fans
      out to multiple backends" design the architecture doc gestured
      at under "Future: CSS, JavaScript, Vue, Svelte."
- [x] `arklight/compiler/pipeline.py` now runs a *list* of backends by
      default (`default_backends() -> [HTMLBackend(), CSSBackend()]`)
      and merges their output file dicts before writing. `build(...,
      backends=[...])` lets callers customize this.
- [x] Style props on any component: `class_name="..."` (renders as the
      HTML `class` attribute; named to dodge the `class` keyword) and
      `style={...}` (a dict of CSS properties, rendered as an inline
      `style` attribute, e.g. `{"font_weight": "bold"}` ->
      `style="font-weight: bold"`).
- [x] **Internal links now compile to real relative file paths.**
      `Link("About", href="/about")` is resolved against the site's
      route table at render time and rewritten to `about.html`,
      `../about.html`, etc., depending on the linking page's location.
      External URLs (`https://...`), protocol-relative URLs (`//...`),
      fragments (`#section`), and `mailto:`/`tel:` links are left
      untouched. Same handling applies to the generated `<link
      rel="stylesheet">` tag, so it resolves correctly for nested
      routes too.
- [x] CLI auto-opens the built site in the default browser
      (`webbrowser.open` on a `file://` URI to `index.html`) after a
      successful `arklight build`, controlled by `--open` (default)
      /`--no-open`. Browser-launch failures (e.g. headless CI) are
      swallowed rather than failing the build.
- [x] Example site (`examples/hello_site/site.py`) rewritten: a shared
      `nav()` helper function (plain Python composition) is called
      from both pages so Home and About actually link to each other;
      `class_name="nav"`/`"card"`/`"muted"` used to lean on the new
      default stylesheet.
- [x] 15 new tests (57 total, all passing): CSS backend output,
      relative-link resolution (same-level, nested, unknown routes,
      externals/fragments untouched), `class_name`/`style` rendering,
      stylesheet link path correctness, and CLI browser-open behavior
      (mocked -- no real browser launched in tests).

### Verification performed

```bash
arklight build examples/hello_site/site.py -o /tmp/dist_v2 --no-open
# inspected output HTML directly: hrefs are "index.html"/"about.html", not "/about"
# rendered both pages with wkhtmltoimage --enable-local-file-access to confirm
# the stylesheet loads and the page is visually styled, not "hot garbage"
python3 -m pytest -q
# -> 57 passed
```

### Bugs found and fixed during this milestone

1. **The actual cause of "index and about aren't linked."** It wasn't
   a missing feature -- the example already had a `Link(..., href="/")`
   -- it was that root-absolute hrefs (`/about`) only resolve correctly
   once a site is deployed at a domain root. Opening `dist/index.html`
   directly via `file://` (exactly what a beginner does on "first
   setup") sends `href="/about"` to the filesystem root, not
   `dist/about.html`. Root-caused and fixed by making the HTML backend
   route-aware: it now knows every page's output path and rewrites
   internal hrefs to correct relative paths at compile time.
2. **Nothing ever opened a browser.** `arklight build` only wrote
   files and printed paths. Added `open_in_browser()` in the CLI,
   wired to run by default after a successful build.

### Deliberate design choices worth remembering later

- **One static, global stylesheet for v0.002**, not per-node CSS
  generation. `CSSBackend.render(ir)` currently ignores `ir` and
  returns a constant `styles.css`. This was a deliberate scope cut --
  collecting `style=` props into real generated CSS rules (instead of
  inline `style` attributes) is a natural v0.002-follow-up but wasn't
  needed to fix the reported problems or ship a good default look.
- **`class_name` instead of `class`** as the prop name, matching how
  most Python-to-HTML tools (JSX's `className`, Django templates via
  `class_`, etc.) dodge the same keyword collision. Kept consistent
  with "AI-friendly API": one obvious, greppable name.
- **Backends now form a list, not a single object**, in both
  `build()`'s signature and internally. This was the smallest change
  that matches the architecture doc's "Future: CSS, JavaScript, Vue,
  Svelte" framing literally -- multiple backends consuming the same IR
  -- rather than treating CSS as a special case bolted onto the HTML
  backend.

## v0.001 -- Python → HTML (DONE)

**Status: DONE.** Full pipeline implemented, tested, and verified
end-to-end against the example from ARCHITECTURE.

### What's implemented

- [x] `ARKNode` (`arklight/ast/nodes.py`) -- the ARK AST node type, plus
      the `node(type_name)` factory used to define every built-in
      component as a plain function.
- [x] Public API (`arklight/api.py`) -- `Site`, `Page`, `Heading`,
      `Text`, `Button`, `Container`, `Link`, `Image`, `List`, `Item`.
- [x] Static Python AST discovery (`arklight/parser/discover.py`) --
      uses the stdlib `ast` module to find `Site()` and
      `@site.page(...)` registrations **without executing user code**.
      This is a real, standalone pipeline stage, not just a comment.
- [x] Module loader (`arklight/parser/loader.py`) -- executes the site
      file in an isolated namespace to get the live `Site` object, with
      errors wrapped in `SiteLoadError` (bad file path, syntax error,
      no `Site()`, no pages, runtime error during module exec).
- [x] Normalization (`arklight/ir/normalize.py`) -- flattens nested
      list children (from comprehensions), drops `None`/`False`
      (conditional rendering pattern), and wraps bare strings as `Text`
      nodes -- *except* inside components that are themselves
      text-only, where a bare string is already correct.
- [x] Validation (`arklight/ir/validate.py`) -- schema-driven: unknown
      component types, missing required props (`Link.href`,
      `Image.src`), disallowed children (`Image`), and disallowed
      nesting (component inside a text-only component) all raise a
      specific `ValidationError` with a path to the offending node.
- [x] Shared schema (`arklight/ir/schema.py`) -- single source of truth
      for per-component rules, used by both normalize and validate so
      they can never disagree (this fixed a real bug -- see "Bugs
      found and fixed" below).
- [x] Website IR (`arklight/ir/build.py`) -- `IRNode` / `IRPage` /
      `WebsiteIR`, deliberately kept as a separate type from `ARKNode`
      even though v0.001's shapes are similar, so future milestones can
      let IR diverge from the public API's ergonomics.
- [x] Backend interface (`arklight/backend/base.py`) -- abstract
      `Backend.render(ir) -> {relative_path: contents}`. Backends never
      touch the filesystem directly, which keeps them trivially
      testable in isolation.
- [x] HTML backend (`arklight/backend/html/render.py`) -- maps IR node
      types to HTML tags, `Heading(level=N)` to `h1`-`h6`, known props
      to real HTML attributes, unknown props to `data-*` attributes,
      HTML-escapes all text content, and maps routes to output file
      paths (`/` -> `index.html`, `/about` -> `about.html`, `/blog/post`
      -> `blog/post.html`).
- [x] Compiler pipeline (`arklight/compiler/pipeline.py`) --
      orchestrates every stage above into `compile_site_file()` (source
      -> IR) and `build()` (source -> files written to disk). Every
      failure mode from every stage is caught and re-raised as a single
      `CompileError` with a clear message, so CLI users never see a raw
      internal traceback for an ordinary mistake (missing prop, unknown
      component, undefined name, etc.).
- [x] CLI (`arklight/cli/main.py`) -- `arklight build <entry.py> [-o
      OUTPUT_DIR]`, `arklight --version`.
- [x] Example site (`examples/hello_site/site.py`) -- two pages (`/`
      and `/about`), matching and extending the ARCHITECTURE.md sample.
- [x] Packaging (`pyproject.toml`) -- installable via `pip install -e
      .`, registers the `arklight` console script.
- [x] Test suite (`tests/`) -- 42 tests covering every stage in
      isolation plus full end-to-end builds. All passing.

### Verification performed

```bash
pip install -e .
arklight build examples/hello_site/site.py -o /tmp/dist_test
# -> valid index.html and about.html produced
python3 -m pytest -q
# -> 42 passed
```

### Bugs found and fixed during this milestone

1. **Double-wrapping strings inside text-only components.**
   Normalization originally wrapped every bare string child in a `Text`
   node unconditionally. This is correct for `Container`-like nodes
   (`Container("hi")` should become `Container(Text("hi"))` so
   container children are a uniform list of nodes) but wrong for
   components that are *themselves* text-only, like `Heading("hi")` --
   wrapping there produced `Heading(Text("hi"))`, which Validation then
   correctly rejected as "a Heading can't contain a nested component."
   Fixed by extracting a shared `arklight/ir/schema.py` with
   `TEXT_ONLY_TYPES`, consulted by both `normalize.py` (to decide
   whether to wrap) and `validate.py` (to decide whether nesting is
   allowed), so the two stages can't drift out of sync again.

2. **Page-function errors not surfaced as `CompileError`.** Because
   `@site.page(...)` only *registers* a function (it isn't called at
   module-exec time), a `NameError` or other exception raised **inside**
   a page function wasn't being caught by the loader's
   exec-time try/except -- it only appeared later, when
   `site.build_ark_ast()` actually calls each page function during
   pipeline execution. Fixed by wrapping the `build_ark_ast()` call
   (and the subsequent `normalize_ark_ast()` call) in the pipeline with
   their own try/except, so *every* stage's failure becomes a
   `CompileError` for CLI/API consumers, not just exec-time errors.

### Deliberate design choices worth remembering later

- **Execution vs. pure static analysis for the ARK AST.** The
  architecture doc's "Python AST" stage is implemented as genuine
  static analysis (via the stdlib `ast` module) for *discovery*
  (finding routes/pages), but the ARK AST itself is still produced by
  *executing* the module, because components are ordinary function
  calls and Python's full semantics (loops, conditionals, imports,
  helper functions) are needed to build real trees. Reimplementing a
  Python interpreter over the AST to avoid execution entirely was
  judged out of scope and against "Flask-like simplicity" for v0.001.
  If sandboxing untrusted site files ever becomes a requirement, this
  is the place to revisit.
- **IR kept structurally distinct from ARK AST**, even though in
  v0.001 `IRNode` and `ARKNode` look almost identical. This was a
  deliberate hedge for v0.100 (alternate backends) and v0.010
  (user-defined components), where the IR may need to diverge from
  whatever shape is most ergonomic for the Python API.
- **Route -> file path mapping** uses the simple convention `/` ->
  `index.html`, `/x` -> `x.html`, `/x/y` -> `x/y.html`. "Pretty URL"
  output (`/x/index.html`) was considered but deferred -- easy to add
  as a backend option later without touching earlier stages.

## v0.036 -- ARK Bundle spec v1 (DONE)

Implemented. Full writeup in `docs/DESIGN-NOTES.md` ("v0.036: ARK
Bundle spec v1"). Short version: `arklight pack <build-dir> -o
site.ark` packages a site's existing build output into a single
`.ark` file, so it can be shared and opened like a native document --
no local server, no Python environment, no separate player app on
desktop *or* Android.

Key design decision: the bundle is an **HTML/ZIP polyglot** -- the raw
build files are stored untouched inside a standard ZIP, with a fully
self-contained, inlined rendering of the entry page placed *before*
the ZIP data. The same bytes are simultaneously a directly-renderable
HTML document (a browser stops parsing at `</html>` and never touches
the trailing ZIP data -- no extraction, no temp files, same as opening
a `.mp4` doesn't unpack it first) and a valid ZIP archive (any archive
tool can extract the original, unmodified build output). Prior art:
this is the same technique the SingleFile web-archiving tool ships in
production as `--self-extracting-archive`. Confirmed working against
both Python's own `zipfile` reader and the system `unzip` binary.

Explicit scope boundary for v1, as shipped: packaging only, over files
the existing pipeline already produces. No changes to `normalize.py`/
`validate.py`/`build.py`/the `Backend` interface/the IR, and a
separate module (`arklight/packer/`) rather than logic folded into
the compiler internals (per explicit request -- see
`docs/DESIGN-NOTES.md`). **Only `.html`/`.css`/`.js` files are
inlined/packed** -- an `assets/` folder (images/audio/video/anything
else) is detected and reported as skipped rather than packed; carrying
those over is the next planned version, not this one. An
`--encrypt`/password flag so the ZIP payload isn't inspectable without
a password is planned for the version after that.

One implementation note worth flagging for future work in this area:
the original design doc assumed manual ZIP-header offset patching
would be needed to prepend arbitrary bytes before the archive. It
wasn't -- opening the same already-open file handle with
`zipfile.ZipFile(handle, mode="a")` after writing the HTML prefix to
it directly is sufficient, since `zipfile` computes offsets from the
handle's current position rather than assuming a byte-0 start.

## v0.004a -- CLI scaffolding (DONE)

`arklight new <name> --template simple|production` --
**implemented and wired into the CLI** (`arklight/cli/scaffold.py`,
`arklight/cli/templates/simple.py` and `.../production.py`,
`_cmd_new` in `arklight/cli/main.py`). This was originally tracked as
one of three pieces under a combined "v0.004" heading; it's since been
split out as v0.004a because it shipped well ahead of the other two.
The stale note further down this file ("v0.0035 -- done; v0.004 --
folder scaffolding only, logic not started") is superseded by this
entry -- see the correction inline there.

## v0.048 -- CSS `@media` queries + `<head>`/`<header>` extension (PLANNED) [STALE -- superseded]

**Superseded:** this entry is stale. `v0.048` (both Stage A and Stage
B) is DONE -- see "v0.048 -- Stage A: structured `<head>` extension"
and "v0.048 -- Stage B: `responsive_style` + `@media` compilation"
further up this file, and the Snapshot table at the top. The two
"explicitly out of scope" items below have since shipped too, as
`v0.042` (see that entry above) -- left in place, struck through
inline, purely as a historical record of what this milestone's design
phase looked like before implementation started.

The other two pieces of the old "v0.004" heading, renumbered to their
own milestone since they didn't land with the scaffolding above and
are now the next scheduled release. Design is complete and unchanged;
implementation has not started. Full writeup in
[`docs/Foundational/DESIGN-NOTES.md`](./docs/Foundational/DESIGN-NOTES.md) ("v0.048: CSS media
queries + `<head>` extension").

- [x] `responsive_style={...}` prop -> real `@media` blocks in the CSS
  backend. (Shipped -- see "v0.048 -- Stage B" above.)
- [x] `Page(meta=..., links=...)` -- a structured, non-arbitrary
  `<head>` extension point (no raw HTML injection). (Shipped -- see
  "v0.048 -- Stage A" above.)
- [ ] Anything else that touches the generated `<header>` element as
  part of this pass (the element, not the `<head>` extension above --
  see `docs/DESIGN-NOTES.md` for the distinction once design work
  starts).

**Explicitly out of scope for v0.048**, tracked separately below under
"Planned, not yet scheduled" -- ~~since shipped as `v0.042`~~:

- ~~User-authored custom CSS classes/rules beyond the fixed
  `class_name=` utility set.~~ Shipped as `Site.style(...)` in `v0.042`.
- ~~`arklight --search <name>` component schema lookup.~~ Shipped in
  `v0.042`.

## v0.010 -- Components (user-defined, reusable) (PLANNED)

Not started. Per `docs/DESIGN-NOTES.md`, this is where "write a plain
Python function" (today's `nav()` pattern) becomes a real, first-class
reusable unit -- likely with its own default styling bundled in, which
would be a genuine differentiator versus htpy/FastHTML (neither ships
opinionated per-component CSS). Rough questions to resolve first:

- What distinguishes a "component" from a plain helper function like
  `nav()` today? If the answer is "nothing, syntactically" the
  milestone may be more about a registration/discovery mechanism (so
  the compiler *knows* about reusable components, e.g. for future
  tooling) than a new runtime concept.
- Should components be able to carry their own default `style=`/CSS
  rules, shipped alongside the component definition rather than
  relying entirely on the global stylesheet?
- Note from the design-notes doc: this milestone does **not** by
  itself move ARKlight toward "Svelte-like." The next real fork in the
  road is whether a future milestone introduces state/event semantics
  into the IR (a prerequisite this doc names for v0.100 to mean
  anything beyond static output) -- worth deciding explicitly before
  v0.100, not assuming it falls out of v0.010 or v0.100 automatically.

## v0.003 -- vocabulary extension addendum I (DONE)

Not a new milestone/version -- this stays v0.003. Added ~46 more
built-in components (semantic layout, text-level semantics, forms,
tables, media) and two more closed JS behaviors (`copy`, `dismiss`) on
top of the original v0.003 JavaScript-helpers work, entirely as data
in `arklight.ir.schema.SCHEMA` / `arklight.ir.schema.KNOWN_BEHAVIORS`
-- no changes to normalize.py, validate.py, or build.py. See
`CHANGELOG.md` for the full list and `docs/DESIGN-NOTES.md` ("v0.003:
closing the vocabulary gap, not the structural ceiling") for what this
does and doesn't change about the ceiling (still no
`@media`/`@container`, still a closed JS vocabulary).

Also fixed a pre-existing version drift: `pyproject.toml` said
`0.001` while `arklight/__init__.py` said `0.003`; both now correctly
read `0.003`.

## v0.003 -- vocabulary extension addendum II (DONE)

Still v0.003, same mechanism as addendum 1: 33 more built-in
components, purely as data in `arklight.ir.schema.SCHEMA` (+
`TAG_MAP`/`PASSTHROUGH_ATTRS`/`VOID_TAGS` in the HTML backend, +
default CSS rules) -- normalize.py/validate.py/build.py untouched
again. This batch closes the "long tail" gaps a production
responsive static site still hits after addendum 1: a numbered list
(`OrderedList` -- addendum 1 could only ever produce `<ul>`),
description lists, art-directed responsive images
(`Picture`/`PictureSource` + `loading`/`decoding`, the image half of
"responsive design" that addendum 1's CSS-only utilities didn't
cover), native progress/gauge/autocomplete/output widgets, a
`Dialog` that opens and closes with zero JS via
`Form(method="dialog")`, the rest of text-level semantics including
bidi (`Bdi`/`Bdo`) and ruby (`Ruby`/`Rt`/`Rp`) annotations, table
column grouping, video/audio caption tracks, image maps, `IFrame`
embeds, and a `NoScript` fallback. 22 new tests in
`tests/test_vocabulary_addendum_2.py` (109 total). Full list and
per-group rationale in `CHANGELOG.md`.

Deliberately left out (see CHANGELOG.md "Notes" for why):
`<canvas>`/`<template>` (meaningless without JS driving them, out of
scope for the closed-behavior model), the new `<search>` landmark
(too new/unsettled), `<object>`/`<embed>` (redundant with `IFrame`
for this project's use cases).

## v0.0035 -- behavior/action fragment refactor (DONE)

**Superseded note, corrected in place (see "v0.004a" above) rather
than deleted, per this file's own convention of not silently editing
history:** this entry originally read "v0.0035 -- done; v0.004 --
folder scaffolding only (logic not started)." The scaffolding logic
described as not-started below has since shipped as v0.004a.

`arklight/backend/js/behaviors/` and `arklight/backend/js/actions/`
were originally added as empty, docstring-only packages ahead of the
actual work; both are now fully populated (see "v0.0035" above) --
`arklight/backend/js/render.py` assembles the runtime from these
fragments instead of one static `RUNTIME_JS` string.

At the time this entry was written, `arklight/cli/templates/` existed
only as placeholder directories (`templates/simple/assets/`,
`templates/production/assets/`, each just a `.gitkeep`) with nothing
wired into `arklight/cli/main.py` yet. That work is now done -- see
"v0.004a -- CLI scaffolding (DONE)" above.

Also documented, not implemented, in `docs/DESIGN-NOTES.md`: two CLI
helpers, `arklight --help` and `arklight --search <name>`, for looking
up a component's schema by name once the vocabulary is large enough
that recall becomes the bottleneck. Still not implemented as of this
restructure -- explicitly held for a separate go-ahead signal,
independent of v0.0035/v0.004a/v0.048.

**Update: both have since shipped, as `v0.042`** -- see the "v0.042 --
Extra CSS features: custom classes, `arklight search`, `arklight
--help`" entry above.

## v0.041 -- stateful JS vocabulary addendum II: list actions (DONE)

Not a new milestone/version -- second growth pass on
`ACTION_REGISTRY`, same mechanism as addendum I directly below. First
actions that assume a list-valued `State(...)` rather than a scalar
one:

- [x] `Action.append(name, value)` -- appends to a list-valued state
      key. `arklight/backend/js/actions/append.py`.
- [x] `Action.remove(name, index)` -- removes by index from a
      list-valued state key. `arklight/backend/js/actions/remove.py`.
- [x] `tests/test_stateful_js_vocabulary_addendum_2.py` -- 12 new
      tests (182 total, all passing).

No changes needed to `Bind`/`renderBindings` -- `el.textContent =
store.get(key)` already renders a list via JS's own
`Array.prototype.toString()`. Per-item templating (a real `<li>` per
item) is bigger scope and deliberately left for a future version, same
as derived/computed state, `Action.set_from_input`, and
debounced/throttled actions -- see `docs/DESIGN-NOTES.md`
("v0.0035: stateful-JS vocabulary addendum II").

## v0.041 -- stateful JS vocabulary addendum I: decrement/reset (DONE)

Not a new milestone/version -- same "addendum, not a full milestone"
treatment as the two v0.003 vocabulary addenda above, applied to
`ACTION_REGISTRY` for the first time. Added the two most commonly
needed state actions, purely as new registry entries + JS fragment
modules (no changes to normalize.py/validate.py/build.py/`JSBackend`'s
generation logic):

- [x] `Action.decrement(name, delta=1)` -- `-1` counterpart to
      `Action.increment`. `arklight/backend/js/actions/decrement.py`.
- [x] `Action.reset(name)` -- resets a state key back to its declared
      initial value, via a new `reset(key)` method on the reactive
      core's `createState` closure. `arklight/backend/js/actions/reset.py`.
- [x] `tests/test_stateful_js_vocabulary_addendum.py` -- 10 new tests
      (170 total, all passing).

Deliberately left for a future version at the time (see
`docs/DESIGN-NOTES.md`, "v0.0035: stateful-JS vocabulary addendum"):
list actions -- addressed in addendum II directly above --
derived/computed state, `Action.set_from_input` (binding state to
`input`/`change` events, not just `click`), and debounced/throttled
actions.

## Milestone checklist

See the "Snapshot" table at the top of this file for current status,
and [`docs/Foundational/ARCHITECTURE.md`](./docs/Foundational/ARCHITECTURE.md) for the canonical
milestone roadmap (kept in sync with this file as the single source of
truth, rather than a third copy of the same list).
