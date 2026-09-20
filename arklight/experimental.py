"""
Experimental / legacy API registry -- see `docs/EXPERIMENTAL-APIS.md`.

ARKlight's default surface is intrinsic-layout-only (see
`docs/DESIGN-NOTES.md`): nothing in it is keyed to a viewport width,
device class, or browser engine. A feature that steps outside that
model isn't refused outright, but it isn't silent either -- it has to
be registered here, and every use prints a warning, both inline (at
the moment it's detected) and as an end-of-run summary. This module
owns the *content* of those warnings; callers (the compiler pipeline,
`arklight/pwa.py`, the CLI) own *when* to call `emit()`.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable


@dataclass(frozen=True)
class ExperimentalFeature:
    id: str
    # One-line reason shown on the compact, inline "unlocked an
    # experimental API" banner (the `-> Note:` line).
    inline_note: str
    # Full paragraph, pre-wrapped to short lines, for the end-of-run
    # summary block ("⚠ Experimental API enabled").
    detail_lines: list[str]
    # Trailing "Legacy API detected" note -- why it's still here /
    # what to prefer instead.
    legacy_note: str
    # Whether heavy reliance on this feature is a sign of a genuine
    # missing-feature gap (worth a PR against ARKlight or ACC) rather
    # than a deliberate, permanent design tradeoff. `css-media-queries`
    # is the model case of `False`: ARKlight *chose* intrinsic layout
    # over viewport queries on purpose, so "lots of media-query usage"
    # isn't a signal anything is missing, just that this project needs
    # the escape hatch a lot. Defaults to `True` since most features
    # registered here are, in fact, "we haven't built the real thing
    # yet" gaps -- see `heavy_reliance_nudge` below.
    upstream_candidate: bool = True


FEATURES: dict[str, ExperimentalFeature] = {
    "css-media-queries": ExperimentalFeature(
        id="css-media-queries",
        inline_note="Media queries target viewport characteristics rather than intrinsic layout.",
        detail_lines=[
            "Media queries target viewport characteristics rather than",
            "intrinsic layout.",
            "Device-specific breakpoints reduce portability and may behave",
            "differently across Android devices, tablets, foldables and",
            "desktop browsers.",
            "Prefer intrinsic layouts (.grid, .switcher, .cluster,",
            "minmax(), auto-fit, clamp()) whenever possible.",
        ],
        legacy_note=(
            "Viewport-keyed rules (whether from site.media_query(...) or a "
            "node's responsive_style={...} prop) step outside ARKlight's "
            "intrinsic layout model and are retained as an explicit escape "
            "hatch, not the default path. New projects should prefer "
            ".switcher, .grid, .cluster, .sidebar, or other intrinsic "
            "layout primitives wherever the design can be expressed that way."
        ),
        # Deliberate, permanent design tradeoff (intrinsic layout over
        # viewport queries) -- not a gap. Heavy use isn't a PR signal.
        upstream_candidate=False,
    ),
    "experimental-install-pwa": ExperimentalFeature(
        id="experimental-install-pwa",
        inline_note="Runtime stability relies entirely on native browser engine support.",
        detail_lines=[
            "The install button depends on the `beforeinstallprompt` event,",
            "which is not part of any web standard and is not implemented",
            "by every browser engine (notably absent or partial on several",
            "non-Chromium browsers, and inconsistent across Android OEM",
            "WebView builds).",
            "Where unsupported, the button silently has nothing to do --",
            "always provide a normal way to use the site alongside it.",
        ],
        legacy_note=(
            "Native install prompts are not standardized across browsers -- "
            "behavior (and availability) varies by engine and platform. "
            "Treat this as a progressive enhancement, not the only way to "
            "install or use the site."
        ),
    ),
    "css-import": ExperimentalFeature(
        id="css-import",
        inline_note="The imported file's contents can't be validated by ARKlight.",
        detail_lines=[
            "@import pulls in a stylesheet from a URL at request time --",
            "the imported file's contents can't be validated by ARKlight,",
            "unlike every other rule this project generates.",
            "It also blocks the CSS Object Model until it resolves, which",
            "can delay first paint, and its availability/behavior depends",
            "on the visiting network and browser having access to that URL.",
            "Prefer Page(links=[{'rel': 'stylesheet', 'href': ...}]) for an",
            "external stylesheet where possible -- it doesn't block the CSSOM",
            "the way @import does.",
        ],
        legacy_note=(
            "An @import URL is opaque to ARKlight -- its contents are fetched "
            "and applied by the browser at request time, so nothing about "
            "them is checked the way every other generated rule is. Retained "
            "as an explicit escape hatch for the rare case a stylesheet truly "
            "isn't reachable via Page(links=[...]), not the default path."
        ),
    ),
    "raw-postprocess": ExperimentalFeature(
        id="raw-postprocess",
        inline_note="Runs your own code directly over the final output files, completely unchecked by ARKlight.",
        detail_lines=[
            "OFFICIALLY DEPRECATED -- Site.raw_postprocess(fn) no longer",
            "registers or runs anything; calling it only prints a log",
            "pointing at its replacement. This entry stays registered for",
            "historical/documentation purposes only (old builds, old docs,",
            "and anything that still calls experimental.emit(\"raw-postprocess\")",
            "directly), not because the escape hatch itself still exists.",
            "",
            "This used to be an advanced experimental feature that handed",
            "your function the *entire* dict of generated output files --",
            "every path, every byte -- after every backend had already",
            "rendered and postprocessed them, with whatever it returned",
            "written to disk exactly as-is. Nothing about it was validated,",
            "normalized, or checked against ARKlight's layout model,",
            "HTML/CSS/JS correctness, or anything else the rest of the",
            "pipeline guarantees -- it was the single widest surface",
            "exposed to user code in the whole project, hence the removal.",
            "",
            "What most callers actually used it for -- adding hand-written",
            "JS alongside the generated arklight.js runtime -- is now",
            "site.register_script_extension(...)",
            "(arklight.backend.script_extension.ScriptExtension): narrower,",
            "class-based, and it only ever touches arklight.js.",
        ],
        legacy_note=(
            "Officially deprecated and removed as of the script-extension "
            "capability. Site.raw_postprocess(fn) is now a no-op that only "
            "logs. Prefer site.register_script_extension(...) "
            "(arklight.backend.script_extension.ScriptExtension) for JS "
            "injection, or a real Backend subclass overriding postprocess() "
            "(see arklight.backend.base.Backend) for anything reusable or "
            "dependent on another backend's output."
        ),
    ),
    "script-extension": ExperimentalFeature(
        id="script-extension",
        inline_note=(
            "Hand-written JS, lowered from a Svelte-script-only subclass, "
            "appended to arklight.js -- unchecked the way every other "
            "escape hatch here is."
        ),
        detail_lines=[
            "ScriptExtension (arklight.backend.script_extension) is the",
            "class-based successor to site.raw_postprocess(fn) for the one",
            "job most raw_postprocess uses were actually for: adding",
            "hand-written JS alongside the arklight.js runtime every page",
            "already loads.",
            "Its surface is narrower than raw_postprocess's -- only the",
            "<script> portion of Svelte single-file-component syntax is",
            "accepted, and only arklight.js is ever touched, never an",
            "arbitrary output file -- but the JS itself is still unchecked:",
            "no eval, no new Function, but also no guarantee it's even",
            "syntactically valid, the same as every other hand-written JS",
            "surface ARKlight ships.",
            "Usage is expected to carry a '#include <expapilib.ARKlight>'",
            "marker comment in the subclass's own source file. Missing it",
            "doesn't block the build -- it just adds one more warning on",
            "top of this one.",
        ],
        legacy_note=(
            "Not a legacy API -- ScriptExtension is new, offered as the "
            "narrower, class-based successor to site.raw_postprocess(fn) "
            "for JS-injection specifically. Flagged for the same reason "
            "every hand-written-JS escape hatch here is: ARKlight cannot "
            "validate the script's contents the way it validates its own "
            "generated runtime."
        ),
    ),
    "provider-integration": ExperimentalFeature(
        id="provider-integration",
        inline_note=(
            "This site declares a Provider -- ARKlight does not implement, "
            "audit, or guarantee the external service it points at."
        ),
        detail_lines=[
            "A Provider declares that this site talks to an external service",
            "(a hosted database, an auth service, your own API) at runtime.",
            "ARKlight only checks the declaration itself against a closed",
            "vocabulary of capabilities, and exposes it to your own scripts",
            "as window.ARKLIGHT_PROVIDER. It ships no vendor SDK, makes no",
            "network calls, and does not implement, audit, or guarantee the",
            "service the declaration points at.",
            "Networking, authentication, data handling and security are",
            "entirely the responsibility of whatever concrete implementation",
            "you supply. ARKlight has no opinion on auth flows, token storage",
            "or security rules, and takes no responsibility for them.",
            "",
            "The contract is still being staged: the capability vocabulary",
            "is provisional until the last stage of the Provider ladder",
            "finalizes it, so a declaration that is valid today may need",
            "updating when you upgrade ARKlight.",
        ],
        legacy_note=(
            "Not a legacy API -- Provider is new, and nothing here is being "
            "kept for backward compatibility yet. It is flagged because the "
            "external service a site points at is outside anything ARKlight "
            "can validate, and because the contract itself (the capability "
            "vocabulary in particular) is still provisional."
        ),
        # A deliberate boundary, not a missing-feature gap: the concrete
        # implementation being the site author's own code is the whole
        # design (PROVIDER-SDK-PROPOSAL.md, sections 2 and 6). The
        # heavy-reliance nudge ("open a pull request for your missing
        # feature") would be the wrong advice to give someone who simply
        # uses a Provider, the same reasoning `css-media-queries` uses.
        upstream_candidate=False,
    ),
}


@dataclass
class ExperimentalUsage:
    """One recorded use of an experimental feature, enough to render
    both the inline banner and (deduplicated) the end-of-run block."""

    feature_id: str
    component: str | None = None


def format_inline_banner(usage: ExperimentalUsage) -> str:
    """The compact, interleaved-with-stage-log banner, printed the
    moment a feature is detected -- see `docs/EXPERIMENTAL-APIS.md`
    "CLI contract"."""
    feature = FEATURES[usage.feature_id]
    if usage.component:
        header = (
            f"\u26a0\ufe0f  [EXPERIMENTAL FEATURE ACTIVE]: Component "
            f"{usage.component!r} unlocked an experimental API."
        )
    else:
        header = f"\u26a0\ufe0f  [EXPERIMENTAL FEATURE ACTIVE]: {feature.id} unlocked an experimental API."
    return "\n".join(
        [
            header,
            f"   -> Feature: {feature.id}",
            f"   -> Note: {feature.inline_note}",
        ]
    )


def format_summary_block(feature_id: str) -> str:
    """The full end-of-run block for one *distinct* feature -- callers
    are responsible for deduplicating by `feature_id` first (one block
    per feature actually used, not once per occurrence)."""
    feature = FEATURES[feature_id]
    lines = ["\u26a0 Experimental API enabled", f"    Feature : {feature.id}"]
    lines.extend(f"    {line}" for line in feature.detail_lines)
    lines.append(f"Legacy API detected: {feature.id}")
    lines.append(feature.legacy_note)
    return "\n".join(lines)


def emit(
    feature_id: str,
    *,
    on_warning: Callable[[str], None] | None = None,
    component: str | None = None,
) -> ExperimentalUsage:
    """
    Record + (if `on_warning` given) immediately print the inline
    banner for one use of `feature_id`. Returns the `ExperimentalUsage`
    so the caller can collect it for the end-of-run summary (see
    `format_summary_block`). Raises `KeyError` if `feature_id` isn't
    registered in `FEATURES` -- fail loudly rather than silently
    skipping the warning for a typo'd id.
    """
    if feature_id not in FEATURES:
        raise KeyError(
            f"{feature_id!r} isn't a registered experimental feature -- "
            f"add it to arklight.experimental.FEATURES first (see "
            f"docs/EXPERIMENTAL-APIS.md)."
        )
    usage = ExperimentalUsage(feature_id=feature_id, component=component)
    if on_warning is not None:
        on_warning(format_inline_banner(usage))
    return usage


def print_summary(usages: list[ExperimentalUsage], *, file=None, show_nudge: bool = True) -> None:
    """Print one deduplicated end-of-run block per distinct feature
    id in `usages`, in first-seen order, followed by a heavy-reliance
    nudge (see `heavy_reliance_nudge`) if warranted. No-op for an empty
    list.

    `show_nudge=False` suppresses only the nudge line -- the per-
    feature warning blocks above it always print regardless, since
    those are the actual safety notice this module exists for. Callers
    source `show_nudge` from a project's `arklight.config.py`
    (`CONFIG = {"experimental": {"heavy_reliance_nudge": False}}`) --
    see docs/Foundational/EXPERIMENTAL-APIS.md.
    """
    import sys

    out = file or sys.stdout
    seen: set[str] = set()
    for usage in usages:
        if usage.feature_id in seen:
            continue
        seen.add(usage.feature_id)
        print(format_summary_block(usage.feature_id), file=out)

    if not show_nudge:
        return
    nudge = heavy_reliance_nudge(usages)
    if nudge is not None:
        print(nudge, file=out)


# How many total uses of upstream-candidate features (see
# `ExperimentalFeature.upstream_candidate`) in a single build trip the
# heavy-reliance nudge. Deliberately a *use* count, not a distinct-
# feature count: someone calling `Site.raw_postprocess(...)` five
# times in one project is leaning on the escape hatch just as hard as
# someone touching two different experimental features once each.
# Picked small on purpose -- this is a normal, per-build console
# nudge, not a rare event; it's fine for it to print on every build of
# a project that's already decided to lean on an escape hatch.
HEAVY_RELIANCE_THRESHOLD = 3


def heavy_reliance_nudge(
    usages: list[ExperimentalUsage], *, threshold: int = HEAVY_RELIANCE_THRESHOLD
) -> str | None:
    """
    If this build's *upstream-candidate* experimental usages (features
    with `upstream_candidate=True` -- i.e. ones that represent an
    actual missing-feature gap, not a deliberate permanent tradeoff
    like `css-media-queries`) meet `threshold`, return a short nudge
    pointing at ARKlight's and ACC's GitHub repos as places to file the
    missing feature instead of leaning on the escape hatch forever.
    Returns `None` if the threshold isn't met -- most builds print
    nothing extra here.

    This is a single-build heuristic only: no on-disk log, no
    across-build history. A project that hits the threshold once will
    see this every build until its usage drops below it again, which
    is the intended, non-naggy behavior -- it reflects the project's
    current reliance, not a one-time trip.
    """
    eligible = [usage for usage in usages if FEATURES[usage.feature_id].upstream_candidate]
    if len(eligible) < threshold:
        return None

    features_used = sorted({usage.feature_id for usage in eligible})
    return "\n".join(
        [
            "[Rei] Hey, just a heads up -- if you're relying on experimental APIs a lot",
            f"[Rei] ({len(eligible)} experimental-API uses this build, across: "
            f"{', '.join(features_used)})",
            "[Rei] Might be a good idea to open a pull request for your missing feature",
            "[Rei] In either the ARKlight or ARKlight-Component-Collections GitHub repo",
        ]
    )
