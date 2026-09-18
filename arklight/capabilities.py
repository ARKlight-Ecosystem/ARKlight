"""
ACC capability-discovery hook.

This is Stage 1 of ARKlight-Component-Collections' (ACC)
`docs/design/IMPLEMENTATION-LADDER.md`: the one piece of ACC's design
that has to live in `alpha` itself, because it's compiler-side by
definition (`acc-foundational-design.md` §39 draws ACC as sitting
*beside* the compiler, not inside it -- the same relationship `npm`
has to Node.js, not a plugin's relationship to its host).

ACC is not merged into this repo. This module only gives the compiler
a way to *discover* capabilities that ACC (or any other installed
distribution) advertises, via the standard Python entry-point
mechanism -- the same mechanism Flask extensions, pytest plugins, etc.
use. Nothing here imports ACC, depends on ACC, or requires ACC to be
installed; a build with no ACC packages installed sees zero
capabilities and is completely unaffected.

Registration contract (deliberately minimal, per the ladder's Stage 1
scope):

    - ARKlight scans the `arklight.capabilities` entry-point group.
    - Each entry point must resolve to a zero-argument callable.
    - Calling it must return an object with a truthy, string
      `.identity` attribute -- the capability identity from
      `acc-foundational-design.md` §9 (e.g. "code.highlight").
    - That's it. No further execution, no scanning arbitrary modules,
      no implicit trust of anything beyond that one documented
      registration function -- the "Preferred model" in
      `acc-foundational-design.md` §6.

Diagnostics (per `acc-foundational-design.md` §27): malformed entry
points and duplicate capability identities both raise `CapabilityError`
at discovery time, with the offending package and capability named.
Nothing is silently skipped or silently resolved by picking a winner.
"""

from __future__ import annotations

from dataclasses import dataclass
from importlib import metadata as importlib_metadata
from typing import Any

# The entry-point group ARKlight scans for ACC capabilities.
# `acc-foundational-design.md` §10 proposed this name; Stage 1 confirms
# it rather than superseding it.
CAPABILITY_ENTRY_POINT_GROUP = "arklight.capabilities"


class CapabilityError(RuntimeError):
    """Raised for any capability discovery/registration failure.

    Covers every case `acc-foundational-design.md` §27 calls out that's
    in scope for Stage 1: a capability entry point that can't be
    imported or called, one that registers no valid identity, and two
    providers claiming the same capability identity without that
    identity being declared multi-provider.
    """


@dataclass(frozen=True)
class Capability:
    """A single discovered capability.

    `identity` is the ARKlight-facing capability name (§9); `provider`
    is the name of the distribution that registered it, kept around
    purely for diagnostics (duplicate-capability errors, `arklight
    info`-style tooling later); `value` is whatever the registration
    function returned, opaque to this module -- consumers (e.g. a
    future `code.highlight` caller) know its shape, this module does
    not need to.
    """

    identity: str
    provider: str
    value: Any


def _resolve_provider_name(entry_point: importlib_metadata.EntryPoint) -> str:
    dist = getattr(entry_point, "dist", None)
    name = getattr(dist, "name", None)
    return name or entry_point.module


def _register_one(entry_point: importlib_metadata.EntryPoint) -> Capability:
    provider = _resolve_provider_name(entry_point)

    try:
        register = entry_point.load()
    except Exception as exc:  # noqa: BLE001 -- surface any import error clearly
        raise CapabilityError(
            f"Could not load ACC entry point {entry_point.name!r} from "
            f"{provider!r} ({entry_point.value}): {exc}"
        ) from exc

    if not callable(register):
        raise CapabilityError(
            f"ACC entry point {entry_point.name!r} from {provider!r} does not "
            f"point at a callable (got {type(register).__name__!r}). A "
            f"capability entry point must resolve to a zero-argument "
            f"registration function."
        )

    try:
        value = register()
    except Exception as exc:  # noqa: BLE001 -- surface any registration error clearly
        raise CapabilityError(
            f"ACC entry point {entry_point.name!r} from {provider!r} raised "
            f"while registering: {exc}"
        ) from exc

    identity = getattr(value, "identity", None)
    if not isinstance(identity, str) or not identity:
        raise CapabilityError(
            f"ACC entry point {entry_point.name!r} from {provider!r} did not "
            f"register a valid capability identity (expected a non-empty "
            f"string `.identity` attribute on its return value, got "
            f"{identity!r})."
        )

    return Capability(identity=identity, provider=provider, value=value)


def discover_capabilities(*, allow_multi: frozenset[str] = frozenset()) -> dict[str, Capability]:
    """
    Scan installed distributions for `arklight.capabilities` entry
    points, call each one's registration function, and return a dict
    of capability identity -> `Capability`.

    `allow_multi` names capability identities that may legitimately
    have more than one provider (`acc-foundational-design.md` §28);
    Stage 1 has no known multi-provider capability, so this defaults to
    empty -- any duplicate identity is a `CapabilityError`.

    Returns an empty dict, and never raises, when no ACC packages
    (or any other `arklight.capabilities`-advertising distribution)
    are installed -- installing zero capability packages is a no-op,
    exactly as a project that never touches ACC expects.
    """
    discovered: dict[str, Capability] = {}

    for entry_point in importlib_metadata.entry_points(group=CAPABILITY_ENTRY_POINT_GROUP):
        capability = _register_one(entry_point)

        existing = discovered.get(capability.identity)
        if existing is not None and capability.identity not in allow_multi:
            raise CapabilityError(
                f"Duplicate capability {capability.identity!r}: already "
                f"provided by {existing.provider!r}, also claimed by "
                f"{capability.provider!r}. ARKlight does not choose between "
                f"capability providers automatically -- remove one, or (if "
                f"this capability is meant to support multiple providers) "
                f"that must be declared explicitly, which Stage 1 does not "
                f"yet support."
            )
        discovered[capability.identity] = capability

    return discovered


def require_capability(identity: str, capabilities: dict[str, Capability]) -> Capability:
    """
    Look up `identity` in an already-discovered capability dict, raising
    a clear `CapabilityError` (rather than a bare `KeyError`) if it's
    missing -- the "capability not found" diagnostic from
    `acc-foundational-design.md` §27, for callers (e.g. a future
    `@acc/common` `CodeBlock` component) that need a specific capability
    to be present.
    """
    capability = capabilities.get(identity)
    if capability is None:
        raise CapabilityError(
            f"Capability {identity!r} was not found among installed ACC "
            f"packages. Install the package that provides it, or check for "
            f"a typo in the capability identity."
        )
    return capability
