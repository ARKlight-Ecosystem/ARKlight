# Proposals

## Overview

Speculative, not-yet-accepted design proposals -- ideas put forward
for review that no maintainer has committed to yet. A file lands here
when someone has done the legwork of an audit or a design sketch, but
before any decision has been made to build it, stage it, or reject
it.

## Why this is separate from `docs/Foundational/`

`docs/Foundational/` is explicitly the **permanent design record** --
"not deletable," updated in place as the project evolves, describing
decisions that have already been made and are in force today (see
`Foundational/README.md`). Everything in there is *settled*: it
explains why ARKlight already works the way it does.

Proposals are the opposite state: **unsettled**. A proposal describes
something that does *not* exist yet, may never be built as written,
and could be rejected outright once a maintainer looks at it. Filing
these next to `ARCHITECTURE.md`/`DESIGN-NOTES.md` would blur that
line -- a reader landing in `Foundational/` should be able to trust
that everything there reflects the project as it actually is, without
having to first work out which files are aspirational. Keeping
proposals in their own folder means:

- **`Foundational/`'s "permanent, not deletable" guarantee stays
  true.** A rejected proposal can simply be deleted or archived
  without that guarantee having to bend for it.
- **A proposal's status is legible from its location, not just its
  header.** Any file under `Proposals/` is, by construction, not yet
  decided -- no need to re-litigate that in every file.
- **Acceptance has a visible move, not just a label change.** When a
  proposal is accepted and built, the natural step is to move its
  content (or a rewritten version of it) into `Foundational/` (if
  it's a permanent design decision) or into `Backends/`/wherever the
  in-progress staging doc for that work lives -- the same "graduate
  out once decided" pattern `docs/README.md` already uses for
  `docs/Far Future Concern/`.
  `Proposals/` is one level earlier than that: `Far Future Concern/`
  holds work that's already been picked up as a direction;
  this folder holds ideas that haven't been picked up as anything
  yet.

In short: **`Foundational/` = what ARKlight is. `Backends/` = work already
underway. `Proposals/` = ideas waiting for either of those to happen to
them, or for rejection.**

## What belongs here

- Audits that end in a recommendation ("here's what's missing, here's
  what it would take to add it").
- New-feature or new-registry-entry proposals not yet scheduled
  against a version-history milestone.
- Anything explicitly framed as "proposal" that isn't already a
  staging doc for approved, in-progress work (those belong in
  `docs/Backends/` alongside `ARKLIGHT_DESKTOP_BACKEND_PROPOSAL.md`,
  which itself started as this kind of document).

## What doesn't

- Decisions already made and in force -- those belong in
  `docs/Foundational/`.
- Work actively being built or staged -- those belong in
  `docs/Backends/` or wherever the relevant in-progress doc lives.
- Version-by-version shipped-feature summaries -- those belong in
  `docs/version history/`.

## Index

| File | Covers |
| --- | --- |
| [`JS-VOCABULARY-EXPANSION-PROPOSAL.md`](JS-VOCABULARY-EXPANSION-PROPOSAL.md) | Proposal to expand the client-side JS vocabulary: the already-designed-but-unshipped trivial gaps, small new runtime primitives, an exhaustive catalog of scalar math/string/list derivations and predicates (both JS's own built-ins and cross-language "batteries included" idioms from Python/Rust/C++ standard libraries), and the larger IR-node-sized gaps (client-side data fetch, reorderable lists, sort/filter, file-upload preview) plus the out-of-scope bucket that conflicts with ARKlight's no-`eval` non-goal. |
| [`URL-STATE-AS-PRIMITIVE-PROPOSAL.md`](URL-STATE-AS-PRIMITIVE-PROPOSAL.md) | Proposal for a `State(..., query=...)` primitive extending the existing `persist=True` mechanism to cover URL query parameters -- reading, coercing, fail-open defaults, write-back via `history.replaceState`, a `popstate` listener, and an opt-in push-history modifier -- and settles which of three navigation architectures a query-param change should trigger. |
| [`ARKLIGHT-ASSISTANT-CLI-PROPOSAL.md`](ARKLIGHT-ASSISTANT-CLI-PROPOSAL.md) | Proposal for an `arklight assistant` subcommand: a read-only, doc-grounded CLI companion ("Raeliana") woken with `--wake-up-raeliana`, an exploratory, tool-using companion ("Miko") woken with `--wake-up-miko`, plus a separate, opt-in, off-by-default `--activate-memory` flag for cross-session recall. **Partially accepted, per its appended sequencing amendment:** Miko's doc-only Stage A is staged as `v0.079`, an experimental CLI feature wrapping the already-shipped `v0.064` doc retrieval, permanence undecided until `v0.080` ships; Raeliana's implementation is not authorized -- `--wake-up-raeliana` currently only logs her proposal stage -- until Miko's dogfooding period trips the amendment's trigger condition. |
| [`PROJECT-KNOWELEDGE-PROPOSAL.md`](PROJECT-KNOWELEDGE-PROPOSAL.md) | Proposal for a compiler-owned `.arklight/` project-local knowledge directory: a providers/facts/observations model, Git as the first knowledge provider, and persistence of derived knowledge across builds. **Accepted -- staged as an eight-rung ladder (`v0.071`-`v0.078`) in [`docs/Implementation/PROJECT-KNOWLEDGE-ADDENDUM.md`](../Implementation/PROJECT-KNOWLEDGE-ADDENDUM.md).** |
| [`PROVIDER-SDK-PROPOSAL.md`](PROVIDER-SDK-PROPOSAL.md) | Proposal for `Provider`, an experimental, barebones interface for a site to declare it talks to an external service (Firebase, a hand-rolled API, ...) at runtime -- named to avoid colliding with the existing output-target meaning of "backend." ARKlight ships only the closed contract and validates/gates it; no vendor SDK, networking, or auth logic lives in core. **Accepted -- staged as a six-rung ladder (`v0.065`-`v0.070`) in [`docs/Implementation/PROVIDER-SDK-ADDENDUM.md`](../Implementation/PROVIDER-SDK-ADDENDUM.md), interleaved with JS vocabulary addendum stages 5-10.** |
| [`APP-SHELL-CAPABILITY-PROPOSAL.md`](APP-SHELL-CAPABILITY-PROPOSAL.md) | Proposal to scope how far the already-shipped `Site(app_shell=True)` (`hx-boost`/`hx-preserve`-based navigation) can be extended toward SPA-shaped UX without reimplementing a client-side router or reintroducing general expression evaluation -- a philosophy-fit checklist plus a candidate list split into plausibly-in-scope (prefetch, view-transitions, wider `shell_persistent` coverage, fine-grained DOM tracking for `app_shell` sites) and permanently-out-of-scope (a general route table, cross-page component state, arbitrary-expression navigation). |
| [`ANDROID-BACKEND-HARDENING-PROPOSAL.md`](ANDROID-BACKEND-HARDENING-PROPOSAL.md) | Proposal for native-shell quality work on the Android backend with no JS-to-native bridge: a source-level audit of `arklight/backend/android/runtime.py` and `arklight/cli/android.py` (external-link handling, offline/load-error handling, predictive back, WebView state restore, edge-to-edge, `WebChromeClient`, a WebView-version floor), which config kwargs earn a place, and what is explicitly rejected from the Capacitor comparison. **Partially accepted -- implemented as of `0.06507`:** external-link handling with `android.allow_navigation`, a load-error page, predictive back, WebView state save/restore, debugging tied to build type. `WebChromeClient`, the WebView-version floor, `append_user_agent` and background colour remain unscheduled. |
| [`ANDROID-IDENTITY-SYSTEM-BAR-SYNC.md`](ANDROID-IDENTITY-SYSTEM-BAR-SYNC.md) | Proposal for the Android scaffold to derive what a site already says instead of hard-coding it: the app name (from `arklight pwa`'s manifest or the home page `<title>`), a package id from that name (today every scaffold is `com.arklight.app`, so two ARKlight sites on one phone replace each other), and system-bar colours that follow the page (`android.status_bar_color`, icon lightness from the colour's luminance rather than the phone's day/night setting) -- all Bucket A, decided at scaffold time, no JS-to-native bridge. Later sections cover per-page bar colour at runtime (whether a read-only `evaluateJavascript` query crosses the bridge line is left to the maintainer) and how targeting SDK 35 changes bar colours. **Proposed. Not accepted, no version slot requested; the first slice's implementation patch was written but is not in this tree.** |
| [`RUNTIME-ERROR-HANDLING-PROPOSAL.md`](RUNTIME-ERROR-HANDLING-PROPOSAL.md) | Proposal to close the gap left by `CHANGELOG.md`'s `[0.041] -- JS runtime error-handling hardening` pass: five stateful primitives shipped since then (`Computed`, `Repeat`, `Show`, `bind_value`, watchers) with no equivalent audit, several with zero exception handling. Proposes per-element guards matching v0.041's own discipline, a default page-level `error`/`unhandledrejection` boundary, and a closed `ARKLIGHT_ON_ERROR` override hook a site author can supply. **Implemented as of `0.06505`** (guards, page-level boundary, override hook); the `Site(on_error=...)` spelling and a message registry are not implemented. |
| [`PLATFORM-API-IR-PROPOSAL.md`](PLATFORM-API-IR-PROPOSAL.md) | Proposal for a **platform API interface layer in the compiler IR**: platform-facing capabilities (notifications, clipboard, filesystem, device info, ...) represented as backend-independent, versioned interfaces the compiler owns, with Web as the default implementation and Android/Desktop earning individual interfaces only once their backend is mature enough to support them. Deliberately framed as an IR/interface layer rather than "a backend," borrows Capacitor's Web-first/native-extension shape without adopting its plugin-runtime model, and draws an explicit line against `Provider` (external-service abstraction) and against any generic native-code escape hatch. **Accepted, staged in `docs/Implementation/PLATFORM-API-IR-ADDENDUM.md` -- Stage 1 of 2 (Web reference implementation) shipped as of `v0.065`.** |
| [`USE-PREAMBLE-PROPOSAL.md`](USE-PREAMBLE-PROPOSAL.md) | Discussion document for a `# use` preamble directive: user-defined components (`<x.ARKlight>`), ACC components (`<x.ACC>`, with non-component ACC staying `# include`), and a `UI`/`UX` split of the stdlib. **Not accepted**; records the maintainer's stated thinking, what is already settled (`include`, `define`), and seven open questions. Until accepted, `# use <...>` is reserved and refused. |
| [`USER-DEFINED-ERROR-HANDLING-PROPOSAL.md`](USER-DEFINED-ERROR-HANDLING-PROPOSAL.md) | Proposal for opt-in, user-defined error handling: `# include <errhanlib.ARKlight>` binds `Try`, a base class a site author extends. `catches=` names real Python exception types, matched by inheritance -- Java's `catch` shape, not its semantics. `catch`/`finally_` are plain lists of closed-vocab `Action.*(...)`/`Log.*(...)` refs (`Log.compiler` for the build-time sink, `Log.js`/`Action.*` for the `0.06505` `arkReportError` runtime sink), read once at build time and never executed as code. Applied via an explicit `@SomeFailure.wraps` decorator, innermost below `@site.page`/`@component`. Log-only: a caught build-time error still fails the build, and it never touches Python's own `try`/`except`. Also borrows the `<x>lib.ARKlight` naming for future platform libs. Full replace of an earlier three-bracket-comment draft. **Not accepted; requested slot `v0.079` (already held by Miko Stage A).** |
| [`REI-LANGUAGE-PROPOSAL.md`](REI-LANGUAGE-PROPOSAL.md) | Proposal for the Rei *language* (`.rei`), a native source frontend for ARKlight -- distinct from Rei the compiler narrator (`REI-COMPILER-NARRATOR-PROPOSAL.md`, shipped `0.06510`). `.rei` -> Rei AST -> ARK AST, changing nothing below the ARK AST: `.rei` site files, a data-only `arklight.config.rei`, a spec that tracks ISO C99's shape and philosophy (not the C language), a Dart-like tree surface, plus a shared preamble, a fixed entry-point/`site`-method shape, Java-shaped exceptions and Platform APIs as an interface. **Accepted as written -- staged as a four-rung ladder (`v0.081`-`v0.084`) in [`docs/Implementation/REI-LANGUAGE-ADDENDUM.md`](../Implementation/REI-LANGUAGE-ADDENDUM.md); the Fun tier is retired in favor of an ordinary alpha maturity gate plus RNI, Rei's own gated escape hatch; the Compute stage is unscheduled, blocked on Open question 3.** |
| [`REI-DYNAMIC-CLASS-WASM-PROPOSAL.md`](REI-DYNAMIC-CLASS-WASM-PROPOSAL.md) | Proposal for a second, distinct Rei class kind -- **dynamic classes** -- compiled ahead-of-time to WebAssembly instead of lowered to ARK AST, for application business logic the closed tree-authoring surface was never meant to carry. Adds the Java-adjacent features the accepted language ladder left out (generics, monomorphized at compile time; real fields/constructors; overloading; interfaces with default methods; enums with fields), reuses the tree-authoring side's exceptions and Platform-APIs-as-interface syntax rather than duplicating it, and calls in via a new closed `DynamicClassRef`, never `eval`. Gated as its own alpha-only tier, distinct from RNI and from `AVM-WASM-SANDBOX-PROPOSAL.md` (curated *existing* JS libraries in sandboxes, not compiled *authored* Rei source). **Proposed. Not accepted, no version slot requested.** |
| [`AVM-WASM-SANDBOX-PROPOSAL.md`](AVM-WASM-SANDBOX-PROPOSAL.md) | Not accepted, filed for maintainer review: a curated-package WebAssembly sandbox ("AVM") that would let ARKlight consume existing JavaScript libraries, from a maintainer-curated catalog only, in isolated, discardable WASM sandboxes -- without ever exposing JavaScript or npm to the site author. Requests no version slot; its own ladder uses placeholder `A0`-`A6` labels pending acceptance. |
| [`KAIOS-NATIVE-TARGET-PROPOSAL.md`](KAIOS-NATIVE-TARGET-PROPOSAL.md) | Proposal for KaiOS as a target-specialized backend rather than a packager: KaiOS needs no host shell (Gecko *is* the app runtime, a packaged app is a ZIP with a `manifest.webapp`), but the existing Web build can't simply be zipped and shipped -- the input model (D-pad/softkeys, no pointer), the engine floor (KaiOS 2.5 = Gecko 48), and layout CSS assuming grid/flex `gap`/`min()`/`clamp()` all break it. **Proposed. Not accepted, not staged, not scheduled against a version.** If accepted, supersedes the packaging-only framing in `docs/Far Future Concern/KAIOS-BACKEND-IMPLEMENTATION.md`'s §§1-3/§7 without touching its manifest design, ZIP-reuse prerequisite, staged CLI ladder, or out-of-scope list. |
| [`ARKlight-ISSUE-REGISTER.md`](ARKlight-ISSUE-REGISTER.md) | The single most important distinction, repeated: most of these are not evidence that ARKlight's central idea is as per current alpha needs to be addressed. The genuinely dangerous ones are the places where the implementation violates its own existing contract — especially hydration, CSP integration, reproducibility, and dev-build lifecycle. The rest are mostly the price of the chosen architecture: closed vocabulary, compiler-first semantics, WebView native targets, constrained runtime, and deliberate escape-hatch boundaries.|

## Contributing

If you add a new proposal, add a row for it in the table above. When
a proposal is accepted, move its content to the appropriate permanent
or staging location and remove it from here (or leave a one-line
pointer if useful history).
