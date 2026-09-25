"""
`Provider`. Stage 1 of 6 (`v0.065`) laid down the contract itself;
stage 6 of 6 (`v0.070`, see below) finalizes its capability vocabulary.

Settled design record: `docs/Foundational/PROVIDER-SDK.md` (the
six-rung `v0.065`-`v0.070` ladder that staged this is fully shipped and
has been retired from `docs/Proposals/`/`docs/Implementation/`; see
that file for the graduation). A `Provider` is how a
site *declares* that it talks to an external service at runtime (a
hosted database, an auth service, a hand-rolled API). It is named
"Provider", not "backend", because `arklight/backend/` already means
*output target* (HTML, CSS, JS, Android, Desktop).

**An interface only.** This module holds the closed vocabulary a
declaration may draw from and the value a site attaches to
`Site(provider=...)`. It contains no vendor code, no networking code,
and no opinion about auth or schemas. A declared Provider adds
nothing to the generated pages or stylesheet (byte-identical with and
without one). Two things in the output differ: the reports every gated
experimental feature already gets (the devtools console reminder in
`arklight.js` and an entry in `sbom.txt`), and, from stage 3 (`v0.067`),
one read-only config object in `arklight.js`, `window.ARKLIGHT_PROVIDER`
(`{name, capabilities}`), which the site author's own code reads to learn
what the site declared. It carries no DOM hooks or `State(...)` keys yet --
there is no authoring surface to wire a capability to one. The
concrete implementation (the real Firebase SDK, your own fetch calls)
is the site author's own code, never generated or checked by ARKlight. What
ARKlight *does* own is the part the compiler can decide ahead of time:
whether the declaration is well-formed, and that using it is flagged
(`arklight.experimental.FEATURES["provider-integration"]`).

**Finalized vocabulary (`Provider` stage 6 of 6, `v0.070`).** Section
7.2 asked whether `capabilities` would stay free-form or become a
closed, finalized set. Five stages of real usage inside this repo (IR
threading, JS emission, script loading, `arklight search`) never
needed a fifth well-known name, so `PROVIDER_CAPABILITIES` -- the four
the proposal itself listed -- is locked in: nothing is added, renamed
or removed here again, and the word "provisional" is retired from
this module, `arklight/ir/validate.py` and `arklight/experimental.py`.

That finalizes the *known* vocabulary, not the *only* vocabulary a
Provider can ever declare. Re-reading section 2's own framing --
a Provider exists so a site can point at *any* external service, the
same way a user-defined component covers markup ARKlight doesn't ship
a name for -- a hard four-name ceiling would contradict that: a site
whose service genuinely needs a fifth kind of capability would have no
way to say so short of misusing one of the four. So stage 6 also opens
a namespaced escape hatch, `CUSTOM_CAPABILITY_PREFIX` (`"custom:"`):
`Provider.declare(capabilities=["auth", "custom:inventory-sync"])`
names a capability the four well-known ones don't cover, without
touching `PROVIDER_CAPABILITIES` or waiting on a new ARKlight release.
This mirrors two established precedents for extending a small closed
protocol without renegotiating it: the Language Server Protocol's
`experimental`/vendor-namespaced capability keys (closed core, an
explicitly separate namespace for anything a client or server adds on
its own), and OAuth's `custom:`-prefixed scope convention (a reserved
prefix that opts a string out of the registered-scope vocabulary
instead of colliding with it). An unprefixed name is still checked
against the closed four -- `"raed"` still fails as an unknown
capability, not a new custom one -- so the typo discipline the
original closed set existed for is unchanged; only a name that opts in
with the prefix gets the open, SDK-flexible treatment.
"""

from __future__ import annotations

from dataclasses import dataclass

# The capabilities a Provider declaration may name without the
# `custom:` prefix below. The four the proposal itself lists (section
# 7, question 2); finalized as of stage 6 (`v0.070`) -- see this
# module's docstring. Declaring a capability says only "this site uses
# this kind of thing from the service" -- it does not say how, and
# ARKlight never implements any of them.
PROVIDER_CAPABILITIES: tuple[str, ...] = ("auth", "read", "write", "subscribe")

# The escape hatch stage 6 adds: a capability name prefixed this way
# is never checked against `PROVIDER_CAPABILITIES` -- it is the site's
# own vocabulary word for something the four well-known names don't
# cover, the same way a user-defined component's name is never checked
# against a fixed list of markup tags. See this module's docstring for
# the LSP/OAuth precedents this convention follows.
CUSTOM_CAPABILITY_PREFIX = "custom:"

def _is_valid_custom_label(label: str) -> bool:
    """Whether `label` (the part after `custom:`) looks like a name:
    lowercase, starting with a letter, with digits/`-`/`_` allowed
    after the first character for multi-word labels
    (`inventory-sync`) but never doubled or trailing (`--`, `-`-at
    either end). No `re` import here on purpose -- see
    `test_the_provider_module_holds_no_network_or_vendor_code`, which
    checks this module imports nothing beyond the standard library
    pieces it already needs; plain string/character checks cover this
    without adding one."""
    if not label or not label[0].isalpha() or not label.islower():
        return False
    if label[-1] in "-_" or "--" in label or "__" in label or "-_" in label or "_-" in label:
        return False
    return all(ch.isdigit() or ch in "-_" or (ch.isalpha() and ch.islower()) for ch in label)


def is_custom_capability(cap: str) -> bool:
    """Whether `cap` is a well-formed `custom:`-prefixed capability --
    the prefix present *and* a valid label after it. A string that
    merely starts with the prefix but has a malformed or empty label
    (`"custom:"`, `"custom:Auth"`, `"custom:-x"`) is not: it falls
    through to the unknown-capability error instead of being accepted
    as some new, oddly-named custom capability."""
    if not cap.startswith(CUSTOM_CAPABILITY_PREFIX):
        return False
    label = cap[len(CUSTOM_CAPABILITY_PREFIX):]
    return _is_valid_custom_label(label)


def is_known_capability(cap: str) -> bool:
    """Whether `cap` is accepted by a `Provider.declare(capabilities=...)`
    call: one of the four finalized well-known names, or a well-formed
    `custom:`-prefixed name (stage 6, `v0.070`)."""
    return cap in PROVIDER_CAPABILITIES or is_custom_capability(cap)


@dataclass(frozen=True)
class ProviderDeclaration:
    """
    What `Provider.declare(name=..., capabilities=[...])` returns: an
    immutable, already-validated declaration, ready for
    `Site(provider=...)`.

    Validation lives here, not only in `Provider.declare`, so a
    `ProviderDeclaration` built by hand can't hold an invalid value
    either. `capabilities` is stored as a tuple in the order it was
    declared, whatever sequence type it was passed as.
    """

    name: str
    capabilities: tuple[str, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.name, str) or not self.name.strip():
            raise ValueError(
                f"Provider.declare(name=...) needs a non-empty string label "
                f"(any name you like -- it is not a fixed list of vendors), "
                f"got {self.name!r}."
            )
        caps = self.capabilities
        # A bare string is iterable, so `capabilities="auth"` would
        # otherwise be read as the four one-letter capabilities
        # "a", "u", "t", "h" and fail with a confusing message.
        if not isinstance(caps, (list, tuple)):
            raise ValueError(
                f"Provider.declare(capabilities=...) needs a list of capability "
                f'names such as ["auth", "read"], got {caps!r}.'
            )
        if not caps:
            raise ValueError(
                "Provider.declare(capabilities=...) needs at least one "
                "capability -- a Provider that declares none has nothing to "
                f"describe. Known capabilities are: {', '.join(PROVIDER_CAPABILITIES)}."
            )
        not_strings = [cap for cap in caps if not isinstance(cap, str)]
        if not_strings:
            raise ValueError(
                f"Provider.declare(capabilities=...) entries must be strings, "
                f"got {not_strings!r}."
            )
        reused_well_known = [
            cap
            for cap in caps
            if cap.startswith(CUSTOM_CAPABILITY_PREFIX)
            and cap[len(CUSTOM_CAPABILITY_PREFIX):] in PROVIDER_CAPABILITIES
        ]
        if reused_well_known:
            raise ValueError(
                f"Provider.declare(capabilities=...) prefixes "
                f"{reused_well_known!r} with {CUSTOM_CAPABILITY_PREFIX!r}, but "
                f"{[cap[len(CUSTOM_CAPABILITY_PREFIX):] for cap in reused_well_known]!r} "
                f"{'is' if len(reused_well_known) == 1 else 'are'} already a "
                f"well-known capability -- declare it without the prefix instead."
            )
        unknown = [cap for cap in caps if not is_known_capability(cap)]
        if unknown:
            raise ValueError(
                f"Provider.declare(capabilities=...) names unknown "
                f"capabilit{'y' if len(unknown) == 1 else 'ies'} {unknown!r}. "
                f"Known capabilities are: {', '.join(PROVIDER_CAPABILITIES)}. For "
                f"a capability of your own that these four don't cover, prefix "
                f"it instead, e.g. {CUSTOM_CAPABILITY_PREFIX}inventory-sync -- "
                f"see arklight/provider.py."
            )
        duplicated = sorted({cap for cap in caps if caps.count(cap) > 1})
        if duplicated:
            raise ValueError(
                f"Provider.declare(capabilities=...) lists {duplicated!r} more "
                f"than once -- name each capability a single time."
            )
        object.__setattr__(self, "capabilities", tuple(caps))


# ---------------------------------------------------------------------------
# `Provider`, stage 5 of 6 (`v0.069`): `arklight search` integration.
#
# A registry of every `ProviderDeclaration` a `Site(provider=...)` has
# attached in this process, keyed by the declaration's `name`. It is the
# same shape as `arklight.ir.components.COMPONENT_REGISTRY`: populated as
# a side effect of building the site, read by `arklight search` so the
# declared contract can be looked up by name. Like user components, it is
# only populated in a process that has actually constructed the `Site`;
# `arklight search` alone never loads a project's site file, so a provider
# is only visible to it in that situation. See `arklight.cli.search`.
# ---------------------------------------------------------------------------

PROVIDER_REGISTRY: dict[str, ProviderDeclaration] = {}


def register_provider(declaration: ProviderDeclaration) -> None:
    """Record `declaration` in `PROVIDER_REGISTRY` under its `name`.

    Called from `Site.__init__` when `Site(provider=...)` is given. A
    later declaration with the same `name` replaces the earlier one --
    one provider per `Site`, and a name is a free label, so two sites
    that reuse a label are simply the last one constructed.
    """
    if not isinstance(declaration, ProviderDeclaration):
        raise ValueError(
            "register_provider() needs a ProviderDeclaration, got "
            f"{declaration!r}."
        )
    PROVIDER_REGISTRY[declaration.name] = declaration


def resolve_provider(name: str) -> ProviderDeclaration | None:
    """Case-insensitive lookup of a registered provider by its `name`.

    Returns the declaration, or `None` if no registered provider carries
    that label. Exact match on the label, ignoring case; no fuzzy
    matching (a provider name is a free label, not a closed vocabulary).
    """
    lowered = {key.lower(): key for key in PROVIDER_REGISTRY}
    canonical = lowered.get(name.lower())
    if canonical is None:
        return None
    return PROVIDER_REGISTRY[canonical]
