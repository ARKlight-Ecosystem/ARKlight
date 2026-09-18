# ACC capability discovery (`arklight/capabilities.py`)

_Current as of `v0.0645`._

## What this is

`arklight/capabilities.py` is the one piece of **ARKlight Component
Collections** (ACC, a separate repository --
[`Rae-ARK/ARKlight-Component-Collections`](https://github.com/Rae-ARK/ARKlight-Component-Collections))
that has to live in `alpha` itself, because it is compiler-side by
definition: a way for `arklight build` to *discover* capabilities an
installed ACC package (or any other distribution) advertises, without
the compiler importing, depending on, or requiring ACC to exist. A
build with no ACC packages installed sees zero capabilities and is
completely unaffected -- installing zero capability packages is a
no-op, exactly as a project that never touches ACC expects.

This mirrors the relationship `npm` has to Node.js, or a pytest plugin
has to pytest -- ACC sits *beside* the compiler, not inside it, and
this module is the compiler's side of that boundary. See
[`V1-DEFINITION.md`](V1-DEFINITION.md) Section 5 for why ACC itself
stays out of ARKlight's `v1.0` stability promise even though this one
discovery hook lives in the same repository.

## The registration contract

Deliberately minimal:

- ARKlight scans the `arklight.capabilities` Python entry-point group
  (`CAPABILITY_ENTRY_POINT_GROUP`) -- the standard mechanism Flask
  extensions, pytest plugins, and similar tools already use for this
  exact job.
- Each entry point must resolve to a zero-argument callable.
- Calling it must return an object with a truthy, string `.identity`
  attribute -- the capability identity an ACC package advertises
  (e.g. `"code.highlight"`).
- That's it. No further execution, no scanning of arbitrary modules,
  no implicit trust of anything beyond that one documented
  registration function.

## API

- `discover_capabilities(*, allow_multi=frozenset()) -> dict[str,
  Capability]` -- scans every installed distribution's
  `arklight.capabilities` entry points, calls each registration
  function, and returns a dict of capability identity -> `Capability`.
  Returns an empty dict, and never raises, when nothing is installed.
  `allow_multi` names capability identities that may legitimately have
  more than one provider; nothing is multi-provider yet, so any
  duplicate identity not named there is a hard error.
- `require_capability(identity, capabilities) -> Capability` -- looks
  up an already-discovered capability, raising a clear `CapabilityError`
  (rather than a bare `KeyError`) if it's missing. For a future caller
  (e.g. an ACC-provided `CodeBlock` component) that needs a specific
  capability to be present.
- `Capability` (frozen dataclass) -- `identity` (the ARKlight-facing
  name), `provider` (the distribution that registered it, for
  diagnostics), `value` (whatever the registration function returned,
  opaque to this module).
- `CapabilityError` (`RuntimeError` subclass) -- raised, at discovery
  time, for every failure mode this stage covers: an entry point that
  can't be imported or called, one that doesn't resolve to a callable,
  one that registers no valid identity, and two providers claiming the
  same identity without that identity being declared multi-provider.
  Nothing is silently skipped or silently resolved by picking a
  winner -- the same "fail loudly at build time" rule every other part
  of the compiler follows (see [`docs/README.md`](../README.md)'s
  Philosophy section).

## Where it's actually consumed today

`arklight/compiler/sbom.py` is the one existing caller: it calls
`discover_capabilities()` while assembling a build's SBOM (Software
Bill of Materials) and lists every discovered ACC capability as its
own SPDX package entry, tagged with its provider and identity --
so a project's SBOM accurately reflects any ACC capability it has
installed, whether or not that build's IR actually exercises it yet.
A `CapabilityError` during that scan is caught and recorded as a
skipped-with-reason line in the SBOM rather than failing the whole
build, since capability discovery is informational at this stage, not
load-bearing.

**Nothing in the compiler pipeline itself consumes a discovered
capability during a build yet.** No component, backend, or validation
step currently calls `require_capability(...)` -- this module only
proves the compiler *can* see a capability that exists outside its own
source tree. Wiring an actual capability into a build (e.g. an
ACC-provided syntax-highlighting component calling
`require_capability("code.highlight", ...)`) is future work, gated on
an ACC package existing to provide one -- see the next section.

## Status against ACC's own implementation ladder

ACC's `docs/design/IMPLEMENTATION-LADDER.md` lays out five stages for
its first real capability + component packages. This module *is*
Stage 1, filed by ACC as a proposal against this repo rather than
something ACC could build unilaterally, and landed here. As of this
writing, per that document:

| Stage | Delivers | Lives in | Status |
| --- | --- | --- | --- |
| 1 | Capability-discovery hook | `alpha` (this repo) | **Landed** -- this module |
| 2 | ACC package skeleton + capability metadata shape | ACC | Not started |
| 3 | `@acc/prism` -- a Pygments-backed syntax-highlighting capability | ACC | Not started |
| 4 | `@acc/common` -- first common-use components, consuming Stage 3 | ACC | Not started |
| 5 | Installability (`arklight install`/`list`/`info` against a local package) | `alpha` + ACC, jointly | Not started |

Stages 2-5 are ACC's to build and track in its own repository; nothing
further is required of `alpha` until Stage 5, which is joint by
nature (a real `arklight install` subcommand doesn't exist yet -- see
[`CLI-REFERENCE.md`](CLI-REFERENCE.md) for the currently-implemented
command set).

## Testing

`tests/test_capabilities.py` (9 tests) exercises the full contract --
successful discovery, each `CapabilityError` diagnostic, and
`require_capability`'s lookup/error path -- by monkeypatching
`importlib.metadata.entry_points` rather than installing a real
throwaway distribution. ACC's own ladder document pre-authorizes this
approach for anything built before an end-to-end ACC package exists to
install for real.
