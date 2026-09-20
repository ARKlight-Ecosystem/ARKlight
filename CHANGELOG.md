# Changelog

All notable changes to ARKlight are tracked here. Format loosely
follows [Keep a Changelog](https://keepachangelog.com/); versions
follow the milestone scheme from ARCHITECTURE.md rather than strict
SemVer.

## [0.06511] -- Fix: Rei's assets sentence, a stage-table drift guard, and doc accuracy (follow-up to `0.06510`)

Numbered by the same `0.0650` + decimals rule as `[0.06501]`-`[0.06510]`
(the roadmap's `v0.065` is never touched). Found while auditing everything
added since `v0.064`.

- **Rei's assets narration was untrue on most builds.** The pipeline logs
  its "Copying assets..." stage on every build, with or without an `assets/`
  folder, but Rei said "Copying your assets/ folder into the output." Now:
  "Copying your assets/ folder into the output, if there is one."
  **Behavior change:** only under `--narrate` (or `rei.default_mode =
  "narrate"`), and only that one line; `--verbose` and plain output are
  unchanged.
- **Drift guard.** `narrate_stage` falls back to a raw `[Rei] <message>`
  passthrough for a message no pattern matches. New tests fail if any stage
  message a real build emits -- or the three conditional ones (raw
  postprocess, `.arklight` snapshot read, IR rebuild) -- lacks a pattern, so
  a future pipeline stage can't silently narrate as raw text.
- **Docs.** `CLI-REFERENCE.md` now says what `--narrate` failure output
  actually is: the plain error text without the `ARKlight build failed:`
  prefix or the `Re-run with --debug` hint (`--debug` can't be combined with
  `--narrate`). `CHANGELOG.md`, `PROGRESS.md` and `v0.065.md` called
  `docs/reference/eliza/eliza.py` "vendored"; it is an original from-scratch
  implementation, and the addendum's Status now records where it landed, as
  the addendum asked.

`tests/test_rei_narrator.py` (36 tests). Full suite 1815 passed; the 2
`tests/test_version.py` failures are unrelated and appear only on a checkout
that isn't `pip install`ed. `0.06510` -> `0.06511`; roadmap `v0.065`
untouched.

## [0.06510] -- Capability fix: Rei, the compiler narrator (`--narrate`) -- the `v0.065` slot's third piece

Numbered by the same `0.0650` + decimals rule as `[0.06501]`-`[0.06509]`
(the roadmap's `v0.065` is never touched). Ships the third of the four pieces
sharing the `v0.065` slot, accepted from
`docs/Proposals/REI-COMPILER-NARRATOR-PROPOSAL.md`, ahead of the
two still PLANNED (JS vocabulary stage 5, `Provider` stage 1).

- **`arklight build --narrate`.** Same pipeline progress `--verbose` prints,
  told as short `[Rei] ...` sentences instead of `[ARKlight] ...` lines.
  Mutually exclusive with `--verbose`/`--debug` (combining them fails the build
  up front, naming the flag); `--debug` still implies `--verbose`. Output is
  deterministic -- the same build narrates byte-identically. Inline
  experimental-API banners still print unconditionally and are never reworded.
- **`arklight/compiler/rei/` (new).** A closed table of `re.fullmatch` patterns,
  one per stage message the pipeline emits, over the same `on_stage=` callback
  `--verbose` already uses -- no new compiler hooks. Anything unrecognized falls
  back to `[Rei] <message>` rather than being dropped. Stdlib only.
- **`rei.default_mode` config key** (`"plain"`/`"verbose"`/`"narrate"`; `rei`
  added to `arklight.config._KNOWN_SECTIONS`). Sets what a build with no
  log-mode flag does; a flag always wins. Missing section/key means `"plain"`;
  any other value fails the build.
- **First-build introduction.** The first narrated build into a missing-or-empty
  output directory starts with a two-line greeting that also says why narration
  is on (flag vs `arklight.config.py`). Not repeated into the same directory;
  back after it is cleared.
- **`arklight search <Name>` pointer on schema violations.** `ValidationError`
  gained a keyword-only `component_name` (default `None`, so every existing
  `ValidationError(msg)` call is unchanged), set only at the SCHEMA-lookup
  sites -- unknown component type, missing required prop, and their two
  `Repeat(...)`-template twins. Under `--narrate`, a failure carrying it gets
  exactly one extra line, `Try: arklight search <Name>`. It is read off
  `CompileError.__cause__`, never scraped from the message; no other
  validation category gets a pointer.
- **ELIZA reference** at `docs/reference/eliza/eliza.py` -- an original,
  from-scratch implementation kept as read-only study material (its header
  says it is not a copy of anyone's code), not a vendored third-party file; nothing under `arklight/` imports it (a test walks every
  module's import statements to keep it that way).
- **Behavior change:** none for a build without `--narrate` and without
  `rei.default_mode` -- output and error text are unchanged.
- **Spec corrected while building it.** The addendum and the proposal's section 5
  said a `DuplicateComponentError`/`DuplicateStyleNameError` from the site file
  would be a raw Python traceback with zero Rei output. It isn't: the site file
  runs inside the "Discovering site..." stage and `load_site` wraps any
  exception it raises into `SiteLoadError` -> `CompileError`, so these are
  ordinary build errors in every log mode. Rather than defer the stage line or
  special-case the loader (either would also change `--verbose`), both documents
  were amended to describe that, and six tests pin it.
- **Docs.** `docs/Foundational/CLI-REFERENCE.md` documents `--narrate` and
  `rei.default_mode`; the addendum's Status is SHIPPED; outcome rolled into
  `docs/version history/v0.065.md`.

`tests/test_rei_narrator.py` (31 tests). Full suite 1810 passed; the 2
`tests/test_version.py` failures are unrelated and appear only on a checkout
that isn't `pip install`ed (no package metadata). `0.06509` -> `0.06510`;
roadmap `v0.065` untouched.

## [0.06509] -- Capability fix: JS vocabulary stage 4/10, the math derivations catalog (the `v0.064` remainder)

Numbered by the same `0.0650` + decimals rule as `[0.06501]`-`[0.06508]`
(the roadmap's `v0.065` is never touched). Finishes the half of the
`v0.064` milestone slot that the capability fixes paused: `v0.064` shipped
`arklight search --retrieve-doc` and left JS vocabulary addendum stage 4/10
(`docs/Implementation/JS-VOCABULARY-ADDENDUM-v0.070.md`) PLANNED.

- **21 new `Derive.*` kinds**, each one fragment file under
  `arklight/backend/js/derivations/` plus one `DERIVATION_REGISTRY` line, no
  new IR node: `absolute`, `ceiling`, `floor`, `truncate_number`, `sign`,
  `sqrt`, `cbrt`, `power`, `exp`, `log`, `log2`, `log10`, `hypot`, `clamp`,
  `average` (`Derive.mean` is an alias for the same kind), `median`, `gcd`,
  `lcm`, `percentage_of`, `to_fixed`, `to_precision`. `random_int` stays
  deferred to `v0.070`, as the addendum's scope filter says.
- Arity: unary transforms take one name; `power`/`percentage_of` take an
  ordered pair; `clamp` an ordered triple (value, low, high); `hypot`/
  `average`/`median`/`gcd`/`lcm` are variadic. `to_fixed`/`to_precision` take
  one name plus a literal `digits`, range-checked at build time
  (`arklight.ir.schema.DIGITS_RANGES`: `0`-`100` and `1`-`100`, exactly what
  JavaScript accepts) so a bad value is one build error, not a `RangeError`
  on every browser recompute. Both return a **string**, for display.
- **`arklight/ir/js_numeric.py` (new)** holds the build-time mirrors. Python's
  `math` *raises* where JavaScript returns a value (`sqrt(-1)`, `log(0)`,
  `exp(1000)`, `ceil(inf)`, `pow(0, -1)`), and disagrees on `pow(1, Infinity)`
  (`NaN` in JavaScript). Each mirror reproduces JavaScript's answer, so
  out-of-domain input gives `NaN`/`Infinity`, never a build or runtime error.
  `to_fixed` rounds an exact tie away from zero like JavaScript
  (`(2.5).toFixed(0) === "3"`; Python's own `format` says `"2"`).
- **Fixed while verifying parity** (behavior changes, all toward the existing
  "server-rendered text agrees with the client recompute" invariant):
  - `_coerce_number` now also maps `NaN` and `-0` to `+0`, as JavaScript's
    `Number(x) || 0` does. Before, a `Computed(...)` reading a `NaN`-valued
    `Computed(...)` got `NaN` at build time and `0` in the browser.
  - `Derive.sum` no longer uses Python's `sum()`, which has been a
    compensated sum since 3.12 and disagrees with JavaScript's `reduce` in the
    last digit (ten `0.1`s: `1.0` vs `0.9999999999999999`).
  - `Bind(...)` pre-fill spells non-finite results `NaN`/`Infinity`/
    `-Infinity` (what the client's `String()` writes), not Python's
    `nan`/`inf`.
- **Known limit, documented rather than hidden:** `exp`, `log*`, `cbrt`,
  `power` and `hypot` go through each platform's libm at build time and
  V8's port in the browser, so the pre-rendered value can differ from the
  recomputed one in the final binary digit (`hypot(2, 3)`: `3.605551275463989`
  vs `3.6055512754639896`). `cbrt` is settled to the nearest double so
  perfect cubes are exact. Format with `Derive.to_fixed` for display.

`tests/test_js_vocabulary_v0064.py` (137 tests), including a Node sweep of
~1,700 inputs that compares every kind's build-time value against the shipped
fragment (string kinds and correctly-rounded kinds bit-for-bit). Full suite
1781 passed. `0.06508` -> `0.06509`; roadmap `v0.065` untouched.

## [0.06508] -- Message/docs fix: the maintainer's speaker tag is now `[Rei]`, not `[Rae ARK]`

Numbered by the same `0.0650` + decimals rule as `[0.06501]`-`[0.06507]`
(the roadmap's `v0.065` is never touched).

- The heavy-reliance nudge `arklight.experimental.heavy_reliance_nudge`
  prints after a build's experimental-API summary now speaks as `[Rei]`
  instead of `[Rae ARK]`, matching the voice name
  `docs/Proposals/REI-COMPILER-NARRATOR-PROPOSAL.md` already uses
  (`[Rei] ...`). Wording is unchanged.
- Same substitution in the places that quote that text:
  `docs/Foundational/EXPERIMENTAL-APIS.md` (the nudge's example output) and
  the status block in the root `README.md`.
- **Behavior change:** anything that matches the literal `[Rae ARK]` in a
  build's output (a log filter, a script) needs `[Rei]`. Nothing else in the
  build output changes.
- Deliberately **not** changed: the `Rae-ARK` GitHub organisation/user name
  where it is part of a real URL or repository slug
  (`github.com/Rae-ARK/...`, `rae-ark.github.io`,
  `Rae-ARK/ARKlight-Component-Collections`), the `LICENSE` copyright line,
  the `cctv.py` prototype credit, and git history. Those name an account or a
  legal holder, not the speaker tag.

`tests/test_cli.py` and `tests/test_experimental_apis.py` assert on the new
tag (5 assertions). Full suite unchanged at 1644 passed.

## [0.06507] -- Capability fix: Android native-shell hardening (external links, back, rotation, load errors)

Numbered by the same `0.0650` + decimals rule as `[0.06501]`-`[0.06506]`
(the roadmap's `v0.065` is never touched). A **capability fix** taken from
`docs/Proposals/ANDROID-BACKEND-HARDENING-PROPOSAL.md`, which is now
**partially accepted**: the items that are correctness fixes with no
JS-to-native bridge, plus the one config key they need. What is left is
listed under "Not done".

The generated `MainActivity.kt` attached a custom `WebViewClient`, which
switches off Android's own link handling: **every tapped link, including
one to another site, loaded inside the app's WebView** with no way back to
the browser. Also fixed in the same file, from the proposal's audit:

- **External links** (proposal 2.1). A main-frame navigation to the app's
  own origin stays in the WebView; any other `http(s)` link, and
  `mailto:`/`tel:`/`sms:`, is handed to the device via `Intent.ACTION_VIEW`
  (an `ActivityNotFoundException` is caught, so a device with no handler
  can't crash the activity). Other schemes and subframe navigations keep
  the WebView's previous behavior.
- **`android.allow_navigation`** (new `arklight.config.py` key, default
  `[]`). External `https` hosts a link may load *inside* the WebView -- an
  OAuth or payment domain. Bare hostnames, `*.` prefix for subdomains
  (not the bare domain); a scheme, port, path, single-label name or bare
  `*.com` is a build-time `AndroidError`, not a warning. Setting it also
  adds the `INTERNET` permission to the manifest, which the scaffold
  otherwise still does not request (an in-WebView external page can't
  load without it).
- **Back** (2.3). `onBackPressed()` (deprecated) is replaced by an
  `OnBackPressedCallback`, enabled only while the WebView has history, and
  `android:enableOnBackInvokedCallback="true"` opts into Android 13+
  predictive back.
- **Rotation** (2.4). `saveState`/`restoreState` keep the WebView's history
  and scroll position across activity recreation. In-page JavaScript state
  is *not* preserved by this (only `State(persist=True)` survives a
  reload); the proposal's wording on this point was too generous.
- **Load errors** (2.2). A failed main-frame load shows a fixed built-in
  page instead of Chromium's error page; nothing from the URL is put in it.
- **Remote debugging** (proposal section 3). `setWebContentsDebuggingEnabled`
  follows `FLAG_DEBUGGABLE`, so debug builds can be inspected and release
  builds cannot. Not a config key.
- The generated project `README.md` documents all of the above.

**Behavior change:** a scaffolded app that previously opened an external
link inside itself now opens it in the browser. Sites that relied on the old
behavior for a specific host list it in `android.allow_navigation` and
re-scaffold. Nothing changes for a project that isn't re-scaffolded, and
non-Android builds are untouched.

**Not done** (still in the proposal, unscheduled): the `append_user_agent`
and WebView background-colour keys, the `WebChromeClient` work
(console messages, file chooser), the WebView-version floor, the
error-page-content key, and the edge-to-edge note (2.5, documentation only).

`tests/test_android_hardening.py` (56 tests): generated-Kotlin content for
each behavior above, manifest permission/attribute, `allow_navigation`
accept/reject matrix and error messages, the runtime builder refusing an
unvalidated host, and a structural check of every `MainActivity.kt` variant.
Full suite 1588 -> 1644 passed (the two `test_version.py` metadata tests need
the package installed; the rest of the suite is unchanged).

**Verification limits.** The generated Kotlin was compiled with Kotlin
1.9.24 (the version the scaffold pins) against hand-written stubs of the
Android/AndroidX classes it uses, and its link-routing/host-matching
methods were run against a URL matrix; it was **not** built with the real
Android SDK or run on a device or emulator. The scaffold's own CI workflow
(`assembleDebug` + emulator smoke test) is the first place that happens.

## [0.06506] -- Capability fix: compiler-native diagnostics for user-defined component calls

Numbered by the same `0.0650` + decimals rule as `[0.06501]`-`[0.06505]`
(the roadmap's `v0.065` is never touched). A **capability fix** for
issue-register #5 and the general point in #32: `@component` promised a
clear message instead of a raw Python `TypeError`, and two boundaries
still leaked one. Full design record:
`docs/Proposals/COMPONENT-CALL-DIAGNOSTICS-PROPOSAL.md`.

- A positional call (`Stat("a", "b")`) raises `ComponentError` naming the
  component, the keyword-only rule, its declared props, a by-name example
  and the call's `file:line`, instead of `Stat() takes 0 positional
  arguments but 2 were given`.
- A `props=` contract that disagrees with the render function's signature
  (a declared prop it has no parameter for, or a required parameter
  `props=` doesn't declare) raises `ComponentError` naming both sides.
  Checked with `inspect.Signature.bind` when the component is *used*
  (expansion, and `mode="registry"` backend-override dispatch), so it
  never runs the function and cannot reject a call that would have
  worked. A component that is defined but never used is unaffected.
- **Behavior change:** both cases are now `ComponentError` (a
  `RuntimeError`), not `TypeError`. Valid components and calls, and every
  build that succeeded before, are unchanged.
- Not changed: positional children on user-defined components (still
  unsupported; the message says so), built-in components, and errors
  raised inside a render function's own body.

`tests/test_component_call_diagnostics.py` (19 tests); full suite 1588
passed.

## [0.06505] -- Capability fix: JS runtime error-handling coverage (`ARKLIGHT_ON_ERROR`)

Numbered by the same `0.0650` + decimals rule as `[0.06501]`-`[0.06503]`
(the roadmap's `v0.065` is never touched). It skips `0.06504`, which is
still the unconfirmed draft slot above. A **capability fix**: `[0.041]`
guarded the runtime as it then stood, but the five stateful primitives
that shipped afterward (`Computed`, `Repeat`, `Show`, `bind_value`,
watchers) got no equivalent audit, so one bad element threw an uncaught
exception and silently skipped every render pass after it. Full design
record: `docs/Proposals/RUNTIME-ERROR-HANDLING-PROPOSAL.md`.

- Per-element guards (proposal 3a) in `recomputeAll` (per `Computed`),
  `renderBindings`, `renderClassBindings`, `renderModelBindings`,
  `renderRepeat` (per container), `renderShow`, and `wireModelBinding`'s
  write-back including the debounce/throttle paths. One failure reports;
  the rest of the pass continues.
- `wireErrorBoundary()` (3b): page-level `error`/`unhandledrejection`
  floor, registered once at `DOMContentLoaded`, ignoring `ResizeObserver
  loop` notices.
- `arkReportError(message, err)` (3c): the single funnel -- console
  line, then `window.ARKLIGHT_ON_ERROR(message, err)` if defined, then
  `arkNotify(message)` unless the hook returned exactly `false`. The
  existing `[0.041]` guards (`initState`, click dispatch, watchers) now
  go through it too. `arkNotify` is unchanged.
- **Behavior change:** guarded failures now log `[ARKlight] ...` to the
  console, and the page-level boundary shows a notice for uncaught
  errors that previously showed nothing.
- Shipped only where `arkNotify` already ships; a page with no
  `State(...)` and no click interceptor is byte-for-byte unchanged.
- Not implemented: `Site(on_error=...)` and a message registry (see the
  proposal's implementation notes).

`tests/test_runtime_error_handling.py` (31 tests, Node-driven for the
fragments); four assertions in `test_js_error_handling.py`/`test_htmx_3.py`
now expect `arkReportError(` where they expected `arkNotify(`. Full
suite 1538 -> 1569 passed. `0.06503` -> `0.06505`.

## [0.06504] -- Bug fix: `trusted_script_origins` CSP directive injection

**DRAFT ENTRY -- version slot not confirmed by a maintainer.** Filed to
close a gap found during a docs-consistency pass: this fix landed in
`arklight/api.py`/`tests/test_csp.py` and its own design record
(`docs/Proposals/CSP-TRUSTED-ORIGIN-INJECTION-BUGFIX.md`) already says
"Implemented, alpha," but -- unlike every other out-of-band fix in this
range (`0.0431`, `0.0641`, `0.0650`-`0.06503`) -- it never got a
`pyproject.toml` version bump, a `CHANGELOG.md` entry, or a
`PROGRESS.md` snapshot row. Numbered `0.06504` here on the same
`0.0650` + decimals precedent as its neighbors; a maintainer should
confirm the slot before this ships. Out-of-band, numbered inside the
`v0.064` -> `v0.065` gap, same "capability fixes take priority"
treatment as `0.0431`/`0.0641`-`0.06503`.

`_render_csp_meta_tag` (`arklight/backend/html/csp.py`) spliced every
`Site(trusted_script_origins=...)` entry verbatim into the `script-src`
directive. `Site.__init__`'s only check was "non-empty string" --
nothing validated *what* the string contained, so
`trusted_script_origins=["'unsafe-inline'"]` silently defeated the
strict-CSP guarantee the module's own docstring promises. Fixed by
rejecting `'unsafe-inline'`/`'unsafe-eval'` (quoted or not, case-
insensitive) and any origin containing a directive-breaking character
(`;`, whitespace) at `Site.__init__` time, so the failure is a build-time
`ValueError`, not a silent hole. Full design record:
`docs/Proposals/CSP-TRUSTED-ORIGIN-INJECTION-BUGFIX.md`.

## [0.06503] -- Capability fix: live-input -> action-value (`Bind(...)` as an `Action.set`/`Action.append` argument)

Numbered by the same rule as `[0.06501]`/`[0.06502]` (`0.0650` plus
decimals; the roadmap's `v0.065` is never touched). A **capability fix**:
`bind_value=Bind.model(...)` could put an input's text into state and
`Action.append(...)` could add to a list, but nothing could pass the one to
the other, so `[type a task] [Add]` wasn't expressible (issue register #7).
Full design record: `docs/Proposals/ACTION-VALUE-FROM-STATE-PROPOSAL.md`.

```python
Input(bind_value=Bind.model("draft"))
Button("Add", on_click=Action.append("tasks", Bind("draft")))
Watch("tasks", then=Action.reset("draft"))
```

- `Action.set`/`Action.append` accept `Bind("name")` as `value`: the value
  `name` holds when the action runs (after any `.debounce(...)`). Stored as
  the JSON marker `{"__state__": "name"}` (`arklight/ast/nodes.py`) -- a
  plain dict so it survives the `.arklight` round trip.
- New `ActionSpec.state_args` opts arguments in; only `set`/`append`'s
  `value` do. `increment`/`decrement`/`remove` reject `Bind(...)` at build
  time (input text is a string: `0 + "5"` is `"05"`).
- Validation (`_validate_action_args`): named state must be a `State`/
  `Computed` on the page; the marker must be well-formed; `__state__` is a
  reserved key in literal dict arguments. Runs for `on_click=`, `Watch`
  `then=`, and `Repeat` templates (`page_state` is now threaded through
  those validators).
- JS: `arklight/backend/js/runtime/action_args.py`'s `resolveActionArgs`,
  inlined into `wireClickInterceptor` and `wireWatchers`. Returns a fresh
  object (a `Watch`'s args live for the whole page). Action fragments are
  unchanged. No eval.
- Component-owned state: markers are renamed with the action's target.
- `arklight search` shows which action arguments accept `Bind(...)`.

**Fixed along the way:** `Action.append("tasks", Bind("draft"))` used to
pass Validation and crash the HTML backend with a raw `TypeError: Object of
type ARKNode is not JSON serializable`.

**Known limits:** debouncing the `Bind.model(...)` a submit button reads
from means a click inside the delay reads the previous value; only
top-level argument values are read; no Enter-to-submit.

**Tests:** `tests/test_action_value_from_state.py` (31), including two
Node-driven tests of the real dispatch fragments (both fail with
resolution disabled). Full suite: 1538 passed.

`0.06502` -> `0.06503` (`pyproject.toml`).

## [0.06502] -- Capability fix: `# define` is a real define; the preamble reaches every Python file; the stdlib is the whole API

Second follow-up to `[0.0650]`, numbered by the same rule as
`[0.06501]` (`0.0650` plus decimals; the roadmap's `v0.065` is never
touched). Still a **capability fix**. Three things, none of them new
surface.

**1. `# define` is C's `#define`.** In `[0.06501]` it was an alias
between *included objects* (`# define Btn -> Button` looked `Button` up
among the includes; `# define Button -> acc.x.Button` picked one
include's copy). That was a second, quieter way to bind names, which is
what `# include` is for. It is now what the word means: `# define
<name> -> <text>` replaces the name with the text at compile time. Both
sides are strings; the right one is the rest of the line, verbatim, so
it can be a number, a string literal, another name, any text that is
valid Python where it lands. It binds nothing and needs no include --
the exception among the directives, on purpose.

- The left side is one Python identifier (not a keyword), matched as a
  whole *token* of code: `Btn` never touches `Btn2`; nothing inside a
  string literal (f-strings included, the same on every supported
  Python) or a comment is replaced.
- One pass, no rescanning. A define whose text mentions another
  define's name is refused instead, so the missing rescan can't turn
  into a surprise.
- Per file. A define may not take the name of included vocabulary
  (that would silently override the API), two defines for one name must
  agree, an empty right side is refused (it used to be silently taken
  for a comment), and the file must still parse afterwards -- if not,
  the error names the defines in effect. No line ever moves.
- `load_site` now runs `discover` and `exec` on the define-applied
  source; that is the source that actually runs.

Behavior change, stated plainly: the collision-picking form
(`# define Button -> acc.some_collection.Button`) is gone, and the
collision message no longer suggests it. Two includes binding one name
to different objects still fail loudly; the way out is to drop one
include or have one side export another name. No directive resolves a
collision today (see the `use` proposal, Q5).

**2. Every Python file ARKlight takes in gets its preamble.** Reproduced
first: in the production scaffold, `pages/home.py` with `# include
<stdlib.ARKlight>` failed with `NameError: name 'Page' is not defined`,
because only the site file's preamble was ever read (which is why the
scaffold's sibling files kept `from arklight import *`). Now an import
hook, installed for the duration of `load_site` and scoped to the site
file's own directory, reads the preamble of each project module the site
imports; `arklight.config.py` goes through the same `run_source` step.
The standard library and pip-installed packages (ACC ones included) are
untouched and never see the hook. Consequences:

- Each file needs its own `# include`, and defines are per file.
- The shadowing check and the `from arklight import *` notice cover
  project modules too.
- The site's directory is on `sys.path` (and the hook installed) while
  the site's own preamble resolves, so an `# include <acc.x>` for a
  module that lives in the project now resolves, and that module gets
  its own preamble. Everything is removed again afterward, including
  after a failed load.
- The production scaffold's `components/nav.py` and `pages/*.py` moved
  to `# include <stdlib.ARKlight>`.
- The hook bypasses the bytecode cache for project modules on purpose:
  what runs is the define-applied source.

**3. `# include <stdlib.ARKlight>` is the whole public API.** It binds
`arklight.__all__`, which lacked four names: `CSSSyntaxError` and
`DuplicateStyleNameError` (defined in `arklight/api.py`), and
`ComponentError` and `DuplicateComponentError` (what the exported
`component(...)` raises). Added. A file that happens to define one of
those names itself now gets the ordinary loud shadowing error. A test
now fails if `arklight.api` gains a public name that `__all__` lacks.

**Also.** The preamble parser is now a small registry (one recogniser
plus one handler per directive) so more directives can be added without
touching the rest; `# use <...>` is *reserved* and refused with a
pointer to `docs/Proposals/USE-PREAMBLE-PROPOSAL.md` (a discussion
document, **not accepted**) rather than silently ignored.

**Tests:** 11 alias-semantics tests in `tests/test_preamble.py` removed
(they encoded the old behavior); `tests/test_preamble_define.py` (41)
and `tests/test_preamble_scope.py` (18) added. Disabling the import
hook makes the project-module tests fail with the `NameError` above.
Full suite: 1502 passed.

`0.06501` -> `0.06502` (`pyproject.toml`).

## [0.06501] -- Capability fix follow-up: retire `from arklight import *`, see names a file defines itself, split `# define` into normalize/validate

Bug-fix follow-up to `[0.0650]`, numbered by the same rule as the
fixes before it: the roadmap's in-progress version (`v0.065`) extended
by extra decimals, never touched itself -- `0.0650` plus two decimals.
Treated as a **capability fix**, not a new feature: `[0.0650]` moved
"get names into this file" onto compiler-owned ground, but three
things it should have covered were still invisible to the compiler.

**1. `from arklight import *` is retired.** It still works, but every
build now logs a notice naming the file and line and telling the site
to put `# include <stdlib.ARKlight>` above its code instead. The
notice starts with the warning glyph the CLI already treats as
"always print", so it shows without `--verbose`. Only the site file is
checked: it is the only file whose preamble ARKlight reads.

**2. Names the compiler couldn't see.** The preamble binds names
*before* `exec`, so anything the file then did to them was Python's
silent default. Two cases, both now fail loudly:

- *The file rebinding an included name* -- `def Button(...)`,
  `Button = ...`, `from x import Button`, a leftover `from x import
  *`, a loop variable. After the file runs, the finished namespace is
  compared, by identity, against what the preamble bound; a rebound
  name is a `PreambleCollisionError` (surfaced as `SiteLoadError`)
  naming the include it came from and the line that rebound it.
  Re-importing the same object, or deleting a name, is not a
  collision.
- *A user `@component` named like a built-in.* Reproduced first:
  `expand_ark_ast` looks a node up in `COMPONENT_REGISTRY` before the
  built-in schema, so `@component() def Button` silently replaced every
  `Button(...)` in the site, ARKlight's own included. (`arklight
  search` already applied "built-ins always win" to the same
  situation, so the compiler and its own search disagreed.)
  `register_component` now raises `DuplicateComponentError` for a
  built-in name unless `allow_redefine=True` -- the same explicit
  opt-in the previous registration-collision fix introduced. A
  component registered with that opt-in is also exempt from the
  namespace check above; `@component` marks the callable it returns
  (`ALLOW_REDEFINE_MARKER`) so the loader can tell.

**3. `# define` split across normalization and validation.** A define
is a rename -- the left name now means the right one -- which is
canonicalization, so `normalize_preamble` applies it, and never raises;
anything it can't apply is recorded. `validate_preamble` is the one
place that raises. `resolve_preamble` keeps its signature and messages
and is now `parse_preamble` -> `normalize_preamble` ->
`validate_preamble`. Validation also gained the one define check that
was missing: two `# define`s giving one alias two different targets is
a collision, not a silent last-one-wins. The preamble's own boundary
is unchanged and now stated and pinned by test: only recognised
comments above the file's contents; the same comment between
statements or at the end of the file is an ordinary comment.

**Implementation:** `arklight/parser/preamble.py` -- `Directive`,
`NormalizedPreamble`, `ResolvedPreamble`, `parse_preamble`,
`normalize_preamble`, `validate_preamble`, `resolve_preamble_detailed`,
`check_namespace_shadowing`, `find_retired_star_imports`,
`retired_star_import_notice`. `arklight/parser/loader.py` --
`load_site(..., on_notice=None)` (silent by default, like every other
stage callback), and the post-`exec` shadowing check.
`arklight/compiler/pipeline.py` -- passes its stage logger as
`on_notice`. `arklight/ir/components.py` / `arklight/api.py` -- the
built-in-name guard and `ALLOW_REDEFINE_MARKER`. `arklight new`'s
`simple` and `production` scaffolds, `examples/hello_site/site.py`,
`GETTING-STARTED.md`'s example, and `arklight/__init__.py`'s quickstart
now open with `# include <stdlib.ARKlight>` (production's
`pages/`/`components/` modules are not site files and keep their
imports). `AUTHORING-GUIDE.md`'s "Preamble directives" section
rewritten to match.

**Tests:** `tests/test_preamble.py` 18 -> 43 (preamble boundary,
normalize/validate split, duplicate defines, each way of shadowing,
the `allow_redefine` exemption, the notice through `load_site`, the
pipeline log and the CLI's no-`--verbose` printing);
`tests/test_user_defined_components_stage0.py` +4 (built-in name
guard, opt-in, marker). Three existing tests changed because they
depended on the old behavior: the two that registered a component
named `Container`/`Heading` to exercise search's "built-ins win" path
now pass `allow_redefine=True`, and the pipeline's exact-stage-list
tests use a preamble-syntax site so the new notice isn't in the list.
Full suite: 1454 passed.

`0.0650` -> `0.06501` (`pyproject.toml`).

## [0.0650] -- Capability fix: preamble directives (`# include`/`# define`)

Out-of-band alpha maintenance release (numbered inside the v0.064 ->
v0.065 gap, same slot-sharing precedent as `[0.0641]`-`[0.0649]`).
Treated as a **capability fix**: a site file's `from arklight import
*` (and the identical pattern against any other vocabulary source)
relies entirely on Python's own star-import semantics to get names
into the module namespace, and Python's rule for two colliding names
is unconditional "last one wins" -- silent, with no diagnostic and no
record of which source lost. This is the exact "silently resolved by
picking a winner" antipattern the compiler's own registries already
refuse elsewhere -- `register_component`/`register_backend_render`
(`DuplicateComponentError`) and ACC capability identities
(`CapabilityError`), both hardened by the `[Unreleased] --
Registration collisions now fail loudly instead of overwriting
silently` entry above -- but neither of those guards touches the
first step, getting names bound at all, which still ran on raw Python
import semantics with zero ARKlight involvement until now.

**What:** `# include <label>` and `# define <alias> -> <target>`,
written as reserved-shape comments before a site file's first
executable statement. ARKlight's own loader parses and resolves these
itself -- not Python's import machinery -- and binds the result into
the module namespace before the rest of the file executes.
`# include <stdlib.ARKlight>` binds ARKlight's own public vocabulary
(`arklight.__all__`), identical to what `from arklight import *`
already provides. `# include <acc.<dotted.module.path>>` imports a
real module and binds its own `__all__` -- the same contract
`arklight.__all__` itself follows; a module with no `__all__` raises
rather than guessing which of its names are vocabulary. If two
includes bind the same name to two different objects, that's a
collision: `PreambleCollisionError`, naming every source involved,
raised at load time. `# define <alias> -> <target>` resolves a
collision explicitly (or just adds a local alias) -- a bare target
must be unambiguous across everything included so far, and a dotted
target (`<include-label>.<name>`) picks one specific include's copy.
`from arklight import *` keeps working exactly as before; this is
purely additive, and only ever acts on comments matching the two
directive shapes.

**Implementation:** `arklight/parser/preamble.py` (new module) --
`resolve_preamble`, `PreambleError`, `PreambleCollisionError`,
`_leading_comment_lines` (a `tokenize`-based preamble scanner),
include-label resolution for `stdlib.ARKlight`/`acc.*`, and
`# define` target resolution (bare and dotted). `arklight/parser/
loader.py` -- `load_site` now calls `resolve_preamble(source, ...)`
and binds the result into the module's namespace before `exec`,
wrapping `PreambleError` as `SiteLoadError` like every other load-time
failure. `docs/Foundational/AUTHORING-GUIDE.md` -- new "Preamble
directives" section, placed first, ahead of "Internal links".

**Tests:** `tests/test_preamble.py` (new, 18 tests) -- stdlib/`acc.`
include resolution, missing-module and missing-`__all__` diagnostics,
agreeing vs. disagreeing collisions, `# define` disambiguation (bare
and dotted, including its own unknown-label/unknown-name failure
modes), and integration through `load_site` (binding without a raw
star-import, wrapping a collision as `SiteLoadError`, and confirming
`from arklight import *` still works unchanged). Full suite: 1425
passed, no regressions.

`0.0641` -> `0.0650` version bump (`pyproject.toml`) -- the docs-only
patches numbered in between (`[0.0642]`-`[0.0649]`) didn't bump it, per
their own "no code changed" entries.

## [0.0646] -- Docs-only: fixed a self-contradiction in `V1-DEFINITION.md`

Docs-only, no compiler code changed.

**Fixed:** `docs/Foundational/V1-DEFINITION.md` Section 5's "zero
special-cased compiler support" bullet, which `[0.0645]` left
contradicting that same section's own newly-amended opening paragraph
(the capability-discovery hook landing as real, compiler-side code).
Narrowed the bullet to Collection *content* specifically, naming the
hook as the one already-acknowledged exception.

**Added:** an explicit removal-side rule to `docs/README.md`'s
"Adding a new doc" section -- deleting a file that leaves the
Proposals/Implementation/Backends/Far Future Concern lifecycle must
remove its index row(s), in the same pass, in both that folder's own
index and `docs/README.md`'s Folder Guide table. Previously only the
add/update direction was stated.

**Fixed:** `PROGRESS.md`'s own `[0.0645]` Snapshot-table row, which
had picked up a literal `\n` merging it with the row below --
the same defect `[0.0644]` had already found and fixed one row
earlier, for `[0.0643]`.

## [0.0645] -- Docs-only: documented the ACC capability-discovery hook

Docs-only, no compiler code changed. Backfills documentation for
`arklight/capabilities.py`, which landed undocumented (outside its own
module docstring and `tests/test_capabilities.py`) at `a4aa6b8`.

**Added:** `docs/Foundational/ACC-CAPABILITIES.md` -- the settled
design record for the ACC (ARKlight Component Collections)
capability-discovery hook: the `arklight.capabilities` entry-point
contract, `Capability`/`CapabilityError`/`discover_capabilities`/
`require_capability`, `arklight/compiler/sbom.py` as its one current
caller, and status against ACC's own `docs/design/
IMPLEMENTATION-LADDER.md` (Stage 1 landed here; Stages 2-5 tracked in
the separate `Rae-ARK/ARKlight-Component-Collections` repository).

**Changed:** `docs/Foundational/V1-DEFINITION.md` Section 5 -- removed
the now-stale "no design doc yet, not-yet-proposed concept" framing
for ARKlight Component Collections now that ACC is a real repository
with its own foundational design doc and a landed implementation
stage; the section's underlying exclusion-from-`v1.0` argument is
unchanged. `README.md`'s repository-layout listing -- added the
previously-missing `capabilities.py` line. `docs/Foundational/
README.md` and `docs/README.md` -- new index rows for
`ACC-CAPABILITIES.md`.

## [Unreleased] -- Platform API IR, stage 1 of 2: Web reference implementation (`v0.065`)

Accepted from `docs/Proposals/PLATFORM-API-IR-PROPOSAL.md` (filed as
merely a candidate in `[0.0642]` below, now accepted and staged in the
new `docs/Implementation/PLATFORM-API-IR-ADDENDUM.md`), interleaved
into `v0.065`'s already-crowded slot as a fourth piece -- same "make
room for one more" precedent Rei's own addition to that slot already
set. Not yet its own numbered release: pyproject stays at `0.0641`
until the whole `v0.065` slot (this piece plus the other three) has
landed, same convention `[0.0642]`/`[0.0643]` (both docs-only) already
followed.

**What:** `PlatformAPI.notify(title, body=None)` and
`PlatformAPI.clipboard_write(text)` (`arklight/api.py`) on `on_click=`,
alongside named behaviors and `Action.*(...)`. Each builds a
`PlatformAPIRef` (`arklight/ast/nodes.py`), validated against a new
compiler-owned interface registry (`arklight/ir/platform_api.py`:
`PlatformAPISpec`, `PLATFORM_API_REGISTRY`,
`BACKEND_PLATFORM_API_SUPPORT`, `PlatformAPIError`,
`check_backend_support`) that describes each capability's
arguments/permissions and which backends currently implement it (`web`:
both starter capabilities; `android`/`desktop`: neither yet) --
independent of any backend's actual implementation, per the proposal's
"the compiler defines the interface, each backend supplies its own
implementation" split.

**Implementation:** `arklight/ir/validate.py`
(`_validate_platform_api`, wired into both `on_click` validation
sites) -- unknown-capability and unexpected-keyword-argument
diagnostics at build time. `arklight/backend/html/attrs.py` -- a
`PlatformAPIRef` on `on_click=` compiles to
`data-ark-on-click="platform:<capability>"` +
`data-ark-platform-api-args`, reusing `ActionRef`'s attribute-slot
convention. `arklight/backend/js/platform_apis/` (new package,
`notify.py` + `clipboard_write.py`) -- the Web backend's own
implementation, one module per capability mirroring the `actions`/
`behaviors` fragment pattern exactly, only shipped when a site's IR
actually references it; `clipboard_write` is deliberately not a
duplicate of the pre-existing `copy` named behavior (`v0.063`) --
see `docs/Foundational/PLATFORM-APIS.md`'s "Relationship to the
`copy` behavior" section for that boundary. `arklight/backend/js/
runtime/dispatch.py` -- a new `"platform:"` branch in
`wireClickInterceptor`, its own try/catch guard mirroring the
`"action:"`/`"behavior:"` branches. `arklight/backend/js/render.py` --
`_collect_usage` tracks `used_platform_apis`; `_platform_apis_object_js`
builds the "only ship what's used" `platformApis` dispatch object;
`needs_click_interceptor` now also triggers on platform API usage;
`check_backend_support(used_platform_apis, backend_name="web")` now
actually runs during `_build_runtime_js` (previously defined but
called from nowhere), failing the build with a named-capability
diagnostic instead of silently accepting a request an unsupported
backend can't fulfill.

**Docs:** new `docs/Foundational/PLATFORM-APIS.md` -- the settled
design record (terminology, architecture model, Web-default/
native-earns-later, and the `copy`-vs-`clipboard_write` boundary).
New `docs/Implementation/PLATFORM-API-IR-ADDENDUM.md` -- the two-stage
tracked ladder (Stage 1 shipped here; Stage 2, Android/Desktop native
implementations, PLANNED and unscheduled). `docs/Proposals/
PLATFORM-API-IR-PROPOSAL.md`'s status header and its
`docs/Proposals/README.md` index row updated from "Proposed" to
"Accepted, staged." `docs/Foundational/WHAT-ARKLIGHT-IS.md`'s "filed
this revision, not yet accepted" note updated to match. `docs/version
history/v0.065.md` and its `README.md` index row updated to describe
this piece as shipped (the slot's other three pieces stay PLANNED).
`PROGRESS.md`'s Snapshot table and narrative section updated.

**Tests:** `tests/test_platform_api.py` (new, 18 tests) -- API
factory return values; validation errors (unknown capability,
unexpected keyword argument); HTML attribute compilation; JS "only
ship what's used" discipline for neither/one/both capabilities;
click-interceptor dispatch wiring; the no-`eval`/`new Function`
invariant; `check_backend_support` firing both standalone and from
inside `JSBackend.render()`. Two pre-existing tests
(`tests/test_htmx_3.py::test_guard_shape_is_one_try_catch_per_dispatch_branch`,
`tests/test_js_error_handling.py::test_wire_click_interceptor_guards_action_dispatch_independently`/
`test_wire_click_interceptor_guards_behavior_dispatch_independently`)
that hard-coded "two dispatch branches" were updated to expect three
(and one split boundary fixed so a trailing branch's own try/catch
isn't double-counted), the same way those tests were themselves
updated when `htmx-5` went from one shared guard to two per-branch
guards. Full suite: 1313 passed (2 pre-existing, unrelated
`test_version.py` failures from a bare non-`pip install`ed checkout,
present before this stage too), no regressions.

## [0.0644] -- Docs-only incremental patch: "The Goal" + `V1-DEFINITION.md`

Out-of-band, numbered inside the same `v0.064` -> `v0.065` gap as
`[0.0431]`/`[0.0641]`/`[0.0642]`/`[0.0643]` below, but docs-only: no
compiler code changed.

**Added:** a new, unnumbered "The Goal" section to
`docs/Foundational/WHAT-ARKLIGHT-IS.md` (placed before Section 1,
deliberately left unnumbered so Sections 2-7's existing numbers, and
`docs/Proposals/PLATFORM-API-IR-PROPOSAL.md`'s two existing references
to "Section 4," stay valid) -- states the project's DX goal
(comparable to React/Vue/Svelte's authoring ergonomics) alongside the
constraint it won't trade away to get there
(`SYSTEM-DESIGN-AGREEMENTS.md`'s "Compiler First, Runtime Last"), and
names the two audiences ARKlight is built for: the Python Community
and the Education Community.

**Added:** `docs/Foundational/V1-DEFINITION.md` -- what
`v1.0`/"Stable compiler" (a bare, unexplained `PLANNED` row in
`ARCHITECTURE.md`'s Milestones table until now) concretely means:
deterministic output, fails-loudly-at-build-time with no known
exceptions in scope, no breaking closed-vocabulary changes without a
deprecation path. Scoped explicitly to the Web Developing parts of the
compiler only (parsing/AST, Normalization/Validation, the Website IR,
HTML/CSS/JS backends -- everything `arklight build` exercises), with
named exclusions: the Android/Desktop packaging backends, CLI
conveniences beyond `build`, `arklight/experimental.py`-gated
features, and `Provider`/Rei/Project Knowledge/`arklight assistant`.
Names **ARKlight Component Collections** for the first time in this
doc tree -- a not-yet-proposed concept for curated bundles of
`@component`-registered content built on `USER-DEFINED-COMPONENTS.md`'s
existing macro-expansion path -- and states why it's excluded from the
`v1.0` promise rather than leaving that inferred. Also documents
"capability fix" (first recognized at `v0.0641`) as the mechanism and
evidence trail behind the `v1.0` reliability claim: each one landed is
a checkable step toward the point where the supply of open capability
fixes for the in-scope surface runs dry.

**Changed:** `docs/Foundational/README.md`'s and `docs/README.md`'s
index rows for `WHAT-ARKLIGHT-IS.md` updated to mention "The Goal";
both gain a new row for `V1-DEFINITION.md`. `ARCHITECTURE.md`'s `v1.0`
Milestones-table row now links to `V1-DEFINITION.md` instead of
standing as an unexplained label. `docs/Foundational/WHAT-ARKLIGHT-IS.md`'s
"Current as of" marker bumped from `v0.0642` to `v0.0644` (it had
drifted after `[0.0643]` shipped without a corresponding bump; fixed
here).

**Fixed** (housekeeping noticed while these files were already open,
per `docs/README.md`'s own "do it in one pass" rule): `docs/README.md`'s
Foundational Folder Guide table was missing rows for both
`WHAT-ARKLIGHT-IS.md` and `PLATFORM-APIS.md`, despite both already
having rows in `docs/Foundational/README.md`'s own index -- added.
`PROGRESS.md`'s `[0.0643]` Snapshot-table row had a literal `\n`
instead of a real line break, merging it with the row below it on one
line -- fixed. A stray, leftover `<<<<<<< HEAD` merge-conflict marker
in `PROGRESS.md`, sitting just above the `v0.0643` narrative section
with no matching conflict in progress -- removed.

## [0.0643] -- Docs-only incremental patch: package docstring refresh

Out-of-band, numbered inside the same `v0.064` -> `v0.065` gap as
`[0.0431]`/`[0.0641]`/`[0.0642]` below, but docs-only: no compiler code
changed.

**Changed:** `arklight/__init__.py`'s module docstring no longer
describes ARKlight as "a Python-first compiler for building static
websites" -- that framing predates `[0.0642]`'s rewrite of
`docs/Foundational/WHAT-ARKLIGHT-IS.md` and had drifted out of sync
with it. The docstring now opens with the same **compiler framework**
wording (static site plus optional wrapped native/PWA targets, its own
batteries-included workflow) and its quickstart example now shows
`State`/`Action.increment` instead of a stateless `Button`, so the
first thing `from arklight import *` shows a reader is that
interactivity exists and goes through the closed-vocabulary primitives
(`State`, `Action.*`, `Derive.*`, `Predicate.*`, `Watch`), not just
static markup.

## [0.0642] -- Docs-only incremental patch: definition rewrite + Platform API IR proposal

Out-of-band, numbered inside the same `v0.064` -> `v0.065` gap as
`[0.0431]`/`[0.0641]` below, but docs-only: no compiler code changed.

**Changed:** `docs/Foundational/WHAT-ARKLIGHT-IS.md`'s one-sentence
definition no longer leans on "static-site compiler" as ARKlight's
load-bearing noun. ARKlight is now stated as a **compiler framework**,
with an explicit, three-bullet statement that it is not a static-site
generator, not a frontend framework, and not a UI framework -- each of
those describes one slice of the project (output shape, authoring
ergonomics, component vocabulary respectively) and none describes the
compiler itself. Added to `docs/Foundational/README.md`'s index.

**Added:** `docs/Proposals/PLATFORM-API-IR-PROPOSAL.md` -- a platform
API interface layer for the compiler IR (notifications, clipboard,
filesystem, device info, ...) represented as backend-independent,
versioned interfaces; Web is the default implementation; native
backends (Android, Linux Desktop) earn individual interfaces only once
mature. Filed as **Proposed**, not accepted, no version-history slot
reserved. Added to `docs/Proposals/README.md`'s index.

## [0.0641] -- Emergency patch: URL query-parameter state

Out-of-band alpha maintenance release (numbered inside the v0.064 ->
v0.065 gap, ahead of v0.065). Accepted from
`docs/Proposals/URL-STATE-AS-PRIMITIVE-PROPOSAL.md`: ARKlight shipped
no authored primitive for reading, writing, or reacting to URL query
parameters at all, confirmed by that proposal's own exhaustive grep of
`arklight/` for `location.search`/`URLSearchParams`. Treated as a
**capability fix** and given the same "stop and fix it now" priority
`[0.0431]` gave its own bug fix, below -- this project's second
recognized category of emergency patch, alongside contract-violation
bug fixes: a missing capability, not a broken promise, but one whose
absence has no ceiling on how much it costs everything built against
this compiler until it's closed.

**What:** `State(name, initial, query=..., history=...)`
(`arklight/api.py`) extends the existing `persist=True`/`media=`
two-way-sync precedent rather than inventing a fourth mechanism.
`query="page"` names the query-string key to sync this state key
with: overridden from `URLSearchParams(location.search)` (with type
coercion -- `int`/`bool`/`str`, inferred from `initial`'s own Python
type, bool checked before int) on init, kept live across
browser back/forward navigation, and written back via
`history.replaceState`/`pushState` on every change.
`history="push"` (opt-in; `"replace"` is the unmarked default)
gives that key's writes a real, back-button-worthy history entry
instead of silently replacing the current one -- its own small
registry (`arklight.ir.schema.KNOWN_QUERY_HISTORY_MODES`), not folded
into `MODIFIER_REGISTRY`, since it's a per-`State`-declaration
property with no event of its own to attach to. Deliberately never a
real navigation or document re-fetch: every reactive primitive in this
vocabulary is synchronous and in-memory, and the compiler-rendered
document is invariant to the query string in the first place (static
file resolution strips it before ARKlight's output is even in the
picture).

**Implementation:** `arklight/api.py` (`State(..., query=,
history=)`). `arklight/ir/schema.py` (`KNOWN_QUERY_HISTORY_MODES`).
`arklight/ir/validate.py` (`_LEGAL_QUERY_KEY_RE`; `history=` requires
`query=`). `arklight/ir/build.py` (`IRPage.query`,
`_query_type_tag`, `_extract_page_state`).
`arklight/backend/html/page_render.py` (`data-ark-query`, riding
alongside the existing five hydration attributes on the same marker/
`<body>` placement `persist`/`media` already use).
`arklight/backend/js/runtime/state.py` (`initState()`'s URL-override/
write-back halves, folded unconditionally into `STATE_CORE_JS` the
same way `persist`/`media` already are). `arklight/backend/js/runtime/
query.py` (new file) -- `wireQuerySync`, the `popstate` listener: the
one genuinely new runtime surface this adds, since nothing shipped by
ARKlight listened for `popstate` before (no SPA router); gated by
`has_query` in `arklight/backend/js/render.py`'s `_collect_usage`, the
same "only ship what's used" discipline `has_reveal` already applies
to `wireReveal`.

**Tests:** `tests/test_url_query_state.py` (new, 44 tests) -- API/
Validation/IR/HTML/JS-gating coverage mirroring `[v0.063]`'s `media=`
suite, plus a Node.js integration suite exercising the actual shipped
`createState`/`initState`/`wireQuerySync` fragments against mocked
`document`/`location`/`history`/`window`: URL-override-on-init,
fallback to `initial` on a missing or malformed query value, `push`-
vs-`replace` write-back, and a `popstate` round-trip both with the
param present and falling back to the server-rendered default when
it's absent. Full suite: 1297 passed, no regressions.

`0.063` -> `0.0641` version bump (`pyproject.toml`) -- also covering
`v0.064`'s own `--retrieve-doc` piece, which landed without a version
bump of its own; see [`PROGRESS.md`](./PROGRESS.md) ("v0.0641 --
Emergency patch") for the full narrative, including that
pre-existing inconsistency.

## [Unreleased] -- Registration collisions now fail loudly instead of overwriting silently

**What:** Three registries that previously followed an unconditional
"last call wins" rule now raise on a name collision by default:
`register_component(name, ...)` (`arklight/ir/components.py`) and the
`@component(...)` decorator that wraps it, `register_backend_render
(component_name, backend_name, ...)` and the `.register_backend
(backend_name)` decorator it powers, and `Site.style(name, rules)`
(`arklight/api.py`). Each gains an `allow_redefine: bool = False`
keyword; passing `True` restores the exact old overwrite behavior for
the one case it legitimately served (redefining a name on purpose,
e.g. re-importing a components module during iterative development).
Left as `False` (the default), re-registering an already-used name now
raises instead of quietly replacing the earlier entry.

**Why:** All three previously stored the newer registration over the
older one with no signal at all -- an accidentally duplicated
component name, a backend override registered twice by mistake, or
two unrelated `site.style(...)` calls colliding on the same class
name all looked completely fine at the call site and only surfaced,
if ever, as wrong output much later with nothing pointing back at
either registration. Silent overwriting is now the opt-in case
(`allow_redefine=True`), not the default.

**Implementation:** `arklight/ir/components.py` -- new
`DuplicateComponentError(ComponentError)`, raised by
`register_component`/`register_backend_render` on a same-name/
same-`(component, backend)` re-registration without
`allow_redefine=True`. `arklight/api.py` -- new
`DuplicateStyleNameError(ValueError)`, raised by `Site.style(...)` on
the same condition; `component(...)`'s `allow_redefine` kwarg threads
through to `register_component`, and the decorated component's
`.register_backend(backend_name, allow_redefine=...)` threads through
to `register_backend_render`.

**Tests:** `tests/test_user_defined_components_stage0.py`,
`tests/test_user_defined_components_stage3.py`, and
`tests/test_api_style.py` -- each of the three previous
"re-registering overwrites" tests now asserts the new
`DuplicateComponentError`/`DuplicateStyleNameError` instead, confirms
the *first* registration survives a rejected second call unchanged,
and a companion test confirms `allow_redefine=True` still reproduces
the old overwrite behavior exactly. New decorator-level coverage for
`@component(..., allow_redefine=...)` and
`.register_backend(..., allow_redefine=...)`.

## [Unreleased] -- JS vocabulary addendum, stage 3 of 10: small new runtime primitives (`v0.063`)

**What:** Five small runtime primitives, third rung of the JS
vocabulary expansion ladder staged in
`docs/Implementation/JS-VOCABULARY-ADDENDUM-v0.070.md`.
`Action.geolocate(name)` (`arklight/api.py`) -- a one-shot,
argument-less action: `navigator.geolocation.getCurrentPosition`
writes `{lat, lng}` into `State(name)` once the browser's permission
prompt resolves; asynchronous, unlike every other action, but safe
under the existing "fire and forget" dispatcher. Clipboard **paste**
(`on_click="paste"`) -- mirrors `copy.py`, reading
`navigator.clipboard.readText()` into the `behavior_target`
selector's `.value`/`.textContent` instead of writing to it; also
dispatches an `input` event so a co-located
`bind_value=Bind.model(...)` picks the pasted text up too.
`State(name, initial, media="(min-width: 768px)")`
(`arklight/api.py`) -- `matchMedia`-driven boolean state: the
runtime overrides `initial` with `matchMedia(media).matches` on init
and keeps writing the key via a `MediaQueryList` "change" listener
after that. `reveal`/`lazy` behavior via `IntersectionObserver`
(`on_reveal="reveal"`) -- deliberately its own prop/registry rather
than folded into `on_click=`, since it's never click-triggered;
adds `toggle_class` (default `"is-visible"`) to the element the first
time it enters the viewport, then stops observing it. Debounced/
throttled two-way binding -- `Bind.model(name, debounce=300)`/
`Bind.model(name, throttle=300)` extend `bind_value=` to accept the
existing `debounce:<ms>`/`throttle:<ms>` modifier tokens.

**Also fixed:** `Repeat`, `RepeatItem`, `Show`, `Predicate`,
`PredicateRef`, `ItemIndexRef`, `ClassBindSpec`, `ModelBindSpec` were
defined in `arklight/api.py`/`arklight/ast/nodes.py` but missing from
`arklight/api.py`'s own `__all__` and from `arklight/__init__.py`'s
import/`__all__` list -- unreachable via `from arklight import *`
(the documented way to import everything) even though `from
arklight.api import Repeat` etc. worked. Same gap
`tests/test_package_exports.py` already caught once before, for the
v0.003 second vocabulary addendum; fixed the same way, plus a
regression test this time.

**Implementation:** `arklight/backend/js/actions/geolocate.py`,
`arklight/ir/schema.py` (`ACTION_REGISTRY["geolocate"]`) --
`Action.geolocate`. `arklight/backend/js/behaviors/paste.py` (new),
`arklight/backend/js/behaviors/__init__.py`, `arklight/ir/schema.py`
(`BEHAVIOR_REGISTRY["paste"]`) -- clipboard paste.
`arklight/ir/build.py` (`IRPage.media`, `_extract_page_state`),
`arklight/ir/validate.py` (media shape check),
`arklight/backend/html/page_render.py` (`data-ark-media`),
`arklight/backend/js/runtime/state.py` (`initState()`'s `matchMedia`
override/listener wiring) -- `media=`. `arklight/ir/schema.py`
(`REVEAL_REGISTRY`/`KNOWN_REVEAL_BEHAVIORS`, separate from
`BEHAVIOR_REGISTRY`), `arklight/ir/validate.py`
(`_validate_reveal_props`), `arklight/backend/html/attrs.py`
(`data-ark-on-reveal`), `arklight/backend/js/runtime/reveal.py`
(new, `wireReveal()`), `arklight/backend/js/render.py` (`has_reveal`
usage detection, shipped/called independent of `has_state`) --
`on_reveal=`. `arklight/ast/nodes.py` (`ModelBindSpec`),
`arklight/api.py` (`Bind.model(..., debounce=..., throttle=...)`),
`arklight/backend/html/attrs.py` (`data-ark-model-modifiers`) --
debounced/throttled binding. Every new `window.*` access is guarded
with `typeof window !== "undefined"` so `arklight.js` stays testable
from a Node.js harness with no real `window` global (caught by
`tests/test_vdom_8.py`'s existing localStorage-persistence Node
tests, which broke without the guard once `initState()`'s JS grew a
`matchMedia` branch). No changes to `arklight/ir/normalize.py`.

**Tests:** `tests/test_js_vocabulary_v0063.py` (new, 36 tests) --
API return values and registry coverage for all five primitives;
validation (undeclared state for `geolocate`, missing
`behavior_target` for `paste`, non-string/empty `media`, unknown
`on_reveal` kinds, and that `on_reveal` does *not* require
`behavior_target`); HTML backend attribute compilation for each;
JS backend "ships only what's used" checks, including that
`wireReveal()` ships/runs independent of `has_state`; a combined
test exercising all five primitives on one page; `from arklight
import *`/`from arklight.api import *` wildcard-export regression
tests; and a Node.js check of the shipped `wireReveal` fragment.
Full suite: 1204 passed (2 pre-existing, unrelated
`test_version.py` failures from a bare non-`pip install`ed checkout,
present before this stage too), no regressions.

## [Unreleased] -- JS vocabulary addendum, stage 2 of 10: string casing + comparison predicates (`v0.062`)

**What:** `Derive.uppercase`, `Derive.trim` (`arklight/api.py`) -- the
missing string-casing siblings of `Derive.join`/`Derive.format`,
second rung of the JS vocabulary expansion ladder staged in
`docs/Implementation/JS-VOCABULARY-ADDENDUM-v0.070.md`. Both are
single-value transforms (same fixed arity as `Derive.count`): each
reads exactly one state/computed value, coerces it to a string
(matching JavaScript's own `String(x)` coercion rather than throwing
on a non-string value), and applies `.toUpperCase()`/`.trim()`.
`Predicate.equals`, `Predicate.gt`, `Predicate.lt` (`arklight/api.py`)
-- `Show(...)` comparison predicates, already speced alongside
`Derive.compare`'s `eq/ne/gt/lt/gte/lte` op set but never wired into
`PREDICATE_REGISTRY` (previously only `truthy`/`falsy`). Each is its
own fixed-arity kind (two names) rather than one `compare`-style kind
plus an `op` extra arg, since `PredicateSpec` has no `extra_args`
slot.

**Implementation:** `arklight/backend/js/derivations/uppercase.py`,
`trim.py` (new) -- each exports `NAME` + `JS_FRAGMENT`, mirroring
`count.py`'s single-name shape.
`arklight/backend/js/derivations/__init__.py` -- registers both new
modules into `DERIVATION_MODULES`/`DERIVATION_FRAGMENTS`.
`arklight/ir/schema.py` -- two new `DERIVATION_REGISTRY` entries
(`uppercase`/`trim`: `min_names=1, max_names=1`) and three new
`PREDICATE_REGISTRY` entries (`equals`/`gt`/`lt`: `names=2`).
`arklight/ir/build.py` -- `_evaluate_derivation` gains `"uppercase"`/
`"trim"` branches (Python `str.upper()`/`str.strip()`), kind-for-kind
mirrors of the new JS fragments. `arklight/backend/html/
page_render.py` -- `_evaluate_predicate` gains `"equals"`/`"gt"`/
`"lt"` branches. `arklight/backend/js/runtime/show.py` --
`arkEvalPredicate` gains matching comparison cases, so a page's
initial server-rendered `hidden` state and every client-side
re-evaluation agree. `arklight/ir/validate.py` -- updated error
message listing the new predicate kinds (no change to validation
*logic*; the existing registry-driven arity checks already cover the
new entries). No changes to `arklight/ir/normalize.py`.

**Tests:** `tests/test_js_vocabulary_v0062.py` (new) -- API return
values; `PREDICATE_REGISTRY` coverage; validation (comparison
predicates reject anything but exactly two names); IR-build
initial-value evaluation for `uppercase`/`trim` (including non-string
coercion); HTML backend `Bind(...)` pre-fill and `Show(...)` `hidden`
attribute against `gt`/`equals` predicates; JS backend ships only the
derivation kind(s) actually used and includes all three new
`arkEvalPredicate` cases whenever `Show(...)` is used;
`DERIVATION_FRAGMENTS` registry coverage; and Node.js end-to-end
checks that the shipped `uppercase` fragment and the shipped
`arkEvalPredicate` `gt` case agree with their Python build-time
counterparts. Full suite: 1170 passed, no regressions.

## [Unreleased] -- JS vocabulary addendum, stage 1 of 10: math siblings (`v0.061`)

**What:** `Derive.subtract`, `Derive.divide`, `Derive.min`,
`Derive.max` (`arklight/api.py`) -- the missing math siblings of
`Derive.sum`/`Derive.multiply`, first rung of the JS vocabulary
expansion ladder staged in
`docs/Implementation/JS-VOCABULARY-ADDENDUM-v0.070.md`. Each follows
the exact registry-fragment pattern that doc promises: no new IR
node, no parser, no `eval`/`new Function`. `subtract`/`divide` take
`names[0]` as the starting value and apply every later name against
it in declared order (`Derive.subtract("total", "discount")` ==
`total - discount`); both need at least two names since neither is
associative the way `sum`/`multiply` are. `min`/`max` are associative
like `sum`, so one name is already meaningful. `divide` mirrors
JavaScript's own `x / 0` semantics (`Infinity`/`-Infinity`/`NaN`) in
its Python build-time counterpart too, instead of letting Python's
`/` raise `ZeroDivisionError` -- keeps a page's server-rendered
`Bind(...)` text and the client recompute in agreement even at this
edge case.

**Implementation:** `arklight/backend/js/derivations/subtract.py`,
`divide.py`, `min.py`, `max.py` (new) -- each exports `NAME` +
`JS_FRAGMENT`, mirroring `sum.py`'s shape.
`arklight/backend/js/derivations/__init__.py` -- registers the four
new modules into `DERIVATION_MODULES`/`DERIVATION_FRAGMENTS`.
`arklight/ir/schema.py` -- four new `DERIVATION_REGISTRY` entries
(`subtract`/`divide`: `min_names=2, max_names=None`; `min`/`max`:
`min_names=1, max_names=None`). `arklight/ir/build.py` --
`_evaluate_derivation` gains `"subtract"`/`"divide"`/`"min"`/`"max"`
branches, kind-for-kind mirrors of the new JS fragments (imports
`math` for the `divide`-by-zero `Infinity`/`NaN` handling).
`arklight/api.py` -- `Derive.subtract`/`.divide`/`.min`/`.max` static
methods, same shape as the existing `Derive.*` methods. No changes to
`arklight/ir/validate.py` (the existing `DerivationSpec`-driven arity
check already covers the new `min_names`/`max_names` values),
`arklight/ir/normalize.py`, or any backend's generation logic.

**Tests:** `tests/test_js_vocabulary_v0061.py` (19 tests, new) -- API
return values; validation (`subtract`/`divide` reject fewer than two
names, `min` accepts one); IR-build initial-value evaluation for all
four kinds, including chained/multi-name `subtract` and the
divide-by-zero `Infinity` case; HTML backend `Bind(...)` pre-fill; JS
backend ships only the derivation kind(s) actually used;
`DERIVATION_FRAGMENTS` registry coverage; and a Node.js end-to-end
check that the shipped `subtract` fragment's recompute agrees with
the Python build-time initial value. Full suite: 1144 passed, no
regressions (1127 before this stage + 19 new; `test_version.py`'s 2
pre-existing, unrelated failures unchanged).

## [Unreleased] -- User-defined components, Stage 4 (component-owned state, final stage)

**What:** `component(..., state={...})` (`arklight/api.py`) lets a
component declare its own local, instance-scoped reactive state --
`ComponentState(initial=..., persist=False)` per name (or a bare
initial value, normalized the same way `State(name, initial)`'s own
two-positional-arg ergonomics already work). A component's render
function references a declared name exactly like a page-level
`State(...)`: `Bind(...)`, `on_click=Action.*(...)`,
`bind_class=Bind.when(...)`, `bind_value=Bind.model(...)` all work
unchanged. Every call site gets its own independent copy -- two
`Counter()` calls on the same page never share one `"count"` value --
solving the "props flowing into a closed-registry reactive system,
re-render scoping" difficulty `docs/Foundational/
user-defined-components.md` Section 4 named as the reason this was
deferred out of `v0.060` proper, by never giving the registry itself
any state: a component's own state is real, page-level `State(...)`
by the time Normalization ever runs, hoisted onto its owning page
under a uniquely-namespaced key per instance. This is the fourth and
final stage of the `v0.060` "User-defined, reusable components"
milestone -- see `docs/Foundational/
USER-DEFINED-COMPONENTS-IMPLEMENTATION.md`'s Stage 4 row and its own
"Stage 4 implementation notes"/"Explicitly out of scope for Stage 4"
sections for the full design (notably: not yet supported inside a
`mode="registry"` backend override's own subtree, and untested against
`Repeat(...)`'s per-item template).

**Implementation:** `arklight/ir/components.py` -- `ComponentState`
(`initial`/`persist`), `ComponentSpec.state`, `_namespaced_state_name`,
`_hoist_component_state`, `_rewrite_component_state_refs`;
`_render_once` gains `instance_id`/`hoisted` keyword-only parameters,
consulted only when `spec.state` is non-empty. `expand_node`/
`expand_child`/`expand_ark_ast` gain new `hoisted: list[ARKNode] |
None`/`counter: itertools.count | None` parameters, both defaulting to
`None` and threaded straight through recursion; `expand_ark_ast`
creates a fresh `hoisted` list and `itertools.count()` per page, and
splices `hoisted`'s accumulated `State(...)` nodes onto that page's own
direct children once the whole page finishes expanding (the one place
`arklight.ir.build._extract_page_state` looks for them). A component
that never declares `state=` -- every component before this stage, and
most after it -- allocates no instance id, touches neither new
parameter, and produces byte-identical output to Stage 0-3, including
for every pre-existing bare `expand_node(...)` test call across the
Stage 0-3 test files that passes neither. `arklight/api.py` --
`component(...)` gains a `state=` keyword, `_validate_component_state`
(mirrors `_validate_component_default_style`'s validate-at-registration-
time contract). `arklight/__init__.py` -- re-exports `ComponentState`
alongside `component`/`Prop`. `arklight/ir/component_dispatch.py` --
comment only, clarifying why its own bare `expand_node(rendered)` call
now raises `ComponentError` for a state-owning component used inside a
backend override (no page-level `hoisted` accumulator exists at that
point in the pipeline). No changes to `arklight/ir/validate.py`,
`arklight/ir/build.py`, `arklight/ir/normalize.py`, or any backend --
a component's hoisted state is indistinguishable from a hand-written
page-level `State(...)` by the time any of them run.

**Tests:** `tests/test_user_defined_components_stage4.py` (18 tests,
new) -- registration/validation (`state=` accepts a bare value or an
explicit `ComponentState`, rejects an empty dict or an empty name;
`register_component` stores `state` directly), expansion (hoists one
`State(...)` per declared name; rewrites `Bind`/`on_click`/`bind_class`/
`bind_value` to the hoisted name; two instances of the same component
get independent, non-colliding namespaced state; `persist` flows
through; a prop value passed in from the page's own `State(...)` is
left untouched; nested state-owning components both get hoisted; a
bare `expand_node()` call with no hoisting context raises
`ComponentError`; a non-stateful component is unaffected by a bare
`expand_node()` call, matching Stage 0-3 behavior), and two end-to-end
compiles through the full `compile_site_file`/`HTMLBackend` pipeline
confirming a counter component's state actually reaches `IRPage.state`
and renders a `data-ark-bind` attribute, and that two sibling instances
produce two independent `IRPage.state` entries. Full suite: 1127
passed, no regressions (1109 before this stage + 18 new).

## [Unreleased] -- User-defined components, Stage 3 (per-backend render dispatch)

**What:** `mode="registry"` components (Option B) get their actual
differentiator: `.register_backend(backend_name)` on the value
`component(...)` returns lets a component ship a *different* render
function per backend, falling back to the shared `render_fn` wherever
a backend hasn't registered its own -- the "registry-based late
binding" `docs/Foundational/user-defined-components.md` describes, and
the open design question `docs/Foundational/
USER-DEFINED-COMPONENTS-IMPLEMENTATION.md`'s "hybrid decision" section
left unresolved ("identity preserved through to a per-backend render
dispatch ... or ... a different mechanism -- open design question, not
pre-decided here"). Resolved via a tagged prop that survives
Normalization/Validation unnoticed (neither module rejects an
unrecognized prop key) and is lifted onto a new `IRNode.component_origin`
field during IR conversion; resolution itself happens once per backend,
after the shared `WebsiteIR` already exists, wired into `HTMLBackend.
render()`. A `mode="registry"` component with no backend override
registered -- every component before this stage, and most after it --
produces byte-identical output to Stage 0-2. See the implementation
doc's Stage 3 notes for the full design and its "Explicitly out of
scope" list (Android/Desktop dispatch -- neither is a `WebsiteIR`-
consuming backend yet -- and `Repeat(...)`-nested coverage, notably).

**Implementation:** `arklight/ir/components.py` --
`ComponentSpec.backend_render_fns`, `ComponentOrigin`,
`COMPONENT_ORIGIN_PROP_KEY`, `register_backend_render(...)`,
`_tag_component_origin`, `apply_default_style_class` (public wrapper
around the existing `_apply_default_class`), `_render_once` tags a
registry-mode rendered root only when `backend_render_fns` is
non-empty. `arklight/ir/build.py` -- `IRNode.component_origin`,
`_ark_node_to_ir_node` pops `COMPONENT_ORIGIN_PROP_KEY` into it (same
treatment `responsive_style` already gets there), new public
single-node wrapper `ark_node_to_ir_node`. `arklight/ir/
component_dispatch.py` (new module) -- `resolve_backend_dispatch(ir,
backend_name)`, a pure function that walks every page's IR tree,
swaps a matched override's own (expanded, default-styled, normalized)
subtree in place of the default rendering, and always clears the
marker either way. `arklight/backend/html/render.py` -- `HTMLBackend.
render()` calls `resolve_backend_dispatch` as its first line;
`CSSBackend`/`JSBackend` untouched (neither walks a node tree for
markup). `arklight/api.py` -- `component(...)`'s decorated value gains
`.register_backend(backend_name)`, delegating to `register_backend_render`.
No changes to `arklight/ir/validate.py`, `arklight/ir/normalize.py`
(reuses its existing `normalize_node`), or `arklight/ir/schema.py`.

**Tests:** `tests/test_user_defined_components_stage3.py` (21 tests,
new) -- registration (`register_backend_render`/`.register_backend`,
rejecting an unknown component and a `mode="macro"` one, last-call-wins),
expansion tagging (only a registry component *with* an override is
tagged; a macro component never is), `resolve_backend_dispatch` (swaps
in a match, falls back cleanly when no override exists for that
backend, clears the marker either way, is a pure function, raises on
an override returning a sibling list or a non-`ARKNode`, applies
`default_style`'s class to an override's own root, supports an
override nesting further components), and end-to-end compiles through
`HTMLBackend`/`CSSBackend`/the full `build()` pipeline confirming the
override actually renders, the internal marker never leaks into
output, and `CSSBackend` is unaffected by backend-specific overrides.
Full suite: 1107 passed, no regressions (1086 before this stage + 21
new); 2 pre-existing, unrelated failures in `tests/test_version.py`
(package metadata lookup fails in a bare source checkout that was
never `pip install`ed -- reproduces identically on `origin/alpha`
before this change).

## [Unreleased] -- User-defined components, Stage 2 (default styling hook)

**What:** `component(..., default_style={...})` (`arklight/api.py`) lets
a registered component ship default CSS under its own name -- a
`{css-property: value}` dict, the same shape and syntax `Site.style(...)`
already accepts (pseudo-class shorthand like `":hover:color"`
included), validated at registration time with the exact same rules.
When a build actually calls the component, its rules are folded into
the generated stylesheet under a `.{ComponentName}` class, and that
class is folded onto the rendered subtree's own root `class_name`
automatically -- so a component can ship with sane default styling
without forcing every caller to pass `class_name=` by hand, closing
the gap `docs/Foundational/user-defined-components.md`'s "styling
hook" requirement called out. See
`docs/Foundational/USER-DEFINED-COMPONENTS-IMPLEMENTATION.md`'s Stage
2 implementation notes for the full design.

**Implementation:** `arklight/ir/components.py` --
`ComponentSpec.default_style`, `register_component(...,
default_style=...)`, `_apply_default_class` (merges the class onto a
rendered `ARKNode` root, a no-op for any other return shape),
`used=`/`collect_default_styles` (usage-keyed, not registry-keyed --
only components a build actually expands contribute CSS, so an
unrelated site's registrations in the same process never leak in).
`arklight/api.py` -- `component(..., default_style=...)`, plus a new
free function `_check_css_syntax` extracted from
`Site._validate_css_syntax` (now a thin wrapper around it) so
`_validate_component_default_style` can reuse the exact same syntax
rules without a `Site` instance to call a method on.
`arklight/compiler/pipeline.py` -- `expand_ark_ast(..., used=...)`
collects the components a build actually uses; `compile_site_file`
merges `{**component_default_styles, **site.custom_styles}` into
`custom_styles=` before building the Website IR, so an explicit
`site.style(name, ...)` registration always wins over a same-named
component default. No changes to `arklight/ir/schema.py`,
`tag_map.py`, `arklight/backend/css/custom_styles.py`, or any
backend's rendering code -- Stage 2 reuses `render_custom_styles(...)`
completely unchanged.

**Tests:** `tests/test_user_defined_components_stage2.py` (20 tests,
new) -- `default_style` validation (empty dict, non-string value,
unsupported pseudo-class, injection characters, pseudo-class
shorthand accepted), `_apply_default_class` behavior (adds the class,
appends to an existing `class_name`, doesn't duplicate an
already-present one, no-ops on a non-`ARKNode` render result),
`collect_default_styles` (usage-keyed, skips components without
`default_style`, returns independent copies), `expand_ark_ast(...,
used=...)` recording transitively-used components, and three
end-to-end compiles asserting the class/CSS actually land in rendered
HTML/stylesheet output, an unused component's styling is never
emitted, and an explicit `site.style(...)` call wins over a
component's own default. Full suite: 1088 passed, no regressions.

**Not done this stage:** Option B's actual per-backend rendering
differentiator (Stage 3), component-owned state (Stage 4). There is no
way to opt a call site *out* of its component's default class once
`default_style` is registered -- see the implementation doc's Stage 2
"Explicitly out of scope" note.

## [Unreleased] -- User-defined components, Stage 0 (registration + Option A macro expansion)

**What:** opens the `v0.060` milestone. `component(*, props=None,
mode="macro")` (new, `arklight/api.py`) registers a plain Python
render function as a named, reusable component -- `NavBar(active=
"home")` now reads exactly like a built-in call, but produces a
marker node that a new pipeline stage expands into its real subtree
before Normalization runs, per Option A of
`docs/Foundational/user-defined-components.md`. `mode="registry"` is
also selectable today as an explicit EXPERIMENTAL opt-in toward Option
B, though it does not yet have distinct behavior -- see
`docs/Foundational/USER-DEFINED-COMPONENTS-IMPLEMENTATION.md` for the
full staged ladder and the hybrid decision this pins down.

**Implementation:** `arklight/ir/components.py` (new) --
`Prop`/`ComponentSpec`/`COMPONENT_REGISTRY`/`register_component`/
`expand_ark_ast`/`expand_node`, with a props contract (unknown/missing/
mistyped props fail the build via `ComponentError`, not a raw Python
`TypeError`) and cycle/depth guards (mirrors `validate.py` check #13's
`Computed`/`Derive` self-reference check). `arklight/compiler/
pipeline.py` gains a new `"Expanding user-defined components..."`
stage between ARK-AST construction and Normalization. No changes to
`arklight/ir/schema.py`, `tag_map.py`, or any backend.

**Tests:** `tests/test_user_defined_components_stage0.py` (17 tests,
new); two `tests/test_pipeline_end_to_end.py` stage-order assertions
updated for the new stage message. Full suite: 1057 passed.

**Not done this stage:** `arklight search` typo-suggestion integration
(Stage 1), default-styling registration hook (Stage 2), Option B's
actual per-backend rendering differentiator (Stage 3), component-owned
state (Stage 4).

## [Unreleased] -- Desktop backend, Stage 4 (CI packaging)

**What:** the generated `.github/workflows/desktop-build.yml` (see
Stage 1's own entry below) gains a third job, `package`, alongside its
existing `build` (Stage 2) and `launch-smoke-test` (Stage 3) jobs --
downloads `build`'s uploaded binary, checks out the repo again for
the scaffolded `<app_id>.desktop` launcher entry, and tars the two
together into a downloadable `<binary>-linux.tar.gz` workflow
artifact. A distributable shape beyond the bare `bin/<binary>` Stage 2
already uploads, mirroring the Android backend's Stage 4 (`assemble-
release`) in staging position -- though, unlike that job, there's no
keystore-signing equivalent to gate this one behind an opt-in flag, so
it's unconditional and generated every time, same as Stages 2/3. See
`docs/Backends/DESKTOP-BACKEND-IMPLEMENTATION.md`'s "Stage 4
implementation notes" for the `needs: build` (not `launch-smoke-
test`), tarball-not-`.deb`, and second-checkout-not-shared-artifact
decisions made while landing it.

**Implementation:** `arklight/backend/desktop/runtime.py` --
`_github_ci_workflow_yml` now also takes `app_id` (to locate the
checked-out `.desktop` file) and generates the `package` job;
`project_files` threads `app_id` through to it. No `arklight/cli/
desktop.py` changes -- this stage is CI-only, nothing runs on the
user's own machine.

**Tests (`tests/test_desktop.py`):** the generated workflow YAML
parses (`yaml.safe_load`) and has exactly the three expected jobs;
`package` depends on `build` alone, not `launch-smoke-test`; it
downloads `build`'s uploaded artifact by name; it bundles the correct
`<app_id>.desktop` file, with and without a `project_subdir` prefix;
and `scaffold_project`'s own output includes the new job end-to-end.

## [Unreleased] -- Desktop backend, Stage 1 (`arklight desktop scaffold`, Linux only)

**What:** `arklight desktop scaffold <build-dir> -o <project-dir>
[--target linux]` -- the first CLI-facing rung of the staged desktop
backend (see `docs/Backends/DESKTOP-BACKEND-IMPLEMENTATION.md`, which
also replaces `ARKLIGHT_DESKTOP_BACKEND_PROPOSAL.md`'s "proposal"
status with an actual staged/tracked plan). Templating +
asset-embedding only, no C toolchain required to run the command
itself: turns an existing `arklight build` output directory into a
small native GTK3 + WebKit2GTK host project -- one window, an
in-process `ark:` resource scheme backed by every build-dir file
embedded as indexed C byte arrays (`assets.gen.c`/`assets.gen.h`), and
a navigation policy that hands anything outside that scheme to the
platform's default external handler instead of following it in the
app's own window. No custom native JavaScript API, per the proposal's
"zero native API surface" design constraint. Linux only for now --
`--target` is explicit and validated (`SUPPORTED_TARGETS`) so
Windows/macOS hosts are additive later work, not a breaking rename.
App identity -- name, app ID, window title, width, height, resizable
-- comes from `arklight.config.py`'s `"desktop"` section, read the
same way `arklight android scaffold` already reads its own
`"android"` section, with a built-in default for every key.

**Implementation:** `arklight/backend/desktop/runtime.py` (new) --
pure `(...) -> str`/`(...) -> dict[path, str]` template builders for
`main.c`/`Makefile`/`.gitignore`/a freedesktop `.desktop` launcher
entry/`README.md`, plus `generate_assets_source()` (embeds a
`{build-relative path: bytes}` dict as C byte arrays with MIME types
via `mimetypes.guess_type`). `arklight/cli/desktop.py` (new) --
`DesktopError`, `ScaffoldResult`, `scaffold_project()`, the same
"template builders never touch disk, the CLI module owns filesystem
writes and config resolution" split the Android backend already
established; validates `app_id` (dotted reverse-DNS identifier, same
shape as Android's `package_id`), `width`/`height` (positive ints, not
`bool`s), and `resizable` (an actual `bool`), each with an actionable
`DesktopError`. Wired into `arklight/cli/main.py` as a nested
`desktop scaffold` subcommand and into `arklight/config.py`'s
`_KNOWN_SECTIONS`.

**Verification beyond the test suite:** the generated project was
actually compiled (`libgtk-3-dev`/`libwebkit2gtk-4.1-dev` on Ubuntu
24.04) and run under a headless `Xvfb` while landing this stage --
caught and fixed a deprecated `WebKit2GTK` navigation-action call and
a `&&`/`||` operator-precedence bug in the generated `Makefile`'s
`pkg-config` probe (a chained `A && echo X || B && echo Y` prints
*both* candidates whenever the first matches, since `&&`/`||` share
precedence and left-associate) that a read-through alone wouldn't have
surfaced.

**Tests (`tests/test_desktop.py`):** default-config scaffolding (every
generated file present), build-dir -> embedded-asset-table coverage
(every file present, asset count matches, MIME-type guessing, exact
byte embedding), config-driven identity (app name/ID/window
title/width/height/resizable, including C-string escaping for names
containing quotes/backslashes), `binary_name()`'s slugging, target
validation, every scaffold-time validation error path (missing/
malformed build dir, non-empty output dir, invalid/single-segment app
ID, non-int/bool/zero width or height, non-bool resizable, empty app
name, malformed config file), and the CLI wiring (success/failure exit
codes and messages, missing subcommand, required `-o`, `--target`
choices enforcement).

## [Unreleased] -- `vdom-8`: `localStorage` persistence for `State(..., persist=True)`

**Scope:** `docs/Backends/REFACTOR-INDEX.md` row 16. The last stage of
the combined reactive-core refactor: an opt-in per `State(...)` key
that survives a page reload via `localStorage`, rather than resetting
to its server-rendered initial value every time.

**API (`arklight/api.py`):**

- `State(name, initial=None, persist=False)` -- a third, optional bool
  prop. Off by default; unchanged output for every existing
  `State(...)` call.

**Validation (`arklight/ir/validate.py`):** `_validate_state_declaration`
now also checks a provided `persist` is actually a bool.

**IR (`arklight/ir/build.py`):** new `IRPage.persist` -- the `name` of
every `State(...)` on the page declared with `persist=True`, in
declaration order, extracted by `_extract_page_state` alongside
`state`/`computed`/`watch`. No value of its own, same shape as `watch`.

**HTML backend (`arklight/backend/html/page_render.py`):** `page.persist`
rides along as its own `data-ark-persist` JSON attribute on the same
state marker `data-ark-computed`/`data-ark-watch` already use (both the
plain-`<body>` and `app_shell` marker-`<div>` shapes).

**JS backend (`arklight/backend/js/runtime/state.py`):** unlike
`computed`/`watch`, this isn't a new sibling module or a `createState`
argument -- `initState()` reads `data-ark-persist` directly and does
two small, independently `try`/`catch`-wrapped steps: overrides each
persisted key's initial value from `localStorage["ark:<location.
pathname>:<key>"]` before the store is built, and (only when at least
one key is persisted) writes the current value of each persisted key
back to that same key on every `store.subscribe` notification. Both
localStorage-touching blocks have their own `try`/`catch`, separate
from the outer one guarding the hydration blob's JSON parsing -- a
private-browsing/quota/malformed-value failure degrades to "this key
just doesn't persist" for that key alone, never a page-wide warning.
Always present on a stateful page (a no-op loop when no key opts in),
not gated behind a usage flag the way `wireWatchers`/
`renderModelBindings`/`renderRepeat`/`renderShow` are.

See `tests/test_vdom_8.py` for dedicated coverage (API, Validation, IR,
both HTML backend shapes, and four Node end-to-end checks against
stubbed `document`/`localStorage`/`location`).

## [Unreleased] -- `vdom-7`: per-item list rendering (`Repeat`) + conditional show/hide (`Show`)

**Scope:** `docs/Backends/REFACTOR-INDEX.md` row 15. Adds the two
remaining reactive-content primitives: `Repeat(name, template=...)`
renders one copy of `template()` per element of a list-valued
`State(...)`/`Computed(...)`, kept in sync through the vendored
snabbdom `patch()`; `Show(predicate, ...)` mounts/hides its children
based on a closed-vocabulary `Predicate.truthy(...)`/`falsy(...)`
check against page state. Unlike `Computed`/`Watch`, both are real,
renderable content -- they stay exactly where they're placed in the
tree rather than being pulled out as page-scoped declarations.

**API (`arklight/api.py`):**

- `Repeat(name, *, template)` -- `template` is called once at compile
  time; reference the current item inside it via `RepeatItem.value()`
  (an `ItemBind` marker node) and `RepeatItem.index()` (an
  `ItemIndexRef`, re-resolved on every render so an `Action.remove(...)`
  inside the template keeps removing the right item even after an
  earlier removal shifted later items' positions).
- `Show(predicate, *children)` -- `predicate` is a `Predicate.truthy(name)`/
  `Predicate.falsy(name)` reference (`PredicateRef`), never a raw
  string or expression.

**AST (`arklight/ast/nodes.py`):** new `PredicateRef` and `ItemIndexRef`
dataclasses, mirroring `DerivationRef`'s "small structured object,
validated at compile time" shape.

**IR (`arklight/ir/schema.py`, `arklight/ir/validate.py`):**

- `SCHEMA["Repeat"]`/`SCHEMA["Show"]` plus a new `PREDICATE_REGISTRY`
  (`truthy`/`falsy`, both fixed-arity 1).
- `_validate_repeat_template` (the only place an `ItemBind` node is
  valid) and `_validate_show_declaration`/`_validate_predicate_ref`
  (predicate `kind` must be known, `names` must resolve to
  `State(...)`/`Computed(...)` declared on the same page). Both, unlike
  `_validate_watch_declaration`, still recurse into ordinary children.

**HTML backend (`arklight/backend/html/page_render.py`,
`tag_map.py`):**

- `_render_repeat` renders a `Repeat`'s *current* items as real,
  unrestricted markup (so a JS-disabled visitor sees the genuine list),
  alongside a JSON `data-ark-repeat-template` spec
  (`_repeat_template_spec`) the client uses to build new items after
  an `Action.append(...)` -- narrower than full rendering (`class`/`id`
  plus one `on_click=` per node), a documented limitation for this
  stage.
- `_render_show` always renders `Show`'s children, toggling the native
  `hidden` attribute (a content-visibility semantic, not a style
  decision) rather than omitting markup -- so there's real content for
  the client to reveal, and a JS-disabled visitor sees exactly
  `predicate`'s initial-state evaluation.
- `Repeat`/`Show` both map to a plain `div` in `TAG_MAP` -- transparent
  anchors for `data-ark-repeat`/`data-ark-show`, not tags of their own.

**JS backend (`arklight/backend/js/runtime/repeat.py` (new),
`show.py` (new), `state.py`, `render.py`):**

- `renderRepeat(store)` -- keys each item's vnode by
  `JSON.stringify(item)`, not index (an index-keyed diff would make
  `Action.remove(name, i)` misdiagnose every later item as changed).
  Its first call for a given container doesn't call `patch()` at all:
  the vendored core has no hydration pass, so it instead "adopts" the
  server-rendered DOM into a matching vnode tree (`arkAdoptVnode`),
  and only real `patch()` diffs happen from the second call on.
- `renderShow(store)` -- deliberately does **not** route through
  `patch()` the way `docs/new js backend proposal/ARCHITECTURE-VDOM.md`
  §6.3 proposes (a vnode-swap between real content and a comment
  placeholder): the same missing-hydration-pass problem would either
  leave stale server content next to an empty vnode, or destroy the
  anchor element on the first real toggle. Uses the `hidden` attribute
  instead.
- `_collect_usage`/`_build_runtime_js` gained `has_repeat`/`has_show`
  flags -- `RENDER_REPEAT_JS`/`RENDER_SHOW_JS` ship only on a page that
  actually uses one or the other, same "only ship what's used"
  discipline as `vdom-6`'s `has_model_binding`.

**Tests:** `tests/test_vdom_7.py` (21 tests, new) -- API, Validation,
HTML backend, JS backend coverage. Full suite: 970 passed, no
regressions.

## [Unreleased] -- Android CI: nested-repo `working-directory`/artifact-path fix

**Scope:** follow-up to the Android CI workflow `arklight android
scaffold` generates. When `output_dir` lands inside an *already
existing* enclosing git repo (rather than at that repo's own root),
the generated `.github/workflows/android-build.yml` now carries the
right `working-directory:`/artifact `path:` for that nested layout
from the start, instead of requiring a manual edit after moving the
file up to the enclosing root.

**CLI (`arklight/cli/android.py`):** `_find_enclosing_git_root` now
runs *before* file generation (not just at the end for
`ScaffoldResult`), and the resolved `project_subdir` (the project's
path relative to that enclosing root) is threaded through to
`runtime.project_files`.

**Android backend (`arklight/backend/android/runtime.py`):**
`project_files`/`_github_ci_workflow_yml` gain a `project_subdir`
parameter -- when set, every `run: gradle ...` step gets a matching
`working-directory:` and both jobs' uploaded APK `path:` get the same
prefix; `None` (the default) keeps the original no-subdirectory
behavior.

**CLI output (`arklight/cli/main.py`):** the "move this workflow file"
warning now also notes the moved file is already generated with the
correct paths for its new location.

## [Unreleased] -- `vdom-6`: two-way input binding (`bind_value=`)

**Scope:** `docs/Backends/REFACTOR-INDEX.md` row 14. Adds two-way
binding for form inputs: `bind_value=Bind.model("name")` keeps an
`Input`'s `value` and a `State("name", ...)` entry in sync in both
directions, instead of requiring a hand-wired `on_click=`/`Action.*`
pair for every keystroke.

**API (`arklight/api.py`):**

- `Bind.model(name)` -- thin, explicit spelling for "this is a
  two-way reference" (`bind_value=` also accepts a plain string
  directly, same relationship `bind_class=`/`Bind.when(...)` already
  has). Only a `State(...)` name is a valid target -- mirrors
  `Action.*(...)`'s own restriction, since a `Computed(...)` has no
  independent value of its own for user input to write back into.

**IR (`arklight/ir/validate.py`):**

- `_validate_model_bind` -- `bind_value` must be a non-empty string
  naming a `State(...)` declared on the page; targeting an undeclared
  name or a `Computed(...)` name raises.

**HTML backend (`arklight/backend/html/attrs.py`):**

- Pre-fills `value=` from the page's initial state, same pattern
  `bind_class=` uses for its own initial-render pre-fill (an explicit
  `value=` prop, if also given, wins). Compiles `bind_value=` to a
  `data-ark-model="name"` attribute.

**JS backend (`arklight/backend/js/runtime/model.py` (new),
`arklight/backend/js/runtime/state.py`, `arklight/backend/js/render.py`):**

- `renderModelBindings(store)` -- one more `store.subscribe` render
  pass alongside `renderBindings`/`renderClassBindings`, writing
  `store.get(key)` into the bound element's `.value` on any state
  change, comparing against the element's current `.value` first so a
  user's own keystroke doesn't get its cursor position reset.
- `wireModelBinding(getStore)` -- one delegated `input` listener on
  `document` (event delegation via `Element.closest()`, same pattern
  `wireClickInterceptor` uses for `click`), writing the element's
  `.value` into state on every keystroke. Takes a zero-argument getter,
  registered exactly once, for the same "must survive an `app_shell`
  boosted navigation without a stale closure" reason
  `wireClickInterceptor` documents.
- `_collect_usage`/`_build_runtime_js` gained a `has_model_binding`
  flag -- both new fragments are only shipped on a page that actually
  declares `bind_value=` somewhere, same "only ship what's used"
  discipline `WIRE_WATCHERS_JS` already follows.
- Deliberately not routed through the vendored snabbdom core -- same
  reasoning `renderClassBindings` already documents for `bind_class`:
  `.value` is DOM element state, not a vnode's own rendered children.

Test coverage: `tests/test_vdom_6.py` (new) -- API, Validation, HTML
backend, JS backend, and two Node-subprocess end-to-end checks that
the shipped fragments actually sync state -> value and value -> state.

**Note:** the commit that landed this was mistitled "Vdom 5" in its
commit message -- it's `vdom-6` throughout the code, docstrings, and
`docs/Backends/REFACTOR-INDEX.md` row 14.

## [Unreleased] -- `vdom-5`: watch effects (`Watch(...)`)

**Scope:** `docs/Backends/REFACTOR-INDEX.md` row 13 /
`docs/Foundational/DESIGN-NOTES.md` sub-system 2 ("Watch effects").
Closes the "when X changes, also do Y" side-effect gap `Computed(...)`
deliberately leaves open: `Watch(name, then=Action.*(...))`, a
page-scoped effect that reuses the exact same `ACTION_REGISTRY`
dispatcher `on_click=Action.*(...)` already uses -- no new dispatch
mechanism, just invoked from a state-change subscription instead of a
click listener.

**API (`arklight/api.py`):**

- `Watch(name, *, then)` -- a new declaration node, valid only as a
  direct child of `Page(...)` (same as `State(...)`/`Computed(...)`).
  `name` may reference a `State(...)` *or* a `Computed(...)` (anything
  `Bind(...)` could render); `then` is an `Action.*(...)` reference
  and, like `on_click=`, may only ever target a real `State(...)` --
  a `Computed(...)` has no independent value of its own to mutate.

**IR (`arklight/ir/validate.py`, `arklight/ir/build.py`):**

- `_validate_watch_declaration` -- direct-child-of-`Page(...)` check,
  `name` checked against the page's bindable set, `then` handed to
  the existing `_validate_action` (no new action-shaped validation
  needed -- `Watch(...)`'s `then=` is exactly the `on_click=` shape).
- `IRPage.watch` -- a new declaration-ordered list of
  `{"name": ..., "then": {...}}` dicts (plain, JSON-serializable
  mirrors of the `ActionRef`, via a new `_action_ref_to_spec` helper),
  extracted from a page's children by `_extract_page_state` the same
  way `state`/`computed` already are.

**HTML backend (`arklight/backend/html/page_render.py`):**

- A sibling `data-ark-watch` JSON attribute on the same
  `data-ark-state`/`data-ark-computed` marker.

**JS backend (`arklight/backend/js/runtime/watch.py` (new),
`arklight/backend/js/runtime/state.py`, `arklight/backend/js/render.py`):**

- `wireWatchers(store, specs)` -- snapshots each watched name, adds
  one more `store.subscribe` listener alongside `renderBindings`/
  `renderClassBindings`, and on change dispatches the watched action
  through the same `actions[...]` object the click interceptor reads.
  Wired from `initState()`, guarded with `typeof wireWatchers ===
  "function"` so a stateful page with no `Watch(...)` isn't broken by
  a call to an unshipped function.
- `_collect_usage`/`_build_runtime_js` fold a `Watch(...)`'s
  `then.action` into the same `used_actions` fragment-selection set an
  `on_click=` reference would, while keeping `needs_actions_object`
  (ships `actions`) separate from `needs_click_interceptor` (ships the
  click listener) -- a watch-only page ships `actions` without an
  unused click interceptor.

**Tests:** `tests/test_vdom_5.py` (24 tests) -- API, Validation, IR
build, HTML backend, JS backend, and two Node-subprocess checks (real
dispatch-on-change, and boundedness of a self-referential watch). Full
suite: 931 passed, no regressions.

## [Unreleased] -- `vdom-4`: computed/derived state (`Computed`/`Derive.*`)

**Scope:** `docs/Backends/REFACTOR-INDEX.md` row 12 / `docs/DESIGN-NOTES.md`
`v0.044` sub-system 1 ("Computed/derived state"). Closes the
"derived/computed state" gap named back in the `v0.0035` addenda:
`Computed(name, deps=(...), derive=Derive.*(...))`, a page-scoped
value derived from other `State(...)`/`Computed(...)` values and
recomputed automatically whenever a dependency changes, with the
runtime never handed an expression string to evaluate.

**API (`arklight/api.py`, `arklight/ast/nodes.py`):**

- `Computed(name, *, deps=(...), derive=...)` -- a new declaration
  node, valid only as a direct child of `Page(...)` (same as
  `State(...)`). `Bind(...)`/`bind_class=` may reference a
  `Computed(...)`'s `name` exactly like a `State(...)`'s;
  `Action.*(...)` may not -- a `Computed(...)` has no independent
  value of its own to mutate.
- `Derive` -- a closed vocabulary producing structured `DerivationRef`
  objects (`arklight.ast.nodes`), never a string of JavaScript or
  Python: `Derive.sum(*names)`, `Derive.multiply(*names)`,
  `Derive.join(*names, sep=" ")`, `Derive.count(name)`,
  `Derive.format(template, **names)` (fixed `{name}`-style
  substitution over named state values only), `Derive.compare(a, b,
  op)` where `op` is itself a closed choice.

**IR (`arklight/ir/schema.py`, `arklight/ir/validate.py`,
`arklight/ir/build.py`):**

- `DerivationSpec`/`DERIVATION_REGISTRY`/`COMPARE_OPS` -- mirrors
  `ActionSpec`/`ACTION_REGISTRY`'s discipline: arity bounds
  (`min_names`/`max_names`) and a closed set of extra keyword
  arguments per `kind`.
- Validation checks a `Computed(...)`'s `deps` each resolve to a
  `State(...)`/other `Computed(...)` declared on the same page
  (forward references allowed), that the resulting dependency graph
  has no cycle (DFS cycle detection), and that its `derive=` value's
  `kind`/arity/`args`/`names`-subset-of-`deps` are all well-formed.
- `IRPage` gains `computed: list[tuple[str, dict]]` (dependency-ordered,
  via a topological sort over the `Computed(...) -> Computed(...)`
  edges) and `computed_initial: dict[str, Any]` (each `Computed(...)`'s
  build-time-evaluated initial value, computed via a Python-side
  `_evaluate_derivation` mirroring the JS runtime's semantics
  kind-for-kind).

**HTML backend (`arklight/backend/html/page_render.py`):**

- `page.computed` rides along as its own `data-ark-computed` attribute
  on the same state marker/body element `data-ark-state` already
  uses, never folded into `data-ark-state` itself -- that attribute
  seeds the client store's *mutable* values only. Build-time
  `Bind(...)` text rendering merges `page.computed_initial` in for
  this read-only pass, so a `Computed(...)` value displays correctly
  even with JS disabled.

**JS backend (new `arklight/backend/js/derivations/` package,
`arklight/backend/js/runtime/state.py`, `arklight/backend/js/render.py`):**

- New `derivations/` package mirroring `actions/`/`behaviors/`: one
  `NAME`/`JS_FRAGMENT` sibling module per `Derive.*` kind (`sum.py`,
  `multiply.py`, `join.py`, `count.py`, `format.py`, `compare.py`),
  each a small `kind: function (state, names, args) { ... }` fragment
  matching `_evaluate_derivation`'s build-time semantics kind-for-kind.
- `createState(initial, computed)` gains a second, optional parameter
  -- the same dependency-ordered `(name, spec)` pairs `IRPage.computed`
  carries. A new `recomputeAll()` closure walks that list in the
  already-sorted order, looks each entry's `kind` up in the
  `derivations` object, and writes the result into `state` under the
  `Computed(...)`'s own `name` -- readable through the same
  `store.get(key)` every `Bind(...)`/`renderBindings` call already
  uses. Runs once at construction and again at the end of every
  `set`/`reset`, *before* that call's subscriber notification.
  `initState()` reads the sibling `data-ark-computed` attribute the
  same way it already reads `data-ark-state`.
- `_collect_usage`/`_build_runtime_js` ship the `derivations` object,
  and only the fragments a site's IR actually references, the same
  "only ship what's used" discipline `ACTION_FRAGMENTS`/
  `BEHAVIOR_FRAGMENTS` already follow. Always inside the existing `if
  has_state:` branch -- every `Computed(...)` dependency chain bottoms
  out at a real `State(...)`, enforced by Validation.

**Tests:** new `tests/test_vdom_4.py` (29 tests) covering the API,
Validation (cross-declaration checks, cycle detection, arity, unknown
kind/op, the mutable-vs-bindable state distinction for
`Action.*(...)` targeting), IR build (dependency ordering, chained
`computed_initial` evaluation), the HTML backend (`data-ark-computed`
emission, `data-ark-state` staying mutable-only, prefilled `Bind(...)`
text), the JS backend (only-used-kinds shipping, recompute-before-
notify ordering, `initState()` reading the new attribute), and a
Node-subprocess check that the shipped `multiply` fragment's runtime
recomputation agrees with the build-time-evaluated initial value.
Two pre-existing `tests/test_refactor_0.py` assertions hardcoded
`createState`'s old single-argument signature; updated to
`createState(initial, computed)`. Full suite: 899 passed.

## [Unreleased] -- Android backend, Stage 4 (CI release build) + stage renumbering

**What:** the GitHub Actions workflow Stage 2 added
(`.github/workflows/android-build.yml`) now has a third job,
`assemble-release`, which builds a release APK via `gradle
assembleRelease` on GitHub-hosted runners -- no JDK/Android SDK
needed on the user's own machine, same as the other two jobs. Runs
independently of `assemble-debug`/`install-launch-smoke-test` (it
doesn't need the debug APK). Signing is opt-in: if the repo has
`RELEASE_KEYSTORE_BASE64` (a base64-encoded keystore file),
`RELEASE_KEYSTORE_PASSWORD`, `RELEASE_KEY_ALIAS`, and
`RELEASE_KEY_PASSWORD` configured as GitHub Actions secrets, a step
decodes the keystore to a workspace-local file (discarded when the
job ends) and Gradle signs the APK with it; if those secrets aren't
configured, the job still succeeds and uploads an unsigned release
APK, same as running `gradle assembleRelease` locally with no signing
env vars set.

Alongside this, the whole Android backend's stage numbering is
simplified: the `2a`/`2b`/`3a`/`3b`/`4a`/`4b` letter-suffixed pairs
are retired in favor of plain sequential numbers 0-7 -- the three
CI-only stages that need no local toolchain (build, smoke test,
release build) are now Stages 2/3/4, and their local-machine
counterparts (`arklight android build`, `--install`, `--release`,
still not yet implemented) are now Stages 5/6/7. Nothing about any
stage's behavior or scope changes, only the numbers naming them --
see `docs/Backends/ANDROID-BACKEND-IMPLEMENTATION.md`'s "Numbering"
note for the full reasoning.

**Implementation:** `arklight/backend/android/runtime.py` --
`_github_ci_workflow_yml` gains the `assemble-release` job (checkout
+ JDK 17 + Gradle setup, an optional keystore-decode step gated on
`secrets.RELEASE_KEYSTORE_BASE64 != ''`, then `gradle assembleRelease
--no-daemon` with the four `RELEASE_*` env vars sourced from repo
secrets, then an artifact upload). `_app_build_gradle_kts`'s signing-
config check changes from `releaseStorePath != null` to
`!releaseStorePath.isNullOrBlank()`, since an unset GitHub Actions
secret resolves to an *empty string* inside the workflow's `env:`
block, not an absent variable -- the old null-only check would have
tried (and failed) to open `file("")` instead of falling back to an
unsigned build. `arklight/cli/android.py`'s module docstring and
`arklight/cli/main.py`'s `android scaffold` help text/post-scaffold
output were updated for the new job and the 0-7 renumbering.

**Docs:** `docs/Backends/ANDROID-BACKEND-IMPLEMENTATION.md`'s staged-
order table rewritten for the 0-7 numbering, with Stages 5/6/7 (the
not-yet-started local-toolchain counterparts) called out explicitly as
"to be done at a later point"; the old "Why split Stage 2 into 2a/2b"
and "Why split Stage 3 into 3a/3b" notes are replaced by a single
"Numbering" note up top explaining the retirement of the letter
suffixes. `docs/Foundational/DESIGN-NOTES.md`'s "A staged CLI ladder"
list and `docs/Foundational/ARCHITECTURE.md`'s v0.080 summary row
updated to match.

**Tests (`tests/test_android.py`):** the release job's presence and
wiring (`gradle assembleRelease`, the release-APK output path, the
artifact name), that it declares no `needs:` dependency on
`assemble-debug`, that it references all four `RELEASE_*` secrets and
the `base64 -d` decode step, and that `build.gradle.kts`'s signing
check uses `isNullOrBlank()` rather than a bare null check.

## [Unreleased] -- Android backend, Stage 3a (CI install + launch smoke test)

**What:** the GitHub Actions workflow Stage 2a added
(`.github/workflows/android-build.yml`) now has a second job,
`install-launch-smoke-test`, which downloads the debug APK the first
job built, boots a throwaway hardware-accelerated emulator on the
runner itself, `adb install`s the APK, launches `.MainActivity`, and
fails the job if the app's process isn't still alive a few seconds
later -- catching crash-on-launch regressions (a manifest mistake, a
missing asset the `WebViewAssetLoader` can't find, etc.) that a clean
compile alone wouldn't. No local device/emulator or Android SDK
needed on the user's own machine. This splits the design doc's
original single "Stage 3" (`arklight android build --install`, `adb
install` onto a *locally* connected device/emulator) into 3a (this
entry -- CI-only install/launch verification, depends on Stage 2a) and
3b (the original Stage 3 scope, depends on Stage 2b, not yet
implemented) -- see `docs/Backends/ANDROID-BACKEND-IMPLEMENTATION.md`'s
"Why split Stage 3 into 3a/3b" note for the full reasoning.

**Implementation:** `arklight/backend/android/runtime.py` --
`_github_ci_workflow_yml` now takes `package_id` as well as `app_name`
(needed to name `.MainActivity`'s component for `adb shell am start
-n`) and emits the second job: `actions/download-artifact` for the
APK built by `assemble-debug`, a KVM-enabling udev-rule step (the
standard way to get hardware acceleration on a GitHub-hosted Linux
runner), then `reactivecircus/android-emulator-runner` running an
inline script that installs, launches, and `adb shell pidof`-checks
the app, dumping `adb logcat -d "*:E"` on failure before exiting
non-zero. `arklight/cli/android.py`'s docstring and
`arklight/cli/main.py`'s `android scaffold` help text/post-scaffold
output were updated to describe the 3a/3b split alongside the existing
2a/2b one.

**Tests (`tests/test_android.py`):** the smoke-test job's presence and
wiring (`needs: assemble-debug`, `download-artifact`,
`android-emulator-runner`, the install/launch/pidof commands), and
that the launched component name and `pidof` check both use the
configured (or default) `package_id` rather than a hardcoded one.

## [Unreleased] -- Android backend, Stage 2a (GitHub Actions CI build)

**What:** `arklight android scaffold`'s generated project now includes
`.github/workflows/android-build.yml` -- push the scaffolded project
to GitHub, or open a PR against it, and a debug APK builds on
GitHub-hosted runners and is attached to the workflow run as a
downloadable artifact. No JDK/Android SDK needed on the user's own
machine for this path; both are already present on the runner image.
This splits the design doc's original single "Stage 2" into 2a (this
entry -- CI-only build verification, zero local toolchain) and 2b
(shelling out to a *local* Gradle install, not yet implemented) -- see
`docs/Backends/ANDROID-BACKEND-IMPLEMENTATION.md`'s "Why split Stage 2
into 2a/2b" note for the full reasoning.

**Implementation:** `arklight/backend/android/runtime.py` --
`_github_ci_workflow_yml(app_name)`, wired into `project_files()`
alongside every other generated file, no new CLI flag or subcommand.
Uses `actions/checkout` + `actions/setup-java` (JDK 17, Temurin) +
`gradle/actions/setup-gradle` (installs a pinned Gradle version
explicitly, since this scaffold doesn't template `gradlew`'s wrapper
jar) + `gradle assembleDebug` + `actions/upload-artifact`. Relies on
the Android SDK GitHub's own `ubuntu-latest` runner image ships
preinstalled rather than adding a third-party `setup-android` action.
The uploaded artifact is named from a defensively slugified
`app_name`, not validated the way `package_id` is elsewhere in this
module. `README.md`'s template gained a "Building without a local
JDK" section pointing at the new workflow; `arklight/cli/android.py`'s
docstring and `arklight/cli/main.py`'s `android scaffold` help text
and post-scaffold console output were updated to describe the 2a/2b
split (the latter also now suggests `gradle assembleDebug` instead of
`./gradlew assembleDebug` for local builds, since no wrapper is
generated).

**Tests (`tests/test_android.py`):** the workflow file's presence and
contents (checkout/setup-java/setup-gradle/assembleDebug/
upload-artifact actions, JDK version, and confirming no `gradlew`
reference anywhere in it), and app-name slugification for the
uploaded artifact's display name.

## [Unreleased] -- Android backend, Stage 1 of 4 (`arklight android scaffold`)

**What:** `arklight android scaffold <build-dir> -o <project-dir>` --
the first CLI-facing rung of the staged Android backend (see
`docs/Backends/ANDROID-BACKEND-IMPLEMENTATION.md`). Templating only,
no JDK/Android SDK/Gradle required: turns an existing `arklight build`
output directory into an Application-mode Android Studio / Gradle
project (a `WebView` + `androidx.webkit.WebViewAssetLoader` shell with
the site baked into `app/src/main/assets/` at generation time, no
Viewer chrome). App identity -- name, package ID, version, launcher
icon, splash image, orientation, edge-to-edge -- comes from
`arklight.config.py`'s `"android"` section, read the same way
`arklight live-streaming` already reads its own `"live_streaming"`
section, with a built-in default for every key so a project with no
config at all still scaffolds a buildable, generically-branded app.

**Implementation:** `arklight/cli/android.py` (new) -- `AndroidError`,
`ScaffoldResult`, and `scaffold_project()`, mirroring the
`arklight.cli.scaffold`/`arklight.pwa` split of "template builders
never touch disk, the CLI module owns filesystem writes and config
resolution." Consumes `arklight.backend.android.runtime.project_files`
(landed in the prior Stage-0 commit) for the actual Kotlin/Gradle/XML
file contents. Validates `package_id` (dotted Java-style identifier),
`version_code` (a real `int`, not a `bool`), `orientation` (mapped to
its manifest value -- `"sensor"` -> `"fullSensor"`), and any configured
`icon`/`splash` (must resolve to a real file inside the build
directory, with a `.png`/`.jpg`/`.jpeg`/`.webp` extension), each with
an actionable `AndroidError` rather than a raw traceback. Wired into
`arklight/cli/main.py` as a nested `android scaffold` subcommand
(`arklight android` alone -- with no further subcommand -- errors via
argparse, leaving room for `arklight android build`, Stage 2, to land
as a sibling subcommand later without changing this one's shape).

**Tests (`tests/test_android.py`):** default-config scaffolding
(every generated file present, portrait orientation), build-dir ->
`assets/` copying, config-driven identity (app name, package ID,
version, orientation mapping, edge-to-edge), custom icon/splash
copying (plus their downstream manifest/theme/Gradle wiring), every
validation error path (missing/malformed build dir, non-empty output
dir, path-traversal/missing/wrong-extension icon or splash, invalid
package ID, non-int/bool version code, unknown orientation, malformed
config file), and the CLI wiring (success/failure exit codes and
messages, missing subcommand, required `-o`).

## [Unreleased] -- `Site.raw_postprocess(...)`: user-facing raw output escape hatch

**What:** a new experimental API, `Site.raw_postprocess(fn)`, gated
through the same `arklight/experimental.py` registry as
`site.media_query(...)` and `site.import_style(...)` (see
`docs/EXPERIMENTAL-APIS.md`). `fn` is a plain
`(output_files: dict[str, str]) -> dict[str, str]` callable, registered
directly (`site.raw_postprocess(my_fn)`) or as a bare decorator
(`@site.raw_postprocess`). It's the user-facing equivalent of
`Backend.postprocess()` (`arklight/backend/base.py`) -- same shape,
same "runs over the *combined* output of every backend, in order,
after every render()" contract -- except authored on `Site` instead of
a `Backend` subclass, for one-off transformations that don't warrant a
whole backend.

**Why gated as experimental:** unlike every other entry in the
registry (all CSS/PWA-scoped), this one is arbitrary user code with
unchecked write access to *every* output file the build produces --
nothing about its return value is validated, normalized, or checked
the way the rest of the pipeline's output is. Registering one prints
the standard inline `[EXPERIMENTAL FEATURE ACTIVE]` banner and
end-of-build summary block, both spelling out that this can "give you
a million different ways to shoot yourself in the foot" and to use it
wisely / proceed with caution.

**Implementation:** `Site.raw_postprocess` (`arklight/api.py`) appends
to `site.raw_postprocessors` and emits an `ExperimentalUsage` at
registration time. `build_website_ir` (`arklight/ir/build.py`) threads
`raw_postprocessors` through to `WebsiteIR` as a straight passthrough.
`arklight.compiler.pipeline.build` runs them last, right after the
existing `backend.postprocess(...)` loop -- each function's output
replaces `output_files` wholesale; a non-`dict` return, or an
exception raised inside `fn`, surfaces as a normal `CompileError` with
the offending function's position, the same way a backend failure
already does.

**Tests (`tests/test_experimental_apis.py`):** registration + usage
recording, decorator form, non-callable rejection, IR threading, the
inline banner, actually running (single and multiple, in order) over a
real build's output files, and both failure modes (exception raised,
non-dict return).

## [Unreleased] -- `head_meta.py` favicon/og_image root-relative path bugfix

**Bug:** a root-relative `favicon`/`og_image` value (leading `/`, e.g.
`/assets/favicon.ico`) was passed straight into
`_relative_asset_path`, which resolves via `posixpath.relpath()`.
With one argument absolute, `relpath` resolves it against the build
process's `os.getcwd()` instead of the site's route structure --
every page ended up with the wrong number of `../` segments (matching
the *build directory's* path depth, not the page's route depth)
instead of the correct site-relative path.

`routing.py`'s `_resolve_src_ref` already hit and fixed this exact
failure mode for `src`-shaped attributes (Image/Source/Track/IFrame/
`poster`/`srcset`) by stripping a leading `/` before calling
`_relative_asset_path` -- see `HTML-BACKEND-REFACTOR.md` / the
`UNROUTED_REFERENCE_ATTRS` fix in `[0.0491]` below. That fix never
made it to `head_meta.py`'s `favicon`/`og_image` handling, which
predates it.

**Fix (`arklight/backend/html/head_meta.py`):** both `favicon` and
`og_image` now go through `.lstrip("/")` before `_relative_asset_path`,
matching `_resolve_src_ref`'s existing treatment. A root-relative path
now resolves identically to the same path written without the leading
`/`, regardless of the directory `arklight build` is invoked from.

**Tests (`tests/test_html_head_meta.py`):** two new regression tests
assert a leading-`/` favicon/og_image renders identically to the same
path with no leading `/`, from a nested route.

## [0.0501] -- Combined refactor, Stage 11 of 16 (HTMX integration, `htmx-5`: audit and remove remaining hand-rolled plumbing)

**Scope:** `docs/Backends/REFACTOR-INDEX.md` row 10 / `docs/Backends/
HTMX-INTEGRATION.md` "Implementation ladder" Stage 4. Audit what's
left in `arklight.js` after `htmx-1` through `htmx-4` and remove
anything that duplicates HTMX. The audit's actual finding cuts the
other way from what the stage description implies: the plumbing worth
removing turned out to be a piece of *HTMX's own* attribute
processing, not anything hand-rolled.

**The finding:** `htmx-1`'s `hx-on:click="arkRunBehavior('<name>',
this)"` (the mechanism every named behavior -- `toggle`, `scroll-to`,
`copy`, `dismiss` -- used to wire a click) turns out to route through
HTMX's own `hx-on:*` attribute-processing internals, which build a
function from the attribute's *string value* with the `Function`
constructor (`new Function("event", attributeValue)`) before calling
it. This is an eval-equivalent operation, gated only by
`htmx.config.allowEval` (`true` by default in the vendored release).
Every named-behavior click on every ARKlight site was, through
`htmx-4`, routing through that path -- directly contradicting this
project's own stated invariant (`arklight/backend/js/render.py`'s
module docstring: "there is no eval, no new Function, no string ever
executed as code"). `arkRunBehavior`'s own body was always a small,
fixed, statically-readable function; the eval-equivalent step was
HTMX's attribute-processing machinery *getting there*, not anything
ARKlight wrote.

**HTML backend (`attrs.py`):**

- A named behavior now compiles to `data-ark-on-click="behavior:<name>"`,
  reverting `htmx-1`'s `hx-on:click` shape. Matched-pair with the
  `"action:<name>"` shape `on_click=Action.*(...)` already emitted --
  both are now read by the same delegated listener on the JS side.
  `behavior_target`/`toggle_class` (`data-ark-target`/
  `data-ark-toggle-class`) are unaffected.

**JS backend (`render.py` + `runtime/`):**

- `runtime/dispatch.py`'s `wireActionInterceptor` is renamed
  `wireClickInterceptor` and gains a `"behavior:"` branch alongside
  its existing `"action:"` one -- still exactly one
  `document.addEventListener("click", ...)` registration for the
  whole page, branching on the clicked element's
  `data-ark-on-click` prefix. Each branch has its own `try`/`catch`.
- `arkBehaviors`/`arkRunBehavior` (previously attached to `window` so
  HTMX's attribute evaluation could reach them) are gone. The closed
  behavior-dispatch object is now a plain local `behaviors` var, read
  by closure the same way `actions` already was.
- `STATE_CORE_JS` is reactive-state machinery only now
  (`createState`/`renderBindings`/`renderClassBindings`/`initState`)
  -- the click interceptor is pulled out of that bundle entirely,
  since it's no longer tied to `has_state` (a behavior-only page has
  no `State(...)` at all, but still needs the interceptor).
  `_build_runtime_js` ships `actions`/`behaviors`/
  `wireClickInterceptor` whenever a page uses an `Action.*(...)` or a
  named behavior, independent of `has_state`.
- `needs_htmx` drops the "or a named behavior is used" condition --
  named behaviors no longer touch any `hx-*` attribute, so a
  behavior-only page (the common "toggle a menu, nothing else" case)
  now ships no HTMX at all. `has_state` and `ir.app_shell` are
  unaffected and remain the only two conditions.
- Defense-in-depth, not required for correctness given the above:
  whenever HTMX does ship, `arklight.js` sets `htmx.config.allowEval =
  false` right after loading it, closing the other vendored-HTMX code
  paths that construct a function from a string
  (`hx-vals`/`hx-vars`, bracket-syntax `hx-trigger` event filters) --
  paths ARKlight's compiler never emits into, but which this stops
  relying on "never emits" alone to guarantee.
- A pure-display state page (`Bind(...)` only, no `Action.*(...)`, no
  named behavior) previously always shipped an unused
  `var actions = {};` alongside its reactive core. It no longer does
  -- a further "ship only what's used" tightening this audit turned up
  as a side effect, not the goal.

**Tests:** new `tests/test_htmx_5.py` covering the renamed
interceptor's two branches, the `data-ark-on-click="behavior:..."`
HTML shape, the dropped `needs_htmx` condition (a behavior-only page
now ships no HTMX), `htmx.config.allowEval = false` being present
whenever HTMX does ship, and -- the actual regression this stage
exists to prevent -- that no ARKlight-compiled HTML output ever
contains `hx-on:*`/`hx-vals`/`hx-vars` for any behavior/action/state
combination. The rename (`wireActionInterceptor` ->
`wireClickInterceptor`, `ACTION_INTERCEPTOR_JS` ->
`CLICK_INTERCEPTOR_JS`, `arkRunBehavior`/`arkBehaviors` removed)
updates literal-string assertions in `tests/test_htmx_3.py`,
`tests/test_htmx_4.py`, `tests/test_html_attrs.py`,
`tests/test_html_backend.py`, `tests/test_js_backend.py`,
`tests/test_js_error_handling.py`, `tests/test_class_binding.py`,
`tests/test_event_modifiers.py`,
`tests/test_stateful_js_vocabulary_addendum.py`, and
`tests/test_refactor_0.py`. Two of those updates reflect the actual
behavior changes above, not just the rename: `test_refactor_0.py`'s
`STATE_CORE_JS`-ordering test now checks four reactive-core pieces,
not five (the interceptor is no longer part of that bundle), and
`test_stateful_js_vocabulary_addendum.py`'s pure-display-state test
now asserts `actions`/`wireClickInterceptor` ship *neither*, not that
`actions` ships empty.

## [0.0500] -- Combined refactor, Stage 10 of 16 (HTMX integration, `htmx-4`: app-shell navigation)

**Scope:** `docs/Backends/REFACTOR-INDEX.md` row 9 / `docs/Backends/
JS-BACKEND-REFACTOR-PLAN.md` "The app-illusion problem, stated
precisely." App-shell navigation for sites wrapped in a packaging
backend (Android/KaiOS/Desktop), where a full document reload on every
internal link defeats the point of shipping ARKlight's output as an
installable app.

**`Site(app_shell=True)`** (naming placeholder kept -- no better name
turned up) is a new, single feature flag. Defaults to `False`, and
every existing site's output -- HTML and JS both -- is byte-for-byte
unaffected unless a site opts in. Threaded through the same
`Site` -> `build_website_ir` -> `WebsiteIR` -> backends plumbing every
other `Site(...)` flag already uses.

**HTML backend (`page_render.py`):**

- `<body hx-boost="true">` when `app_shell=True` -- htmx's own
  mechanism for turning same-origin link clicks into an in-place AJAX
  swap instead of a full document reload.
- New `shell_persistent=True` prop (any component) compiles to
  `hx-preserve="true"` -- htmx's mechanism for keeping an element
  untouched across a boosted swap, matched by `id` between the old and
  newly-fetched page. Validation now requires a non-empty `id`
  alongside `shell_persistent=True`, since a `hx-preserve` with no
  stable `id` for htmx to match on is silently useless. This is the
  actual fix for the "shell-persistent regions (nav/header) survive a
  boosted swap" half of the design doc.
- A state page's `data-ark-state` blob moves off `<body>` and into a
  hidden `<div id="ark-state" data-ark-state="...">` marker when
  `app_shell=True`. Verified directly against htmx's own docs: an
  `hx-boost`ed swap replaces `<body>`'s *innerHTML* only, never the
  `<body>` tag's own attributes -- so a `data-ark-state` attribute
  placed directly on `<body>` (the existing, non-app_shell shape,
  unchanged) would freeze at whatever page first loaded and never
  update across a boosted navigation. The marker, being part of the
  swapped content, updates correctly.

**JS backend (`render.py` + `runtime/`):**

- `needs_htmx` now also ships HTMX for `ir.app_shell` alone, not just
  "a named behavior or `State(...)` is used somewhere on the site."
  Closes a real gap the audit surfaced: `arklight.js` is one shared
  file across the whole site, so a plain nav-only page in an
  `app_shell` site with no behaviors or state used *anywhere* would
  previously have shipped without HTMX loaded at all, silently
  falling back to a real document navigation on every click.
- Page init (`highlightActiveNavLink()`/`initState()`/
  `renderBindings()`/`renderClassBindings()`) is extracted into a
  re-callable `arkInitPage()`. Closes a second gap: `DOMContentLoaded`
  only ever fires once per real document load, and a boosted
  navigation doesn't refire it, so nothing before this stage re-ran
  nav highlighting or state hydration after navigating to a
  *different* page via a boosted link. `arkInitPage()` is wired to
  `DOMContentLoaded` unconditionally (unchanged initial-load behavior)
  and, only for `app_shell` sites, to htmx's own `"htmx:afterSettle"`
  event too.
- `runtime/dispatch.py`'s `wireActionInterceptor(store)` becomes
  `wireActionInterceptor(getStore)` -- a zero-argument getter instead
  of a fixed value. The interceptor's one `document`-level `click`
  listener is still registered exactly once, at `DOMContentLoaded`,
  and must never be re-registered on a later boosted swap (`document`
  itself is never replaced by `hx-boost`, so a second registration
  would stack a second listener closing over a now-stale store,
  double-firing every click). The getter lets that one listener always
  read whatever `arkInitPage()` most recently assigned to the shared
  `arkStore` variable, without re-registering.
- `runtime/state.py`'s `initState()` checks for the `#ark-state`
  marker element first, falling back to the `<body>` attribute --
  handles both the `app_shell` and non-`app_shell` shapes without
  needing to know which one it's looking at.

**Tests:** new `tests/test_htmx_4.py` (23 tests) covering the
`Site`/IR plumbing, `hx-boost` emission, the state-marker relocation,
`shell_persistent`/`hx-preserve` (including the Validation
requirement), `needs_htmx`'s new condition, and the `arkInitPage()`/
`htmx:afterSettle` re-init wiring. `wireActionInterceptor`'s signature
change updates the literal-string assertions in
`tests/test_htmx_3.py`, `tests/test_class_binding.py`,
`tests/test_event_modifiers.py`, `tests/test_js_error_handling.py`,
and `tests/test_refactor_0.py` -- no behavioral assertion in any of
those files changed, only the function signature they check for.

## [0.0499] -- Combined refactor, Stage 9 of 16 (HTMX integration, `htmx-3`: action dispatch)

Full design in `docs/Backends/HTMX-INTEGRATION.md` ("Stage 3 --
Replace `wireActions()` wiring loop" / "Revised stage atomicity" ->
Stage 3) and `docs/Backends/REFACTOR-INDEX.md` row 6. Ninth stage of
the merged 16-row staged order, immediately following `htmx-2`.

JS-backend-only change (HTML-side `data-ark-action-*` attributes are
unchanged, per `REFACTOR-INDEX.md` row 6):

- **JS backend** (`arklight/backend/js/runtime/dispatch.py`): the
  `wireActions(store)` function -- a `document.querySelectorAll(
  '[data-ark-on-click^="action:"]')`/`forEach`/per-element-
  `addEventListener` wiring loop -- is deleted and replaced with
  `wireActionInterceptor(store)`: a single delegated `click` listener
  registered once on `document`, resolving the actual target element
  via `Element.closest('[data-ark-on-click^="action:"]')`. One
  `addEventListener` call for the whole page instead of one per
  action element, same "audit and remove hand-rolled plumbing" outcome
  `htmx-2` left queued for this stage.
- **Documented deviation from the design doc:** `HTMX-INTEGRATION.md`
  describes this stage as registering an `htmx:beforeRequest`
  interceptor. That event is only ever dispatched by HTMX's own
  request path (`he()`), which only runs for an element carrying a
  request-verb attribute (`hx-get`/`hx-post`/etc) -- something
  `Action.*(...)` buttons deliberately never have, being client-local
  state mutations rather than server requests (see
  `HTMX-INTEGRATION.md` "HTMX as a client-local interaction target").
  An `ActionRef` *with* modifiers does get a compiled `hx-trigger`
  attribute (`htmx-2`) that HTMX's own attribute processing wires a
  native listener for even without a request verb, but an `ActionRef`
  with *no* modifiers -- the common case -- gets no compiled attribute
  at all, so HTMX's own processing does nothing with it. Wiring only
  through an HTMX-dispatched event would silently drop click handling
  for every unmodified `Action.*(...)` button. `wireActionInterceptor`
  is a delegated native `click` listener instead, which is correct for
  both the modified and unmodified case and still satisfies the
  "single registration, not a per-element wiring pass" outcome the
  design calls for. See `dispatch.py`'s module docstring for the full
  reasoning.
- **`data-ark-on-click="action:..."`/`data-ark-action-state`/
  `data-ark-action-args` are unchanged** -- `wireActionInterceptor`
  reads them exactly as `wireActions()` used to, off the resolved
  target element instead of a pre-bound closure variable.
  `event.preventDefault()` is unconditional, same as before -- `
  "prevent"` remains honored by construction.
- **Guard shape changed**: `wireActions()` had two `try`/`catch`
  blocks (an outer per-element wiring guard, an inner per-click
  dispatch guard). `wireActionInterceptor` has one -- there is no
  separate wiring phase per element any more, so a single guard around
  the attribute reads + dispatch on each click covers the same
  "one malformed element/click can't break anything else" guarantee
  (each invocation of the delegated listener is independent).

### Changed

- `arklight/backend/js/runtime/dispatch.py`: `WIRE_ACTIONS_JS` ->
  `ACTION_INTERCEPTOR_JS`; `wireActions(store)` -> `wireActionInterceptor(store)`,
  rewritten as a delegated `click` listener. Module docstring rewritten
  to document the `htmx:beforeRequest` deviation above.
- `arklight/backend/js/runtime/__init__.py`: import/reassembly updated
  for the renamed export; module docstring updated.
- `arklight/backend/js/render.py`: `DOMContentLoaded` ready-call
  updated from `wireActions(store);` to `wireActionInterceptor(store);`;
  module docstring and the generated runtime's explanatory header
  comment both updated to describe `htmx-3`.
- `arklight/backend/html/attrs.py`: module docstring note pointing to
  `wireActions()`/`dispatch.py` updated to reflect that `htmx-3` has
  landed (attribute shape itself is unchanged).
- `docs/Backends/HTMX-INTEGRATION.md` / `docs/Backends/REFACTOR-INDEX.md`
  / `docs/Backends/JS-BACKEND-REFACTOR-PLAN.md`: Stage 3 / row 6 /
  `htmx-3` marked **Done**, with the delegated-`click`-listener
  deviation documented inline.
- `tests/test_refactor_0.py`, `tests/test_event_modifiers.py`,
  `tests/test_js_error_handling.py`, `tests/test_js_backend.py`
  updated to assert on `wireActionInterceptor`/`ACTION_INTERCEPTOR_JS`
  instead of `wireActions`/`WIRE_ACTIONS_JS`, and on the new
  single-try/catch guard shape, preserving the same underlying
  coverage (malformed-input isolation, action dispatch, "only ship
  what's used") rather than the old assertions verbatim.

### Added

- `tests/test_htmx_3.py`: this stage's dedicated coverage --
  `wireActions` is gone, `wireActionInterceptor` is present and
  registered via a single delegated `click` listener (not a
  `querySelectorAll`/`forEach` loop), dispatch still resolves
  `data-ark-action-state`/`data-ark-action-args` correctly, `"prevent"`
  remains honored by construction, and the guard shape holds.

### Removed

- `arklight/backend/js/runtime/dispatch.py`'s old `wireActions(store)`
  per-element wiring loop. No successor per-element loop -- the
  delegated listener replaces it outright.

### Not in this pass

Modifier *timing* (`debounce`/`throttle`/`once`/`stop`) is still not
functionally enforced by the shipped runtime: `wireActionInterceptor`
dispatches on every native click regardless of the compiled
`hx-trigger` attribute's contents, same as `wireActions()` did before
it. Routing this interceptor through HTMX's own trigger-spec parsing
(the `hx-trigger`-only branch of its attribute processing, which does
support debounce/throttle/once/consume without a request verb) is
deferred -- `htmx-4`'s app-shell audit settles what survives a boosted
DOM swap first, and that answer affects whether trigger-spec parsing
can be safely relied on here. This is a narrower, more honest version
of the gap `htmx-2` originally described as closing at this stage; see
`dispatch.py`'s module docstring for the full reasoning.

## [0.0498] -- Combined refactor, Stage 8 of 16 (HTMX integration, `htmx-2`: modifiers)

Full design in `docs/Backends/HTMX-INTEGRATION.md` ("Stage 2 --
Modifiers" / "Revised stage atomicity") and
`docs/Backends/REFACTOR-INDEX.md` row 5. Eighth stage of the merged
16-row staged order, immediately following `htmx-1`.

Matched-pair change spanning the HTML and JS backends, same atomicity
constraint `htmx-1` already established:

- **HTML backend** (`arklight/backend/html/attrs.py`): an `ActionRef`'s
  `.with_modifiers(...)`/`.debounce(...)`/`.throttle(...)` tokens now
  compile to an `hx-trigger="click debounce:300ms"`-shaped attribute
  via new `_modifiers_to_hx_trigger`, instead of the comma-joined
  `data-ark-modifiers="prevent,debounce:300"` attribute. `"once"` maps
  straight across; `"debounce"`/`"throttle"` gain an `ms` suffix;
  `"stop"` maps to HTMX's `consume` modifier (the closest built-in
  equivalent to `stopPropagation`); `"prevent"` produces no token at
  all -- `wireActions()`'s click listener already calls
  `event.preventDefault()` unconditionally, so it was "honored by
  construction" before this stage too. The attribute is omitted
  entirely when there's nothing left to say (no modifiers, or only
  `"prevent"`), same "only ship what's used" discipline as elsewhere.
  `data-ark-on-click="action:..."`/`data-ark-action-state`/
  `data-ark-action-args` are unaffected -- `htmx-3` scope.
- **JS backend** (`arklight/backend/js/runtime/`): `arkApplyModifiers`
  -- the ~60-line hand-rolled debounce/throttle/once/stop wrapper --
  and its sibling module (`runtime/modifiers.py`) are deleted.
  `wireActions()` (`runtime/dispatch.py`) no longer wraps its dispatch
  through it; it now calls the action directly on every native click,
  same as `event.preventDefault()` already ran unconditionally before.
  **Documented, temporary gap:** `hx-trigger` is compiled into the
  page's markup by this stage, but nothing reads it as an actual
  trigger yet, so `debounce`/`throttle`/`once`/`stop` have no runtime
  effect until `htmx-3` (`REFACTOR-INDEX.md` row 6) replaces
  `wireActions()`'s hand-rolled loop with an `htmx:beforeRequest`
  interceptor that HTMX's own trigger processing actually feeds.
  `STATE_CORE_JS` (`runtime/__init__.py`) is reassembled without the
  deleted piece; `_build_runtime_js`'s (`js/render.py`) explanatory
  header comment updated to match.

### Changed

- `arklight/backend/html/attrs.py`: new `_modifiers_to_hx_trigger` /
  `_HX_TRIGGER_MODIFIER_MAP`; `ActionRef` branch of `_attr_string`
  emits `hx-trigger` instead of `data-ark-modifiers`.
- `arklight/backend/js/runtime/dispatch.py`: `WIRE_ACTIONS_JS` no
  longer calls `arkApplyModifiers`; module docstring documents the
  `htmx-3` handoff.
- `arklight/backend/js/runtime/__init__.py`: `STATE_CORE_JS`
  reassembled without `APPLY_MODIFIERS_JS`; module docstring updated.
- `arklight/backend/js/render.py` / `arklight/backend/html/render.py`:
  module docstrings updated to describe the new attribute shape and
  the `htmx-3` dependency the temporary functional gap above resolves
  through.
- `docs/Backends/HTMX-INTEGRATION.md` / `docs/Backends/REFACTOR-INDEX.md`
  / `docs/Backends/JS-BACKEND-REFACTOR-PLAN.md`: Stage 2 / row 5 /
  `htmx-2` marked **Done**.
- `tests/test_html_attrs.py`, `tests/test_event_modifiers.py`,
  `tests/test_refactor_0.py` updated to assert on the new `hx-trigger`
  output shape and the deletion of `arkApplyModifiers`/
  `data-ark-modifiers`, preserving the same underlying coverage
  (which modifier combinations are accepted, which attribute shape
  each produces, that the runtime module split still reassembles
  correctly) rather than the old assertions verbatim.

### Removed

- `arklight/backend/js/runtime/modifiers.py` (`APPLY_MODIFIERS_JS`):
  deleted outright, per `HTMX-INTEGRATION.md`'s "Removed by HTMX"
  section. No successor module -- there is nothing left for a runtime
  modifier parser to do once modifiers are compiled at build time.

### Not in this pass

`htmx-3` (`REFACTOR-INDEX.md` row 6, `wireActions()`'s wiring loop
replaced by a single `htmx:beforeRequest` interceptor) is what
actually makes `hx-trigger` functionally govern dispatch timing --
until it lands, this stage's `hx-trigger` attribute is compiled but
inert, as documented above and in `runtime/dispatch.py`'s module
docstring.

## [0.0497] -- Combined refactor, Stage 7 of 16 (HTMX integration, `htmx-1`: behaviors)

Full design in `docs/Backends/HTMX-INTEGRATION.md` ("Stage 1 --
Behaviors" / "Revised stage atomicity") and
`docs/Backends/REFACTOR-INDEX.md` row 4. Seventh stage of the merged
16-row staged order, and the first of the `htmx-*` rows -- the ones
Stages 1-6 (the HTML backend module split) were sequenced ahead of
specifically so this landed directly in the new modules instead of
the 580-line `render.py` those stages had already split apart.

This is a matched-pair change spanning the HTML and JS backends at
once, per `HTMX-INTEGRATION.md`'s own atomicity note -- changing one
side without the other breaks named behaviors silently, so both land
in this single stage:

- **Vendored HTMX** (`arklight/backend/js/htmx.py`, new file): the
  real `htmx.org` npm package, version 2.0.10, Zero-Clause BSD
  licensed, `dist/htmx.min.js` included unmodified byte-for-byte --
  same "cite the vendored source" discipline
  `arklight/backend/js/vdom.py` already established for snabbdom.
  Unlike snabbdom's Stage 1 (a hand-picked "bare core" subset), HTMX
  ships as one self-contained bundle with no smaller subset to
  extract, so it's vendored whole.
- **HTML backend** (`arklight/backend/html/attrs.py`): a plain string
  `on_click` (a named behavior -- `toggle`/`scroll-to`/`copy`/
  `dismiss`) now compiles to `hx-on:click="arkRunBehavior('<name>',
  this)"` instead of `data-ark-on-click="<name>"`. `on_click` removed
  from `BEHAVIOR_PROP_ATTRS` accordingly (the generic dict-based
  dispatch it used to go through is now dead for this key --
  special-cased ahead of it instead, same shape as the pre-existing
  `ActionRef` special case). `behavior_target`/`toggle_class` are
  unaffected -- still `data-ark-target`/`data-ark-toggle-class`.
  `on_click=Action.*(...)` (`ActionRef`) is untouched; that's
  `htmx-3` scope.
- **JS backend** (`arklight/backend/js/render.py`): `wireBehaviors()`
  and its `DOMContentLoaded` query/`addEventListener` wiring loop over
  `[data-ark-on-click]` are gone -- HTMX's own `hx-on:click` attribute
  processing does the wiring now (and, unlike the old pass, keeps
  working on any DOM HTMX subsequently swaps in, not just once at
  page load). `_behaviors_block` now emits only the closed
  `arkBehaviors` dispatch object (still just the fragments a site's
  IR actually references) plus a one-line `arkRunBehavior(name, el)`
  lookup-and-call wrapper, both attached to `window` since HTMX
  evaluates `hx-on:click`'s value in normal global scope, not inside
  `arklight.js`'s own IIFE. `_build_runtime_js` ships vendored HTMX
  whenever a page uses a named behavior or declares state (state-only
  pages don't yet emit any `hx-*` attribute themselves, but are scoped
  in now per `REFACTOR-INDEX.md` row 4 so `htmx-2`/`htmx-3` landing
  later doesn't also have to touch this condition).

### Changed

- `arklight/backend/html/attrs.py`: string `on_click` special-cased
  to emit `hx-on:click`; `on_click` removed from `BEHAVIOR_PROP_ATTRS`.
- `arklight/backend/js/render.py`: `wireBehaviors()` deleted;
  `_behaviors_block` rewritten around `arkBehaviors`/`arkRunBehavior`;
  `_build_runtime_js` includes vendored `HTMX_JS` per `needs_htmx`.
- `docs/Backends/HTMX-INTEGRATION.md` / `docs/Backends/REFACTOR-INDEX.md`:
  Stage 1 / row 4 marked **Done**.
- Six test files updated to assert on the new `hx-on:click`/
  `arkRunBehavior` output shape instead of `data-ark-on-click`/
  `wireBehaviors` -- `tests/test_html_attrs.py`,
  `tests/test_html_backend.py`, `tests/test_js_backend.py`,
  `tests/test_js_error_handling.py`, `tests/test_event_modifiers.py`.
  Two of these also scope their pre-existing "no eval/no new Function"
  guarantee to ARKlight's own authored code, now that pages shipping
  vendored HTMX (a general-purpose third-party library) legitimately
  contain those tokens internally, unrelated to that guarantee.

### Added

- `arklight/backend/js/htmx.py`: vendored HTMX 2.0.10 (`HTMX_JS`) plus
  its upstream Zero-Clause BSD license text (`HTMX_LICENSE`).

## [0.0496] -- Combined refactor, Stage 6 of 16 (HTML backend refactor confirmation check, `html-6`)

Full design in `docs/Backends/HTML-BACKEND-REFACTOR.md` (Stage 6) and
`docs/Backends/REFACTOR-INDEX.md` row 11. Sixth stage of the merged
16-row staged order, and the last of the six HTML-side staging items
-- a confirmation check against the *finished* state of the HTML
backend split (Stages 1-5, all now done), not a code change: does
`README.md`'s "Compiler pipeline" HTML Backend bullet still describe
only external behavior, now that Stages 1-5 have moved every function
it could plausibly reference out of `render.py` and into
`tag_map.py`/`routing.py`/`attrs.py`/`head_meta.py`/`page_render.py`?

Confirmed, as the design doc predicted: no code or doc change needed.
`README.md`'s bullet describes what the backend does from the outside
-- maps IR node types to HTML tags, rewrites internal `Link`/`Image`
references to relative file paths, links the generated stylesheet and
behavior runtime -- none of which changed across Stages 1-5; only
*where* that logic lives internally changed. The bullet names
`arklight/backend/html/render.py` as the pipeline stage (not a
specific function inside it), and that's still exactly where
`HTMLBackend.render()` lives after the split, so the reference stays
accurate. `docs/ARCHITECTURE.md`'s pipeline diagram was checked for
the same reason (it names "HTML Backend" as a stage with no function-
level detail at all) and is unaffected for the same reason.

With this stage done, every row `HTML-BACKEND-REFACTOR.md` originally
staged (1-6) is complete; `docs/Backends/REFACTOR-INDEX.md`'s merged
order moves on to the not-yet-started `htmx-*`/`vdom-*` rows (12-16 in
that table), none of which are part of this document's own scope.

### Changed

- `docs/Backends/HTML-BACKEND-REFACTOR.md`: Stage 6 checkbox marked
  **Done** with the confirmation writeup above; Status line updated to
  reflect all six stages implemented.
- `docs/Backends/REFACTOR-INDEX.md`: row 11 (`html-6`) marked **Done**.

No source or test files touched -- this stage is a documentation
confirmation, not an extraction. 761 tests, unchanged from Stage 5.

## [0.0495] -- Combined refactor, Stage 5 of 16 (HTML backend page_render.py split, `html-5`)

Full design in `docs/Backends/HTML-BACKEND-REFACTOR.md` (Stage 5) and
`docs/Backends/REFACTOR-INDEX.md` row 8. Fifth stage of the merged
16-row staged order, and the last of the HTML-side module
extractions: splits `arklight/backend/html/render.py`'s per-page
composition -- `_render_bind`, `_render_children`, `_render_node`,
`_render_page` -- into a new `arklight/backend/html/page_render.py`,
mirroring the `tag_map.py`/`routing.py`/`attrs.py`/`head_meta.py`
per-concern split Stages 1-4 already established. With this stage
done, `render.py` holds only `HTMLBackend`, whose `render()` is a
short composition of the five sibling modules -- the target shape's
stated end state. Pure refactor -- no generated HTML output changes;
`render.py` now imports the moved functions from
`arklight.backend.html.page_render` instead of defining them inline,
and re-exports them for backward compatibility, same as Stages 1-4.
Sequenced ahead of the not-yet-started `htmx-4` (app-shell navigation)
deliberately, per `REFACTOR-INDEX.md` row 8: `_render_page` is exactly
where that stage's shell-persistent-region audit has to look, so this
extraction lands first -- the same reasoning `html-3` already applied
ahead of `htmx-1`.

### Added

- New `arklight/backend/html/page_render.py`: `_render_bind`,
  `_render_children`, `_render_node`, `_render_page` -- moved
  verbatim from `render.py`. Imports tag selection from `tag_map.py`
  (Stage 1), route/asset-path resolution from `routing.py` (Stage 2),
  attribute rendering from `attrs.py` (Stage 3), and `<head>`
  metadata assembly from `head_meta.py` (Stage 4) -- the same call
  graph `render.py` had before this split, just addressed through
  the sibling modules directly instead of re-exported names.
- New `tests/test_html_page_render.py` -- 17 tests: `_render_bind`
  (value rendering, missing-key default, escaping), `_render_node`/
  `_render_children` (simple containers, void tags, `Bind` dispatch,
  text/nested-node flattening, escaping, route-relative link
  resolution through recursion), and `_render_page` (full document
  shell, title/lang fallback and override, state hydration presence/
  absence, nested-route asset-path resolution, head-meta inclusion).
  761 tests total.

### Changed

- `arklight/backend/html/render.py`: rewritten to hold only
  `HTMLBackend` plus the Stages 1-5 backward-compatibility re-exports;
  every per-node/per-page rendering function now lives in
  `page_render.py`. Module docstring rewritten with a "module map"
  section pointing at where each Stage 1-5 concern actually lives, so
  "what does the HTML backend do" is answerable without a 580-line
  scroll -- the same goal the original design doc's "Cheap to read"
  bullet named for the finished split.
- `docs/Backends/HTML-BACKEND-REFACTOR.md`: Stage 5 checkbox and
  Status line marked **Done**.
- `docs/Backends/REFACTOR-INDEX.md`: row 8 (`html-5`) marked **Done**.

## [0.0494] -- Combined refactor, Stage 4 of 16 (HTML backend head_meta.py split, `html-4`)

Full design in `docs/Backends/HTML-BACKEND-REFACTOR.md` (Stage 4) and
`docs/Backends/REFACTOR-INDEX.md` row 7. Fourth stage of the merged
16-row staged order, and the fourth HTML-side extraction: splits
`arklight/backend/html/render.py`'s per-page `<head>` metadata
assembly -- `_render_head_meta` -- into a new
`arklight/backend/html/head_meta.py`, mirroring the `tag_map.py`/
`routing.py`/`attrs.py` per-concern split Stages 1-3 already
established. Pure refactor -- no generated HTML output changes;
`render.py` now imports `_render_head_meta` from
`arklight.backend.html.head_meta` instead of defining it inline, and
re-exports it for backward compatibility, same as Stages 1-3.
Independent of the not-yet-started `htmx-*` track per
`REFACTOR-INDEX.md` row 7's own note -- no shared surface with
behavior/modifier/action attribute emission, so this stage didn't need
to wait on or block anything in that track.

### Added

- New `arklight/backend/html/head_meta.py`: `_render_head_meta` --
  moved verbatim from `render.py`. Depends on `routing.py` (Stage 2)
  for `_relative_asset_path` (resolves `favicon`/`og_image` the same
  way `page_render.py` resolves the stylesheet/script paths); depends
  on nothing from `attrs.py` (Stage 3) or the not-yet-split
  `page_render.py` (Stage 5).
- New `tests/test_html_head_meta.py` -- 11 tests: the no-optional-
  props empty-string case, `description`/`favicon` rendering,
  Open-Graph opt-in behavior (no og_* prop supplied vs. `description`
  alone vs. an explicit `og_title` override), `og_image` asset-path
  resolution, `meta`/`links` dict/list rendering (ordering, multiple
  entries, `links`' verbatim-not-asset-resolved handling), and HTML
  escaping. 744 tests total.

### Changed

- `arklight/backend/html/render.py`: `_render_head_meta` is now
  imported from `arklight.backend.html.head_meta` instead of defined
  inline. Every other function in the file (`_render_bind`,
  `_render_children`, `_render_node`, `_render_page`, `HTMLBackend`) is
  unchanged; the `IRPage` import stays, still used by `_render_page`'s
  own signature.
- `docs/Backends/HTML-BACKEND-REFACTOR.md`: Stage 4 checkbox and
  Status line marked **Done**.
- `docs/Backends/REFACTOR-INDEX.md`: row 7 (`html-4`) marked **Done**.

## [0.0493] -- Combined refactor, Stage 3 of 16 (HTML backend attrs.py split, `html-3`)

Full design in `docs/Backends/HTML-BACKEND-REFACTOR.md` (Stage 3) and
`docs/Backends/REFACTOR-INDEX.md` row 3. Third stage of the merged
16-row staged order, and the third HTML-side extraction: splits
`arklight/backend/html/render.py`'s attribute-rendering concern --
`PASSTHROUGH_ATTRS`, `PROP_ALIASES`, `BEHAVIOR_PROP_ATTRS`,
`_style_dict_to_css`, `_attr_string` -- into a new
`arklight/backend/html/attrs.py`, mirroring the `tag_map.py`/
`routing.py` per-concern split Stages 1-2 already established. Pure
refactor -- no generated HTML output changes; `render.py` now imports
the moved names from `arklight.backend.html.attrs` instead of defining
them inline, and re-exports them for backward compatibility, same as
Stages 1-2. Sequenced ahead of the not-yet-started `htmx-1` stage
deliberately, per `REFACTOR-INDEX.md`'s "Why the HTML split and the
HTMX attribute changes collide": landing the HTMX attribute-emission
rewrite directly in `attrs.py` once that stage starts, rather than in
`render.py` a few commits before being moved out from under it.

### Added

- New `arklight/backend/html/attrs.py`: `PASSTHROUGH_ATTRS`,
  `PROP_ALIASES`, `BEHAVIOR_PROP_ATTRS`, `_style_dict_to_css`,
  `_attr_string` -- moved verbatim from `render.py`. Depends on
  `routing.py` (Stage 2) for the route/asset-path resolution
  `_attr_string` delegates to; depends on nothing from `head_meta.py`
  or `page_render.py` (Stages 4-5, not yet split out).
- New `tests/test_html_attrs.py` -- 24 tests: the moved data
  tables' exact contents, `_style_dict_to_css` conversion/joining/
  filtering, and `_attr_string` across passthrough attrs, aliases,
  inline styles, unknown-prop `data-*` fallback, `aria_*` mapping,
  boolean attrs, route-aware `href` rewriting, `ActionRef`/
  `ClassBindSpec` attribute emission (including modifiers and
  state-driven class pre-fill). 733 tests total.

### Changed

- `arklight/backend/html/render.py`: `PASSTHROUGH_ATTRS`/
  `PROP_ALIASES`/`BEHAVIOR_PROP_ATTRS`/`_style_dict_to_css`/
  `_attr_string` are now imported from `arklight.backend.html.attrs`
  instead of defined inline. The now-unused `ActionRef`/
  `ClassBindSpec` import was dropped from `render.py` (both are only
  referenced from `attrs.py` now); `json`/`html.escape` imports stay,
  still used by `_render_bind`/`_render_head_meta`/`_render_page`.
  Every other function in the file (`_render_bind`, `_render_children`,
  `_render_node`, `_render_head_meta`, `_render_page`, `HTMLBackend`)
  is unchanged.
- `docs/Backends/HTML-BACKEND-REFACTOR.md`: Stage 3 checkbox and
  Status line marked **Done**.
- `docs/Backends/REFACTOR-INDEX.md`: row 3 (`html-3`) marked **Done**.

## [0.0492] -- Combined refactor, Stage 2 of 16 (JS runtime module split, `refactor-0`)

Full design in `docs/Backends/JS-BACKEND-REFACTOR-PLAN.md` (`refactor-0`
row) and `docs/Backends/HTMX-INTEGRATION.md`; sequencing against the
HTML backend split and the `htmx-*`/`vdom-*` tracks in
`docs/Backends/REFACTOR-INDEX.md` row 2. Second stage of the merged
16-row staged order that document closes, and the first stage on the
JS-backend side of it: splits `arklight/backend/js/render.py`'s old
`_STATE_CORE_JS` (`createState`, `renderBindings`,
`renderClassBindings`, `initState`, `arkApplyModifiers`,
`wireActions`, one 145-line triple-quoted string) plus its
`_NOTIFY_JS`/`_NAV_HIGHLIGHT_JS` constants into
`arklight/backend/js/runtime/{state,bindings,modifiers,dispatch,nav,
notify}.py`, mirroring the `actions/`/`behaviors/` per-file pattern
already established for the per-name registries. Pure refactor -- no
generated JS output changes; `render.py` now imports the reassembled
fragments from `arklight.backend.js.runtime` instead of defining them
inline. Landed ahead of the `htmx-*` track deliberately, since both
that track and the not-yet-started `vdom-*` track touch this same
file -- splitting once first avoids two large, unrelated diffs
colliding in review (see `JS-BACKEND-REFACTOR-PLAN.md` "Ordering
rationale, stated explicitly").

### Added

- New `arklight/backend/js/runtime/` package:
  - `state.py` -- `CREATE_STATE_JS` (`createState`), `INIT_STATE_JS`
    (`initState`).
  - `bindings.py` -- `RENDER_BINDINGS_JS` (`renderBindings`),
    `RENDER_CLASS_BINDINGS_JS` (`renderClassBindings`).
  - `modifiers.py` -- `APPLY_MODIFIERS_JS` (`arkApplyModifiers`).
  - `dispatch.py` -- `WIRE_ACTIONS_JS` (`wireActions`).
  - `nav.py` -- `NAV_HIGHLIGHT_JS` (`highlightActiveNavLink`).
  - `notify.py` -- `NOTIFY_JS` (`arkNotify`).
  - `__init__.py` -- reassembles `STATE_CORE_JS` from the six modules
    above in the original `_STATE_CORE_JS` order, and re-exports
    `NOTIFY_JS`/`NAV_HIGHLIGHT_JS`.
- New `tests/test_refactor_0.py` -- 9 tests: each new module exposes
  the fragment it's supposed to, `STATE_CORE_JS` reassembles them in
  the original order, and `JSBackend.render()`'s output for both a
  plain and a stateful page is unaffected by the split. 709 tests
  total.

### Changed

- `arklight/backend/js/render.py`: `_STATE_CORE_JS` / `_NOTIFY_JS` /
  `_NAV_HIGHLIGHT_JS` are now imported from
  `arklight.backend.js.runtime` instead of defined inline; every
  other function in the file (`_collect_usage`, `_behaviors_block`,
  `_actions_block`, `_build_runtime_js`, `JSBackend`) is unchanged.
- `docs/Backends/REFACTOR-INDEX.md`: row 2 (`refactor-0`) marked
  **Done**.

## [0.0491] -- HTML backend refactor, Stage 2 of 6 (routing.py + UNROUTED_REFERENCE_ATTRS fix)

Full design in `docs/Backends/HTML-BACKEND-REFACTOR.md`; sequencing
against the JS backend/HTMX work in `docs/Backends/REFACTOR-INDEX.md`
row 1 (`html-2`). Second of six staged extractions splitting
`arklight/backend/html/render.py`'s five unrelated jobs into their own
modules. Unlike Stage 1, this stage is deliberately not
behavior-preserving in one respect: it also lands the
`UNROUTED_REFERENCE_ATTRS` reachability fix the design doc's audit
flagged as open, per that doc's own stated exception to "behavior
unchanged after every stage."

### Added

- New `arklight/backend/html/routing.py`: route/asset-path resolution
  -- `_output_path_for_route`, `_is_internal_route_ref`,
  `_resolve_route_ref`, `_resolve_src_ref`, `_relative_asset_path`, and
  the attribute-classification sets `ROUTE_AWARE_ATTRS`,
  `ASSET_OR_ROUTE_AWARE_ATTRS`, `SRC_ATTRS` -- moved out of `render.py`.
- New `_resolve_srcset_ref` in `routing.py`: `srcset` packs one or more
  comma-separated `url descriptor` pairs into a single value (e.g.
  `"wide.jpg 800w, narrow.jpg 400w"`), so it needed its own resolver
  rather than reusing `_resolve_route_ref`/`_resolve_src_ref` directly
  -- each URL is split out, resolved independently (same
  route-or-asset treatment `poster`/`src` get), and rejoined with its
  descriptor intact. New `SRCSET_ATTRS` set drives this in `_attr_string`.
- **The `UNROUTED_REFERENCE_ATTRS` fix**, per the design doc's audit:
  - `action`/`formaction` (Form, and any submit-capable Button/Input)
    join `ROUTE_AWARE_ATTRS` -- resolved exactly like `href`. The
    audit's flagged sub-question (whether these should warn-and-skip
    instead, since a form action is at least as likely to target an
    external API as an internal route) is resolved by
    `_resolve_route_ref`'s existing "unknown route left as-is" safety
    net: an external API URL never matches a registered route, so it's
    never rewritten either way -- no separate warn-and-skip path
    needed.
  - `poster` (Video) joins `ASSET_OR_ROUTE_AWARE_ATTRS` -- resolved
    exactly like `src` (route-checked first, asset-fallback
    otherwise), since a poster names an image asset, not a route.
  - `srcset` (PictureSource) resolved via the new `_resolve_srcset_ref`
    above.
- New `tests/test_html_routing.py` -- 31 tests exercising `routing.py`
  directly, independent of `HTMLBackend.render`/a full IR build (same
  "independent testability" goal `tests/test_html_tag_map.py`
  established for Stage 1). 700 tests total.
- 8 new end-to-end tests in `tests/test_html_backend.py` covering the
  `UNROUTED_REFERENCE_ATTRS` fix through real `Page(...)`/`render()`
  calls: known-route `action`/`formaction` rewriting (including across
  nested page depth), `poster` as both a known-route embed and a
  root-relative asset, and `srcset` with multiple entries, a density
  descriptor, and an external URL left untouched.

### Fixed

- A separate, pre-existing bug surfaced while wiring `formaction`
  through the fix above: `formaction` was missing from
  `PASSTHROUGH_ATTRS` entirely, so it always rendered as
  `data-formaction="..."` instead of a real HTML attribute, independent
  of routing. Added to `PASSTHROUGH_ATTRS` in the same commit --
  a route-rewritten `formaction` value isn't observable through a
  `data-formaction` fallback attribute, so shipping the routing half of
  the fix without this would have been silently incomplete.

### Removed

- `UNROUTED_REFERENCE_ATTRS` and `_warn_unrouted_reference` (the
  v0.0431 emergency-patch build-time warning) -- removed entirely, not
  deprecated. Once every attribute the warning covered is correctly
  resolved, there is nothing left for it to flag. The CLI's
  `[ARKlight ALPHA]`-marker warning-surfacing machinery
  (`arklight/cli/main.py`) is unaffected -- it's generic across every
  alpha-limitation warning, not specific to this one, and other
  `[ARKlight ALPHA]` warnings may still exist elsewhere.

### Changed

- `render.py` now imports the routing names from `routing.py` instead
  of defining them, and re-exports them so
  `from arklight.backend.html.render import ROUTE_AWARE_ATTRS` (etc.)
  keeps working unchanged -- same backward-compatibility discipline
  Stage 1 established for `TAG_MAP`/`VOID_TAGS`/`_tag_for`.
  `tests/test_html_backend.py`'s existing suite passes unchanged
  *except* for the one test the design doc's own staging notes as the
  expected exception (the build-time warning previously asserted via
  `pytest`'s captured-warnings summary for `test_form_elements_render_with_form_attrs`'s
  `action="/submit"` no longer fires, since `/submit` isn't a
  registered route and is correctly left untouched with no warning --
  the test's own assertions were already correct and needed no
  changes).

### Not in this pass

Stages 3-6 (`attrs.py`, `head_meta.py`, `page_render.py`, the
`README.md` compiler-pipeline description check) are unstarted -- see
`docs/Backends/HTML-BACKEND-REFACTOR.md`'s staging table and
`docs/Backends/REFACTOR-INDEX.md` for how they sequence against the JS
backend/HTMX work.

## [0.049] -- HTML backend refactor, Stage 1 of 6

Full design in `docs/Backends/HTML-BACKEND-REFACTOR.md`. First of six
staged, behavior-preserving extractions splitting
`arklight/backend/html/render.py`'s five unrelated jobs into their own
modules, mirroring the CSS backend refactor's earlier split.

### Added

- New `arklight/backend/html/tag_map.py`: `TAG_MAP` (IR node type ->
  HTML tag name), `VOID_TAGS` (tags with no closing tag/children), and
  `_tag_for(node)` (resolves `Heading`'s tag from its `level` prop,
  falls back to `TAG_MAP` otherwise) -- moved verbatim out of
  `render.py`. Pure data plus one tiny pure function, no dependency on
  anything else in the HTML backend.
- New `tests/test_html_tag_map.py` -- 8 tests exercising `tag_map.py`
  directly, independent of `HTMLBackend.render`/a full IR build (the
  refactor's "independent testability" goal). 661 tests total.

### Changed

- `render.py` now imports `TAG_MAP`/`VOID_TAGS`/`_tag_for` from
  `tag_map.py` instead of defining them, and re-exports all three
  names so `from arklight.backend.html.render import TAG_MAP` (etc.)
  keeps working unchanged. Zero behavior change: `tests/test_html_backend.py`
  passes unmodified, generated HTML is byte-for-byte identical.
- `docs/ARCHITECTURE.md`'s Backend Interface section updated to point
  at the refactor doc's real path (`docs/Backends/HTML-BACKEND-REFACTOR.md`,
  not `docs/HTML-BACKEND-REFACTOR.md`) and reflect Stage 1 landing.

### Not in this pass

Stages 2-6 (`routing.py`, `attrs.py`, `head_meta.py`, `page_render.py`,
the `README.md` compiler-pipeline description check) are unstarted --
see the design doc's staging table. Stage 2 in particular also carries
the `UNROUTED_REFERENCE_ATTRS` reachability fix (`srcset`/`poster`/
`action`/`formaction` not route-rewritten) flagged there; deliberately
not pulled forward into this stage.

## [0.049] -- Feedback-loop fix + `@import` made experimental

Two fixes, bundled together since both touch the same "Stage 8
compile-time feedback loop" and "at-rule vocabulary" areas from the
work directly below.

### Fixed

- **Stage 8's self-learning typo feedback loop never actually fired.**
  Every component (`Heading`, `Image`, ...) is a real Python
  function/name, so misspelling one (`Headingg(...)`) fails as a
  plain Python `NameError` inside `Site.build_ark_ast()` -- several
  pipeline stages before `validate_node()` ever runs -- so it never
  reached the `ValidationError` `arklight/search/feedback.py`'s
  `record_validation_feedback` was built to listen for. In ordinary
  use, that `ValidationError` path is essentially unreachable: all
  three `ARKNode(type=...)` construction sites in the codebase pass a
  fixed, correctly-spelled string, never one that round-trips through
  user input.
  - New `parse_undefined_component_name`/`record_name_error_feedback`
    in `arklight/search/feedback.py`, recognizing Python's own
    `NameError` message shape (`name 'X' is not defined`) -- the
    message a typo'd component call actually raises.
  - `compile_site_file` (`arklight/compiler/pipeline.py`) gains a new
    `except NameError` branch around `site.build_ark_ast()`, ahead of
    the existing catch-all `except Exception`, calling this new
    best-effort recorder. Same failure-swallowing, build-behavior-
    neutral contract as the existing `ValidationError` hook --
    recording a confusion never affects whether/how a build succeeds
    or fails.
  - `record_validation_feedback`/`parse_unknown_component_type` are
    unchanged and kept for the rarer path where an already-built
    `ARKNode` reaches `validate_node()` with an unknown `.type`
    directly (IR constructed by a lower-level caller that skips the
    documented component functions).
  - New `tests/test_search_feedback.py` -- 12 tests, including an
    end-to-end repro of the original bug report (scaffold a typo'd
    site, build it, confirm a `confusions` row is now actually
    recorded). 647 tests total, all passing.
  - Not fixed here, left as-is: `arklight search`'s undisclosed
    first-run creation of `~/.local/share/arklight/search.sqlite3`
    (or the platform equivalent) -- flagged in the same audit, but a
    documentation/disclosure gap, not a bug, and out of scope for this
    pass.

### Changed

- **`Site.import_style(url)` (`@import`) is now an EXPERIMENTAL API**
  (see `docs/EXPERIMENTAL-APIS.md`), gated through the same mechanism
  `site.media_query(...)` already uses. New `css-import` entry in
  `arklight/experimental.py`'s `FEATURES` registry: *"the imported
  file's contents can't be validated by ARKlight"* -- unlike every
  other rule this project generates, an `@import` URL is fetched and
  applied by the browser at request time, so nothing about it is
  checked. Every call now prints the inline `[EXPERIMENTAL FEATURE
  ACTIVE]` banner and an end-of-run summary block, same as
  `media_query`. `container_query` remains deliberately **not**
  flagged (unaffected by this change) -- it isn't request-time-opaque
  the way `@import`/`@media` are.
  - `tests/test_experimental_apis.py` and
    `tests/test_css_structural_addendum.py` extended with `css-import`
    coverage (registration, inline banner, IR threading, invalid-URL-
    doesn't-record, summary text).
  - `docs/EXPERIMENTAL-APIS.md` and `docs/DESIGN-NOTES.md` updated to
    list `css-import` alongside `css-media-queries`/
    `experimental-install-pwa`.

## [0.049] -- Pseudo-class vocabulary addendum III

Full writeup in `docs/DESIGN-NOTES.md` ("v0.049: pseudo-class
vocabulary addendum III"). Same mechanism as the CSS selector algebra
work directly below, just growing the set -- every parameterless
pseudo-class (single word, no `(...)` argument) is the same shape as
`hover`/`focus`/`disabled` already in `ALLOWED_PSEUDO_CLASSES`, so
adding more is a one-line set extension, not a regex or pipeline
change. No new mechanism, no new tests infrastructure -- just more
entries validated by the two call sites that already read this set
(`site.style(...)`'s `:pseudo:property` shorthand in `arklight/api.py`,
and the general selector parser in `arklight/backend/css/selectors.py`
used by `Site.style_selector(...)`).

### Added

- 20 more entries in `ALLOWED_PSEUDO_CLASSES`: `focus-within`, `link`,
  `target`, `enabled`, `indeterminate`, `default`, `required`,
  `optional`, `valid`, `invalid`, `in-range`, `out-of-range`,
  `read-only`, `read-write`, `placeholder-shown`, `root`, `empty`,
  `only-child`, `first-of-type`, `last-of-type`, `only-of-type`.
- `tests/test_api_style.py::test_style_accepts_every_supported_pseudo_class`
  extended to cover all 29 pseudo-classes (was 7).
- `tests/test_css_selectors.py::test_round_trips_a_valid_selector`
  extended with parameterless-pseudo-class and multi-pseudo-class
  cases (`:focus-within`, `:target`, `:empty`, `:required`,
  `:invalid`, `:in-range`, `:only-child`, `input:required:invalid`).
- 635 tests total (31 new test cases from the two parametrize
  extensions above), all passing.

### Notes

- Deliberately still a curated set, not "any `:whatever` the user
  types" -- functional/parameterized pseudo-classes (`:not()`,
  `:nth-child()`, etc.) and pseudo-elements (`::before`, etc.) are out
  of scope here; they're handled by the separate mechanisms added in
  the CSS selector algebra work directly below (`SELECTOR_LIST_PSEUDO_CLASSES`,
  `NTH_PSEUDO_CLASSES`, `PSEUDO_ELEMENTS`).

## [0.049] - Unreleased

**CSS selector algebra + at-rule vocabulary.** Closes the remaining
structural CSS gaps flagged in `docs/DESIGN-NOTES.md` ("CSS selector
algebra + at-rule vocabulary"): pseudo-elements, parameterized
pseudo-classes, attribute selectors, combinators, grouped selectors,
bare tag-selector overrides, `@keyframes`, `@font-face`, `@container`,
`@supports`, `@page`, and `@import`. Same discipline as every other
extension point in the project -- a closed grammar/registry, never a
raw-CSS-string escape hatch.

- New `arklight/backend/css/selectors.py`: a small recursive-descent
  selector parser. `parse_selector_list(text)` either returns a
  validated AST or raises `CSSSelectorSyntaxError`; `render_selector_list`
  turns that AST back into canonical CSS text.
- New `Site.style_selector(selector: str, rules: dict) -> None` --
  combinators (`.a > .b`, `.a + .b`, `.a ~ .b`, `.a .b`), grouped
  selectors (`h1, h2, h3`), bare tag overrides (`blockquote`),
  attribute selectors (`[type="email"]`), pseudo-elements
  (`::before`, `::after`, `::placeholder`, `::selection`, `::marker`,
  `::first-line`, `::first-letter`), and parameterized pseudo-classes
  (`:not()`, `:is()`, `:where()`, `:has()` -- including its relative
  form, `:has(> .icon)` -- and the `:nth-child()` family with real
  An+B validation). Supports one level of `&`-prefixed nesting
  (`"&:hover"`, `"& .child"`, `"& > .child"`), desugared at author
  time into fully-resolved selectors rather than emitted as real CSS
  nesting syntax. `Site.style(name, rules)` is unchanged.
- New `Site.keyframes(name, frames)`, `Site.font_face(family, src,
  **descriptors)`, `Site.container_query(condition, selector, rules,
  *, name=None)`, `Site.supports(condition, selector, rules)`,
  `Site.page_rule(rules, *, pseudo=None)`, and `Site.import_style(url)`
  -- new closed-vocabulary `Site` methods, each rendered by a new pure
  function in the new `arklight/backend/css/at_rules.py`.
  `container_query` is deliberately not flagged EXPERIMENTAL the way
  `media_query` is (a container query isn't viewport-keyed, so it
  doesn't carry the same caution). `import_style` output is placed
  first in the generated stylesheet, ahead of `BASE_CSS_HEADER`, per
  the CSS spec's `@import`-must-come-first requirement.
- All additions are pure passthrough data on `WebsiteIR`
  (`selector_rules`, `keyframes`, `font_faces`, `container_queries`,
  `supports_rules`, `page_rules`, `style_imports`) -- no change to
  `normalize.py`/`validate.py`'s tree-walking logic. 63 new tests
  (`tests/test_css_selectors.py`, `tests/test_css_structural_addendum.py`);
  604 tests total, all passing. Fully additive -- a site that never
  calls any of these methods renders byte-for-byte unchanged.

## [0.048] - Unreleased

**Stage A of v0.048: structured `<head>` extension.** `Page(...)`
gains two more optional, structured props: `meta: dict[str, str] |
None` (name/content pairs, each rendered as `<meta name="..."
content="...">`) and `links: list[dict[str, str]] | None` (each dict
an attribute -> value map rendered as one `<link ...>` tag, for
preconnect/webfonts/extra icon sizes beyond `favicon`). No raw
HTML-injection escape hatch -- same discipline as every other
extension point in the project. Validated in `arklight/ir/validate.py`
(`_validate_page_head_extensions`, `Page`-only); rendered in
`arklight/backend/html/render.py`'s `_render_head_meta`, appended
after the existing `description`/`favicon`/`og_*` tags. `links`
entries are emitted verbatim (not resolved as a relative build asset
the way `favicon`/`og_image` are), since a `links` entry is at least
as likely to point at an external origin as a local one. 10 new tests
in `tests/test_html_backend.py`; 541 tests total, all passing. Fully
additive -- a page that sets neither prop renders byte-for-byte
unchanged.

With this stage landing, **v0.048 (CSS `@media` queries + `<head>`
extension) is now DONE in full** -- Stage B (`responsive_style` +
`@media` compilation) shipped previously; see `PROGRESS.md` for both
stages' implementation records.

**Renumbered the milestones behind v0.048** now that it has shipped
(see `docs/ARCHITECTURE.md` for the full note): JS backend capability
expansion moves `v0.044` -> `v0.054`; user-defined components moves
`v0.100` -> `v0.060`; the Desktop backend moves `v0.060` -> `v0.080`;
the Android backend moves `v0.080` -> `v0.100`; and the KaiOS backend
-- previously designed but unnumbered -- is now `v0.120`. No scope or
design changes, sequencing only.

## [0.0436] - Unreleased

**Added `arklight live-streaming`, an alpha-only dev server: watch,
auto-rebuild, and auto-reload a project in the browser as you edit.**
`arklight live-streaming --subscribe site.py [-o ARK] [--host H]
[--port P]` blocks in the terminal it's run from, serves the build
output over stdlib `http.server`, and re-runs the normal
`arklight.compiler.pipeline.build()` pipeline (with full
`--verbose`-style stage narration) whenever a `.py` file or `assets/`
under the entry's directory changes on disk -- detected via a plain
mtime-polling loop, no third-party watcher dependency (ARKlight stays
zero-dependency). Reload is delivered over a Server-Sent-Events
endpoint (`/__arklight_live__/events`) to a small vendored client
script (`/__arklight_live__/client.js`), injected into every HTML page
*only* during a live-streaming build via a new, purely additive
`_LiveReloadBackend` (`Backend.postprocess`, same extension point
`arklight/backend/base.py` already documents for "injecting
analytics/OG tags... without editing that backend's source") -- a
plain `arklight build` is byte-for-byte unaffected. `arklight
live-streaming --unsubscribe [site.py]` and `--status [site.py]
[--status-pin]` run from another terminal and talk to the running
session via a small on-disk registry (`~/.arklight/live_streaming/
registry.json`) keyed by the entry file's absolute path, plus a
`SIGTERM` for shutdown; both are idempotent (`--unsubscribe` on a
session that isn't running, or a second `--subscribe` on one already
running, are no-ops rather than errors). `--status-pin` is a purely
per-invocation formatting flag -- it's never written into the
registry, so it has no effect on the running `--subscribe` session and
isn't remembered for the next `--status` call. Host/port/poll-interval
can also be pinned per-project via a new, deliberately small
`arklight.config.py` (see `arklight/config.py` and next entry) instead
of passed as flags every time. New regression tests in
`tests/test_live_streaming.py` cover reload-script injection, registry
read/write/corrupt-file recovery and stale-PID pruning, and session
lookup/disambiguation; manually verified end-to-end (idempotent
subscribe, live edit -> rebuild -> reload, clean `--unsubscribe`, and
graceful shutdown on an external `SIGTERM`).

**Added `arklight.config.py`, a minimal per-project config file.**
Currently the only reader is `arklight live-streaming` (see above),
which wants a place to pin `host`/`port`/`poll_interval` under a
`live_streaming` section without flags on every `--subscribe`. Rather
than design a full schema with no second consumer yet, `arklight/
config.py` defines just enough to load a project's
`arklight.config.py` (a plain Python file next to `site.py` containing
a top-level `CONFIG = {...}` dict), merge a named section over a
reader-supplied set of defaults, and fail loudly (`ConfigError`) on a
present-but-broken file rather than silently falling back -- extending
it later is a one-line addition to whichever module reads a new
section, not a rewrite of the loader. New regression tests in
`tests/test_config.py`.

**`arklight pwa` can now register manifest icons via `--icon`.**
`enable_pwa(icons=...)` already accepted a list of manifest icon
dicts, but the CLI had no way to pass them -- every `arklight pwa`
run shipped an empty `icons` list, which is enough for some browsers
to decline to prompt an install. Added a repeatable `--icon
SRC:SIZES[:TYPE]` flag (e.g. `--icon assets/icon-192.png:192x192`);
`SRC` is a path relative to the build directory (same as an icon
already copied into `assets/` by a normal build), `SIZES` is
`WIDTHxHEIGHT` or `any`, and `TYPE` is optional, inferred from `SRC`'s
extension via `mimetypes` when omitted. Malformed values (bad `SIZES`,
an extension `mimetypes` can't resolve without an explicit `TYPE`)
report a normal CLI error rather than a traceback or a silently wrong
manifest.

## [0.0435] - Unreleased

**`arklight new --template production` now recommends the layout it
already scaffolds.** The `production` template's `site.py` +
`components/` + `pages/` + `content/` split was already
service-oriented and separated by concern, but a first-time user got
no explanation of *why* the files were laid out that way -- just a
file list. A short note now prints after every `production` scaffold
(`arklight new` output for `simple` is unchanged, since there's
nothing to explain there). Added `arklight new --explain-architecture`
to print the full guide -- concrete to this template's actual
directories, not generic advice -- either standalone (`arklight new
--explain-architecture`, no project name needed) or right after a
`--template production` scaffold. `name` is now an optional positional
on `new` (only to allow the standalone form); omitting it without
`--explain-architecture` still errors exactly as before.

## [0.0434] - Unreleased

**`<html lang="...">` is no longer hardcoded to `"en"` with zero
override path.** Every page of every ARKlight site, regardless of
actual content language, rendered `lang="en"` -- wrong for any
non-English site, and consequential: `lang` drives screen-reader
pronunciation, browser auto-translate prompts, and search engines'
language signal, not just cosmetics. Added `WebsiteIR.lang` (default
`"en"`, unchanged), `Site(lang=...)` for a sitewide default, and a
per-page `Page(lang=...)` override read the same way `title`/
`favicon`/`description` already are -- a page-level override wins over
the sitewide default, which wins over the `"en"` stock default. Also
added `arklight build --lang TAG`, which overrides `Site(lang=...)`
(but not an explicit `Page(lang=...)`) without a site-file edit.
Verified the emitted value is HTML-escaped (no injection risk from an
untrusted `lang` string).

**Button text color decoupled from accent, silently.** `button`'s
`color: #ffffff` was a literal, independent of `background:
var(--ark-accent)` -- harmless while the stock accent stayed a dark
indigo, but a real usability trap for any site now setting a *light*
accent (via the override paths added in 0.0432/0.0433): white text on
a light button background, unreadable, with no var to fix it through.
Added `--ark-button-text` (default `#ffffff`, unchanged) and
`Site(button_text=...)` / `arklight build --button-text VALUE`.

## [0.0433] - Unreleased

**`body`'s `font-family` is no longer unreachable.** Same bug class as
the container-width fix, just not caught in that pass: `body` read a
literal font stack directly (no `--ark-*` var at all), so there was no
way -- sitewide *or* per-instance -- for a site author to change the
font. Added `--ark-font-family` (universal `"*"` `@property` syntax,
since font stacks don't fit a typed CSS syntax component) and
`Site(font_family=...)` + `arklight build --font-family "..."`,
mirroring `max_width`/`bg`. Default unchanged from BASE_CSS's existing
system-font stack.

**PBKDF2 iterations raised from 200,000 to 600,000 (`ARKSEAL2`),
without breaking any bundle already sealed at the old count.**
`_PBKDF2_ITERATIONS` was a fixed module constant with no version
attached to it in the blob format -- bumping it in place would have
made `unseal()` silently derive the wrong key (and report a misleading
"wrong passphrase") for every `.ark` bundle sealed by an older
ARKlight release. Fixed by making the format self-describing about its
own iteration count instead of assuming one: `ARKSEAL2` embeds a
4-byte iteration count in passphrase mode; `unseal()` still recognizes
`ARKSEAL1` bundles and falls back to the old fixed 200,000 for them.
Every bundle sealed by every past release still opens unchanged; only
newly-sealed bundles get the stronger, current-OWASP-guidance count.
`arklight.packer.bundle`'s sealed-bundle detection (`was_sealed = ...`)
updated to recognize both magics (`SEALED_MAGICS`) instead of hardcoding
`ARKSEAL1`.

## [0.0432] - Unreleased

**`--max-width`/`--bg` CLI flags on `arklight build`.** The site-file
API (`Site(max_width=..., bg=...)`) already existed, but there was no
way to set either without editing the site file itself. `arklight
build site.py --max-width 90rem --bg "#0f0f1a"` now overrides those
design tokens at build time, taking precedence over whatever the site
file sets; leaving both flags off changes nothing. Threaded through
`compile_site_file()`/`build()` as an optional `css_var_overrides`
merge, layered *over* `site.css_var_overrides` rather than replacing
it.

**Layout-primitive tokens (`Stack`/`Cluster`/`Sidebar`/`Switcher`/
`Grid`/`Reel`) are now sitewide-configurable via `Site(...)`.**
Previously `--ark-stack-space`, `--ark-grid-min`,
`--ark-switcher-threshold`, `--ark-sidebar-width`,
`--ark-cluster-space`, `--ark-sidebar-space`, `--ark-switcher-space`,
`--ark-grid-space`, `--ark-center-gutter`, and `--ark-reel-space` each
had a `var(--ark-x, fallback)` at their point of use in `BASE_CSS`, so
a *per-instance* wrapper `style="--ark-grid-min: 20rem"` already
worked -- but there was no sitewide override path the way
`max_width`/`bg` have, a gap `design_tokens.py` flagged in its own
comments as "tracked as a follow-up." `Site(stack_space=..., grid_min=...,
switcher_threshold=..., sidebar_width=..., cluster_space=...,
sidebar_space=..., switcher_space=..., grid_space=..., center_gutter=...,
reel_space=...)` are now real constructor kwargs, all defaulting to
`None` (unset) -- an unconfigured site's rendered layout is unchanged,
byte-identical apart from these values now also being declared
explicitly at `:root` (needed for the `@property` typing and the
override path to work at all).

## [Unreleased]

**Stage 3 of the vdom staging: event modifiers.**
`Action.set("saved", True).debounce(300)` /
`Action.remove("items", 0).with_modifiers("prevent", "stop", "once")`
attach `prevent`/`stop`/`once`/`debounce:<ms>`/`throttle:<ms>` tokens
to an `ActionRef`, validated against a new closed `MODIFIER_REGISTRY`
(`arklight/ir/schema.py`) the same way `ACTION_REGISTRY` already is.
Compiles to a single `data-ark-modifiers="prevent,debounce:300"`
attribute (omitted when unused), read once per element by a new
`arkApplyModifiers` JS runtime wrapper that handles `stop`/`once`
short-circuiting and debounce/throttle timing around the existing
action dispatcher -- `prevent` was already honored unconditionally by
the click listener, so this stage mostly makes that intent explicit
and named. 17 new tests (`tests/test_event_modifiers.py`); no change
to `State`/`Bind`/existing `Action.*` behavior. Deliberately does not
route through Stage 1's vendored vdom -- this is a dispatch-timing
concern on the listener, not a DOM-diffing one.

**Documentation fix: the container-width bug fix itself was never
documented.** `arklight/api.py`'s own `Site.__init__` comment has
pointed at `docs/CONTAINER-WIDTH-BUG.md` since the fix landed in
`7aabfb5` ("CSS Backend is being refactored for predictability. Stage
1 done.") -- but that file never existed in this repo (only in a
downstream site's own repo, which independently diagnosed the same
bug from the outside). Added `docs/CONTAINER-WIDTH-BUG.md` here,
documented `Site(max_width=..., bg=...)` in `README.md`'s "Styling
components" section (previously undocumented anywhere despite being
live, working public API), and this entry. No code change -- the fix
itself already shipped; only the paper trail was missing.

**Stage 2 of the vdom staging: reactive class binding.**
`Bind.when("active", "is-active")` + `bind_class=` toggles a CSS class
as a `State(...)` value's truthiness changes (`ClassBindSpec`,
validated the same way `Action.*`/`Bind` already are). HTML backend
pre-fills the class from the initial state value; the JS runtime uses
a small direct `classList.toggle` pass (`renderClassBindings`) rather
than routing through Stage 1's vdom `patch()`, since the vendored bare
core has no class module and doing so would remount the element on
every toggle. 10 new tests (`tests/test_class_binding.py`); no
page-facing change to `State`/`Bind`/`Action.*`.

**Stage 1 of a staged reactive-core expansion: vendored vdom core.**
Pages that declare `State(...)` now re-render their `data-ark-bind`
elements through a vendored [snabbdom](https://github.com/snabbdom/snabbdom)
core (`init` + `h` + `vnode` + `htmlDomApi`, MIT licensed, no optional
modules -- see `arklight/backend/js/vdom.py`) instead of a raw
`el.textContent = ...` assignment. This is a mechanism swap only: no
new page-facing Python API, no change to `State`/`Bind`/`Action.*`
behavior, and pages without `State(...)` still ship none of it (only
ship what's used, unchanged). It exists to give later stages (list
rendering, conditional show/hide, attribute/class binding, and a
planned "Stage 8": `localStorage` persistence for `State`) a real
diff/patch algorithm to build on rather than each hand-rolling one.

**v0.048** (CSS `@media` queries + structured `<head>`/`<header>`
extension) has since shipped in full -- see the `[0.048]` entry above.
Next up is **v0.054** (renumbered from v0.044: JS backend capability
expansion -- computed/derived state, watch effects, two-way input
binding, per-item list rendering, conditional show/hide, event
modifiers, reactive class binding) -- see the "Planned" section of
[`PROGRESS.md`](./PROGRESS.md) and
[`docs/Foundational/DESIGN-NOTES.md`](./docs/Foundational/DESIGN-NOTES.md) ("v0.044: JS backend
capability expansion -- reactive core parity with Vue 3") for the
design.

## [0.0431] -- Emergency patch: unrouted-reference build warning

Out-of-band alpha maintenance release (numbered inside the v0.043 ->
v0.0438 gap, ahead of v0.044). Addresses one finding from an external
HTML-backend audit: `ROUTE_AWARE_ATTRS` covers only `href`/`src`, while
`Picture`/`PictureSource`'s `srcset`, `Video`'s `poster`, and `Form`'s
`action`/`formaction` are all emitted verbatim -- a route-shaped value
(`/assets/preview.png`) silently 404s once the site is deployed outside
the domain root.

**Detection only, not a fix yet.** `arklight.backend.html.render` now
warns at build time (`warnings.warn`, build still succeeds) whenever
one of those four attributes is given a route-shaped value, naming the
node/attribute/value and pointing at this patch series. Real
route-rewriting for these four attributes -- splitting/rejoining
`srcset`'s comma-separated list, and deciding whether `action`/
`formaction` should warn-and-skip instead of rewrite -- is tracked as a
follow-up, not shipped here.

Also confirmed **not** an issue on this branch: the audit's other
finding, an unrecognized `on_click` value silently no-opping, doesn't
reproduce -- `arklight/ir/validate.py` already hard-errors on any
`on_click` outside `KNOWN_BEHAVIORS`.

Three further findings (`<html lang="en">` hardcoded, `--ark-max-width`
unreachable from any prop, untyped `--ark-*` custom properties) were
open at the time but aren't build-time-detectable -- no prop existed
yet for a site author to trigger them. `--ark-max-width` was fixed by
the CSS backend refactor (`docs/CONTAINER-WIDTH-BUG.md`); `<html
lang="en">` was fixed above, in `[0.0434]`. Untyped `--ark-*` custom
properties remains open. These were tracked as "against the CSS/HTML
backend refactor in `docs/DESIGN-NOTES.md`" -- that section was never
written; the design doc that promise pointed to is now
`docs/HTML-BACKEND-REFACTOR.md` (HTML side) and
`docs/CSS-BACKEND-REFACTOR.md` (CSS side, already landed).

`0.043` -> `0.0431` version bump only; no page-facing API change;
existing builds produce byte-for-byte identical HTML/CSS/JS. See
[`PROGRESS.md`](./PROGRESS.md) ("v0.0431 -- Emergency patch") for the
full narrative.

## [0.043] -- Optional `<head>` metadata props + backend `postprocess` hook

Two independent, additive changes: five new optional `Page(...)` props
for common `<head>` metadata (filling part of the gap ahead of
v0.048's full `<head>`/`<header>` extension), and a new extension
point on `Backend` for adding a backend that depends on another
backend's already-rendered output, without editing that backend's
source.

### Added

- **`description`, `favicon`, `og_title`, `og_description`,
  `og_image`** (`arklight/backend/html/render.py`) -- optional
  `Page(...)` props rendering `<meta name="description">`, `<link
  rel="icon">`, and Open Graph `<meta property="og:*">` tags,
  following the same `page.root.props.get(...)` pattern `title`
  already used. All five are additive: a page that sets none of them
  renders byte-for-byte identically to before this change. Open Graph
  tags specifically are opt-in -- they only render once `description`
  or any `og_*` prop is supplied, so `title`-only pages don't get an
  unsolicited `og:title`. `favicon`/`og_image` resolve to a relative
  path the same way the stylesheet/script links already do.
- **`Backend.postprocess(output_files) -> output_files`**
  (`arklight/backend/base.py`, `arklight/compiler/pipeline.py`) --
  optional second pass, called once per backend (same order as
  `backends=[...]`) after every backend's `render()` has finished,
  over the *combined* `{path: contents}` dict from all of them.
  Default implementation is a no-op identity, so `HTMLBackend`,
  `CSSBackend`, and `JSBackend` needed no changes. Lets a new backend
  (analytics injection, build stamps, sitemap generation, ...) see and
  transform what other backends already produced without editing
  their source -- see `tests/test_pipeline_end_to_end.py` for a
  worked example.

## [0.042] -- Extra CSS features: custom classes, `arklight search`, `arklight --help`

Goal was cutting boilerplate/nesting in the styling API and closing
two long-open CLI discoverability gaps -- not new `@media`/`<head>`
capability (that's still v0.048). Full design context in
[`docs/Foundational/DESIGN-NOTES.md`](./docs/Foundational/DESIGN-NOTES.md) ("v0.042: extra CSS
features").

### Added

- **`Site.style(name, rules)`** (`arklight/api.py`) -- registers a
  real, named, reusable CSS class from a plain `{css-property: value}`
  dict. `class_name="name"` anywhere in the site then picks up the
  rules from the generated stylesheet, instead of repeating a
  `style={...}` dict on every node that needs it. Validated at
  registration time: `name` must be a safe, single CSS class
  identifier (letters/digits/hyphens/underscores, no leading digit);
  `rules` must be a non-empty dict of non-empty string
  properties/values. Deliberately **not** a raw CSS string -- same
  "no arbitrary CSS/HTML strings" boundary the rest of the project
  holds. Calling `site.style()` again with a name already registered
  overwrites it (last call wins).
- **`WebsiteIR.custom_styles`** (`arklight/ir/build.py`) -- threads
  `Site.custom_styles` through `build_website_ir()` (new optional
  keyword arg, backward-compatible) so `CSSBackend` can see what a
  site registered.
- **`CSSBackend`** (`arklight/backend/css/render.py`) now renders
  `ir.custom_styles` as real `.name { prop: value; }` blocks, sorted
  by class name (and by property within each class) for deterministic
  output, appended after the fixed `BASE_CSS` stylesheet so custom
  classes can override base rules by cascade order.
- **`arklight search <name>`** (`arklight/cli/search.py`,
  `arklight/cli/main.py`) -- read-only schema lookup against
  `arklight.ir.schema.SCHEMA`: required props, whether children are
  allowed, and whether the component is a `Bind(...)`-able target
  (i.e. `text_only_children`). Exact match (case-insensitive) wins
  outright; otherwise falls back to typo-tolerant "did you mean"
  suggestions via stdlib `difflib` + a camelCase-aware tokenizer --
  no external dependency, no new data format, no compiler-pipeline
  changes.
- **`arklight --help` / bare `arklight`** (`arklight/cli/main.py`) --
  `--help` already worked via argparse's built-in flag (every
  subcommand already carried a `help=` description), but running
  `arklight` with **no** subcommand used to print argparse's terser
  "error: the following arguments are required: command" instead of
  the same usage/help text. Subparsers are no longer `required=True`;
  a bare `arklight` now prints full help and exits `0`.

### Notes

- Custom classes and the fixed `BASE_CSS` utility classes (`.nav`,
  `.card`, `.stack`, ...) share the same `class_name=` mechanism --
  nothing new needed on the HTML backend side, since `class_name` was
  already a generic prop-to-`class`-attribute passthrough.
  `arklight search` does not currently search `BASE_CSS`'s utility
  class names, only component schema -- noted as a possible follow-up,
  not scoped for this pass.
- Test coverage: `tests/test_api_style.py` (new),
  `tests/test_css_backend.py` (extended),
  `tests/test_pipeline_end_to_end.py` (extended),
  `tests/test_search.py` (new), `tests/test_cli.py` (extended) --
  251 tests passing.

**Fixed a real version-drift bug from the published PyPI release, and
bumped to `0.42.0`.** The shipped `0.37`/`0.038`-internal release had
`pyproject.toml`'s version and `arklight.__version__` disagreeing --
two hardcoded copies of the same number, nothing keeping them in
sync, and they'd drifted apart by release time. `arklight/__init__.py`
no longer hardcodes a second copy: `__version__` is now read back
from the installed package's own metadata
(`importlib.metadata.version("arklight")`), so `pyproject.toml` is the
single source of truth and there's no second place for it to drift
from. Also moved off the old two/three-digit "milestone number as a
decimal fraction" scheme (`0.037`, `0.041`, a future `0.100`) to a
proper three-part `MAJOR.MINOR.PATCH` string -- the old scheme is a
real PEP 440 hazard: `0.100` normalizes (trailing zeros stripped) to
`0.1`, which would have sorted *below* `0.048`'s `0.48` the moment a
`v0.100`-named milestone shipped. `0.100.0` compares each dotted
component as an integer instead, so this can't happen again. Staying
under `1.0` intentionally -- `1.0` is reserved for when ARKlight
actually reaches that milestone, not a general "looks more mature"
bump. New regression test (`tests/test_version.py`) locks
`arklight.__version__` to installed package metadata so this can't
silently drift apart again.

Next up is **v0.048** (CSS `@media` queries + structured
`<head>`/`<header>` extension) -- see the "Planned" section of
[`PROGRESS.md`](./PROGRESS.md) and [`docs/Foundational/DESIGN-NOTES.md`](./docs/Foundational/DESIGN-NOTES.md)
("v0.048: CSS media queries + `<head>` extension") for the design.
Custom CSS class authoring and an `arklight --search <name>` schema
lookup are sketched but not yet scheduled to a version -- also in
`PROGRESS.md`.

## [0.041] -- CLI, pipeline & JS runtime hardening + stateful JS vocabulary addenda

Four change sets that landed together and are released as one version.
Each keeps its own "Added"/"Notes" detail below; this line is only
here so the version-history reader doesn't have to guess why 0.041
covers four unrelated-sounding headings.

## [0.041] -- JS runtime error-handling hardening

Follow-up to "CLI & pipeline error-handling hardening" directly below
-- that pass covered the Python/CLI side; this covers the generated
client-side `arklight.js` runtime, which previously had **zero**
`try`/`catch` anywhere in it (confirmed by reading
`arklight/backend/js/render.py` and every behavior/action fragment
directly).

### Added

- **`arkNotify(message)`** (`arklight/backend/js/render.py`) -- a
  small, self-contained, inline-styled on-page notice, shipped only
  when a site actually uses a behavior or declares `State(...)` (same
  "only ship what's used" discipline as everything else in this
  runtime). Gives end users a visible signal when the runtime hits a
  case its closed vocabulary didn't anticipate, instead of a
  console-only error nobody but a developer would ever see. Wrapped in
  its own `try`/`catch` so the notifier itself can never throw.
- **`try`/`catch` around `initState()`'s `JSON.parse`** -- a malformed
  `data-ark-state` attribute previously threw inside the
  `DOMContentLoaded` handler and silently aborted `wireActions()` (and
  anything scheduled after it) for the entire page. Now caught,
  notified via `arkNotify`, and the page degrades to non-reactive
  instead of partially broken with no explanation.
- **`try`/`catch` around each element's setup *and* click dispatch**
  in both `wireActions()` and `wireBehaviors()` -- previously a single
  malformed `data-ark-action-args` attribute (or a behavior/action
  throwing at click time) could abort the `forEach` loop for every
  *other* element on the page, not just the one at fault. Each element
  now fails independently.
- **`.catch()` on the `copy` behavior's clipboard promise**
  (`arklight/backend/js/behaviors/copy.py`) -- `navigator.clipboard
  .writeText(...).then(...)` had no rejection handler, notable because
  `arklight build --open` opens sites as `file://` URLs by default,
  exactly the context where clipboard permissions are likeliest to be
  denied. A copy failure now notifies the user instead of silently
  doing nothing when clicked.
- `tests/test_js_error_handling.py` -- 8 new tests (212 total, all
  passing) covering `arkNotify` shipping conditions, the new guard
  structure in `initState`/`wireActions`/`wireBehaviors`, the clipboard
  `.catch()`, and re-confirming no `eval`/`new Function` was
  introduced.

### Notes

- No changes to `normalize.py`/`validate.py`/`build.py`/the IR --
  this is purely a `JSBackend` generation change, same class of
  change as every behavior/action addendum before it.
- Deliberately did not add error handling to `renderBindings()` or
  `highlightActiveNavLink()` -- neither has a plausible runtime
  failure mode given their inputs (`store.get(key)` returning
  `undefined` just renders as the text "undefined", not a throw; the
  nav-highlight loop only ever touches `<a>` elements' own `.href`).

## [0.041] -- CLI & pipeline error-handling hardening

A UX audit of the CLI's error handling (comparing it against how the
generated client-side JS runtime handles -- or doesn't handle --
failures) found that every subcommand only ever caught its *own*
typed error (`CompileError`/`PackError`/`PWAError`/`ScaffoldError`).
Anything outside those specific, anticipated failure modes propagated
as a raw Python traceback, contradicting the CLI's own stated design
goal ("error messages that point at exactly what went wrong... rather
than a raw traceback" -- `arklight/cli/main.py` module docstring).

### Added

- **Top-level catch-all in `main()`** (`arklight/cli/main.py`) --
  wraps subcommand dispatch. Anything not already handled by a
  subcommand's own typed `except` clause now prints a clear,
  clearly-labeled "outside ARKlight's known, handled failure modes"
  message (which command was running, the underlying exception type
  and message, an explicit note that this isn't a documented/
  recommended failure path) instead of a raw traceback, and returns
  exit code `1` like every other failure mode. Points at
  https://github.com/Rae-ARK/ARKlight/issues for reporting.
- **`OSError` guards around `build()`'s file-write loop and asset
  copy** (`arklight/compiler/pipeline.py`) -- previously neither step
  was guarded against filesystem failures (permissions, disk full, a
  network drive disconnecting mid-write), so a failure there escaped
  as a raw `OSError` instead of the `CompileError` every other pipeline
  stage raises. Both paths now report exactly how much of the build
  completed before the failure (e.g. "3/6 file(s) written before the
  failure"), so a partially-written output directory is never
  mistaken for a clean one.
- **Runtime warning for `--passphrase` on the command line**
  (`_cmd_pack`) -- previously this risk (shell history / process-
  listing exposure) was only documented in `--help` text, easy to
  never see. Now prints at the moment the flag is actually used.

### Fixed

- **Removed a duplicate `_cmd_pwa` definition** in `arklight/cli/main.py`
  -- found while adding the catch-all above. Two identical copies of
  the function existed; the second silently shadowed the first at
  import time. Harmless today since the bodies matched exactly, but
  exactly the kind of latent bug the new catch-all exists to guard
  against if they'd ever drifted apart.
- **`pyproject.toml` / `arklight/__init__.py` version mismatch**
  (`0.1.0` vs. `0.038`) -- a second recurrence of the same class of
  drift already fixed once during the "v0.003 addendum" pass (see
  below); `pyproject.toml` now correctly reads `0.038`. This is a
  distinct issue from the previously-documented `arklight --version`
  vs. `pip show arklight` mismatch, which is about the *published*
  PyPI package's own reported version, not this repo's internal
  build-metadata sync.

### Notes

- Scope was deliberately kept to the CLI's own dispatch/build path --
  the generated client-side `arklight.js` runtime has an analogous
  gap (no `try`/`catch` anywhere in `arklight/backend/js/render.py`'s
  output, an unhandled clipboard-promise rejection in the `copy`
  behavior, one malformed `data-ark-action-args` attribute able to
  abort `wireActions()` for every other element on the page) --
  tracked as separate, follow-up work, not addressed in this pass.
  **Update:** this follow-up is now done -- see "JS runtime
  error-handling hardening" above.

## [0.041] -- Stateful JS vocabulary addendum II

Full writeup in `docs/DESIGN-NOTES.md` ("v0.0035: stateful-JS
vocabulary addendum II"). Second growth pass on `ACTION_REGISTRY`,
same "additive data" discipline as addendum I directly below -- this
batch is the first to assume a **list-valued** `State(...)` rather
than a scalar one.

### Added

- `Action.append(name, value)` -- appends `value` to a list-valued
  `State(...)`. New `arklight/backend/js/actions/append.py` fragment
  and `ACTION_REGISTRY["append"]` entry.
- `Action.remove(name, index)` -- removes the element at `index` from
  a list-valued `State(...)`. Index-based on purpose (unambiguous,
  unlike a value-based removal, which would need an equality rule for
  objects). New `arklight/backend/js/actions/remove.py` fragment and
  `ACTION_REGISTRY["remove"]` entry.
- `tests/test_stateful_js_vocabulary_addendum_2.py` -- 12 new tests
  (182 total).

### Notes

- No changes to `renderBindings`/`Bind` were needed: `el.textContent =
  store.get(key)` already renders a list via JS's own
  `Array.prototype.toString()` (comma-joined elements) -- enough for a
  simple tag list or count display. Per-item templating (a real
  `<li>` per item, with per-item remove buttons wired individually) is
  materially bigger scope -- would need the compiler to emit a
  template per list item and re-render *that*, not just re-run
  `renderBindings` -- and is deliberately left for a future version.

### Deliberately deferred to a future version

Still not an exhaustive vocabulary pass -- see `docs/DESIGN-NOTES.md`:

- Per-item list rendering/templating (see note above).
- Derived/computed state.
- `Action.set_from_input` / binding state to `input`/`change` events.
- Debounced/throttled actions.

## [0.041] -- Stateful JS vocabulary addendum I

Full writeup in `docs/DESIGN-NOTES.md` ("v0.0035: stateful-JS
vocabulary addendum"). Grows `ACTION_REGISTRY` (added in v0.0035) with
the two most commonly needed actions real usage hits right away,
following the same "additive data, not a compiler change" discipline
the v0.0035 registry refactor was built for.

### Added

- `Action.decrement(name, delta=1)` -- the `-1` counterpart to
  `Action.increment`. New `arklight/backend/js/actions/decrement.py`
  fragment and `ACTION_REGISTRY["decrement"]` entry.
- `Action.reset(name)` -- resets a state key to the value it was
  declared with in `State(...)`, without hardcoding that value again
  at the call site. Backed by a new `reset(key)` method on the
  reactive core's `createState` closure (reads its own captured
  `initial` snapshot), plus a new
  `arklight/backend/js/actions/reset.py` fragment and
  `ACTION_REGISTRY["reset"]` entry.
- `tests/test_stateful_js_vocabulary_addendum.py` -- 10 new tests
  (170 total).

### Deliberately deferred to a future version

Not an exhaustive vocabulary pass -- see `docs/DESIGN-NOTES.md` for
the reasoning behind leaving these out of this addendum:

- List actions (`Action.append` / `Action.remove`) -- addressed in
  addendum II directly above.
- Derived/computed state.
- `Action.set_from_input` / binding state to `input`/`change` events.
- Debounced/throttled actions.

## [0.037] -- Sealed ARK Bundles

Full writeup in `docs/DESIGN-NOTES.md` ("v0.037: sealed bundles").

### Added

- `arklight.packer.seal` -- new stdlib-only (`hmac`/`hashlib`/
  `secrets`) sealing primitive: `seal(payload, *, passphrase=None)` /
  `unseal(blob, *, passphrase=None)`, an HMAC-SHA256 counter-mode
  stream cipher with an HMAC-SHA256 authentication tag
  (encrypt-then-MAC). `SealError` on missing/wrong passphrase or a
  failed integrity check.
- `arklight pack` now **seals the archive half by default**. Without
  `--passphrase`, a random embedded key travels with the bundle (blocks
  generic archive tools, not a secret from ARKlight itself -- see
  DESIGN-NOTES for the honest framing); with `--passphrase`, the key is
  derived via PBKDF2-HMAC-SHA256 and never stored, for real
  confidentiality.
- `--plain` flag on `arklight pack` -- opts back into the original v1
  plain-ZIP-tail behavior.
- `arklight unpack <bundle.ark> -o OUTPUT_DIR [--passphrase ...]` --
  new CLI subcommand and `arklight.packer.bundle.unpack()` Python API,
  reversing `pack()`. Auto-detects sealed vs. plain bundles.
- `arklight.packer.bundle.UnpackResult` -- `output_dir`,
  `extracted_paths`, `was_sealed`.
- `PackResult` gained `sealed` and `passphrase_protected` fields.
- `tests/test_seal.py` (new) and expanded `tests/test_pack.py` --
  round-trips for both key modes, tamper/wrong-passphrase rejection,
  `--plain` opt-out, CLI wiring for `pack`/`unpack`.

### Changed

- **`assets/` (and any other non-html/css/js file) is now carried into
  the archive**, closing the v1 scope gap `docs/DESIGN-NOTES.md`
  explicitly flagged as deferred. `PackResult.skipped_paths` is always
  empty now; kept on the dataclass for backward compatibility rather
  than removed.
- The archive is now built entirely in memory (`io.BytesIO`) before a
  single `write_bytes()` call, rather than writing prefix bytes to disk
  and appending to that same file handle -- needed so the sealing step
  has a complete in-memory ZIP blob to encrypt; produces byte-identical
  plain bundles to before.

## [0.036] -- ARK Bundle spec v1

Full writeup in `docs/DESIGN-NOTES.md` ("v0.036: ARK Bundle spec v1").

### Added

- `arklight pack <build-dir> -o site.ark` -- a new CLI subcommand
  (`arklight/packer/bundle.py`) that packages an existing
  `arklight build` output directory into a single `.ark` file: an
  HTML/ZIP polyglot. A fully self-contained, inlined rendering of the
  entry page is prepended before a standard ZIP archive of the
  original build output, so the same bytes are both a directly-
  renderable HTML document (double-click / open in a browser, no
  unzip step, no temp files, no local server) and a valid ZIP archive
  (any archive tool extracts the original build output untouched).
- `arklight.packer.bundle.pack(build_dir, output_path) -> PackResult`
  -- the underlying Python API, importable independently of the CLI.
  `PackResult` exposes `packed_paths` and `skipped_paths`.
- `arklight.packer.bundle.PackError` -- raised with a specific message
  when `build_dir` isn't an `arklight build` output directory (missing
  `index.html`/`styles.css`/`arklight.js`, or missing the expected
  `<link>`/`<script src>` tags to inline).

### Scope (v1)

- Only `.html`/`.css`/`.js` files are inlined/packed. Any other file in
  the build directory -- most notably an `assets/` folder with images,
  audio, video, or anything else -- is intentionally left out of the
  bundle and reported as skipped (`PackResult.skipped_paths`, printed
  by the CLI) rather than silently dropped. Asset carry-over is planned
  for a follow-up version, not included here.
- Packaging only, over already-built output: no changes to
  `normalize.py`/`validate.py`/`build.py`/the `Backend` interface/the
  IR. `arklight/packer/` only reads already-written build files and
  never imports the parser/ir/backend internals.
- stdlib `zipfile` turned out to handle writing entries after an
  arbitrary byte prefix correctly (`zipfile.ZipFile(handle, mode="a")`
  on a handle that already has the HTML prefix written to it computes
  every offset from the handle's current position) -- no manual ZIP
  header patching was needed, simplifying the original design's
  assumption on this point.

## [0.0035] -- Stateful JS

This entry documents what actually shipped in the commits titled "v0.0035
is done" -- it was missing from this file even though
`pyproject.toml`/`arklight/__init__.py` already read `0.0035` and the
README's "Status" section already described it. See
`docs/DESIGN-NOTES.md` ("v0.0035: stateful JS -- capability, not
vocabulary") for the full design rationale.

### Added

- `arklight.ir.schema.BEHAVIOR_REGISTRY: dict[str, BehaviorSpec]`,
  replacing the flat `KNOWN_BEHAVIORS` frozenset from v0.003 as the
  source of truth (`KNOWN_BEHAVIORS` is now a derived view over it, so
  Validation's existing check didn't need to change shape).
- `arklight/backend/js/behaviors/` -- `JSBackend`'s runtime is now
  assembled from small per-behavior JS fragments (`toggle.py`,
  `scroll_to.py`, `copy.py`, `dismiss.py`) instead of one hand-written
  string; only the fragments a given site's IR actually references are
  emitted.
- `arklight.ir.schema.ACTION_REGISTRY` and `arklight/backend/js/actions/`
  (`set.py`, `increment.py`, `toggle_bool.py`) -- the same registry
  pattern applied to a new closed *action* vocabulary for state
  mutation.
- New public API in `arklight.api`: `State(name, initial)` (page-scoped
  reactive state, stored on the IR's `Page` node), `Bind(name)`
  (references a declared `State(...)` from anywhere a literal prop
  value is accepted, e.g. `Text(Bind("count"))`), and
  `Action.set(name, value)` / `Action.increment(name, delta=1)` /
  `Action.toggle_bool(name)` (structured `ActionRef` objects for
  `on_click=` -- never an arbitrary JS/Python string).
- Validation: every `Bind(...)`/`Action.*(...)` must reference a
  `State(...)` actually declared on that page, or the build fails at
  compile time with a specific message.
- `JSBackend`: pages that declare `state` get one additional small
  fixed reactive core (a `createState` closure, a `data-ark-bind`
  re-render wiring pass, and an action dispatcher walking
  `ACTION_REGISTRY`) appended to the runtime. Pages with no
  `State(...)` get none of this. Still no `eval`, no `new Function`, no
  string ever executed as code.
- `tests/test_stateful_js.py` -- 14 new tests (130 total).

### Notes

- Explicit scope boundary honored: capability, not vocabulary -- no
  new named behaviors were added in this milestone, only the registry
  refactor plus the `State`/`Bind`/`Action` primitives.

## [0.003] -- JavaScript helpers (+ two vocabulary extension addenda)

### Addendum 2: even more vocabulary

Still not a version bump -- this stays v0.003, same as addendum 1
below. Extends the same `arklight.ir.schema.SCHEMA` dict with the
"long tail" of standard, production-grade static-site HTML that
addendum 1 left out: numbered/description lists, art-directed
responsive images, native form/progress widgets, a zero-JS dialog,
the rest of HTML's text-level semantics (bidi + ruby included), table
column grouping, video captions, image maps, iframes, and a
`<noscript>` fallback. Same guarantee as before: zero changes to
normalize.py, validate.py, or build.py -- every addition below is
data only, in `SCHEMA` (+ `TAG_MAP`/`PASSTHROUGH_ATTRS`/`VOID_TAGS` in
the HTML backend, + default CSS rules in the CSS backend).

#### Added

- **33 new built-in components:**
  - Lists: `OrderedList` (`<ol>`, with `start`/`reversed`) --
    genuinely missing before this: v0.003's first pass could only ever
    produce `<ul>` via `List`, with no numbered list at all.
    `DescriptionList`/`DescriptionTerm`/`DescriptionDetails`
    (`<dl>`/`<dt>`/`<dd>`) for key/value and glossary content (specs,
    FAQs, metadata blocks) a `<ul>` can't express semantically.
  - Responsive images: `Picture`/`PictureSource` (`<picture>` +
    `srcset`/`sizes`/`media` art-direction) -- the image half of
    "responsive design", which addendum 1's CSS-only intrinsic-layout
    utilities didn't touch at all. `PictureSource` is a distinct type
    from the existing `Source` (used by `Video`/`Audio`, which
    requires `src`) since a `<picture>`'s `<source>` takes `srcset`
    instead. Also added `loading`/`decoding` as generic passthrough
    attributes, so `Image(..., loading="lazy")` gets native
    lazy-loading with zero JS.
  - Native, zero-JS widgets: `Progress`, `Meter`, `Datalist`, `Output`
    -- progress bars, gauges, input autocomplete, and calculation
    output are all built into the browser already.
  - `Dialog` (`<dialog open>`): renders open with zero JS, and
    `Form(method="dialog")` closes it natively (a real browser
    behavior, not a script) -- a static confirmation/FAQ modal needs
    no JS at all with this pairing. Opening it programmatically from
    an arbitrary trigger would need JS and stays out of scope, same as
    the rest of v0.003's "no arbitrary JS" boundary.
  - More text-level semantics: `Kbd`, `Samp`, `Var`, `Data`
    (`required_props=("value",)`), `Ins`, `Del`, `Q`, `Dfn`,
    `Address`, `Wbr`, plus bidirectional-text isolation/override
    (`Bdi`, `Bdo`) for real production i18n needs (mixed LTR/RTL
    content), and ruby annotations (`Ruby`/`Rt`/`Rp`) for East-Asian
    typography -- a genuine gap nothing above could express at all.
  - Table extras: `ColGroup`/`Col` for column-level styling without
    repeating a rule on every cell in the column.
  - Media: `Track` (`required_props=("src",)`) for caption/subtitle
    tracks -- accessibility, not decoration.
  - Image maps: `Map` (`required_props=("name",)`) / `Area` for
    multiple clickable regions on one image.
  - Embeds: `IFrame` (`required_props=("src",)`, no children) --
    arguably the single most common piece of "extra functionality" a
    static site reaches for that plain markup alone can't provide
    (embedding a map, a video host's player, or another site's
    widget), while staying pure declarative HTML.
  - `NoScript`: fallback content for the visitor with JavaScript
    disabled, pairing naturally with ARKlight's own small JS runtime
    -- anything gated behind `toggle`/`copy`/`dismiss` can have a
    `NoScript` sibling.
- New passthrough HTML attributes: `start`, `reversed` (`<ol>`);
  `srcset`, `sizes`, `media`, `loading`, `decoding` (responsive
  images); `low`, `high`, `optimum` (`<meter>`); `dir` (bidi text);
  `span` (`<colgroup>`/`<col>`); `kind`, `srclang`, `default`
  (`<track>`); `shape`, `coords` (`<area>`); `allow`,
  `allowfullscreen`, `sandbox`, `referrerpolicy` (`<iframe>`).
- Four new void tags in the HTML backend (`wbr`, `col`, `area`,
  `track`), alongside the existing `img`/`hr`/`br`/`input`/`source`.
- Default styling for every new tag in the generated stylesheet
  (`ol`/`dl`/`dt`/`dd`, `progress`/`meter`, `dialog`, `kbd`/`samp`/
  `var`, `dfn`, `address`, `ruby`/`rt`, `iframe`, `map`/`area`).
- 22 new tests (109 total) in `tests/test_vocabulary_addendum_2.py`
  covering every new component, its required props, and its rendered
  HTML.

#### Notes

- `DescriptionDetails`, `Ins`, `Del`, `Ruby`, and `Address` are real
  containers (like `TableCell`/`Blockquote`), not text-only -- a
  definition, an edit, a ruby base, or an address block routinely
  holds a `Link`/`Strong`/`Span`, not just a bare string. As with
  `Blockquote(Text("..."))` elsewhere, wrap plain text explicitly
  (e.g. `Ruby(Span("漢"), Rt("kan"))`) rather than relying on the
  auto-wrap, since a bare string in a non-text-only container becomes
  a block-level `Text`/`<p>` node, which isn't what an inline element
  like `<ruby>` wants.
- `DescriptionTerm`, `Progress`, `Meter`, `Output`, `Kbd`, `Samp`,
  `Var`, `Data`, `Q`, `Dfn`, `Bdi`, `Bdo`, `Rt`, `Rp` stay text-only,
  matching how `Item`/`Caption`/`Label` already work.
- Considered and deliberately left out: `<canvas>`/`<template>` (both
  are meaningless without JS driving them, which is out of scope for
  v0.003's closed-behavior model); a brand-new `<search>` landmark
  (too new/unsettled for a "production-grade" vocabulary claim); and
  `<object>`/`<embed>` (redundant with the new `IFrame` for the static
  use cases this project targets, with worse fallback-content
  ergonomics).

### Addendum 1: vocabulary extension

Not a version bump and not a new pipeline stage -- this stays v0.003.
Every addition below is data, not new compiler logic:
`arklight.ir.schema.SCHEMA` is the single source of truth every stage
(normalize/validate/build/backends) already reads from, so extending
it is how this addendum adds ~46 new component types without touching
normalize.py, validate.py, or build.py at all.

#### Added

- **46 new built-in components**, grouped the same way HTML groups
  them:
  - Semantic layout: `Header`, `Footer`, `Main`, `Nav`, `Section`,
    `Article`, `Aside`, `Figure`, `FigCaption`, `Details`, `Summary`
    (the last two are a *native* browser disclosure widget -- an
    accordion/expand-collapse that needs zero JS, not even the
    `toggle` behavior).
  - Text-level semantics: `Strong`, `Em`, `Small`, `Mark`, `Code`,
    `Cite`, `Abbr`, `Sub`, `Sup`, `Span`, `Time`, `HorizontalRule`,
    `LineBreak`, `Pre`, `Blockquote`.
  - Forms: `Form`, `Input`, `Textarea`, `Select`, `Option`,
    `OptGroup`, `Label`, `FieldSet`, `Legend`.
  - Tables: `Table`, `TableHead`, `TableBody`, `TableFoot`,
    `TableRow`, `TableHeaderCell`, `TableCell`, `Caption`.
  - Media: `Video`, `Audio`, `Source`.
- **Two new closed JS behaviors**, alongside `toggle`/`scroll-to`:
  `copy` (clipboard copy with button-text feedback) and `dismiss`
  (one-way hide, e.g. closing a banner/alert for good). Both are
  stateless in the same sense the original two are -- a pure reaction
  to one click, nothing retained in JS across events.
- **A generic `aria_*` prop convention** (`aria_label`, `aria_hidden`,
  `aria_expanded`, ...) mapping straight to the real `aria-*`
  attribute, plus `role`/`tabindex` and a `for_`/`html_for` alias for
  `<label for>` (since `for` is a Python keyword).
- **Intrinsic responsive layout utility classes** in the default
  stylesheet -- `.stack`, `.cluster`, `.sidebar`, `.switcher`, `.grid`,
  `.center`, `.reel`, `.fluid-heading` -- built entirely from flexbox/
  grid sizing keywords (`minmax`, `auto-fit`, `clamp`, `flex-basis`
  math), with **no `@media`/`@container` query anywhere**, addressing
  the structural ceiling recorded in `docs/DESIGN-NOTES.md`: `Page`
  still has no `<head>` hook for a breakpoint-based rule, so
  responsiveness has to come from the browser reflowing content from
  available width alone.
- Default styling for every new tag (forms, tables, `<details>`,
  `<code>`/`<pre>`, media, etc.) in the generated stylesheet, plus an
  `.alert` utility that pairs with the new `dismiss` behavior.
- 34 new tests (87 total) covering the new components, behaviors, and
  CSS utilities across `test_html_backend.py`, `test_css_backend.py`,
  `test_js_backend.py`, and `test_validate.py`.

#### Notes

- `TableHeaderCell`/`TableCell` are real containers (like `Container`),
  not text-only -- a real table cell routinely holds a `Link` or
  `Strong`, not just plain text. This means a bare string child gets
  wrapped in a `Text` node the same way it would inside a `Container`
  (consistent with existing normalization behavior, not new).
  `FigCaption`, `Summary`, `Legend`, `Caption`, `Label`, `Option`,
  `Textarea` stay text-only, matching how `Heading`/`Text`/`Button`
  already work.
- `pyproject.toml`'s version was still `0.001` while
  `arklight/__init__.py` said `0.003` -- both now correctly read
  `0.003`.

### Added

- `JSBackend` (`arklight.backend.js`) generating a static
  `arklight.js`: a fixed, closed vocabulary of client-side behaviors
  (`toggle`, `scroll-to`) plus automatic current-page nav-link
  highlighting. No arbitrary JavaScript is ever accepted from user
  code.
- `on_click` / `behavior_target` / `toggle_class` props on any
  component, validated against `arklight.ir.schema.KNOWN_BEHAVIORS` at
  build time and rendered as `data-ark-*` attributes.
- `default_backends()` now returns `[HTMLBackend(), CSSBackend(),
  JSBackend()]`.
- `.nav a.is-active` and `.hidden` added to the default stylesheet.
- `docs/DESIGN-NOTES.md`: styling ceiling, audience positioning,
  Svelte-comparison, and Mitosis-reframe (state/event semantics as the
  real prerequisite for v0.100) writeups.
- 9 new tests (66 total): JS backend content, behavior validation, and
  HTML attribute/script-tag rendering. Also verified interactively with
  Playwright against a real headless browser (nav highlighting + toggle
  click), not just by inspecting generated HTML.
- Example site: home page gained a working "Show details" toggle using
  `on_click="toggle"`, with no hand-written JavaScript.

### Changed

- CLI/package version bumped to 0.003.

## [0.002] -- CSS

### Added

- `CSSBackend` (`arklight.backend.css`) generating a default
  `styles.css` (typography, spacing, buttons, links, `.nav`/`.card`/
  `.muted` utility classes) -- every generated site is styled with zero
  CSS written by hand.
- `arklight.compiler.pipeline.build()` now runs a list of backends by
  default (`default_backends() -> [HTMLBackend(), CSSBackend()]`) and
  merges their output; customizable via `build(..., backends=[...])`.
- `class_name` and `style` (dict) props on any component, rendered as
  the HTML `class` attribute and an inline `style` attribute
  respectively.
- CLI: `arklight build` now opens the built site in the default
  browser automatically (`--open`, the default) or can be disabled
  (`--no-open`).
- 15 new tests (57 total): CSS backend output, relative-link
  resolution, `class_name`/`style` rendering, stylesheet link
  correctness, CLI browser-open behavior.

### Fixed

- **Internal links (`Link(..., href="/about")`) now compile to real
  relative file paths** instead of root-absolute routes. Previously,
  opening `dist/index.html` directly (the normal "first setup"
  experience) sent `href="/about"` to the filesystem root instead of
  `dist/about.html` -- pages appeared linked in the Python source but
  the links didn't actually work once rendered. The HTML backend is
  now route-aware and rewrites internal hrefs based on each page's
  actual output location; external URLs, fragments, and `mailto:`/
  `tel:` links are left untouched.
- The bundled example site now actually links Home and About to each
  other (via a shared `nav()` helper function) and uses the new
  styling props, instead of looking unstyled.

## [0.001] -- Python → HTML

First working compiler pipeline: a Python site file compiles all the
way to static HTML files, matching the full pipeline described in
ARCHITECTURE.md.

### Added

- `ARKNode` ARK AST node type and `node()` component factory.
- Public API: `Site`, `Page`, `Heading`, `Text`, `Button`, `Container`,
  `Link`, `Image`, `List`, `Item`.
- Static Python AST discovery stage (`arklight.parser.discover`) using
  the stdlib `ast` module.
- Site-file loader (`arklight.parser.loader`) that executes a site file
  in isolation and returns the live `Site` object.
- Normalization stage: flattens nested list children, drops
  `None`/`False`, wraps bare strings as `Text` nodes where appropriate.
- Validation stage: schema-checked component types, required props,
  and text-only nesting rules, with precise error messages.
- Shared component schema (`arklight.ir.schema`) used by both
  normalization and validation.
- Website IR (`IRNode` / `IRPage` / `WebsiteIR`), kept structurally
  distinct from the ARK AST.
- Backend interface (`Backend.render(ir) -> {path: contents}`).
- HTML backend: component-to-tag mapping, heading levels, prop-to-HTML
  attribute mapping (including a `data-*` fallback for unknown props),
  HTML escaping, and route-to-file-path mapping.
- Compiler pipeline (`compile_site_file`, `build`) unifying every
  stage behind a single `CompileError` for any failure.
- CLI: `arklight build <entry.py> [-o OUTPUT_DIR]`, `arklight --version`.
- Example site (`examples/hello_site/site.py`) with two pages.
- 42 tests covering every stage in isolation and end-to-end.
- Packaging via `pyproject.toml` (`pip install -e .`).

### Fixed

- Normalization no longer double-wraps strings inside text-only
  components (e.g. `Heading("hi")` no longer became an invalid
  `Heading(Text("hi"))`).
- Errors raised inside a page function (e.g. referencing an undefined
  component) are now caught by the pipeline and surfaced as
  `CompileError`, not left to propagate as raw exceptions.
