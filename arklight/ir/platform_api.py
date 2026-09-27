"""
Platform API interface layer (`v0.065`, accepted from
`docs/Proposals/PLATFORM-API-IR-PROPOSAL.md`; see
`docs/Foundational/PLATFORM-APIS.md` for the settled design record).

This module is the compiler-owned half of the split the proposal
argues for throughout: **the compiler defines the platform API
interface, each platform backend supplies its own implementation.**
Nothing in this module contains a single line of JavaScript, Kotlin,
or C -- it only knows *that* `notify` exists, what arguments it takes,
what permission it implies, and which backends currently implement it.
The actual implementations live per-backend (see
`arklight/backend/js/platform_apis/` for the Web reference
implementation the proposal's Section 5 calls "the default, not a
fallback").

Three registries, matching the proposal's own terminology (Section 3):

- `PLATFORM_API_REGISTRY` -- the platform API interface registry
  (Section 19): one `PlatformAPISpec` per capability, this compiler's
  full knowledge of what that capability *means*, independent of any
  backend.
- `BACKEND_PLATFORM_API_SUPPORT` -- the backend capability-discovery
  table (Section 10): which capabilities each named backend currently
  implements. Web is the reference implementation and starts non-empty;
  Android and Linux Desktop start empty on purpose (Section 6/22 --
  "native implementations are earned by backends", not granted because
  a backend merely exists).
- Nothing here is a `PlatformAPIRequest`'s *value* -- that's
  `arklight.ast.nodes.PlatformAPIRef`, the small structured object an
  author actually writes (`PlatformAPI.notify(...)`), validated
  against the registries below the same way `arklight.ast.nodes.
  ActionRef` is validated against `ACTION_REGISTRY`.

Versioning (Section 20) is tracked but deliberately minimal at this
stage: every interface below is `version=1`, and nothing in this
module resolves a version mismatch yet -- there is exactly one version
of each interface in existence, so there is nothing to resolve. The
`version` field exists now so that adding a `notify@2` later is a
matter of extending this table, not inventing the concept from
scratch under deadline.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class PlatformAPISpec:
    """
    One platform API interface's full compiler-owned contract (Section
    7 of the proposal): its version, the keyword arguments it accepts,
    the permission(s) it implies exist on the target platform, and a
    short human-readable description. Nothing about *how* any backend
    implements the capability lives here -- see this module's
    docstring.
    """

    version: int
    args: tuple[str, ...] = field(default_factory=tuple)
    permissions: tuple[str, ...] = field(default_factory=tuple)
    description: str = ""


# The platform API interface registry (Section 19). Deliberately small
# at acceptance -- Section 23's "Initial scope" is the architecture,
# not a large API catalogue -- so this starts with exactly the two
# capabilities the Web reference implementation (Section 5) actually
# ships against: a user-visible notification, and a plain-text
# clipboard write. Both are one-shot, argument-in/no-value-out calls
# (Section 8: a `PlatformAPIRequest` carries `arguments`, not a return
# binding into `State(...)` -- unlike `Action.geolocate`, which is a
# state-mutating `Action`, not a Platform API; see `docs/Foundational/
# PLATFORM-APIS.md` Section 6 for that boundary). Extending this table
# is how a future capability (clipboard *read*, filesystem, device
# info, ...) gets added -- one entry here, plus a per-backend
# implementation, never a change to the validation/dispatch machinery
# that reads this table.
PLATFORM_API_REGISTRY: dict[str, PlatformAPISpec] = {
    "notify": PlatformAPISpec(
        version=1,
        args=("title", "body"),
        permissions=("notifications",),
        description="Show a user-visible notification (title, optional body).",
    ),
    "clipboard_write": PlatformAPISpec(
        version=1,
        args=("text",),
        permissions=("clipboard-write",),
        description="Write plain text to the system clipboard.",
    ),
}

KNOWN_PLATFORM_APIS = frozenset(PLATFORM_API_REGISTRY)

# Backend capability discovery (Section 10). A backend name maps to
# the frozenset of capability names *that backend's own implementation
# currently supports* -- not the full `PLATFORM_API_REGISTRY`. "web"
# is the compiler's own backend name for the combined HTML/CSS/JS
# output (matching `arklight.backend.js.render.JSBackend.name`, the
# backend that actually emits the dispatch code -- see
# `arklight/backend/js/platform_apis/`). "android"/"desktop" are
# listed and start empty on purpose (Section 6): those backends exist,
# but have not yet implemented any platform API interface, so nothing
# requested against them succeeds today -- see `check_backend_support`
# below for the diagnostic a build against either backend gets instead
# of a silent no-op.
BACKEND_PLATFORM_API_SUPPORT: dict[str, frozenset[str]] = {
    "web": frozenset({"notify", "clipboard_write"}),
    "android": frozenset(),
    "desktop": frozenset(),
}


class PlatformAPIError(Exception):
    """
    Raised when a build requests a platform API capability the
    selected backend does not implement (Section 11: "compilation must
    fail with a clear diagnostic"). Deliberately its own exception
    type, not a bare `ValueError`/`ValidationError` -- the compiler
    pipeline's own `arklight.compiler.pipeline.build()` already wraps
    any exception a backend's `render()` raises into a `CompileError`
    naming that backend, so this only needs to carry the ARK-numbered,
    source-located message itself; it does not need its own pipeline
    wiring to be surfaced correctly.
    """


def backend_supports(backend_name: str, capability: str) -> bool:
    """Section 10's actual check: does `backend_name` currently
    implement `capability`? Unknown backend names support nothing
    (fail closed, never fail open)."""
    return capability in BACKEND_PLATFORM_API_SUPPORT.get(backend_name, frozenset())


def check_backend_support(
    used_capabilities: set[str],
    *,
    backend_name: str,
) -> None:
    """
    Section 11's compile-time backend-capability check, run once per
    backend against the full set of platform API capabilities that
    backend's own IR walk found in use. Capability *existence* and
    *argument* validity are already enforced earlier, at Validation
    (`arklight.ir.validate._validate_platform_api`) -- this is
    strictly the backend-support half: "the compiler must not silently
    remove the request... or defer a known incompatibility to
    runtime." Raises `PlatformAPIError` naming every unsupported
    capability at once (not just the first one hit), matching the
    proposal's own `ARK1234`-style example diagnostic shape.
    """
    unsupported = sorted(
        capability for capability in used_capabilities if not backend_supports(backend_name, capability)
    )
    if not unsupported:
        return
    names = ", ".join(repr(name) for name in unsupported)
    raise PlatformAPIError(
        f"platform interface(s) {names} requested by this site are not "
        f"implemented by backend {backend_name!r}. See "
        f"docs/Proposals/PLATFORM-API-IR-PROPOSAL.md Section 6/22 -- a "
        f"backend only gains a platform API capability once it has "
        f"implemented that capability's own contract, not merely "
        f"because the backend exists."
    )
