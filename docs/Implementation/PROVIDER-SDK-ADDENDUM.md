# Provider SDK Addendum: Staged Order, v0.065 -> v0.070

**Status:** Stages 1-4 of 6 SHIPPED (`0.06514`, `0.06516`, `0.06518`,
`0.06613`); stages 5-6 PLANNED, interleaved one stage per version
alongside the JS vocabulary addendum's own stages 5-10 in the same
`v0.065`-`v0.070` milestone range. This file turns the accepted
[`docs/Proposals/PROVIDER-SDK-PROPOSAL.md`](../Proposals/PROVIDER-SDK-PROPOSAL.md)
into a trackable landing order, the same role
`JS-VOCABULARY-ADDENDUM-v0.070.md` plays for the JS vocabulary
expansion proposal. It does not restate that proposal's reasoning; it
exists to turn "here's an accepted barebones interface" into "here's
the six-rung order it ships in."

This file was referenced from `docs/version history/v0.065.md` through
`v0.070.md`, `docs/Proposals/PROVIDER-SDK-PROPOSAL.md`'s own Status
line, `docs/Implementation/README.md`'s index, and
`docs/Implementation/JS-VOCABULARY-ADDENDUM-v0.070.md`'s "other
proposals share this range" note for several versions before it
existed on disk -- `v0.065.md` itself flags this explicitly ("Note
that addendum file is referenced here and in the proposal but is not
in the repository"). This file closes that gap.

## Scope filter: what's in this ladder, and what isn't

`Provider` stays exactly as scoped by the proposal's own §2 ("barebones")
and §6 ("explicitly out of scope") throughout every stage below:

- **In scope:** the closed `Provider` interface/contract, IR threading,
  build-time validation, the fixed minimal JS config object, external
  script loading as its own separately-gated primlet, `arklight search`
  integration, and finalizing the closed capability enum.
- **Out of scope, on purpose:** any bundled vendor SDK (Firebase,
  Supabase, or otherwise), any server ARKlight stands up or deploys,
  any opinion on auth flows/token storage/security rules, and any
  client-side data-fetch orchestration (loading states, caching,
  retries) -- that remains `JS-VOCABULARY-EXPANSION-PROPOSAL.md`'s own,
  separate, still-open Tier 3 gap. Nothing in this ladder authorizes
  work on any of it.

`Provider` remains gated behind `arklight/experimental.py`'s
`provider-integration` entry for every stage below, per the proposal's
own §5 -- it is not part of ARKlight's default surface at any point in
this ladder, shipped or planned.

## The ladder

### v0.065 -- Stage 1 of 6: the contract itself (SHIPPED, `0.06514`)

Proposal §3's sketch, made real: `Provider.declare(name=..., capabilities=[...])`
building a `ProviderDeclaration`, and `Site(provider=...)` accepting
one. Registers `provider-integration` in `arklight/experimental.py`'s
`FEATURES` dict per §5 -- inline warning at the point a page's IR shows
a declared `Provider`, plus the same end-of-build summary entry every
other experimental feature gets. A site that never declares a
`Provider` ships no `Provider` code at all, same "only ship what's
used" discipline the JS backend's own `actions`/`behaviors` objects
already follow.

### v0.066 -- Stage 2 of 6: IR and validation integration (SHIPPED, `0.06516`)

Threads a declared `Provider` through the compiler pipeline the same
way `Site.media_query(...)` already threads its own experimental
config through `WebsiteIR`: `WebsiteIR.provider: ProviderDeclaration | None`
(`arklight/ir/build.py`), and `arklight/ir/validate.py`'s
`validate_provider(provider)` enforcing the closed capability
vocabulary (`arklight.provider.PROVIDER_CAPABILITIES`) at the
pipeline's own validation stage -- defense in depth alongside
`ProviderDeclaration.__post_init__`'s own construction-time check, the
same "the officially designated validation stage independently
re-confirms a value built elsewhere" discipline every other schema
check in that module follows. Still nothing reads `ir.provider`
downstream at this stage -- a build with a `Provider` stays
byte-identical to one without, apart from the experimental-feature
reports every gated feature already gets.

### v0.067 -- Stage 3 of 6: JS backend emission (SHIPPED, `0.06518`)

Emits the fixed, minimal config a validated `Provider` declaration
needs at runtime -- no network call, no vendor SDK, no generated glue
that actually talks to anything: `window.ARKLIGHT_PROVIDER` in
`arklight.js` (`arklight/backend/js/render.py`'s
`_provider_config_js`), a frozen object carrying `name` and
`capabilities`, read-only, for the site author's own script to read.
This is the first stage where `ir.provider` actually reaches emitted
output -- the same "only ship what's used" gate as every other JS
backend object, present in the runtime only when a page's IR actually
declares a `Provider`.

### v0.068 -- Stage 4 of 6: external script loading (SHIPPED, `0.06613`)

Resolves the proposal's own open question §7.1: a `Provider`
declaration alone doesn't get a real vendor SDK (the actual Firebase
JS SDK, say) loaded into the page. Adds the small, separately-gated
primitive that makes the contract usable end-to-end: `Page(scripts=
[{"src": "https://.../sdk.js", ...}])`, validated the same
`{attribute: value}`-dict, `rel`/`src`-required structural discipline
`links` already uses (`arklight.ir.validate._validate_page_head_extensions`),
rendered as verbatim `<script ...></script>` tags at the end of
`<head>` (`arklight/backend/html/head_meta.py`). Gated as its own
`provider-scripts` experimental feature rather than folded into
`provider-integration` (loading an arbitrary external script is a
distinct risk from declaring a capability contract, and gating them
together would either under-warn the script-loading case or over-warn
every plain `Provider` declaration that never needs one) -- a page can
carry one without the other, and each records its own, independent
`ExperimentalUsage`. Unlike a bare `Provider` declaration, a script
`src` on another origin also has to clear the page's own
`script-src 'self'` CSP default (`arklight/backend/html/csp.py`) via
`Site(trusted_script_origins=[...])`, or the tag the build just added
will be blocked by the very policy the same build emits -- noted in
both the experimental warning's detail lines and the CSP module's own
docstring.

### v0.069 -- Stage 5 of 6: `arklight search` integration (PLANNED)

Extends `arklight search`'s existing schema-lookup reflection to a
registered `Provider`'s capability contract -- `arklight search
<provider-name>` prints the declared contract (name, capabilities, DOM
hooks/state keys), reusing the existing typo-tolerant fallback
machinery rather than a second, parallel fuzzy-matcher. The same "look
something up without opening a file" convenience `SCHEMA` already
gets for components, extended to cover a site's own declared
`Provider` too.

### v0.070 -- Stage 6 of 6: capability enum finalization (PLANNED, capstone)

Resolves the proposal's own open question §7.2: whether `capabilities`
stays a free-form string or becomes a fixed, versioned enum (`auth`,
`read`, `write`, `subscribe`, ...). Placed last, after five stages of
real usage against the interface, so the enum is finalized against
what `Provider.declare(...)` actually needed rather than guessed at
Stage 1 -- the closed-registry discipline `Action.*`/`Behavior.*`
already use everywhere else in the runtime, and for the same reason:
it keeps generated output inspectable and keeps ARKlight's "no eval,
no `new Function`, no string ever executed as code" promise intact
even as this surface grows.

## Status tracking

| Stage | Covers | Status |
| --- | --- | --- |
| 1 of 6 | The contract (`Provider.declare`, `Site(provider=...)`, `provider-integration` gating) | SHIPPED (`0.06514`) |
| 2 of 6 | IR and validation integration | SHIPPED (`0.06516`) |
| 3 of 6 | JS backend emission (`window.ARKLIGHT_PROVIDER`) | SHIPPED (`0.06518`) |
| 4 of 6 | External script loading (`Page(scripts=[...])`, `provider-scripts` gate) | SHIPPED (`0.06613`) |
| 5 of 6 | `arklight search` integration | PLANNED |
| 6 of 6 | Capability enum finalization | PLANNED (capstone) |

See `docs/version history/v0.065.md` through `v0.070.md` for each
stage's forward-looking, user-facing summary, and
`PROGRESS.md`/`CHANGELOG.md` for the internal record.
