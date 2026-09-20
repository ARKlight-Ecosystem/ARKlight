# ARKlight Alpha — Consolidated Issue Register

_Based on source behavior, generated output, hands-on testing, the external
Focus Board audit, native scaffolding, CLI behavior, and
documentation/source mismatches._

This register separates **actual defects** from **limitations, maturity
gaps, and documentation inconsistencies**. Otherwise "Python developers
cannot magically import the npm ecosystem" ends up filed as a bug, which
would be a rather exciting failure of taxonomy.

**The single most important distinction:** most of these are not evidence
that ARKlight's central idea is wrong. The genuinely dangerous ones are the
places where the implementation violates its own existing contract —
especially hydration, CSP integration, reproducibility, and dev-build
lifecycle. The rest are mostly the price of the chosen architecture: closed
vocabulary, compiler-first semantics, WebView native targets, constrained
runtime, and deliberate escape-hatch boundaries.

---

## Table of Contents

- [A. Confirmed functional bugs](#a-confirmed-functional-bugs)
- [B. Confirmed expressiveness gaps](#b-confirmed-expressiveness-gaps)
- [C. Runtime architecture limitations](#c-runtime-architecture-limitations)
- [D. Runtime dependency / output-size issues](#d-runtime-dependency--output-size-issues)
- [E. Reproducibility issues](#e-reproducibility-issues)
- [F. .arklight binary IR limitations](#f-arklight-binary-ir-limitations)
- [G. Packaging / native backend maturity](#g-packaging--native-backend-maturity)
- [H. Preamble/source-system transition issues](#h-preamblesource-system-transition-issues)
- [I. Component system issues](#i-component-system-issues)
- [J. Documentation and specification issues](#j-documentation-and-specification-issues)
- [K. Ecosystem limitations](#k-ecosystem-limitations)
- [L. Build/install/release maturity](#l-buildinstallrelease-maturity)
- [M. Testing / verification gaps](#m-testing--verification-gaps)
- [N. Live-development issues](#n-live-development-issues)
- [O. Persistence/hydration issues](#o-persistencehydration-issues)
- [P. Security model caveats](#p-security-model-caveats)
- [Q. Escape-hatch ecosystem issues](#q-escape-hatch-ecosystem-issues)
- [R. Compiler architecture maturity](#r-compiler-architecture-maturity)
- [S. Watch/reactivity edge cases](#s-watchreactivity-edge-cases)
- [T. Repeat scalability / correctness edge cases](#t-repeat-scalability--correctness-edge-cases)
- [U. Product-positioning / maturity issues](#u-product-positioning--maturity-issues)
- [V. Agent/AI-specific issues](#v-agentai-specific-issues)
- [The short version](#the-short-version)

---

## A. Confirmed functional bugs

### 1. `persist=True` + `Repeat` hydration is broken

The most concrete runtime bug reproduced. When a persisted collection is
restored before `Repeat` initializes:

- the store contains the persisted collection,
- the server-rendered DOM contains the compile-time initial collection,
- `Repeat` assumes those two are identical,
- adopt-only hydration walks only the common prefix,
- extra persisted items are never created,
- the `Repeat` is nevertheless marked initialized.

**Result:** persisted list state can exist correctly in the store while the
corresponding rows are missing from the DOM. The next genuine list mutation
causes normal patching and makes the UI catch up.

A second, separate issue: item keys are derived from `JSON.stringify(item)`,
so duplicate primitive values produce duplicate keys and identical items can
collide and under-render. That duplicate-key limitation was already
known/documented — the persistence hydration incompatibility is the newly
demonstrated defect.

**Status:** confirmed alpha bug.

### 2. Imported `@component` definitions break dev rebuilds

The development loop can hit `component already registered` when a
component lives in an imported module and the application is rebuilt.
`allow_redefine=True` works around it, but that treats the symptom — the
underlying problem is compiler/dev-loop lifecycle state surviving between
builds. Particularly awkward since the production scaffold encourages
component organization across modules.

**Status:** confirmed tooling bug.

### 3. PWA-generated inline scripts conflict with strict CSP

ARKlight's normal pages use:

```
script-src 'self'
trusted-types default
require-trusted-types-for 'script'
```

The `pwa` command injects inline JavaScript for service-worker
registration/install behavior, without adjusting CSP accordingly — so a
generated PWA can have a CSP that blocks scripts the PWA generator itself
inserted. Not "PWA doesn't work" — more precisely, PWA script injection and
the default strict-CSP policy are currently inconsistent. Potential fixes:
externalize those scripts, or deliberately adjust the generated CSP.

**Status:** confirmed cross-feature integration bug.

### 4. Server/runtime serialization mismatch: `0.0` vs `0`

A computed value can render server-side as `0.0` while the runtime
subsequently computes `0` — a tiny initial visual correction users can
observe. A correctness/consistency issue rather than a catastrophic
failure, but it shows the compiler's initial-value serialization and
runtime coercion/formatting don't share exactly the same representation
semantics.

**Status:** confirmed minor rendering mismatch.

### 5. Positional component errors leak raw Python `TypeError`

For a keyword-only component API, e.g. `Stat("a", "b")`, the error can be a
raw `takes 0 positional arguments` Python-level message instead of a
compiler-quality ARKlight diagnostic identifying the actual component API
violation. Validation quality is uneven depending on which boundary catches
the error first.

**Status:** addressed in `0.06506` -- a positional call now raises a
`ComponentError` naming the component, the keyword-only rule and the
declared props, with the call's `file:line`; see
[`COMPONENT-CALL-DIAGNOSTICS-PROPOSAL.md`](COMPONENT-CALL-DIAGNOSTICS-PROPOSAL.md).
(Originally: confirmed diagnostic-quality bug.)

### 6. `--near` behavior doesn't match its documented expectation

`arklight search --near NAME` was expected/documented to have meaningful
behavior when the named component isn't in the usage graph. In testing, an
unknown component silently fell back rather than producing the
documented/error behavior implied by the help text. Minor, but a genuine
documentation/behavior mismatch.

**Status:** confirmed minor CLI inconsistency.

---

## B. Confirmed expressiveness gaps

Not necessarily bugs — deliberate consequences of the current closed
vocabulary — but they materially constrain what applications can be
expressed.

### 7. No sanctioned live-input → action-value primitive

Probably the biggest architectural limitation discovered through actual
application work. `Action.append("tasks", "literal value")` takes a
compile-time literal. ARKlight can bind an input to state with
`bind_value`, but there's no sanctioned mechanism to say "take the current
value of this input/state and pass it as the argument to this action." So a
conventional `[type task here] [Add]` workflow isn't naturally expressible
— the Focus Board application had to use quick-add buttons instead. A
`raw_postprocess` workaround proved the browser *can* do it; the semantic
vocabulary simply doesn't currently provide the operation.
`Action.set_from_input` is explicitly deferred.

**Status:** addressed in `0.06503` -- `Action.set`/`Action.append` now accept
`Bind("name")` as their `value`; see
[`ACTION-VALUE-FROM-STATE-PROPOSAL.md`](ACTION-VALUE-FROM-STATE-PROPOSAL.md).
(Originally: deliberate current capability gap.)

### 8. No general-purpose arbitrary expression layer

The closed vocabulary intentionally does not permit arbitrary client-side
expressions. If the vocabulary doesn't contain the semantic operation you
need, you cannot simply write the operation — the fundamental tradeoff
behind #7 and several other limitations. Adding arbitrary expressions would
weaken one of ARKlight's central guarantees, so this can't simply be
"fixed" without changing the design.

**Status:** intentional architectural constraint.

### 9. Escape hatches sit outside compiler guarantees

`raw_postprocess`, imported CSS, media-query mechanisms, developer APIs,
etc. provide sensible escape routes — but once you leave the normal
semantic vocabulary, ARKlight cannot provide the same guarantees.
`raw_postprocess` can create arbitrary JavaScript, modify generated files,
introduce files not represented in normal semantic analysis, depend on
generated DOM details, and break if compiler output changes. The Focus
Board workaround exploited exactly this boundary.

**Status:** intentional pressure valve, with known safety/maintenance cost.

### 10. `raw_postprocess` artifacts aren't fully represented in provenance/SBOM

The normal compiler has knowledge about its generated artifacts and
dependencies; a raw postprocessor can create something like
`scripts/add-task.js` without that artifact necessarily appearing in the
same provenance model. Future SBOM/provenance work needs to distinguish
compiler-generated artifacts, vendored runtime dependencies, declared
library inputs, and developer-generated escape-hatch artifacts.

**Status:** architectural provenance gap.

### 11. `Repeat` has duplicate-key limitations

Using serialized item values as keys means `["Deploy", "Deploy"]` doesn't
have two independently identifiable items — the same value produces the
same key. Particularly relevant to list UIs.

**Status:** known/documented limitation.

---

## C. Runtime architecture limitations

### 12. State updates rescan bound DOM nodes

On state mutation, binding rendering uses `querySelectorAll("[data-ark-bind]")`
rather than maintaining direct references to every affected binding — cost
is approximately *(number of state mutations) × (number of bound nodes)*
rather than only the bindings actually affected. Reasonable for small
static/content-heavy sites and small interactive widgets; a scalability
concern for large SPA-shaped applications.

**Status:** architectural limitation.

### 13. No fine-grained dependency-to-DOM tracking

The compiler knows a lot statically, but the runtime doesn't maintain a
granular mapping of state → exact binding; rendering performs broader DOM
discovery instead. One reason the system suits its intended
small/static/reactive workload much better than very large client
applications.

**Status:** architectural limitation.

### 14. Snabbdom is used despite the architecture describing VDOM as a non-goal

Partly a documentation contradiction: the implementation uses vendored
Snabbdom for bound text updates, while other architecture docs describe
virtual DOM as a non-goal. More precisely: ARKlight does not maintain a
conventional application-wide VDOM/component tree — it uses Snabbdom as a
localized patching mechanism for particular bound nodes. Should be
documented consistently.

**Status:** documentation/terminology inconsistency, not necessarily a
runtime defect.

### 15. Class bindings had to bypass Snabbdom

Class updates use `classList.toggle(...)` instead of going through the same
vnode patch path, because changing the vnode selector/class could cause
Snabbdom's identity logic to treat the node as different and remount it,
potentially dropping event listeners. Sensible workaround, but it means the
runtime has multiple update mechanisms.

**Status:** intentional implementation workaround, worth documenting as an
invariant.

### 16. `Repeat` hydration relies on a strong server-DOM/store invariant

The existing adopt strategy assumes *server DOM == initial store state* at
hydration. Persistence violates that assumption. The deeper architectural
issue behind #1: ARKlight's hydration model currently has no general
reconciliation phase for state that can change before hydration completes.

**Status:** architectural weakness exposed by a confirmed bug.

---

## D. Runtime dependency / output-size issues

### 17. htmx is included at page level when state is present

The "only emit what you use" principle has an important exception: a
stateful page pulls in the vendored htmx runtime even if it doesn't
actually use an `hx-*` feature. In the Focus Board build, JS was roughly
89 KB uncompressed / 26 KB gzipped, and around 58% of the JS was htmx. The
claim should narrow from "only ship what's used" to something closer to
"fine-grained emission for ARKlight vocabulary, with some page-level
runtime dependencies."

**Status:** known optimization gap.

### 18. Runtime size is significant for very small applications

Not enormous by ordinary web standards, but for a tiny static/reactive
page, an ~89 KB uncompressed JS output where much of the payload is
framework/runtime machinery is proportionally substantial — notable given
ARKlight's selling point includes compiler-driven minimalism.

**Status:** optimization/messaging issue, not correctness bug.

---

## E. Reproducibility issues

### 19. Builds aren't currently byte-for-byte reproducible because of SBOM timestamping

The generated `sbom.txt` contains a timestamp, so two otherwise identical
builds can differ at the byte level — notable given ARKlight explicitly
values deterministic builds and has a binary IR/provenance direction. Fix
is conceptually simple: omit timestamps, normalize them, or make them
explicitly opt-in metadata rather than part of deterministic artifact
content.

**Status:** confirmed reproducibility defect.

### 20. SBOM exists, but provenance isn't yet deeply integrated into `.arklight`

The SBOM is real and shipped; the binary `.arklight` format doesn't yet
encode all of the provenance information you'd want for a genuinely
self-describing portable build artifact — especially relevant given the
future direction of semantic IR + IR version + provenance/SBOM.

**Status:** incomplete architectural integration.

---

## F. `.arklight` binary IR limitations

### 21. Current `.arklight` doesn't round-trip the whole `WebsiteIR`

The independently decoded format is real and substantial, but the current
binary representation doesn't capture every `WebsiteIR` feature. Known
omissions include `custom_styles`, `css_var_overrides`,
`experimental_usages`, raw postprocessors, and other non-core
metadata/features. `.arklight` currently represents a substantial portable
subset of the semantic model, not a complete serialization of everything
`WebsiteIR` can contain. If a pipeline reconstructs a build exclusively
from `.arklight`, those omitted semantics can be lost.

**Status:** confirmed format limitation.

### 22. `.arklight` format/version contract needs to become more explicit

The architecture already distinguishes the binary format from the compiler
version conceptually, but a real multi-implementation ecosystem needs
explicit independent contracts for: ARKlight language/source version,
ARKlight compiler version, `.arklight` IR format version, library/ACC
versions, and target/backend versions. Otherwise cross-version
interoperability eventually becomes archaeology with extra steps.

**Status:** maturity/design work.

### 23. Independent encoder/backend round-trip remains an unproven milestone

A Node decoder matching Python's decoder is strong evidence the format is
language-independent. The stronger test — independent encoder →
`.arklight` → ARKlight reader → backend → same output — hasn't yet been
established.

**Status:** validation gap, not a demonstrated bug.

---

## G. Packaging / native backend maturity

### 24. Android is scaffolded, not yet a complete demonstrated build pipeline

The generated Android project has a credible design: Kotlin/Gradle,
WebView, `WebViewAssetLoader`, stable HTTPS-style asset origin, deliberate
preservation of `localStorage`/persistence semantics. But local APK
compilation/install/release wasn't demonstrated (Android
SDK/toolchain/network environment unavailable), and the CLI itself
currently indicates build/install/release functionality isn't fully
implemented. Android backend exists as a meaningful scaffold, not yet a
fully demonstrated production pipeline.

**Status:** maturity gap.

### 25. Desktop backend is currently Linux-specific

Targets GTK3 + WebKit2GTK on Linux. The manually compiled project did
successfully build with `-Wall -Wextra` and launch — real, but deliberately
narrow.

**Status:** supported scope limitation.

### 26. Native targets remain web shells

Android and desktop do not produce a native widget/rendering abstraction
comparable to Flutter — they package the same web output inside Android
WebView / Linux WebKit. No demonstrated general-purpose native bridge for
camera, Bluetooth, sensors, or arbitrary native plugins. Some of this is
explicitly ruled out by design rather than merely unfinished.

**Status:** intentional architectural scope.

### 27. iOS isn't supported

Explicitly not a current target.

**Status:** deliberate scope exclusion.

### 28. Far-future platform proposals aren't evidence of implementation

KaiOS/Windows Phone and similar material exists as proposal/future
territory and shouldn't be conflated with the demonstrated web, desktop, or
Android scaffolding.

**Status:** documentation/roadmap distinction.

---

## H. Preamble/source-system transition issues

### 29. The old Python import-based vocabulary mechanism created namespace collision problems

The former `from arklight import *` approach let Python's namespace rules
participate in semantic vocabulary resolution, creating the possibility of
user definitions shadowing compiler vocabulary. The preamble system is
specifically intended to move this responsibility into ARKlight itself; the
collision issue was addressed around the preamble/import transition.

**Status:** largely addressed architectural issue, but transition risk
remains.

### 30. Preamble implementation introduces a second source-language layer

Once you have:

```
# include <stdlib.ARKlight>
# define foo -> bar
# use <something.ACC>
```

you effectively have Python syntax + ARKlight preamble syntax. The
directives being comments to Python is clever, but it means ARKlight must
maintain its own lexical/parser/validation semantics on top of Python — not
inherently bad, but another compiler surface needing diagnostics,
formatting, linting, versioning, and migration rules.

**Status:** architectural complexity introduced intentionally.

### 31. ARKfmt/ARKlinter don't yet eliminate migration complexity

The proposed formatter/linter gives ARKlight a strong future migration
mechanism (old source → ARKlinter → deprecated API detected → ARKfmt/fix →
canonical source), but that system isn't yet established infrastructure.
Increasingly important as preamble directives and vocabulary evolve toward
v1 and beyond.

**Status:** planned tooling gap.

---

## I. Component system issues

### 32. Component API diagnostics aren't consistently compiler-native

The raw positional `TypeError` (see #5) is the obvious example. More
generally, user-defined components introduce Python-level call semantics
into a compiler that otherwise wants semantic ARKlight diagnostics. The
compiler should ideally catch component misuse before Python's own runtime
does, wherever practical.

**Status:** partly addressed in `0.06506` -- the positional-call boundary
(#5) and the `props=`-vs-render-function-signature boundary now raise
`ComponentError` before Python's own `TypeError` can surface; see
[`COMPONENT-CALL-DIAGNOSTICS-PROPOSAL.md`](COMPONENT-CALL-DIAGNOSTICS-PROPOSAL.md).
Other boundaries (built-in components, errors raised inside a render
function's own body) are unchanged. (Originally: validation-boundary
weakness.)

### 33. Component state semantics and documentation have drifted

Earlier documentation described user-defined components as not owning
local state; current implementation/testing indicates user-defined
components *can* have local state. Docs and implementation haven't always
moved together on this point.

**Status:** documentation drift.

### 34. Component macro expansion makes debugging source-to-output relationships harder

The component disappears from generated output because it expands before
backend emission — one of the architectural benefits, but it also means
source component → macro expansion → normalized tree → output can make
source-level debugging more difficult unless diagnostics preserve source
provenance. Not currently a demonstrated failure, but a predictable
consequence of the architecture.

**Status:** architectural/tooling consideration.

---

## J. Documentation and specification issues

### 35. Documentation has accumulated contradictions during rapid alpha development

Examples encountered: VDOM described as a non-goal while Snabbdom is
actually used internally; component-state documentation lagging
implementation; `--near` behavior differing from documented expectations;
some claims about runtime/code generation being broader than what the
implementation strictly guarantees. These contradictions are actively being
corrected, but are still evidence the specification layer is moving
quickly.

**Status:** ongoing alpha documentation debt.

### 36. "Cannot run code it didn't generate anywhere in the pipeline" is too broad

Needs qualification — ARKlight absolutely executes Python authoring/build
code during compilation, and it has escape hatches. The stronger defensible
claim: *the generated application runtime is constrained to
compiler-generated behavior and the closed runtime vocabulary, except where
explicitly leaving that contract through developer/experimental
mechanisms.* Much harder to misinterpret.

**Status:** specification wording issue.

### 37. "Compile away the runtime" is also too strong if used literally

ARKlight still has runtime machinery: state storage, event handling, URL
synchronization, persistence, binding interpretation, Snabbdom patching,
htmx in relevant pages, etc. The accurate claim: *compile as much semantics
as possible, retaining runtime machinery only for behavior that genuinely
depends on runtime information.*

**Status:** terminology/pitch precision issue.

### 38. "Only ship what's used" needs qualification

As the Focus Board measurement demonstrated, htmx can be shipped merely
because the page is stateful. Directionally true for the semantic
vocabulary, not literally true for every generated dependency.

**Status:** documentation/pitch precision issue.

### 39. Alpha version churn makes external evaluation harder

The project moves quickly through versions — normal for an alpha, but
review at `v0.064x` can become stale surprisingly quickly. Not inherently a
quality defect, especially since the project explicitly separates alpha
progress from v1 stability.

**Status:** alpha maturity characteristic.

---

## K. Ecosystem limitations

### 40. Closed vocabulary inherently limits access to the existing web ecosystem

Not a bug — the central cost of the architecture. A normal JS developer can
install charts, editors, maps, payment SDKs, auth libraries, accessibility
packages, data-grid components, animation systems, etc. ARKlight cannot
simply consume arbitrary npm packages as native semantic vocabulary. ACC is
intended to address this through curated ARKlight Component Collections,
but: **ACC is an ecosystem mechanism, not yet a mature ecosystem.**

**Status:** deliberate architectural tradeoff + ecosystem maturity gap.

### 41. ACC adoption is unproven

For the closed-vocabulary model to scale beyond a solo compiler, the
ecosystem needs people other than the maintainer producing and maintaining
vocabulary. Until that happens, the closed vocabulary remains mostly
compiler-defined capability rather than a large community-maintained
capability ecosystem.

**Status:** adoption/maturity gap.

### 42. Zero independent adoption signal

The project has been evaluated externally, but meaningful independent
production adoption hasn't been established. Matters because a compiler
architecture can look coherent under its creator's workload while still
having undocumented assumptions another developer immediately hits.

**Status:** ecosystem validation gap.

---

## L. Build/install/release maturity

### 43. PyPI/package availability has lagged the repository

The Focus Board evaluation found the tested alpha version wasn't available
from PyPI and had to be pinned to a specific Git commit — survivable during
alpha development, but raises installation friction and reproducibility
concerns for outsiders.

**Status:** alpha distribution limitation.

### 44. Source builds can be gated by license/environment configuration

The build backend can require a license environment variable before a
source build proceeds. Not necessarily wrong, but creates a non-obvious
failure mode: the dependency lock can be perfectly valid and
`uv sync --frozen` can still fail at the package build step until the
required license configuration exists.

**Status:** intentional gate, but onboarding friction.

### 45. Native release workflows are behind the scaffolding

There's a distinction between *generate project* and *build/install/release
artifact*. Desktop has crossed further into demonstrated implementation
through manual compilation and launch; Android remains more clearly on the
scaffold side.

**Status:** roadmap maturity gap.

---

## M. Testing / verification gaps

### 46. Full test suite hasn't been independently exercised as part of the external evaluation

The external hands-on testing didn't run the complete ~1,400-test suite —
"the test suite exists" shouldn't be treated as equivalent to "the whole
suite independently passed during evaluation."

**Status:** verification scope limitation.

### 47. Real-browser validation was incomplete

A lot of runtime behavior was tested through jsdom — valuable, but not a
real browser. Doesn't fully exercise browser CSP enforcement, Trusted Types
enforcement, actual service-worker behavior, WebView quirks, browser
rendering, real storage/origin behavior, or actual browser event timing.
The PWA/CSP problem (#3) is a particularly good example of why this
matters.

**Status:** verification gap.

### 48. Native backend testing is uneven

Desktop received an actual local compilation/launch test; Android did not
receive an equivalent APK build/install test. Native confidence is
asymmetric.

**Status:** verification gap.

---

## N. Live-development issues

### 49. Build lifecycle state needs stronger isolation

The imported-component rebuild problem (#2) is one manifestation. More
broadly, any global registries or mutable compiler state that survive a
build can cause unexpected collisions between build 1 and build 2. The
compiler should ideally behave as a fresh semantic compilation for every
build, unless state persistence is explicitly part of the design.

**Status:** architectural/tooling hardening area.

---

## O. Persistence/hydration issues

### 50. Persistence restoration happens at a stage that can invalidate server-rendered assumptions

The deeper version of #1. Rough sequence: compile-time initial value →
server-rendered DOM → persistence restoration → runtime state
initialization → `Repeat` adoption. That ordering means persistence can
modify state after the DOM was constructed but before components that
assume DOM/store equality have reconciled. A robust hydration model needs
to explicitly account for this.

**Status:** confirmed architectural weakness.

### 51. Persistence can produce startup visual corrections

The `0.0` → `0` mismatch (#4) is one example. More generally, persisted
state can differ from compile-time state, meaning the initial HTML is
necessarily a fallback representation before client restoration —
flash-of-initial-state behavior is possible.

**Status:** architectural behavior that needs careful handling, not
inherently a bug.

---

## P. Security model caveats

### 52. Normal generated runtime has strong constraints, but escape hatches weaken the guarantee

The normal closed vocabulary is deliberately constrained, but developer
APIs and raw postprocessing allow arbitrary web code into the output.
Security claims need to distinguish the normal ARKlight compilation
contract from "developer explicitly exited the contract." Experimental
warnings help communicate this, but the distinction needs to stay explicit
in documentation.

**Status:** intentional security boundary.

### 53. PWA CSP compatibility is currently the most concrete security-model integration problem

Worth repeating separately: CSP is one of ARKlight's stronger selling
points, and strict CSP + Trusted Types is genuinely interesting — but if an
officially generated feature emits inline scripts the official default
policy blocks, the security model and feature generator aren't fully
integrated.

**Status:** confirmed integration defect.

---

## Q. Escape-hatch ecosystem issues

### 54. Developer APIs are powerful enough to undermine semantic portability

A developer API targeting HTML/CSS/vanilla JS is intentionally useful as an
adoption bridge, but the moment developers rely on it heavily, they can
recreate the very target-specific/application-specific complexity
ARKlight's semantic layer was designed to constrain. Not necessarily a
flaw — the unavoidable pressure boundary.

**Status:** intentional tradeoff.

### 55. Raw postprocessing has no semantic dependency analysis

If a postprocessor reads or modifies generated artifacts, the compiler has
no semantic understanding of what that code does — optimization is
limited, provenance is weaker, static guarantees stop at the boundary, and
output assumptions can become fragile across compiler versions.

**Status:** intentional limitation.

---

## R. Compiler architecture maturity

### 56. The compiler executes authoring Python, so the strongest "static" claims need careful wording

ARKlight's generated application can be heavily constrained, but the build
pipeline itself is not a pure declarative interpreter — it statically
discovers source structures, loads/executes the Python module, constructs
the semantic tree, normalizes/validates it, and emits output. Better
described as "Python-authored compiler/metaprogramming" than "Python source
is never executed." Matters especially for security and reproducibility
claims.

**Status:** architectural clarification.

### 57. Static discoverability and actual build execution are separate phases

`discover.py` can identify `Site()` and `@site.page` without executing the
module; `loader.py` actually executes it. Good design, but diagnostics and
tooling need to remain clear about which phase failed — import-time Python
exceptions are not compiler semantic errors.

**Status:** intentional architecture, diagnostic boundary to maintain.

---

## S. Watch/reactivity edge cases

### 58. Watcher cycles are a potential semantic hazard

Because watchers can react to state changes and state changes can trigger
other watchers, cycles are possible in principle. The closed vocabulary
gives ARKlight enough structure that it could potentially detect many such
cycles statically, but it hasn't been established that all relevant cycles
are detected and diagnosed in the examined implementation.

**Status:** verification/design gap.

---

## T. Repeat scalability / correctness edge cases

### 59. `Repeat`'s current identity model is weaker than general keyed reconciliation

Because item identity is derived from serialized values, there's no
explicit user-defined stable key concept equivalent to `key=item.id`. This
limits reliable list reconciliation for mutable/duplicate data.

**Status:** architectural limitation.

### 60. `Repeat` currently has two different semantic phases that don't fully reconcile

"Adopt existing DOM" (optimized around the assumption the DOM is already
correct) and "perform real patch" (can create/remove/update nodes).
Persistence exposes the seam between those two models.

**Status:** architectural weakness.

---

## U. Product-positioning / maturity issues

Not software bugs, but real issues for the alpha as a project.

### 61. The scope is extremely broad for a single-maintainer alpha

ARKlight is simultaneously pursuing: compiler frontend, semantic IR, HTML
backend, CSS backend, JS runtime, components, PWA, `.ark` packaging,
`.arklight` binary IR, Android, desktop, ACC, SBOM, CLI tooling, live
streaming, editor integration, Rei, Project Knowledge, and future assistant
tooling. The architecture is unusually coherent given the scope, but the
breadth creates verification debt.

**Status:** project-risk issue.

### 62. v1 stability will not magically resolve architectural limitations

The current v1 definition is about stability of the existing contract — it
does not inherently solve live input → action, ecosystem breadth, large-app
runtime scaling, native API depth, raw-postprocess limitations, `Repeat`
identity, etc. It stabilizes the tradeoff rather than removing it.

**Status:** product-definition reality.

### 63. The ecosystem must eventually validate the closed-vocabulary thesis

The compiler can prove "this source conforms to the vocabulary." It cannot
by itself prove "this vocabulary contains everything users need" — that
requires actual applications and external developers.

**Status:** empirical validation gap.

---

## V. Agent/AI-specific issues

Since ARKlight is also being considered in terms of agent use, a few
additional issues apply.

### 64. Static schema validity isn't behavioral correctness

The agent-friendly appeal is obvious: finite vocabulary → constrained
search space → deterministic validation. But the persist + `Repeat` bug
(#1) demonstrates the critical limitation: **something can be semantically
valid according to the schema and still be behaviorally wrong.** A future
agent cannot treat successful compilation as equivalent to correctness.

**Status:** fundamental limitation.

### 65. Current vocabulary is not yet broad enough for an agent to avoid escape hatches

The live-input → action problem (#7) is especially important. An agent can
discover `Action.append(...)` but cannot construct the normal semantic
operation required for arbitrary user-entered task creation — it either
says "outside current contract" or uses a developer escape hatch. Useful
information, but it limits current agent ergonomics.

**Status:** current capability gap.

### 66. Project Knowledge and ACC are not yet shipped mature infrastructure

They're exactly the things that could make the bounded-vocabulary model
more useful to agents — stable schema + project-specific knowledge +
curated capability ecosystem + machine-facing search — but these pieces
aren't yet established enough to count as current evidence.

**Status:** roadmap gap.

---

## The short version

Reduced to the issues that actually matter most, rather than an
encyclopedic funeral procession for every imperfect semicolon:

### Must-fix correctness issues

1. `persist=True` + `Repeat` hydration.
2. Imported-component dev rebuild registration.
3. PWA inline scripts vs strict CSP.
4. Initial/runtime numeric serialization mismatch.
5. Raw Python `TypeError` leaking through component validation.
6. CLI `--near` documentation/behavior mismatch.

### Biggest capability gaps

7. No live input/state → action argument primitive.
8. No arbitrary expression layer by design.
9. `Repeat` duplicate-value/key identity limitation.
10. Limited large-app runtime scaling due to broad DOM binding scans.
11. No deep native API bridge.
12. iOS absent.
13. Android build/install/release pipeline not yet fully demonstrated.

### Biggest architectural maturity gaps

14. `.arklight` doesn't serialize all `WebsiteIR`.
15. IR version/provenance contract needs maturation.
16. SBOM isn't fully integrated with IR/provenance.
17. Raw postprocess artifacts can escape normal provenance.
18. Build reproducibility is currently broken by SBOM timestamping.
19. Hydration assumes DOM/store equality too strongly.
20. Watcher-cycle guarantees need verification.
21. Compiler/global build state needs stronger lifecycle isolation.

### Biggest ecosystem/product gaps

22. ACC isn't yet a real mature ecosystem.
23. Independent adoption is unproven.
24. PyPI/distribution friction remains during alpha.
25. The project has enormous scope relative to maintainer/verification
    capacity.
26. Documentation still contains some source/implementation drift.
27. Several pitch claims need narrower wording.

---

**The single most important distinction, repeated:** most of these are not
evidence that ARKlight's central idea is wrong. The genuinely dangerous
ones are the places where the implementation violates its own existing
contract — especially hydration, CSP integration, reproducibility, and
dev-build lifecycle. The rest are mostly the price of the chosen
architecture: closed vocabulary, compiler-first semantics, WebView native
targets, constrained runtime, and deliberate escape-hatch boundaries.
