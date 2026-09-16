# SYSTEM-DESIGN-AGREEMENTS

## Compiler First, Runtime Last

ARKlight is a compiler first.

The compiler should perform every transformation, validation,
specialization, optimization, and decision that can be determined before
deployment. Runtime behavior exists only where the target platform
necessarily requires a runtime to perform work that cannot be completed
during compilation.

This is a design agreement, not merely an implementation preference.

The central rule is:

> **If the compiler can solve it correctly and completely, the runtime
> should not solve it again.**

The inverse is also important:

> **If a behavior is inherently determined by the target runtime,
> ARKlight should delegate it rather than recreate that runtime inside
> its own abstraction.**

This keeps generated output small, predictable, portable, inspectable,
and native to its deployment environment.

------------------------------------------------------------------------

## 1. The Compiler Owns Everything It Can Know

ARKlight should prefer compile-time work whenever the required
information is available during compilation.

Examples include:

-   route resolution
-   internal-link resolution
-   component validation
-   HTML structure
-   CSS generation
-   unused component-style elimination
-   behavior selection
-   static content generation
-   asset copying and dependency analysis
-   page-specific output decisions
-   metadata generation
-   platform-specific artifact selection
-   output optimization
-   packaging decisions that can be made before deployment

The compiler should not emit a general-purpose runtime mechanism merely
because another framework traditionally does so.

A feature should first be evaluated as a compiler problem.

Only after establishing that the compiler cannot perform the required
work should runtime behavior be considered.

------------------------------------------------------------------------

## 2. Runtime Is a Delegation Boundary

Runtime code is not inherently bad.

Runtime code is appropriate when the target environment must make a
decision using information unavailable at compilation time.

Examples include:

-   browser interaction
-   browser history
-   viewport-dependent behavior
-   user input
-   local storage
-   URL query state
-   network responses
-   operating-system APIs
-   native application lifecycle
-   device capabilities

When such behavior is required, ARKlight should generate the **smallest
target-native mechanism necessary**.

The compiler remains responsible for deciding:

1.  that the runtime behavior is needed,
2.  which behavior is needed,
3.  what data the behavior requires,
4.  what configuration can be baked into the artifact,
5.  and what runtime code can be omitted.

The target runtime is responsible only for the part that genuinely
cannot happen earlier.

------------------------------------------------------------------------

## 3. Do Not Reimplement the Target Runtime

ARKlight should not attempt to become a replacement for the environment
in which its output executes.

For the web, the browser already provides:

-   URL navigation
-   History API
-   DOM
-   CSS layout
-   form submission
-   storage
-   networking
-   accessibility behavior
-   media playback
-   native dialogs and controls
-   service-worker infrastructure
-   standard browser APIs

ARKlight should compile against these capabilities rather than recreate
them.

For example, internal links should become ordinary links whose paths are
resolved during compilation.

ARKlight does not need a client-side router merely to decide which
already-built HTML file corresponds to a URL.

Likewise, a query parameter can be bridged into runtime state when
necessary, but that does not require inventing a routing system.

------------------------------------------------------------------------

## 4. The Compiler May Specialize for the Target

"Compiler first" does not mean that every target receives identical
output.

Different targets expose different capabilities and constraints.

The compiler should therefore produce a **target-specific optimized
artifact** rather than forcing every platform through one universal
runtime.

Conceptually:

``` text
                    ARKlight source
                          |
                          v
                  Compiler / IR
                          |
             +------------+------------+
             |            |            |
             v            v            v
           Web          Android      Desktop
             |            |            |
             v            v            v
      optimized web  optimized app  optimized app
          output        output          output
```

The source model can remain shared while the generated implementation is
specialized for the target.

------------------------------------------------------------------------

## 5. Target Backends Define the Final Boundary

A target backend describes how ARKlight's compiled representation
becomes an artifact appropriate for a particular deployment environment.

Examples may include:

-   HTML/CSS/JavaScript for the web
-   an Android application artifact
-   a desktop application artifact
-   a future native or embedded target

The backend may choose different:

-   runtime libraries
-   asset formats
-   lifecycle integration
-   platform APIs
-   packaging
-   manifests
-   startup behavior
-   installation metadata
-   native bridges

This does not violate the compiler-first principle.

It is the compiler doing target-specific work.

The important distinction is that the target backend should emit **only
what that target requires**.

------------------------------------------------------------------------

## 6. One Source Model, Multiple Optimized Targets

ARKlight should not assume that a feature has one universal
implementation.

A capability may be represented once in the source model while being
compiled differently for each target.

For example:

``` text
ARKlight component / behavior
            |
            v
       normalized IR
            |
     +------+------+------+
     |      |      |      |
     v      v      v      v
    Web  Android Desktop  ...
     |      |      |
     v      v      v
 browser  Android  OS
 runtime  runtime  runtime
```

The compiler decides what is statically knowable.

The backend decides how that knowledge is expressed for the target.

The target runtime performs the remaining dynamic work.

This separation prevents the core API from becoming polluted with
platform-specific implementation details.

------------------------------------------------------------------------

## 7. Optimize Before Shipping Runtime Code

Runtime payload should be treated as a compiled output, not as a
permanent framework dependency.

If a page uses no interactive behavior, the generated page should not
receive runtime machinery that exists only for unrelated behaviors.

If a page uses one behavior, the compiler should have enough information
to emit only the implementation required for that behavior, where the
backend supports such specialization.

If an application target provides a native facility for a capability,
the generated application should prefer that facility over shipping an
ARKlight recreation of it.

The desired direction is:

``` text
source capability
      |
      v
compiler analysis
      |
      +--> can solve statically?
      |        |
      |       yes --> bake result into artifact
      |
      +--> cannot solve statically?
               |
               v
        identify required runtime
               |
               v
        specialize for target
               |
               v
        emit minimum required code
```

------------------------------------------------------------------------

## 8. Runtime Features Must Justify Their Existence

A runtime feature should exist because there is a genuine runtime
problem to solve.

It should not exist because another frontend framework has an equivalent
abstraction.

For every proposed runtime feature, ask:

1.  What information is unavailable at compile time?
2.  Why must this decision happen at runtime?
3.  Does the target platform already provide the capability?
4.  Can ARKlight delegate to that capability?
5.  What is the smallest generated runtime needed?
6.  Can unused portions be removed during compilation?
7.  Does another target require a different implementation?

If the answer to the first question is "nothing," the feature probably
belongs in the compiler.

If the target platform already provides the capability, ARKlight should
generally use it.

------------------------------------------------------------------------

## 9. The Web Is Not an Application Runtime to Rebuild

The web target deserves particular discipline.

ARKlight's web output should remain ordinary web output:

-   HTML remains HTML.
-   CSS remains CSS.
-   JavaScript remains JavaScript.
-   browser APIs remain browser APIs.
-   URLs remain URLs.
-   forms remain forms.
-   browser history remains browser history.

ARKlight may generate JavaScript where interactivity requires it, but
the generated JavaScript should be a narrow bridge between compiled
declarations and browser APIs.

The browser should continue doing browser work.

This is why ARKlight can avoid several conventional frontend
abstractions without sacrificing useful capabilities.

A build-time route does not need a client router.

A statically known layout does not need a runtime layout tree.

A static page does not need a client-side renderer.

A browser-native form does not automatically need a form framework.

------------------------------------------------------------------------

## 10. URL State Is Runtime State

URL query parameters are an example of the compiler/runtime boundary.

The compiler can know the declared default:

``` text
State("page", initial=1, query="page")
```

It can bake that default into the generated document.

It cannot know which URL the browser will actually receive at runtime.

Therefore:

``` text
compile time:
    initial = 1
          |
          v
    baked into HTML

runtime:
    URL ?page=3
          |
          v
    browser API
          |
          v
    State("page") = 3
```

The compiler should generate only the bridge necessary to connect these
two worlds.

It should not introduce a router merely because the URL is involved.

------------------------------------------------------------------------

## 11. Deployment Features Should Prefer Post-Compilation Transformation

Features that operate on already-built artifacts should remain outside
the core compilation model when practical.

Examples include:

-   PWA generation
-   packaging
-   archive creation
-   installation bundles
-   platform-specific manifests
-   deployment metadata
-   application wrappers

The preferred structure is:

``` text
ARKlight source
      |
      v
   compiler
      |
      v
 compiled artifact
      |
      +----> web deployment
      |
      +----> PWA transformation
      |
      +----> Android packaging
      |
      +----> desktop packaging
      |
      +----> other target adapters
```

A deployment adapter should consume the compiler's output rather than
reaching backward into compiler internals unless a target genuinely
requires earlier integration.

This keeps the compilation pipeline stable and keeps deployment concerns
isolated.

------------------------------------------------------------------------

## 12. Android, Desktop, and Web May Diverge

Target parity does not mean implementation parity.

The same ARKlight source may legitimately produce different generated
structures for different targets.

For example:

### Web

The compiler may emit:

-   HTML
-   CSS
-   minimal JavaScript
-   browser-native APIs
-   PWA metadata when requested

### Android

The compiler may additionally emit or configure:

-   Android application identity
-   package metadata
-   icons
-   splash-screen configuration
-   orientation
-   Android lifecycle integration
-   a web or native runtime appropriate to the backend

### Desktop

The compiler may additionally emit or configure:

-   application identity
-   desktop window configuration
-   icons
-   platform packaging
-   desktop lifecycle integration
-   the selected embedded runtime

These differences are not duplication for its own sake.

They are target specialization.

------------------------------------------------------------------------

## 13. Do Not Force Lowest-Common-Denominator Design

ARKlight should not weaken every target merely to maintain identical
behavior across all targets.

If a target provides a superior native mechanism, the target backend may
use it.

If a target has a constraint that the web does not have, the backend may
account for it.

If a capability is meaningless on a target, it should not be emitted.

The shared source abstraction should represent the developer's intent.

The backend should determine the most appropriate target implementation.

------------------------------------------------------------------------

## 14. Optimization Is Part of Compilation

Optimization should not be treated as an optional cleanup pass that
happens after the architecture is already decided.

The compiler should continuously reduce unnecessary output.

Potential optimization dimensions include:

-   dead component elimination
-   unused CSS elimination
-   unused behavior elimination
-   page-specific JavaScript
-   asset dependency pruning
-   static value folding
-   output specialization
-   deterministic file generation
-   incremental compilation
-   target-specific asset selection
-   platform-specific runtime reduction

The goal is not merely to make builds faster.

The goal is to make the **resulting artifact smaller, simpler, and more
directly representative of what the source actually uses**.

------------------------------------------------------------------------

## 15. Portability Comes From Standard Output

ARKlight's portability should come from producing artifacts understood
by the target environment, not from shipping a large ARKlight runtime
everywhere.

For the web, this means standard web artifacts.

For application targets, this means using the platform's normal
application mechanisms where appropriate.

A target-specific backend may add what is necessary, but the resulting
artifact should still be as native to its environment as the target
permits.

This gives ARKlight two useful properties:

1.  **Authoring portability**: the source model remains largely shared.
2.  **Deployment specialization**: each target receives an artifact
    optimized for itself.

------------------------------------------------------------------------

## 16. Architecture Decision Rule

When deciding where a feature belongs, use this order:

### First: Can the compiler solve it?

If yes, solve it during compilation.

### Second: Can the target platform solve it?

If yes, delegate to the target runtime or native platform API.

### Third: Can ARKlight generate a minimal bridge?

If the compiler cannot solve it and the platform needs generated glue,
emit the smallest bridge necessary.

### Fourth: Does a reusable ARKlight runtime abstraction remain necessary?

Only then should a persistent runtime feature be introduced.

This produces the following preference order:

``` text
compiler magic
      >
target-native capability
      >
minimal generated bridge
      >
ARKlight runtime abstraction
```

The farther down this list a feature sits, the stronger its
justification should be.

------------------------------------------------------------------------

## 17. Anti-Pattern: Framework Feature Parity

ARKlight should not pursue feature parity with frontend frameworks as a
goal.

A framework feature exists to solve a problem within that framework's
architecture.

ARKlight has a different architecture.

Therefore:

> **The existence of a feature elsewhere is not evidence that ARKlight
> needs the feature.**

The correct question is:

> **Does the underlying problem still exist in ARKlight's
> compiler-first, target-specialized model?**

If the compiler already eliminates the problem, adding the framework
abstraction would increase complexity without adding equivalent value.

------------------------------------------------------------------------

## 18. Design Goal

The long-term architecture should converge toward:

``` text
                 Python authoring model
                          |
                          v
                   ARKlight compiler
                          |
              analysis / validation
                          |
                   shared Website IR
                          |
              +-----------+-----------+
              |           |           |
              v           v           v
             Web       Android     Desktop
              |           |           |
        target backend target backend target backend
              |           |           |
              v           v           v
        optimized      optimized    optimized
         artifact       artifact     artifact
              |           |           |
              v           v           v
          browser       Android       OS
          runtime       runtime      runtime
```

The compiler should move as much work as possible upward.

The target runtime should receive as little work as possible downward.

The shared IR should describe intent rather than dictate implementation.

The backend should specialize that intent for its target.

The final artifact should contain only the capabilities required by the
source and target.

------------------------------------------------------------------------

## 19. The Core Agreement

ARKlight is not a runtime that happens to have a compiler.

**ARKlight is a compiler that emits artifacts which use their target
runtime.**

That distinction should guide API design, compiler architecture, runtime
design, backend design, optimization work, and future feature proposals.

When a new feature is proposed, the default assumption should be:

> **Compile it if possible. Delegate it if necessary. Generate only what
> is required. Never recreate a capability that the target already
> provides.**

The compiler should do the clever work.

The runtime should do the work that only the runtime can know.

The target backend should make sure each platform gets the smallest
useful artifact.

That is the architectural boundary.
