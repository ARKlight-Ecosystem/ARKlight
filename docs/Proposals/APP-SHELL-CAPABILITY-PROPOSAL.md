# Proposal: App-Shell Navigation as an ARKlight-Native Capability
(not a client-side SPA framework)

## Status

Proposed. Not accepted, not staged, not scheduled against a version.
Filed to give "should ARKlight get closer to SPA-shaped UX" a decision
record instead of a recurring conversation.

## The actual question

Not: *"should ARKlight become an SPA framework."* That's already
answered, permanently, in `docs/Foundational/WHAT-ARKLIGHT-IS.md`
Section 4 ("Not a client-side application framework") and
`SYSTEM-DESIGN-AGREEMENTS.md` Section 3 ("Do Not Reimplement the
Target Runtime"). A persistent client-side router and a component
tree that survives navigation are not on the table -- adopting them
would require exactly the kind of general expression evaluation the
closed vocabulary exists to rule out.

The actual question: **`Site(app_shell=True)` already exists and
already delivers no-full-reload navigation via `hx-boost` +
`hx-preserve`, delegated entirely to htmx rather than a router ARKlight
wrote itself. Given that this capability is real, shipped, and
philosophy-compliant by construction (it delegates to the runtime
instead of reimplementing it), what is the ceiling on how far it can
be pushed before it stops being "boosted navigation" and starts being
"a router in a trenchcoat"?**

This proposal's job is to draw that line explicitly, so future
`app_shell` work has a checklist instead of a vibe.

## What already exists (verified against source, not aspirational)

- `Site(app_shell=True)` -- `arklight/backend/html/page_render.py`,
  `render.py`. Defaults `False`, byte-for-byte unaffected otherwise.
- `<body hx-boost="true">` -- same-origin links become in-place
  `innerHTML` swaps, htmx's own mechanism, not ARKlight's.
- `shell_persistent=True` (any component) -> `hx-preserve="true"`,
  matched by `id`, for nav/header/sidebar elements that should survive
  a boosted swap.
- `State` re-initialization per boosted navigation
  (`arkInitPage()` / `arklight/backend/js/runtime/dispatch.py`) --
  each page's reactive core is torn down and rebuilt, not persisted
  across pages by default.
- `State(..., query=..., history=...)` -- URL-query-synced state via
  `history.replaceState`/`pushState`, already composable with
  `app_shell`.

Internally referred to (per `CHANGELOG.md` `v0.0500`) as solving "the
app-illusion problem" -- the point being that it's explicitly framed as
an illusion of an app, not an app framework.

## Known, already-documented ceiling

From `docs/Proposals/ARKlight-ISSUE-REGISTER.md` items 12-13:

- State updates rescan bound DOM via
  `querySelectorAll("[data-ark-bind]")` rather than maintaining direct
  references to affected bindings -- cost scales as
  *(mutations) x (bound nodes)*. Explicitly flagged as fine for
  small/medium sites, a scalability concern at SPA-shaped scale.
- No fine-grained state -> DOM dependency tracking. The compiler knows
  a lot statically; the runtime does broad rediscovery instead of a
  granular map.

Any extension proposed here has to either accept this ceiling
explicitly or make fixing it part of the scope -- not pretend it isn't
there.

## Philosophy-fit checklist

Before any concrete `app_shell` extension gets accepted, it should
pass all of these (drawn directly from `SYSTEM-DESIGN-AGREEMENTS.md`):

1. **Delegates, doesn't reimplement.** Does the feature hand the
   problem to something the runtime/htmx/browser already solves, or
   does it require ARKlight to grow its own routing/expression logic?
2. **Stays closed-vocabulary.** No `eval`, no `new Function`, no
   string executed as code. If the feature needs a general expression
   evaluator to be useful, it fails here regardless of how compelling
   the DX win is.
3. **Compiler resolves what it can, ahead of time.** If a decision
   (which page, which route, which component) can be made at build
   time, it must be -- runtime is reserved for what only the browser
   can know.
4. **No second untrusted layer.** Consistent with the native-backend
   precedent (Android/Desktop wrap ARKlight's own closed output, never
   an arbitrary second app) -- an `app_shell` extension can't introduce
   a place for arbitrary developer-authored JS to run that the compiler
   didn't validate.
5. **Byte-for-byte unaffected when opted out.** Same precedent every
   `Site(...)` flag already follows -- default `False`, zero output
   drift for sites that don't ask for it.

## Candidate extensions -- scoped by whether they pass the checklist

**Plausibly in-scope** (delegates to the runtime, stays closed-vocab):

- Prefetch-on-hover/viewport for boosted links (`hx-boost` supports
  `hx-trigger`-style prefetch patterns already in htmx's own
  vocabulary) -- purely a compile-time attribute decision.
- View-transition support (`document.startViewTransition`) wired
  through `hx-boost`'s swap -- browser-native API, no router needed.
- Extending `shell_persistent` to cover more element classes
  (`Repeat`-rendered lists that shouldn't remount on a boosted swap
  where `id` stability can be proven at compile time).
- A resolved answer to issue-register item 12 (fine-grained
  state->DOM tracking) scoped specifically to `app_shell` sites, since
  that's exactly where the current broad-rescan cost bites hardest.

**Out of scope, permanently** (fails the checklist, not just
"not yet"):

- A general client-side route table / dynamic route matching.
- Component instances with state that survives across *different*
  pages (as opposed to `State` re-initializing per page, which is the
  current, correct behavior).
- Any fetch/navigate primitive that takes an arbitrary URL or
  expression rather than a compile-time-resolved, validated target.

## What "accepted" would look like

If a maintainer picks this up: split into staged capability fixes the
same way `PROVIDER-SDK-PROPOSAL.md` and
`URL-STATE-AS-PRIMITIVE-PROPOSAL.md` were staged -- each rung small
enough to land independently, each one re-checked against the
philosophy-fit checklist above before merge, not just at proposal time.

## What this proposal is not

Not a pitch to make ARKlight's output "a real SPA." It's the opposite:
a way to keep pushing the *illusion* further, on purpose, while making
the line between "boosted navigation" and "a router" a checked thing
instead of a debate that recurs every time someone asks for SPA-shaped
UX.
