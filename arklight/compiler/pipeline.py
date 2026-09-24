"""
Compiler Pipeline.

Ties every stage together, matching the architecture doc exactly:

    Python Source
        -> Python AST         (arklight.parser.discover, static analysis)
        -> ARK AST            (arklight.parser.loader executes the module;
                                 Site.build_ark_ast() calls each page fn)
        -> Component expansion (arklight.ir.components, v0.060 Stage 0 --
                                 user-defined component markers are
                                 spliced out here, before Normalization
                                 ever sees them; a no-op for a site that
                                 never registers one)
        -> Normalization      (arklight.ir.normalize)
        -> Validation         (arklight.ir.validate)
        -> Website IR         (arklight.ir.build)
        -> Backend Interface  (arklight.backend.base.Backend)
        -> HTML + CSS Backends (arklight.backend.html / arklight.backend.css)
        -> index.html, styles.css (+ other routes)

As of v0.002, `build()` runs *multiple* backends over the same Website
IR by default (HTML and CSS) and merges their output files -- this is
exactly the fan-out the architecture doc describes under "Backend
Interface": each backend consumes the
same IR and contributes its own output files.

`build()` also copies a top-level `assets/` folder (next to the site's
entry file) into `<output_dir>/assets` automatically, if one exists --
see `_copy_assets` below.
"""

from __future__ import annotations

import shutil
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from arklight import __version__, experimental
from arklight.backend.base import Backend
from arklight.backend.css.render import CSSBackend
from arklight.backend.html.render import HTMLBackend
from arklight.backend.js.render import JSBackend
from arklight.config import ConfigError, load_config, overdrive_enabled
from arklight.compiler.asset_check import (
    check_required_assets,
    collect_required_assets,
    format_report,
)
from arklight.compiler.link_check import check_links, format_report as format_link_report
from arklight.compiler.overdrive import ASSET_WAIVABLE, LINK_WAIVABLE, format_notice
from arklight.compiler.sbom import build_sbom_text
from arklight.ir import binary as binary_ir
from arklight.ir.build import WebsiteIR, build_website_ir
from arklight.ir.components import ComponentError, collect_default_styles, expand_ark_ast
from arklight.ir.normalize import normalize_ark_ast
from arklight.ir.validate import ValidationError, validate_ark_ast, validate_provider
from arklight.parser.loader import SiteLoadError, load_site
from arklight.search.engine import default_engine
from arklight.search.feedback import record_name_error_feedback, record_validation_feedback

# A stage callback: called with a short, human-readable message every
# time the pipeline moves into a new stage (site discovery, AST build,
# normalization, validation, IR build, each backend's render/
# postprocess, writing output, copying assets, ...). `compile_site_file`
# and `build` both default this to a no-op, so calling either exactly
# as before is unaffected -- passing `on_stage=` is purely additive.
# The CLI's `--verbose`/`--debug` flags are what actually supply one
# (see `arklight.cli.main`); nothing in this module ever prints on its
# own, keeping stage reporting a presentation concern, not a pipeline one.
StageLogger = Callable[[str], None]


def _noop_stage_logger(_message: str) -> None:
    return None


def _looks_like_arklight_file(entry_path: str | Path) -> bool:
    """
    True if `entry_path` is a `.arklight` binary IR snapshot
    (`arklight.ir.binary`) rather than a Python site file -- checked
    by extension first (cheap, covers the ordinary `--emit-arklight`
    default filename and anything a person names `something.arklight`
    themselves), falling back to sniffing the file's first 4 bytes
    against `binary_ir.MAGIC` for a differently-extensioned file (e.g.
    `--emit-arklight=build/site` with no extension at all). Never
    raises for a missing/unreadable path -- `build` surfaces that as
    its own `CompileError` a few lines later regardless of which
    branch it took, the same as it always has for a missing Python
    site file.
    """
    path = Path(entry_path)
    if path.suffix == ".arklight":
        return True
    try:
        with open(path, "rb") as f:
            return f.read(len(binary_ir.MAGIC)) == binary_ir.MAGIC
    except OSError:
        return False


def _record_validation_feedback_best_effort(message: str) -> None:
    """Stage 8's compiler-pipeline hook into
    `arklight.search.feedback`: records unknown-component-type typos
    against the Stage 6 engine's own current top suggestion, purely so
    future `arklight search` calls can learn from real, in-the-wild
    mistakes. This is a background side effect, never a build
    behavior -- any failure here (e.g. the on-disk usage-stats store
    being unwritable, or a first-run knowledge/graph build hitting an
    unexpected error) is swallowed on purpose, exactly as if this hook
    weren't wired in at all. `compile_site_file` calls this right
    before re-raising the same `CompileError` it always raised, with
    the same message -- this only ever adds a record after the fact.
    """
    try:
        record_validation_feedback(message, default_engine())
    except Exception:  # noqa: BLE001 -- best-effort only, must never affect the build
        pass


def _record_name_error_feedback_best_effort(message: str) -> None:
    """The actual live counterpart to the hook above. Every component
    (`Heading`, `Image`, ...) is a real Python function/name, so a
    misspelled component call (`Headingg(...)`) fails as a plain
    Python `NameError` inside `Site.build_ark_ast()` -- several stages
    before `validate_node()` ever runs, meaning it never reaches the
    `ValidationError` `_record_validation_feedback_best_effort` above
    listens for. `compile_site_file` calls this right before
    re-raising the same `CompileError` it always raised for a
    `NameError` out of page-function execution, with the same message
    -- same best-effort, build-behavior-neutral contract as above.
    """
    try:
        record_name_error_feedback(message, default_engine())
    except Exception:  # noqa: BLE001 -- best-effort only, must never affect the build
        pass

# Name of the top-level, next-to-`site.py` folder ARKlight auto-copies
# into the output directory (verbatim, recursively) if it exists. Fixes
# the "404 images" gotcha documented in docs/Foundational/DESIGN-NOTES.md: previously
# a site's `assets/` (images, fonts, favicons, ...) had to be copied by
# hand with `cp -r assets ARK/assets` after every build.
ASSETS_DIR_NAME = "assets"


def default_backends() -> list[Backend]:
    """The backends a normal `arklight build` runs: HTML + CSS + JS."""
    return [HTMLBackend(), CSSBackend(), JSBackend()]


@dataclass
class BuildResult:
    ir: WebsiteIR
    output_files: dict[str, str]
    written_paths: list[Path]


class CompileError(RuntimeError):
    """Raised when any pipeline stage fails. Wraps the underlying error."""


def compile_site_file(
    entry_path: str | Path,
    *,
    on_stage: StageLogger | None = None,
    css_var_overrides: dict[str, str] | None = None,
    lang: str | None = None,
    strict_csp_override: bool | None = None,
    devtools_console_reminder: bool = True,
) -> WebsiteIR:
    """
    Run every stage up to (and including) Website IR construction, but
    do not render or write files. Useful for tooling that just wants
    the IR (linting, additional backends, tests).

    `on_stage`, if given, is called once per stage with a short message
    describing what's about to run -- purely for observability (e.g.
    the CLI's `--verbose`/`--debug` output); it has no effect on the
    result and defaults to a no-op.

    `css_var_overrides`, if given, is merged *over* whatever the site
    file itself set via `Site(max_width=..., bg=...)` -- i.e. this is
    an outer override, for callers (the CLI's `--max-width`/`--bg`
    flags) that need to set a design token without editing the site
    file. Defaults to `None` (no additional overrides), so calling
    `compile_site_file` exactly as before is unaffected.

    `lang`, if given, overrides the site file's own `Site(lang=...)`
    (or its "en" default) the same way -- for the CLI's `--lang` flag.

    `strict_csp_override`, if not `None`, wins over whatever the site
    file itself set via `Site(strict_csp=...)` -- an outer override,
    same shape as `css_var_overrides`/`lang` above, for the CLI's
    `arklight.config.py` (`CONFIG = {"csp": {"strict_csp": ...}}`)
    project-wide policy knob (see `arklight.config`'s "csp" section
    comment). `None` (the default) means "no override, defer entirely
    to the site file's own `Site(strict_csp=...)` value" -- it is *not*
    the same as passing `False`, which would force the policy off for
    every site regardless of what the site file asked for.

    `devtools_console_reminder` is `arklight.config.py`'s
    `CONFIG = {"experimental": {"devtools_console_reminder": ...}}`
    passthrough (see `WebsiteIR.devtools_console_reminder`'s comment in
    `arklight/ir/build.py`) -- unlike `strict_csp_override` this has no
    `Site(...)` kwarg to defer to, so it's a plain bool, not a
    three-state override: `True` (the default) unless the project's
    config file turns it off.
    """
    log = on_stage or _noop_stage_logger

    log("Discovering site and compiling AST trees...")
    try:
        site, _discovered = load_site(entry_path, on_notice=log)
    except SiteLoadError as exc:
        raise CompileError(str(exc)) from exc

    try:
        ark_ast = site.build_ark_ast()
    except NameError as exc:
        _record_name_error_feedback_best_effort(str(exc))
        raise CompileError(f"Error while building page(s): {exc}") from exc
    except Exception as exc:  # noqa: BLE001 -- surface page-function errors clearly
        raise CompileError(f"Error while building page(s): {exc}") from exc

    log("Expanding user-defined components...")
    used_components: set[str] = set()
    try:
        ark_ast = expand_ark_ast(ark_ast, used=used_components)
    except ComponentError as exc:
        raise CompileError(str(exc)) from exc

    # v0.060, Stage 2 ("Default styling hook"): only components this
    # build actually expanded get their `default_style` folded into
    # the stylesheet -- see `collect_default_styles`'s own docstring
    # for why that's keyed on usage rather than on the whole (process-
    # global) `COMPONENT_REGISTRY`. An explicit `site.style(name, ...)`
    # registration for the same name wins over a component's own
    # default (the merge below, keyed by `site.custom_styles` applied
    # last) -- same "the more specific/explicit thing wins" cascade
    # reasoning every other CSS-generating layer in this pipeline
    # already follows.
    component_default_styles = collect_default_styles(used_components)

    log("Normalizing AST...")
    try:
        normalized = normalize_ark_ast(ark_ast)
    except TypeError as exc:
        raise CompileError(str(exc)) from exc

    log("Running validation...")
    try:
        validate_ark_ast(normalized)
        # `Provider` stage 2 of 6 (`v0.066`): `Site(provider=...)` isn't
        # a node in `normalized`, so it isn't covered by the tree walk
        # above -- checked here, in the same stage, so a bad
        # declaration fails the build the same way a bad node does
        # (see `arklight.ir.validate.validate_provider`'s docstring).
        validate_provider(site.provider)
    except ValidationError as exc:
        _record_validation_feedback_best_effort(str(exc))
        raise CompileError(str(exc)) from exc

    # Experimental API warnings (docs/Foundational/EXPERIMENTAL-APIS.md): every
    # opt-in call the site made (currently just `site.media_query(...)`)
    # was already recorded on `site.experimental_usages` at call time --
    # print the inline "[EXPERIMENTAL FEATURE ACTIVE]" banner for each
    # one now, right after validation succeeds, so it's interleaved with
    # stage narration instead of only showing up in an end-of-build
    # summary. Not gated behind `on_stage`/`--verbose` being set for
    # anything else: an experimental-feature warning always prints if
    # a logger was supplied at all.
    for usage in site.experimental_usages:
        log(experimental.format_inline_banner(usage))

    log("Building website IR...")
    merged_css_var_overrides = dict(site.css_var_overrides)
    if css_var_overrides:
        merged_css_var_overrides.update(css_var_overrides)

    return build_website_ir(
        site.name,
        normalized,
        custom_styles={**component_default_styles, **site.custom_styles},
        media_queries=site.custom_media_queries,
        experimental_usages=site.experimental_usages,
        css_var_overrides=merged_css_var_overrides,
        lang=lang if lang is not None else site.lang,
        # v0.048 Stage B: `responsive_style={...}` usages are only
        # discovered while building the IR (see `build_website_ir`'s
        # `on_warning` docstring), unlike `site.media_query(...)`
        # calls, which are already known by this point and printed by
        # the loop just above. This is that feature's own inline
        # "[EXPERIMENTAL FEATURE ACTIVE]" detection point.
        on_warning=log,
        # Structural addendum (docs/Foundational/DESIGN-NOTES.md "CSS selector
        # algebra + at-rule vocabulary"): straight passthroughs, same
        # as `custom_styles`/`media_queries` above.
        selector_rules=site.selector_rules,
        keyframes=site.custom_keyframes,
        font_faces=site.font_faces,
        container_queries=site.container_queries,
        supports_rules=site.supports_rules,
        page_rules=site.page_rules,
        style_imports=site.style_imports,
        # htmx-4 (REFACTOR-INDEX.md [retired -- see CHANGELOG.md] row 9): straight
        # passthrough, same shape as the CSS addendum fields above --
        # no CLI flag equivalent (unlike `lang`/`css_var_overrides`),
        # since app-shell navigation is a whole-site authoring
        # decision the site file itself makes, not a per-build override.
        app_shell=site.app_shell,
        # EXPERIMENTAL (docs/Foundational/EXPERIMENTAL-APIS.md): straight passthrough,
        # same shape as the CSS addendum fields above -- `build()` below
        # is what actually runs these, after every backend's own
        # render()+postprocess() pass.
        raw_postprocessors=site.raw_postprocessors,
        # Runtime policy enforcement (arklight/backend/html/csp.py):
        # straight passthrough, same shape as `app_shell` above -- no
        # CLI flag equivalent, for the same reason `app_shell` has none:
        # this is a whole-site authoring decision, not a per-build
        # override a CI invocation would plausibly want to flip.
        # `strict_csp_override` (`arklight.config.py`'s "csp" section)
        # wins over the site file's own `Site(strict_csp=...)` when the
        # project's config explicitly set one -- `None` means the
        # config had nothing to say, so the site file's own value
        # passes through unchanged, same "outer override, absent by
        # default" shape as `css_var_overrides`/`lang` above.
        strict_csp=site.strict_csp if strict_csp_override is None else strict_csp_override,
        trusted_script_origins=site.trusted_script_origins,
        devtools_console_reminder=devtools_console_reminder,
        # `Provider` stage 2 of 6 (`v0.066`): straight passthrough, same
        # shape as `app_shell`/`raw_postprocessors` above -- already
        # validated by `validate_provider` a few lines up, in this same
        # `build` call, before this IR-build stage runs.
        provider=site.provider,
    )


def compile_arklight_file(
    entry_path: str | Path,
    *,
    on_stage: StageLogger | None = None,
    css_var_overrides: dict[str, str] | None = None,
    lang: str | None = None,
    strict_csp_override: bool | None = None,
    devtools_console_reminder: bool = True,
) -> WebsiteIR:
    """
    The `.arklight`-file counterpart to `compile_site_file` above --
    closes the "uncharted territory" `arklight.ir.binary`'s module
    docstring calls out: `encode_arklight`/`decode_arklight` already
    existed on both sides of this round trip, but nothing in
    ARKlight-py ever ran the decode side to actually rebuild something
    a backend could render. This does: reads a previously-`--emit-
    arklight`'d snapshot straight off disk and hands back the same
    `WebsiteIR` `compile_site_file` would have built from the original
    Python source -- none of the Python-source stages (discovery, AST,
    component expansion, normalization, validation) run at all, which
    is the entire point of the format (see `arklight.ir.binary`'s
    module docstring: "doesn't require re-running the Python compiler
    pipeline to read back").

    `on_stage`, if given, narrates the two stages this path actually
    has (read+decode, then rebuild) -- `--verbose` parity with
    `compile_site_file`'s own stage narration, even though there's
    much less work happening here.

    `css_var_overrides`/`lang`/`strict_csp_override`/
    `devtools_console_reminder` are the exact same outer overrides
    `compile_site_file` accepts (see its docstring) -- applied
    directly to the rebuilt `WebsiteIR` here rather than to a `Site(
    ...)` object, since a `.arklight` snapshot has no live `Site(...)`
    to defer to; a rebuilt site's `strict_csp`/every other field
    `encode_arklight` doesn't carry already starts at `WebsiteIR`'s
    own stock default (see `decoded_site_to_website_ir`'s docstring),
    so `strict_csp_override=None` here means "leave that default
    alone", same as it meaning "defer to `Site(strict_csp=...)`" on
    the Python-source path.
    """
    log = on_stage or _noop_stage_logger
    path = Path(entry_path)

    log(f"Reading .arklight snapshot from {path}...")
    try:
        data = path.read_bytes()
    except OSError as exc:
        raise CompileError(f"Could not read .arklight file {path}: {exc}") from exc

    try:
        decoded = binary_ir.decode_arklight(data)
    except binary_ir.ArklightFormatError as exc:
        raise CompileError(f"{path} is not a valid .arklight file: {exc}") from exc

    log(f"Rebuilding Website IR from {len(decoded.pages)} page(s)...")
    ir = binary_ir.decoded_site_to_website_ir(decoded)

    if css_var_overrides:
        ir.css_var_overrides = {**ir.css_var_overrides, **css_var_overrides}
    if lang is not None:
        ir.lang = lang
    if strict_csp_override is not None:
        ir.strict_csp = strict_csp_override
    ir.devtools_console_reminder = devtools_console_reminder
    return ir


def build(
    entry_path: str | Path,
    output_dir: str | Path,
    *,
    backends: list[Backend] | None = None,
    on_stage: StageLogger | None = None,
    css_var_overrides: dict[str, str] | None = None,
    lang: str | None = None,
    strict_csp_override: bool | None = None,
    devtools_console_reminder: bool = True,
    overdrive: bool | None = None,
) -> BuildResult:
    """
    Full pipeline: Python source file -> rendered files written to `output_dir`.

    Runs every backend in `backends` (default: HTML + CSS) over the
    same Website IR and merges their output files before writing.

    `on_stage`, if given, is called once per stage (site discovery/AST,
    normalization, validation, IR build, each backend's render/
    postprocess, writing files, copying assets) with a short message --
    see `compile_site_file` above. Defaults to a no-op; purely additive.

    `css_var_overrides`/`lang`, if given, are forwarded to
    `compile_site_file` (see there) -- this is how the CLI's
    `--max-width`/`--bg`/`--font-family`/`--lang` flags reach the
    design tokens and `<html lang>` without requiring a site-file edit.

    `strict_csp_override`/`devtools_console_reminder` are also
    forwarded to `compile_site_file` (see there) -- the CLI's
    `arklight.config.py` `"csp"`/`"experimental"` sections reach the
    generated CSP meta tag and the devtools console reminder the same
    way, without requiring a site-file edit either.

    `entry_path` may be a `.arklight` binary IR snapshot instead of a
    Python site file (`_looks_like_arklight_file` detects which) -- in
    that case `compile_arklight_file` runs instead of
    `compile_site_file`, skipping the Python-source stages entirely;
    every other argument here means the same thing either way (see
    `compile_arklight_file`'s docstring for how the overrides apply
    without a `Site(...)` to defer to).

    `overdrive`, if `None` (the default), is read from the project's
    `arklight.config.py` (`CONFIG = {"overdrive": True}`, next to the
    entry file) -- read here rather than only in the CLI so every caller
    agrees. `True`/`False` overrides the config. See
    `arklight.compiler.overdrive` for exactly what it waives.

    Also always writes `sbom.txt` -- a per-build manifest of what this
    specific compile actually contains (see `arklight.compiler.sbom`
    for the format and what it deliberately does/doesn't claim).
    """
    log = on_stage or _noop_stage_logger
    backends = backends if backends is not None else default_backends()

    if overdrive is None:
        try:
            overdrive = overdrive_enabled(load_config(Path(entry_path).resolve().parent))
        except ConfigError as exc:
            raise CompileError(str(exc)) from exc

    if _looks_like_arklight_file(entry_path):
        ir = compile_arklight_file(
            entry_path,
            on_stage=log,
            css_var_overrides=css_var_overrides,
            lang=lang,
            strict_csp_override=strict_csp_override,
            devtools_console_reminder=devtools_console_reminder,
        )
    else:
        ir = compile_site_file(
            entry_path,
            on_stage=log,
            css_var_overrides=css_var_overrides,
            lang=lang,
            strict_csp_override=strict_csp_override,
            devtools_console_reminder=devtools_console_reminder,
        )

    output_files: dict[str, str] = {}
    for backend in backends:
        log(f"Rendering backend {backend.name!r}...")
        try:
            rendered = backend.render(ir)
        except Exception as exc:  # noqa: BLE001 -- surface backend errors clearly
            raise CompileError(f"Backend {backend.name!r} failed to render: {exc}") from exc
        output_files.update(rendered)

    # Second pass: each backend gets a chance to transform the *combined*
    # output of every backend's render(), in the same order. Default
    # Backend.postprocess() is a no-op, so this changes nothing unless a
    # backend explicitly overrides it -- see arklight.backend.base.Backend.
    for backend in backends:
        log(f"Postprocessing backend {backend.name!r}...")
        try:
            output_files = backend.postprocess(output_files)
        except Exception as exc:  # noqa: BLE001 -- surface backend errors clearly
            raise CompileError(f"Backend {backend.name!r} failed to postprocess: {exc}") from exc

    # `site.raw_postprocessors` -- functions registered here get the
    # exact same second pass every `Backend.postprocess()` just got
    # above, run last and in registration order, over the fully
    # combined output of every backend. This list is no longer
    # user-facing: `Site.raw_postprocess(fn)` is deprecated and never
    # appends to it anymore (see `arklight/experimental.py`'s
    # `raw-postprocess` entry) -- the only thing that populates it now
    # is `arklight.backend.script_extension.register()`, via
    # `site.register_script_extension(...)`. A no-op loop (as before)
    # for sites that never call it.
    for i, raw_fn in enumerate(ir.raw_postprocessors, start=1):
        log(f"Running raw postprocess function {i}/{len(ir.raw_postprocessors)}...")
        try:
            result = raw_fn(output_files)
        except Exception as exc:  # noqa: BLE001 -- surface user code errors clearly
            raise CompileError(
                f"raw postprocess function #{i} raised an error: {exc}"
            ) from exc
        if not isinstance(result, dict):
            raise CompileError(
                f"raw postprocess function #{i} must return a "
                f"dict[str, str] of {{relative_path: contents}}, got "
                f"{type(result).__name__!r}."
            )
        output_files = result

    # Asset gate -- runs after every backend/postprocess has produced the
    # final file set and *before* anything touches disk, so a failure
    # leaves no half-written output. The report goes straight to stderr
    # (not through `log`, the narrator, or `warnings`) and there is no
    # flag to silence it. See `arklight.compiler.asset_check`.
    log("Checking required assets...")
    required_assets = collect_required_assets(ir)
    assets_src = Path(entry_path).resolve().parent / ASSETS_DIR_NAME
    asset_problems = check_required_assets(
        required_assets,
        assets_src=assets_src,
        generated=set(output_files),
        assets_dir_name=ASSETS_DIR_NAME,
    )
    link_total, link_problems = check_links(ir, generated=set(output_files))
    asset_waived: list = []
    if overdrive:
        # Only the *unverifiable* findings are waived (see overdrive.py);
        # each one is still printed, every build, on stderr.
        asset_waived = [p for p in asset_problems if p.kind in ASSET_WAIVABLE]
        link_waived = [p for p in link_problems if p.kind in LINK_WAIVABLE]
        asset_problems = [p for p in asset_problems if p.kind not in ASSET_WAIVABLE]
        link_problems = [p for p in link_problems if p.kind not in LINK_WAIVABLE]
        if asset_waived or link_waived:
            print(
                format_notice(asset_waived, link_waived, entry_path=Path(entry_path).resolve()),
                file=sys.stderr,
                flush=True,
            )
    if asset_problems or link_problems:
        failures = []
        if asset_problems:
            print(
                format_report(
                    asset_problems,
                    total_required=len(required_assets),
                    entry_path=Path(entry_path).resolve(),
                    assets_src=assets_src,
                ),
                file=sys.stderr,
                flush=True,
            )
            failures.append(
                f"Asset check failed: {len(asset_problems)} of {len(required_assets)} "
                f"required asset(s) missing or not an exact name match"
            )
        if link_problems:
            print(
                format_link_report(
                    link_problems,
                    total_checked=link_total,
                    entry_path=Path(entry_path).resolve(),
                ),
                file=sys.stderr,
                flush=True,
            )
            failures.append(
                f"Link check failed: {len(link_problems)} internal link(s) don't resolve"
            )
        raise CompileError("; ".join(failures) + " (full report above). Nothing was written.")
    verified_assets = len(required_assets) - (len(asset_waived) if overdrive else 0)
    log(f"Asset check passed: {verified_assets} required asset(s), all present.")
    log(f"Link check passed: {link_total} internal link(s), all resolve.")

    log("Generating build manifest (sbom.txt)...")
    output_files["sbom.txt"] = build_sbom_text(ir, version=__version__)

    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    log(f"Writing {len(output_files)} file(s) -> {out_dir}/...")
    written: list[Path] = []
    try:
        for rel_path, contents in output_files.items():
            dest = out_dir / rel_path
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(contents, encoding="utf-8")
            written.append(dest)
    except OSError as exc:
        # Uncharted territory: nothing above this validates disk space,
        # permissions, or a mid-write disconnect (e.g. a network drive).
        # Say plainly how much of the build did land, since `out_dir` is
        # now a mix of complete and missing files, not a clean failure.
        raise CompileError(
            f"Failed while writing output to {out_dir}/ "
            f"({len(written)}/{len(output_files)} file(s) written before "
            f"the failure -- the output directory is now incomplete): {exc}"
        ) from exc

    log("Copying assets...")
    try:
        written.extend(_copy_assets(entry_path, out_dir))
    except OSError as exc:
        raise CompileError(
            f"Failed while copying assets/ into {out_dir}/assets/ -- "
            f"{len(written)} page file(s) were already written successfully, "
            f"so the build is partially complete: {exc}"
        ) from exc

    log(f"Build complete -> {out_dir}/index.html")
    return BuildResult(ir=ir, output_files=output_files, written_paths=written)


def _copy_assets(entry_path: str | Path, out_dir: Path) -> list[Path]:
    """
    Copy a top-level `assets/` folder (sitting next to the site's entry
    file) into `<output_dir>/assets`, recursively, if one exists.

    This was previously a manual, easy-to-forget step (`cp -r assets
    ARK/assets`) -- a real gap, not a template-only concern, per
    docs/Foundational/DESIGN-NOTES.md. No-op (returns an empty list) when there's no
    `assets/` folder to copy.
    """
    assets_src = Path(entry_path).resolve().parent / ASSETS_DIR_NAME
    if not assets_src.is_dir():
        return []

    assets_dest = out_dir / ASSETS_DIR_NAME
    shutil.copytree(assets_src, assets_dest, dirs_exist_ok=True)
    return sorted(p for p in assets_dest.rglob("*") if p.is_file())
