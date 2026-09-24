"""
Rei -- the compiler narrator (`arklight build --narrate`).

Implements `docs/Proposals/REI-COMPILER-NARRATOR-PROPOSAL.md`
(`v0.065`, shipped as `0.06510` -- see
`docs/version history/v0.065.md`).

Rei is a **pure-Python, deterministic pattern renderer**: given the
same stage-completion message (or the same failure), she always
produces the same sentence(s). No JSON, no config file of her own, no
network access, no LLM -- see the proposal's §4. She hooks the exact
same stage-completion calls `--verbose` already prints from
(`arklight.compiler.pipeline`'s `on_stage=` callback) -- this module
adds a second *renderer* over those calls, not a new instrumentation
pass, and defines no new compiler hooks of its own.

A classic ELIZA implementation is vendored, read-only, at
`docs/reference/eliza/eliza.py` as a *studied design reference only*
(the proposal's §4: "ELIZA as a studied reference, not a dependency").
Nothing in `arklight/` imports it, and this module doesn't either --
Rei's stage-to-sentence mapping below is an original implementation,
purpose-built for structured compiler events, not a reuse of ELIZA's
free-text script-transformation machinery.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Callable

# Every line Rei prints starts with this, the same way every
# `--verbose`/`--debug` line starts with `[ARKlight]` -- see
# `arklight.cli.main._STAGE_PREFIX`.
REI_PREFIX = "[Rei]"

# `default_mode` values `arklight.config.py`'s `"rei"` section and the
# `--verbose`/`--narrate` flags resolve to. Kept here (rather than only
# in `arklight.cli.main`) since both the CLI and this renderer need the
# same closed vocabulary.
LOG_MODES = ("plain", "verbose", "narrate")


def _line(message: str) -> str:
    return f"{REI_PREFIX} {message}"


@dataclass(frozen=True)
class _StagePattern:
    """One entry in `_STAGE_PATTERNS`: `regex` is matched against the
    raw stage message with `re.fullmatch`; `render` turns the match
    into Rei's sentence(s) for that stage. Order matters -- the first
    matching pattern wins, same "first match, no fallthrough" contract
    every other closed-vocabulary dispatch table in this project
    already follows (`ACTION_REGISTRY`, `SCHEMA`, ...).
    """

    regex: re.Pattern[str]
    render: Callable[[re.Match[str]], str]


def _pat(pattern: str, render: Callable[[re.Match[str]], str]) -> _StagePattern:
    return _StagePattern(re.compile(pattern), render)


# The closed set of stage messages `arklight.compiler.pipeline`
# actually emits today (see that module's `log(...)` call sites), each
# given a short natural-language rendering. Deliberately literal,
# closed-vocabulary matching (`re.fullmatch` against the exact stage
# text) rather than free-text understanding -- Rei doesn't need to
# understand a build, only to describe this small, known set of
# stage-completion events (proposal §4).
_STAGE_PATTERNS: tuple[_StagePattern, ...] = (
    _pat(
        r"Discovering site and compiling AST trees\.\.\.",
        lambda m: _line("Reading your site file and turning it into an AST tree."),
    ),
    _pat(
        r"Expanding user-defined components\.\.\.",
        lambda m: _line("Expanding any @component(...)-registered pieces you used."),
    ),
    _pat(
        r"Normalizing AST\.\.\.",
        lambda m: _line("Normalizing the tree into a consistent shape."),
    ),
    _pat(
        r"Running validation\.\.\.",
        lambda m: _line("Checking everything against the known component schema."),
    ),
    _pat(
        r"Building website IR\.\.\.",
        lambda m: _line("Building the Website IR from the validated tree."),
    ),
    _pat(
        r"Rendering backend '(?P<name>[^']*)'\.\.\.",
        lambda m: _line(f"Rendering the {m.group('name')} backend."),
    ),
    _pat(
        r"Postprocessing backend '(?P<name>[^']*)'\.\.\.",
        lambda m: _line(f"Postprocessing the {m.group('name')} backend's output."),
    ),
    _pat(
        r"Running raw postprocess function (?P<i>\d+)/(?P<n>\d+)\.\.\.",
        lambda m: _line(
            f"Running your registered ScriptExtension/postprocess function "
            f"({m.group('i')} of {m.group('n')})."
        ),
    ),
    _pat(
        r"Checking required assets\.\.\.",
        lambda m: _line("Checking that every asset your site references exists, by exact name."),
    ),
    _pat(
        r"Asset check passed: (?P<n>\d+) required asset\(s\), all present\.",
        lambda m: _line(f"All {m.group('n')} referenced asset(s) are present."),
    ),
    _pat(
        r"Link check passed: (?P<n>\d+) internal link\(s\), all resolve\.",
        lambda m: _line(f"All {m.group('n')} internal link(s) resolve to a real page."),
    ),
    _pat(
        r"Generating build manifest \(sbom\.txt\)\.\.\.",
        lambda m: _line("Writing the build manifest, sbom.txt."),
    ),
    _pat(
        r"Writing (?P<n>\d+) file\(s\) -> (?P<dir>.+)/\.\.\.",
        lambda m: _line(f"Writing {m.group('n')} file(s) to {m.group('dir')}/."),
    ),
    _pat(
        r"Copying assets\.\.\.",
        lambda m: _line("Copying your assets/ folder into the output, if there is one."),
    ),
    _pat(
        r"Build complete -> (?P<path>.+)",
        lambda m: _line(f"All done -- open {m.group('path')} whenever you're ready."),
    ),
    _pat(
        r"Reading \.arklight snapshot from (?P<path>.+)\.\.\.",
        lambda m: _line(f"Reading the .arklight snapshot at {m.group('path')}."),
    ),
    _pat(
        r"Rebuilding Website IR from (?P<n>\d+) page\(s\)\.\.\.",
        lambda m: _line(f"Rebuilding the Website IR from {m.group('n')} page(s)."),
    ),
)


def is_unconditional_banner(message: str) -> bool:
    """True for the one class of `on_stage` message that isn't stage
    narration at all -- an inline experimental-API banner (see
    `arklight.experimental.format_inline_banner`), which always starts
    with the warning glyph and prints unconditionally regardless of
    log mode (`docs/Foundational/EXPERIMENTAL-APIS.md`'s CLI contract). Rei never
    narrates these -- she prints them exactly as `--verbose` does,
    same as `arklight.cli.main._stage_logger` already treats them as a
    separate case from plain stage narration.
    """
    return message.startswith("\u26a0")


def narrate_stage(message: str) -> str:
    """Render one `on_stage` message in Rei's voice.

    Deterministic: the same `message` always renders to the same
    string. Every message the pipeline actually emits today matches
    one of `_STAGE_PATTERNS`; anything unrecognized (a future stage,
    or a loader notice such as `retired_star_import_notice`) falls
    back to a plain, still-deterministic passthrough rather than
    silently dropping it -- narrating *something* beats narrating
    nothing, and this is exactly the kind of gap `_STAGE_PATTERNS`
    should grow to cover next.
    """
    for pattern in _STAGE_PATTERNS:
        match = pattern.regex.fullmatch(message)
        if match is not None:
            return pattern.render(match)
    return _line(message)


def introduction(*, mode_source: str, resolved_mode: str) -> str:
    """Rei's one-time-per-fresh-output-directory banner (proposal §3):
    printed before the first narrated stage line when `--narrate` is
    active and the build's output directory doesn't exist yet, or
    exists and is empty. `mode_source` is `"--narrate flag"` or
    `"arklight.config.py"`, whichever actually turned narration on for
    this build -- shown so a project pinning `rei.default_mode` in its
    config can tell that's why they're seeing Rei at all.
    """
    return "\n".join(
        [
            _line("Hi -- I'm Rei, ARKlight's compiler narrator."),
            _line(
                f"Narration is on via {mode_source} (mode: {resolved_mode}). "
                f"I'll talk through each build stage as it runs."
            ),
        ]
    )


def is_fresh_output_dir(output_dir: "str") -> bool:
    """True if `output_dir` doesn't exist yet, or exists but is empty
    -- the signal `introduction`'s one-time banner gates on (proposal
    §3). Deleting/clearing the output directory and rebuilding shows
    the banner again, which is the intended, non-"ever" behavior.
    """
    from pathlib import Path

    path = Path(output_dir)
    if not path.exists():
        return True
    if not path.is_dir():
        return False
    return not any(path.iterdir())


def render_failure(message: str, *, component_name: str | None) -> str:
    """Render a failed build's message in Rei's voice.

    `component_name` should come from the underlying `ValidationError`
    (`arklight.ir.validate.ValidationError.component_name`, threaded
    through `CompileError.__cause__`) -- never re-derived by scraping
    `message` with a regex. It is only ever set at the two SCHEMA-
    lookup sites (unknown component type, missing required prop -- see
    that class's docstring), so its mere presence is what decides
    whether the `arklight search <name>` pointer gets appended (§5)
    -- not any inspection of the message text itself. Every other
    `ValidationError` (Bind/on_click/modifier/behavior checks, ...)
    leaves it `None`, and gets no pointer line.
    """
    lines = [_line("Compilation halted."), "", _line(message)]
    if component_name is not None:
        lines.append("")
        lines.append(f"Try: arklight search {component_name}")
    return "\n".join(lines)
