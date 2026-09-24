"""
Overdrive -- the project's opt-in to references the build can't verify.

The asset gate (`asset_check.py`) and the link gate (`link_check.py`)
halt the build on anything they can prove is wrong. Two of their
findings are different in kind: they aren't provably wrong, they're
*unverifiable* --

- an internal `href` that names no registered page (`/api/login`,
  `/robots.txt`): it may be a typo, or it may be a route the deployed
  host serves that this build knows nothing about; and
- a `src`/`url(...)` that isn't under `assets/` and isn't a generated
  file (`/api/avatar`): the build has no way to supply it, but a server
  might.

By default both halt the build. With

    # arklight.config.py
    CONFIG = {
        "overdrive": True,
    }

they don't. Everything else stays fatal regardless: a missing or
wrong-case file *inside* `assets/`, a directory where a file is
expected, a path that escapes the output folder, and a dead `#fragment`
are all provably broken, so there's nothing to take on trust.

Overdrive never goes quiet. Every reference it lets through is listed in
a report on stderr on every build (same channel, same non-silenceable
contract as the gates' failure reports), so a typo doesn't hide inside a
setting -- it just stops being fatal.
"""

from __future__ import annotations

from pathlib import Path

ASSET_WAIVABLE = frozenset({"outside-assets"})
LINK_WAIVABLE = frozenset({"unknown-route"})


def format_notice(asset_waived, link_waived, *, entry_path: Path) -> str:
    bar = "=" * 72
    total = len(asset_waived) + len(link_waived)
    lines = [
        bar,
        f"ARKlight OVERDRIVE -- {total} reference(s) passed through UNVERIFIED (build continues).",
        f"  site file: {entry_path}",
        '  enabled by "overdrive": True in arklight.config.py',
        "",
    ]
    for problem in link_waived:
        lines.append(f"  [UNVERIFIED-ROUTE] {problem.href}")
        lines.append(f"      {problem.detail}")
        lines.append(f"      used by: {'; '.join(problem.used_by)}")
        lines.append("")
    for problem in asset_waived:
        lines.append(f"  [UNVERIFIED-ASSET] {problem.path}")
        lines.append(f"      {problem.detail}")
        lines.append(f"      used by: {'; '.join(problem.used_by)}")
        lines.append("")
    lines.append("These point at things this build can't check or supply. Make sure your")
    lines.append('host serves them, or remove "overdrive" to have the build halt on them.')
    lines.append(bar)
    return "\n".join(lines)
