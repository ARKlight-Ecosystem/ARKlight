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
| [`v0.036.md`](./v0.036.md) | ARK Bundle spec v1 -- `arklight pack`. |
| [`v0.037.md`](./v0.037.md) | Sealed ARK Bundles -- encrypted by default, `arklight unpack`. |
| [`v0.041.md`](./v0.041.md) | CLI/pipeline/JS runtime hardening + stateful JS vocabulary addenda I & II. |
| [`v0.54.0.md`](./v0.54.0.md) | Alpha catch-up -- CSS `@media`, HTML backend refactor, reactive JS core, search engine, live-streaming/CCTV. First release on the new `MAJOR.MINOR.PATCH` version format. |

## Adding a new version

When a version ships, add a new `vX.Y.md` (or `vX.Y.Z.md`) file here
with a short, user-facing summary of what shipped -- what a reader
would actually want to know, not a line-by-line diff -- and add a row
for it to the Index table above. The detailed, internal entry still
goes in the root [`CHANGELOG.md`](../../CHANGELOG.md); this directory
should never accumulate changelog-style detail itself.
