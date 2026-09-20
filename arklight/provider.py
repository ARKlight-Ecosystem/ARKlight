"""
`Provider`, stage 1 of 6 (`v0.065`): the contract itself.

Accepted from `docs/Proposals/PROVIDER-SDK-PROPOSAL.md`; the per-version
preview is in `docs/version history/v0.065.md`. A `Provider` is how a
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

**Provisional vocabulary.** `PROVIDER_CAPABILITIES` is a closed set on
purpose, the same discipline `Action.*`/`Derive.*` use, so a typo fails
the build instead of silently declaring nothing (proposal, section 7,
question 2). It is *provisional*: the ladder finalizes the vocabulary in
its last stage, so a name may still be added, renamed or removed until
then.
"""

from __future__ import annotations

from dataclasses import dataclass

# The capabilities a Provider declaration may name. The four the
# proposal itself lists (section 7, question 2); provisional until the
# ladder's last stage finalizes the vocabulary. Declaring a capability
# says only "this site uses this kind of thing from the service" -- it
# does not say how, and ARKlight never implements any of them.
PROVIDER_CAPABILITIES: tuple[str, ...] = ("auth", "read", "write", "subscribe")


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
        unknown = [cap for cap in caps if cap not in PROVIDER_CAPABILITIES]
        if unknown:
            raise ValueError(
                f"Provider.declare(capabilities=...) names unknown "
                f"capabilit{'y' if len(unknown) == 1 else 'ies'} {unknown!r}. "
                f"Known capabilities are: {', '.join(PROVIDER_CAPABILITIES)}."
            )
        duplicated = sorted({cap for cap in caps if caps.count(cap) > 1})
        if duplicated:
            raise ValueError(
                f"Provider.declare(capabilities=...) lists {duplicated!r} more "
                f"than once -- name each capability a single time."
            )
        object.__setattr__(self, "capabilities", tuple(caps))
