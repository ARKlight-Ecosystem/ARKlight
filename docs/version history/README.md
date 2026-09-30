# Version history

## Overview

This directory is the **user-facing** record of ARKlight's released
versions -- a short overview of each version's feature set, meant for
someone deciding whether to upgrade or looking up what changed,
without wading through internal implementation notes.

It's deliberately separate from the **changelog** and **progress
log**, both of which are internal/dev-facing and live at the repo
root: [`CHANGELOG.md`](../../CHANGELOG.md) is the plain,
Keep-a-Changelog-style version log (exact files touched, rationale
for each decision, what was deliberately deferred and why);
[`PROGRESS.md`](../../PROGRESS.md) is the narrative record of what
was tried, what was rejected, and what broke along the way, kept in
reverse-chronological order -- its snapshot table at the top is the
fastest way to see what's DONE / IN PROGRESS / PLANNED right now.
The docs in this directory are the distilled, user-facing version of
that history for everyone else.

For the architecture-level roadmap (the numbered `v0.0xx` milestone
table itself, independent of what's landed so far), see
[`docs/Foundational/ARCHITECTURE.md`](../Foundational/ARCHITECTURE.md).

## Index

| Version | Covers |
| --- | --- |
| [`v0.001.md`](./v0.001.md) | Python -> HTML -- the first working compiler pipeline. |
| [`v0.002.md`](./v0.002.md) | CSS -- default stylesheet backend. |
| [`v0.003.md`](./v0.003.md) | JavaScript helpers + two vocabulary addenda -- closed-behavior JS backend, ~79 new components. |
| [`v0.0035.md`](./v0.0035.md) | Stateful JS -- `State`/`Bind`/`Action` primitives. |
| [`v0.004a.md`](./v0.004a.md) | CLI scaffolding -- `arklight new <name> --template simple\|production`. |
| [`v0.036.md`](./v0.036.md) | ARK Bundle spec v1 -- `arklight pack`. |
| [`v0.037.md`](./v0.037.md) | Sealed ARK Bundles -- encrypted by default, `arklight unpack`. |
| [`v0.041.md`](./v0.041.md) | CLI/pipeline/JS runtime hardening + stateful JS vocabulary addenda I & II. |
| [`v0.042.md`](./v0.042.md) | Extra CSS features -- `Site.style(...)` custom classes, `arklight search`, `arklight --help`. |
| [`v0.0431.md`](./v0.0431.md) | Emergency patch -- build-time warning for unrouted `srcset`/`poster`/`action`/`formaction`. |
| [`v0.048.md`](./v0.048.md) | CSS `@media` queries + structured `<head>`/`<header>` extension. |
| [`v0.054.md`](./v0.054.md) | JS backend capability expansion (reactive core) -- rolls up all 8 `vdom-N` staging sub-stages. |
| [`v0.060.md`](./v0.060.md) | User-defined, reusable components -- full milestone rollup (Stages 0-4: registration/props, typo diagnostics, default styling, per-backend rendering, component-owned state). |
| [`v0.061.md`](./v0.061.md) | JS vocabulary addendum, stage 1/10 -- math siblings (`subtract`/`divide`/`min`/`max`). |
| [`v0.062.md`](./v0.062.md) | JS vocabulary addendum, stage 2/10 -- string-casing sibling + comparison `Show` predicates. |
| [`v0.063.md`](./v0.063.md) | JS vocabulary addendum, stage 3/10 -- small new runtime primitives (`reveal`, debounced binding, clipboard paste, geolocation, `matchMedia`). |
| [`v0.064.md`](./v0.064.md) | `arklight search --retrieve-doc` -- doc-tree retrieval mode on the existing `search` subcommand. **Shipped.** Also carries JS vocabulary addendum stage 4/10, the math derivations catalog (21 `Derive.*` kinds), which landed later as `0.06509`. |
| [`v0.0641.md`](./v0.0641.md) | Emergency patch -- `State(..., query=..., history=...)`, URL query-parameter state as a primitive. |
| [`v0.065.md`](./v0.065.md) | All four pieces have **shipped**: `Provider`, stage 1/6 (the contract itself -- `Provider.declare(...)`, `Site(provider=...)`, the gated `provider-integration` feature; shipped as `0.06514`), JS vocabulary addendum, stage 5/10 (string derivations catalog, 18 `Derive.*` kinds, shipped as `0.06513`), Rei, the compiler narrator (`arklight build --narrate` + `rei.default_mode`, shipped as `0.06510`) and Platform API IR, stage 1/2 (Web reference implementation -- `PlatformAPI.notify`/`.clipboard_write`) -- see that file's own status note for how this milestone slot's four independently-staged pieces are tracked. |
| [`v0.06515.md`](./v0.06515.md) | `arklight deploy` -- the deployment CLI: builds the site, then hands it to Wrangler to deploy on Cloudflare Workers. Out-of-band release. |
| [`v0.066.md`](./v0.066.md) | **DONE -- package version `0.066`.** `Provider`, stage 2/6 -- IR/`validate.py` integration: a declared Provider threaded through `WebsiteIR`, closed-vocabulary capability validation at build time. **Shipped as `0.06516`.** JS vocabulary addendum, stage 6/10 -- predicates catalog, 8 new `Predicate.*` kinds (`and_`/`or_`/`not_`, `in_range`, `one_of`, `is_empty`/`is_not_empty`, `is_null`) -- **shipped as `0.06517`**, so both pieces are done. |
| [`v0.067.md`](./v0.067.md) | **DONE -- package version `0.067`.** `Provider`, stage 3/6 -- JS backend emission: a read-only `window.ARKLIGHT_PROVIDER` config object (name + capabilities) in `arklight.js`, no networking/vendor code generated. **Shipped as `0.06518`.** JS vocabulary addendum, stage 7/10 -- list-scalar derivations catalog, 9 new `Derive.*` kinds (`list_length`, `list_min`/`list_max`/`list_average`, `list_first`/`list_last`, `list_includes`, `list_any`/`list_all`) -- **shipped as `0.06612`**, so both pieces are done. |
| [`v0.068.md`](./v0.068.md) | **DONE.** JS vocabulary addendum, stage 8/10 -- cross-language numeric batteries (`lerp`, `midpoint`, saturating arithmetic, `value_or`/`first_present`). Plus `Provider`, stage 4/6 -- an authored external-`<script src>` primitive. |
| [`v0.069.md`](./v0.069.md) | **DONE.** JS vocabulary addendum, stage 9/10 -- cross-language formatting/case batteries (`humanize_*`, `to_ordinal`, case converters). Plus `Provider`, stage 5/6 -- `arklight search` schema-lookup support for a registered Provider's capability contract. |
| [`v0.070.md`](./v0.070.md) | **DONE.** JS vocabulary addendum, stage 10/10 (capstone) -- `pluralize` + `random_int`. Plus `Provider`, stage 6/6 (capstone) -- the finalized capability enum. |

## Version numbering

Every version here uses the plain milestone scheme
[`ARCHITECTURE.md`](../Foundational/ARCHITECTURE.md)'s roadmap table
uses (`v0.001`, `v0.0035`, `v0.060`, `v0.0641`, ...). Point releases
between milestones (`v0.0431`, `v0.0641`, `v0.06515`) are out-of-band
patches and sit between their neighbors in the index.

Only versions that actually shipped get a file. Planned milestones
(for example the `v0.071`-`v0.078` Project Knowledge ladder) live in
the roadmap table until they land.

## Adding a new version

When a version ships, add a new `vX.Y.md` file here
with a short, user-facing summary of what shipped -- what a reader
would actually want to know, not a line-by-line diff -- and add a row
for it to the Index table above. The detailed, internal entry still
goes in the root [`CHANGELOG.md`](../../CHANGELOG.md); this directory
should never accumulate changelog-style detail itself.
