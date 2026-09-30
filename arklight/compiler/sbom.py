"""
Per-build manifest -- "what this specific compiled site is made of" --
written to `<output_dir>/sbom.txt` by `arklight.compiler.pipeline.build`.

Deliberately built from what a build's `WebsiteIR` actually references
(`arklight.backend.js.render.collect_used_runtime_features`,
`ir.experimental_usages`), never from ARKlight's own feature registries
(`FEATURES`, `ACTION_FRAGMENTS`, ...) directly -- those describe what
ARKlight is *capable of*, which is a spec sheet, not a bill of
materials. A site that never touches `Watch(...)` gets no
`Watch`-related entry here, even though ARKlight the compiler
obviously supports it.

Format: SPDX's own tag-value shape (`Tag: Value` per line) -- SPDX
calls this its "simple text-based format", both human- and
machine-readable -- but this file is NOT a validated, spec-conformant
SPDX document. It's missing things a real one requires (a resolvable
`DocumentNamespace` URI, package verification codes, full relationship
graphs, ...). Written this way anyway so that if a real SPDX/CycloneDX
exporter is ever built, the data model underneath doesn't have to
change, just the serialization -- see the `##`-prefixed header comment
this module writes into the file itself, so nobody downstream mistakes
this for the auditable thing.

Note: installed ARKlight Component Collections (ACC) packages are not
listed here -- that package-manager layer (`arklight/capabilities.py`)
does not ship on this branch, so this module only ever emits the
first-party section below.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from arklight import CHANNEL
from arklight.backend.js.render import collect_used_runtime_features
from arklight.ir.build import WebsiteIR

_NOASSERTION = "NOASSERTION"


def _spdx_ref(*parts: str) -> str:
    """A `PackageName`-derived value isn't automatically a legal
    SPDXID (letters, digits, `.`, `-` only) -- ARKlight capability/
    behavior names use `:`/`_` freely (`code.highlight`, `scroll-to`).
    Sanitize rather than reject, since this file's own header already
    disclaims full SPDX conformance."""
    joined = "-".join(parts)
    return "SPDXRef-" + "".join(c if c.isalnum() or c == "-" else "-" for c in joined)


@dataclass(frozen=True)
class _Entry:
    name: str
    ref: str
    kind: str  # human label for the PackageComment, e.g. "behavior"


def _first_party_entries(ir: WebsiteIR) -> list[_Entry]:
    usage = collect_used_runtime_features(ir)
    entries: list[_Entry] = []
    for name in sorted(usage.used_behaviors):
        entries.append(_Entry(name, _spdx_ref("behavior", name), "named behavior"))
    for name in sorted(usage.used_actions):
        entries.append(_Entry(name, _spdx_ref("action", name), "action"))
    for name in sorted(usage.used_derivations):
        entries.append(_Entry(name, _spdx_ref("derivation", name), "Computed(...) derivation"))
    for name in sorted(usage.used_platform_apis):
        entries.append(_Entry(name, _spdx_ref("platform-api", name), "PlatformAPI.* capability"))
    # One entry per distinct experimental feature this build actually
    # triggered (deduplicated by feature id -- ir.experimental_usages
    # is one entry *per use*, e.g. once per Watch(...) call).
    experimental_ids = sorted({u.feature_id for u in ir.experimental_usages})
    for feature_id in experimental_ids:
        entries.append(_Entry(feature_id, _spdx_ref("experimental", feature_id), "experimental/legacy API"))
    return entries


def build_sbom_text(ir: WebsiteIR, *, version: str) -> str:
    """
    Render the tag-value manifest text for one completed build.

    `version` is `arklight.__version__` (the caller's job to supply --
    this module doesn't import it directly so it stays easy to test
    with a fixed string instead of whatever happens to be installed).
    """
    created = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    doc_name = f"{ir.site_name}-build-manifest"

    lines = [
        "## ARKlight build manifest (SBOM-shaped, SPDX tag-value inspired)",
        "## This is NOT a validated/spec-conformant SPDX document -- see",
        "## arklight/compiler/sbom.py's module docstring for exactly what's",
        "## missing and why. It describes what THIS build actually contains,",
        "## not what ARKlight the compiler is generally capable of.",
        "",
        "SPDXVersion: SPDX-2.3-informal",
        "DataLicense: CC0-1.0",
        f"DocumentName: {doc_name}",
        "SPDXID: SPDXRef-DOCUMENT",
        f"Creator: Tool: ARKlight-v{version} ({CHANNEL})",
        f"Created: {created}",
        "",
        "## -- ARKlight itself --------------------------------------------------",
        "PackageName: ARKlight",
        "SPDXID: SPDXRef-Package-arklight",
        f"PackageVersion: {version}",
        "PackageSupplier: Organization: ARKlight",
        "PackageLicenseDeclared: GPL-3.0-or-later",
        "PrimaryPackagePurpose: APPLICATION",
        "PackageComment: The compiler that produced this build.",
        "Relationship: SPDXRef-DOCUMENT DESCRIBES SPDXRef-Package-arklight",
        "",
    ]

    first_party = _first_party_entries(ir)
    lines.append("## -- First-party runtime pieces shipped in this build ------------------")
    lines.append("## Authored in-tree by ARKlight's own author, not installed separately.")
    lines.append("## Only entries this build's IR actually references are listed, same")
    lines.append("## \"only ship what's used\" principle the compiler itself follows when")
    lines.append("## it renders the runtime JS.")
    lines.append("")
    if not first_party:
        lines.append("## This build references no optional first-party runtime pieces")
        lines.append("## (no named behaviors, actions, Computed(...) derivations, Platform")
        lines.append("## API calls, or experimental/legacy features).")
        lines.append("")
    else:
        for entry in first_party:
            lines.extend(
                [
                    f"PackageName: {entry.name}",
                    f"SPDXID: {entry.ref}",
                    f"PackageVersion: {version}",
                    "PackageSupplier: Person: ARKlight author (in-tree)",
                    "PrimaryPackagePurpose: LIBRARY",
                    f"PackageComment: {entry.kind}, shipped as part of ARKlight's own runtime.",
                    f"Relationship: SPDXRef-DOCUMENT DESCRIBES {entry.ref}",
                    "",
                ]
            )

    return "\n".join(lines).rstrip() + "\n"
