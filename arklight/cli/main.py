"""
ARKlight CLI.

    arklight new my-site
    arklight build site.py -o ARK
    arklight pack ARK -o site.ark
    arklight unpack site.ark -o ARK
    arklight pwa ARK --name "My Site" --icon assets/icon-192.png:192x192
    arklight android scaffold ARK -o android-project
    arklight desktop scaffold ARK -o desktop-project
    arklight deploy cloudflare
    arklight search Picture

Beginner-friendly by design: a handful of subcommands, sensible
defaults (builds AND opens the result in your browser), and error
messages that point at exactly what went wrong (parse error, missing
Site(), unknown component, etc.) rather than a raw traceback.
"""

from __future__ import annotations

import argparse
import functools
import mimetypes
import os
import re
import sys
import traceback
import warnings
import webbrowser
from pathlib import Path

from arklight import __version__, experimental
from arklight.cli import android, deploy, desktop, live_streaming
from arklight.cli.android import AndroidError
from arklight.cli.deploy import DeployError
from arklight.cli.desktop import DesktopError
from arklight.cli.doc_retrieval import DOC_FOLDERS, DocRetrievalError, ignored_flag_notices, run_retrieve_doc
from arklight.cli.license_gate import ensure_license_accepted
from arklight.cli.mdrender import render_markdown, resolve_color
from arklight.cli.whats_new import read_version, show_release_notes_if_new
from arklight.cli.scaffold import ScaffoldError, new_project
from arklight.cli.search import record_acceptance, resolve_exact, search_component
from arklight.cli.templates import TEMPLATES
from arklight.cli.upgrade import upgrade_to_alpha
from arklight.compiler import rei
from arklight.compiler.pipeline import BuildResult, CompileError, build
from arklight.config import ConfigError, load_config, overdrive_enabled, section
from arklight.ir import binary as binary_ir
from arklight.ir.validate import ValidationError
from arklight.packer.bundle import PackError, pack, unpack
from arklight.pwa import PWAError, enable_pwa
from arklight.search.endpoint import serve_stdio
from arklight.search.engine import SearchEngineError, default_engine

# Prefix every `--verbose`/`--debug` stage line gets, so pipeline
# progress reads as ARKlight "thinking out loud" rather than bare,
# unattributed text mixed in with normal build output.
_STAGE_PREFIX = "[ARKlight]"

# Short nudge printed after every `production`-template scaffold --
# the template's layout (components/ pages/ content/) already puts
# this into practice, but a first-time user staring at four new
# directories benefits from being told *why*, not just handed the
# files. Points at `--explain-architecture` rather than dumping the
# full guide inline, so the normal `arklight new` output stays short.
_PRODUCTION_ARCHITECTURE_NOTE = (
    "Recommended: keep this project service-oriented and separated by "
    "concern (routes thin, content/markup/logic in their own modules) "
    "-- minimal boilerplate, not a framework to fight. Run `arklight "
    "new --explain-architecture` to see how."
)

# The `--explain-architecture` guide itself -- concrete, tied to the
# actual `production` template layout (site.py/components/pages/
# content/assets), not generic architecture advice. Printed standalone
# (`arklight new --explain-architecture`, no `name` needed) or after a
# fresh `production` scaffold when the flag is passed alongside a name.
_ARCHITECTURE_GUIDE = """\
ARKlight production layout: service-oriented, separated by concern
--------------------------------------------------------------------

  site.py           routes only -- @site.page(...) decorators that
                     each delegate to one function in pages/. Nothing
                     else belongs here.
  pages/*.py        one module per route. Builds that page's Page(...)
                     tree by composing components/ + content/ --
                     no markup lives inline in site.py.
  components/*.py   reusable pieces (nav, footer, cards, ...). Plain
                     functions still work with zero setup -- ordinary
                     composition, nothing framework-specific required.
                     For a piece that wants a checked prop contract
                     (required/optional props, build-time validation)
                     or per-backend rendering, register it instead with
                     the optional @component(...) decorator (v0.060) --
                     see docs/Foundational/USER-DEFINED-COMPONENTS.md.
                     Neither is required to use the other; mix freely.
  content/*.py      copy/text/config constants, kept out of both
                     components/ and pages/ so wording can change
                     without touching markup or logic.
  assets/           images, fonts, favicons -- copied into the build
                     output automatically.

Why this shape:
  - Each concern (routing, page assembly, presentation, content) lives
    in exactly one place, so a change to wording, layout, or a shared
    nav touches exactly one file, not several.
  - "Service-oriented" here just means: pages/ and components/ are
    plain functions with a clear input/output contract (return
    Page(...) or a node) -- swap, test, or reuse them independently,
    the same way you'd treat any small service.
  - It stays minimal-boilerplate on purpose -- no base classes, no
    config beyond content/, no generated files to keep in sync by
    hand. Every file above is something you'd write anyway; this is
    just where it goes.

How to extend it:
  1. New page: add pages/<name>.py returning Page(...), then wire a
     @site.page("/<route>") decorator in site.py that calls it. The
     decorator must live in site.py -- ARKlight discovers routes by
     statically scanning the entry file's own source, not files it
     imports.
  2. New shared piece (nav, card, footer, ...): add it to components/
     as a plain function, import it from whichever pages/ use it.
  3. New copy/config: add it to content/, import from pages/ or
     components/ rather than hardcoding strings in either.

Scaffold this layout with: arklight new <name> --template production
"""


def open_in_browser(result: BuildResult, output_dir: str | Path) -> bool:
    """
    Open the site's home page ("/") in the default browser as a
    `file://` URL. Internal links are already rewritten to relative
    file paths by the HTML backend, so navigating between pages works
    correctly straight off disk -- no local server required.

    Returns True if a browser launch was attempted, False if there was
    nothing to open (e.g. no "/" route). Swallows browser-launch
    failures (e.g. headless environments) rather than failing the
    build -- the files are already written either way.
    """
    index_path = Path(output_dir) / "index.html"
    if not index_path.exists():
        return False
    try:
        webbrowser.open(index_path.resolve().as_uri())
    except Exception:  # noqa: BLE001 -- opening a browser is best-effort
        return False
    return True


def _stage_logger(message: str, *, mode: str) -> None:
    """`on_stage` callback for `build()` -- prints each pipeline stage
    as it starts, prefixed like the rest of ARKlight's CLI output.
    `mode` is one of `arklight.compiler.rei.LOG_MODES`
    (`"plain"`/`"verbose"`/`"narrate"`) -- `arklight.compiler.rei`'s
    closed vocabulary, since both the CLI and that renderer need to
    agree on it.

    Two different things flow through this one callback:
      - plain pipeline narration ("Running validation...", etc.) --
        printed as a `[ARKlight] ...` line when `mode == "verbose"`
        (`--verbose`/`--debug`), or as one of Rei's narrated sentences
        when `mode == "narrate"`; nothing prints in `"plain"` mode,
        same as before `--narrate` existed.
      - an inline experimental-API banner (see
        `arklight.experimental.format_inline_banner`; always starts
        with the warning glyph) -- printed unconditionally in every
        mode, per docs/Foundational/EXPERIMENTAL-APIS.md's CLI contract ("neither
        surface is gated behind --verbose/--debug"): an experimental-
        feature warning isn't narration, it's the entire point of
        gating the feature, so it always prints regardless of log
        mode, and Rei never narrates it (`rei.is_unconditional_banner`).
    """
    if rei.is_unconditional_banner(message):
        print(message)
    elif mode == "verbose":
        print(f"{_STAGE_PREFIX} {message}")
    elif mode == "narrate":
        print(rei.narrate_stage(message))


# v0.0431 emergency patch: marker prefix `arklight.backend.html.render`
# used to put on every known-alpha-limitation warning it raised. That
# particular warning (UNROUTED_REFERENCE_ATTRS/_warn_unrouted_reference)
# was removed once the HTML backend refactor's Stage 2 fixed the gap it
# flagged (see HTML-BACKEND-REFACTOR.md [retired -- see CHANGELOG.md], CHANGELOG.md's
# [0.0491]) -- the marker mechanism itself stays, generic across any
# `[ARKlight ALPHA]`-prefixed warning a future alpha limitation might
# raise. Matched here so the CLI can surface these clearly and always --
# not gated behind --verbose, and not dependent on Python's default
# warning filters (which only show a `UserWarning` once per call site,
# and not at all if the caller has warnings configured/silenced) --
# without touching unrelated warnings a site's own code might raise.
_ALPHA_WARNING_MARKER = "[ARKlight ALPHA]"


def _print_alpha_warnings(caught: list[warnings.WarningMessage]) -> None:
    """Print every captured `[ARKlight ALPHA]`-marked warning from a
    build, framed as a known, non-fatal alpha limitation -- not a build
    failure, but not silent either. This is the graceful-degradation
    path: the feature the site author used isn't broken by ARKlight
    refusing to build, it's flagged as "may not work everywhere yet"
    with a pointer to the patch tracking it.
    """
    alpha_warnings = [w for w in caught if _ALPHA_WARNING_MARKER in str(w.message)]
    if not alpha_warnings:
        return

    print(
        f"{_STAGE_PREFIX} NOTE: this alpha build is under active maintenance. "
        f"{len(alpha_warnings)} known limitation(s) were hit during this build "
        f"-- the site was still built, but the feature(s) below may not work "
        f"correctly everywhere. Please wait for (or update to) the emergency "
        f"patch series (v0.043x) to have these handled gracefully:",
        file=sys.stderr,
    )
    for w in alpha_warnings:
        print(f"  - {w.message}", file=sys.stderr)


def _cmd_build(args: argparse.Namespace) -> int:
    # --debug implies --verbose: tracing compiler errors is much easier
    # with the stage-by-stage narration already on screen above the
    # traceback, so there's no reason to ask for both separately.
    verbose = args.verbose or args.debug

    # `--narrate` is mutually exclusive with `--verbose`/`--debug` --
    # at most one log mode wins per invocation (proposal §1), the same
    # "last flag wins, no silent stacking" rule `--open`/`--no-open`
    # already follows. Checked here (rather than an argparse mutually
    # exclusive group) because `--debug` implying `--verbose` isn't
    # itself a flag conflict -- only `--narrate` alongside either of
    # the other two is.
    if args.narrate and verbose:
        conflicting = "--debug" if args.debug else "--verbose"
        print(
            f"ARKlight build failed: --narrate can't be combined with "
            f"{conflicting} -- pick one log mode per build.",
            file=sys.stderr,
        )
        return 1

    # Project config's `rei.default_mode` only matters when *no*
    # `--verbose`/`--debug`/`--narrate` flag was passed at all -- a
    # flag on this invocation always wins over the project's pinned
    # default (proposal §2). Resolved after the config load below,
    # once `project_config` exists; `mode_source` records *why* this
    # build ended up in the mode it did, purely for Rei's first-compile
    # introduction banner (§3).
    if args.narrate:
        mode = "narrate"
        mode_source = "--narrate flag"
    elif verbose:
        mode = "verbose"
        mode_source = "--verbose/--debug flag"
    else:
        mode = None  # resolved from config below
        mode_source = "arklight.config.py"

    # --max-width/--bg let the *build invocation* set a design token
    # without touching the site file's Site(...) call -- e.g. CI
    # producing a widescreen variant of a site that otherwise ships
    # with a narrower Site(max_width=...) default. Only the flags the
    # user actually passed are forwarded, so leaving both off changes
    # nothing (falls straight through to the site file's own value, or
    # ARKlight's stock default if it set none either).
    css_var_overrides: dict[str, str] = {}
    if args.max_width is not None:
        css_var_overrides["--ark-max-width"] = args.max_width
    if args.bg is not None:
        css_var_overrides["--ark-bg"] = args.bg
    if args.font_family is not None:
        css_var_overrides["--ark-font-family"] = args.font_family
    if args.button_text is not None:
        css_var_overrides["--ark-button-text"] = args.button_text

    # arklight.config.py's "experimental"/"csp" sections are the only
    # control for the heavy-reliance nudge, the devtools console
    # reminder (docs/Foundational/EXPERIMENTAL-APIS.md), and a project-wide CSP
    # override (arklight/backend/html/csp.py) -- no CLI flag for any of
    # these, on purpose: a project that's decided it's fine leaning on
    # an escape hatch (or wants one CSP policy for every site it
    # builds) sets this once, next to the site file, the same place
    # `live_streaming`/`android`/`desktop` project settings already
    # live, rather than remembering a flag on every invocation.
    try:
        project_config = load_config(Path(args.entry).resolve().parent)
    except ConfigError as exc:
        print(f"ARKlight build failed: {exc}", file=sys.stderr)
        return 1
    experimental_cfg = section(
        project_config,
        "experimental",
        {"heavy_reliance_nudge": True, "devtools_console_reminder": True},
    )
    show_experimental_nudge = bool(experimental_cfg["heavy_reliance_nudge"])
    devtools_console_reminder = bool(experimental_cfg["devtools_console_reminder"])

    csp_cfg = section(project_config, "csp", {"strict_csp": None})
    strict_csp_override = csp_cfg["strict_csp"]
    if strict_csp_override is not None and not isinstance(strict_csp_override, bool):
        print(
            f"ARKlight build failed: `CONFIG['csp']['strict_csp']` must be "
            f"True, False, or None, got {strict_csp_override!r}.",
            file=sys.stderr,
        )
        return 1

    # `overdrive` (top-level flag): waives the gates' *unverifiable*
    # findings -- see `arklight.compiler.overdrive`. Validated here so a
    # bad value gets the same "build failed" treatment as `csp`'s.
    try:
        overdrive = overdrive_enabled(project_config)
    except ConfigError as exc:
        print(f"ARKlight build failed: {exc}", file=sys.stderr)
        return 1

    # `rei.default_mode` (proposal §2) only resolves `mode` when no
    # `--verbose`/`--debug`/`--narrate` flag was passed above -- a flag
    # always wins over the project's pinned default.
    if mode is None:
        rei_cfg = section(project_config, "rei", {"default_mode": "plain"})
        default_mode = rei_cfg["default_mode"]
        if default_mode not in rei.LOG_MODES:
            print(
                f"ARKlight build failed: `CONFIG['rei']['default_mode']` must "
                f"be one of {rei.LOG_MODES!r}, got {default_mode!r}.",
                file=sys.stderr,
            )
            return 1
        mode = default_mode

    # Always wired up now, not just when a log mode is active --
    # `_stage_logger` itself decides what to actually print (see its
    # docstring): plain stage narration stays gated behind `mode`, but
    # an experimental-API inline banner always gets through regardless.
    on_stage = functools.partial(_stage_logger, mode=mode)

    # Rei's one-time-per-fresh-output-directory introduction (proposal
    # §3): only when narration is actually active for this build, and
    # only the first time into a missing-or-empty output directory --
    # checked *before* `build()` runs, since `build()` itself creates
    # the directory as part of writing output.
    if mode == "narrate" and rei.is_fresh_output_dir(args.output):
        print(rei.introduction(mode_source=mode_source, resolved_mode=mode))

    try:
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            result = build(
                args.entry,
                args.output,
                on_stage=on_stage,
                css_var_overrides=css_var_overrides or None,
                lang=args.lang,
                strict_csp_override=strict_csp_override,
                devtools_console_reminder=devtools_console_reminder,
                overdrive=overdrive,
            )
    except CompileError as exc:
        if args.debug:
            # Full chained traceback (CompileError's __cause__ is the
            # original stage exception -- see arklight.compiler.pipeline)
            # instead of the short one-line message, so the exact
            # Python frame/line that failed is visible rather than just
            # which pipeline stage wrapped it.
            print(f"{_STAGE_PREFIX} Build failed -- full trace (--debug):", file=sys.stderr)
            traceback.print_exception(type(exc), exc, exc.__traceback__, file=sys.stderr)
        elif mode == "narrate":
            # Proposal §5: the `arklight search <name>` pointer only
            # ever comes from `ValidationError.component_name` --
            # structured data threaded through `CompileError.__cause__`
            # -- never from re-parsing `str(exc)`. `__cause__` is only
            # a `ValidationError` when *that* stage is what failed
            # (`compile_site_file`'s `except ValidationError as exc:
            # raise CompileError(...) from exc`); any other failing
            # stage (site load, component expansion, IR build, a
            # backend, ...) leaves `component_name` unset, same as any
            # other `ValidationError` that isn't schema-backed.
            cause = exc.__cause__
            component_name = (
                cause.component_name if isinstance(cause, ValidationError) else None
            )
            print(rei.render_failure(str(exc), component_name=component_name), file=sys.stderr)
        else:
            print(f"ARKlight build failed: {exc}", file=sys.stderr)
            print("Re-run with --debug for the full traceback.", file=sys.stderr)
        return 1

    print(f"ARKlight v{__version__} built {len(result.written_paths)} file(s) -> {args.output}/")
    for path in result.written_paths:
        print(f"  {path}")

    if args.emit_arklight is not None:
        arklight_path = args.emit_arklight or os.path.join(args.output, "site.arklight")
        os.makedirs(os.path.dirname(arklight_path) or ".", exist_ok=True)
        payload = binary_ir.encode_arklight(result.ir)
        with open(arklight_path, "wb") as f:
            f.write(payload)
        print(f"  {arklight_path} ({len(payload)} bytes, binary IR)")

    _print_alpha_warnings(caught)
    experimental.print_summary(result.ir.experimental_usages, show_nudge=show_experimental_nudge)

    if args.open:
        opened = open_in_browser(result, args.output)
        if opened:
            print("Opened in your default browser.")

    return 0


def _cmd_pack(args: argparse.Namespace) -> int:
    if args.passphrase:
        print(
            "Heads up: passing --passphrase on the command line is not the "
            "recommended way to do this -- it can end up in your shell "
            "history and in process listings visible to other users on this "
            "machine. Prefer an interactive prompt or an environment "
            "variable in scripted/CI use.",
            file=sys.stderr,
        )

    try:
        result = pack(
            args.build_dir,
            args.output,
            sealed=not args.plain,
            passphrase=args.passphrase,
        )
    except PackError as exc:
        print(f"ARKlight pack failed: {exc}", file=sys.stderr)
        return 1

    print(f"ARKlight v{__version__} packed {len(result.packed_paths)} file(s) -> {result.output_path}")
    for path in result.packed_paths:
        print(f"  {path}")
    print(
        "Note: .ark is ARKlight's own bundle format, not something a browser "
        "opens directly -- double-clicking it will offer to open it as a "
        "generic ZIP/archive, not as a site. Run `arklight unpack "
        f"{result.output_path}` to get a build/ directory back, then open "
        "that directory's index.html in a browser (or serve it)."
    )

    if not result.sealed:
        print(
            "Archive half is PLAIN -- openable/inspectable/editable by any "
            "generic ZIP tool. Drop --plain (the default) to seal it instead."
        )
    elif result.passphrase_protected:
        print(
            "Archive half is SEALED with your passphrase -- keep it, "
            "`arklight unpack` will need the same one to open this bundle."
        )
    else:
        print(
            "Archive half is SEALED (embedded key) -- opaque to generic archive "
            "tools, but `arklight unpack` can always open it with no extra input. "
            "For real secrecy against someone who also has ARKlight, use --passphrase."
        )

    return 0


def _cmd_unpack(args: argparse.Namespace) -> int:
    try:
        result = unpack(args.bundle, args.output, passphrase=args.passphrase)
    except PackError as exc:
        print(f"ARKlight unpack failed: {exc}", file=sys.stderr)
        return 1

    kind = "sealed" if result.was_sealed else "plain"
    print(
        f"ARKlight v{__version__} unpacked {len(result.extracted_paths)} file(s) "
        f"from a {kind} bundle -> {result.output_dir}/"
    )
    for path in result.extracted_paths:
        print(f"  {path}")

    return 0


_ICON_SIZES_RE = re.compile(r"^(\d+x\d+|any)$")


def _parse_icon_spec(spec: str) -> dict[str, str]:
    """
    Parse one `--icon SRC:SIZES[:TYPE]` value into a manifest icon dict
    (`{"src": ..., "sizes": ..., "type": ...}`), same shape
    `enable_pwa(icons=...)` already accepts.

    `SRC` is a path relative to the build directory root (same as
    `manifest.json` itself), e.g. an icon already copied into the
    build under `assets/`. `SIZES` is `WIDTHxHEIGHT` (e.g. `192x192`)
    or `any`. `TYPE` is optional and inferred from `SRC`'s extension
    via `mimetypes` when omitted -- pass it explicitly for anything
    `mimetypes` doesn't resolve.

    Raises `ValueError` (caught by `_cmd_pwa` and reported as a normal
    CLI error) on anything malformed.
    """
    parts = spec.split(":")
    if len(parts) not in (2, 3):
        raise ValueError(
            f"Invalid --icon value {spec!r} -- expected SRC:SIZES or "
            f"SRC:SIZES:TYPE, e.g. --icon assets/icon-192.png:192x192"
        )

    src, sizes = parts[0], parts[1]
    mime_type = parts[2] if len(parts) == 3 else None

    if not src:
        raise ValueError(f"Invalid --icon value {spec!r} -- SRC is empty")
    if not _ICON_SIZES_RE.match(sizes):
        raise ValueError(
            f"Invalid --icon value {spec!r} -- SIZES must look like "
            f"WIDTHxHEIGHT (e.g. 192x192) or 'any', got {sizes!r}"
        )

    if mime_type is None:
        guessed, _ = mimetypes.guess_type(src)
        if guessed is None:
            raise ValueError(
                f"Invalid --icon value {spec!r} -- couldn't infer a MIME type "
                f"from {src!r}; pass one explicitly as SRC:SIZES:TYPE"
            )
        mime_type = guessed

    return {"src": src, "sizes": sizes, "type": mime_type}


def _cmd_pwa(args: argparse.Namespace) -> int:
    try:
        icons = [_parse_icon_spec(spec) for spec in (args.icon or [])]
    except ValueError as exc:
        print(f"ARKlight pwa failed: {exc}", file=sys.stderr)
        return 1

    try:
        result = enable_pwa(
            args.build_dir,
            name=args.name,
            short_name=args.short_name,
            start_url=args.start_url,
            theme_color=args.theme_color,
            background_color=args.background_color,
            display=args.display,
            icons=icons,
            install_button=args.install_button,
        )
    except PWAError as exc:
        print(f"ARKlight pwa failed: {exc}", file=sys.stderr)
        return 1

    # Experimental API warning (docs/Foundational/EXPERIMENTAL-APIS.md) -- printed
    # inline before the normal success output, unconditionally (not
    # gated behind any verbosity flag), same contract `arklight build`
    # follows for `site.media_query(...)`.
    for usage in result.experimental_usages:
        print(experimental.format_inline_banner(usage))

    print(
        f"ARKlight v{__version__} enabled PWA support in {result.build_dir}/ "
        f"({len(result.cached_paths)} file(s) precached, cache {result.cache_name})"
    )
    print(f"  {result.manifest_path.relative_to(result.build_dir)}")
    print(f"  {result.service_worker_path.relative_to(result.build_dir)}")
    if icons:
        print(f"  {len(icons)} icon(s) registered in the manifest")
    else:
        print(
            "  no --icon given -- manifest has an empty icons list; "
            "browsers may decline to prompt an install"
        )
    for path in result.updated_pages:
        print(f"  {path} (manifest link + SW registration injected)")
    print(
        "Re-run `arklight pwa` on this directory after every `arklight build` "
        "to keep the manifest/service worker/precache list in sync -- it's "
        "idempotent, so this is always safe."
    )
    experimental.print_summary(result.experimental_usages)

    return 0


def _cmd_android_scaffold(args: argparse.Namespace) -> int:
    try:
        result = android.scaffold_project(
            args.build_dir,
            output_dir=args.output,
            debug_keystore=args.debug_keystore,
            include_release_job=args.release,
        )
    except AndroidError as exc:
        print(f"ARKlight android scaffold failed: {exc}", file=sys.stderr)
        return 1

    print(
        f"ARKlight v{__version__} scaffolded an Android project for "
        f"{result.app_name!r} ({result.package_id}) -> {result.project_dir}/ "
        f"({len(result.written_paths)} file(s))"
    )
    print(f"  name:        {result.app_name!r} ({result.app_name_source})")
    print(f"  package id:  {result.package_id} ({result.package_id_source})")
    if result.system_bar_color is not None:
        print(f"  system bars: {result.system_bar_color} ({result.system_bar_source})")
    else:
        print(f"  system bars: {result.system_bar_source}")
    if result.system_bar_note:
        print(f"               note: {result.system_bar_note}")
    if not result.package_id_configured:
        print("  Set android.app_name / android.package_id in arklight.config.py to choose")
        print("  your own. The com.arklight.* id is fine for testing on your own device; use")
        print("  a package id you control before publishing anywhere.")
    print()
    print("Includes a GitHub Actions workflow (.github/workflows/android-build.yml)")
    print("that builds a debug APK and smoke-tests it (install + launch on an")
    print("emulator) on push/PR -- no local JDK/Android SDK/emulator needed for")
    print("that.")
    if args.release:
        print("Also includes a signed release-build job (--release was passed) --")
        print("it reads its signing key from the RELEASE_KEYSTORE_BASE64,")
        print("RELEASE_KEYSTORE_PASSWORD, RELEASE_KEY_ALIAS, and RELEASE_KEY_PASSWORD")
        print("repo secrets, which you still need to set yourself -- see the")
        print("generated README.md's \"Building a release APK\" section.")
    else:
        print("No release-build job is included: an unsigned release APK isn't")
        print("installable and a signed one needs a keystore only you should hold, so")
        print("that step is left out unless you pass --release -- see the generated")
        print("README.md's \"Building a release APK\" section when you're ready for it.")
    print()
    if result.has_debug_keystore:
        print("Debug builds are signed with your pinned app/debug.keystore, so an")
        print("updated debug APK -- built on this machine, a different machine, or")
        print("CI -- can be reinstalled over an existing test install on the same")
        print("device without uninstalling first.")
    else:
        print("WARNING: no --debug-keystore given -- debug builds will sign with")
        print("each machine's own auto-generated ~/.android/debug.keystore. That's")
        print("fine on one machine, but a fresh CI runner generates its own debug")
        print("key on every run too, so a debug APK from CI won't share a signature")
        print("with one built elsewhere -- reinstalling it over an existing test")
        print("install on the same device will fail until you uninstall first. If")
        print("you'll be updating a test install from CI (or from more than one")
        print("machine), generate a shared debug keystore and re-run this command")
        print("with --debug-keystore <path> -- see the generated README.md's")
        print("\"Debug signing\" section for the exact keytool command.")
    print()
    if result.enclosing_git_root is not None:
        print(
            f"NOTE: {result.project_dir}/ is nested inside the existing git repo "
            f"at {result.enclosing_git_root}/ -- GitHub Actions only discovers "
            f"workflows at a repo's root, so move"
        )
        print(f"  {result.project_dir}/.github/workflows/android-build.yml")
        print("to")
        print(f"  {result.enclosing_git_root}/.github/workflows/android-build.yml")
        print(
            "(already generated with the right working-directory/artifact paths "
            "for this nested layout -- moving it is all that's needed)"
        )
        print("or the workflow above will never run.")
        print()
    print("To build locally instead (needs a JDK -- see the generated project's own")
    print("README.md):")
    print(f"  cd {result.project_dir}")
    print("  gradle assembleDebug")

    return 0


def _cmd_desktop_scaffold(args: argparse.Namespace) -> int:
    try:
        result = desktop.scaffold_project(
            args.build_dir,
            output_dir=args.output,
            target=args.target,
        )
    except DesktopError as exc:
        print(f"ARKlight desktop scaffold failed: {exc}", file=sys.stderr)
        return 1

    print(
        f"ARKlight v{__version__} scaffolded a {result.target} desktop project for "
        f"{result.app_name!r} ({result.app_id}) -> {result.project_dir}/ "
        f"({len(result.written_paths)} file(s))"
    )
    print()
    print("A native GTK3 + WebKit2GTK host, not a second application framework -- it")
    print("loads the packaged site straight from memory through an in-process 'ark:'")
    print("resource scheme. See the generated README.md for the system packages")
    print("(libgtk-3-dev / libwebkit2gtk-4.1-dev, or your distro's equivalents) and")
    print("build instructions.")
    print()
    print("Includes a GitHub Actions workflow (.github/workflows/desktop-build.yml)")
    print("that builds the project on a GitHub-hosted Linux runner, uploads the")
    print("binary as a downloadable artifact, then launches it under a headless Xvfb")
    print("display on that same runner to confirm it doesn't crash immediately -- no")
    print("local toolchain or display server needed for either check.")
    if result.enclosing_git_root is not None:
        print()
        print(
            f"NOTE: {result.project_dir}/ is nested inside the existing git repo "
            f"at {result.enclosing_git_root}/ -- GitHub Actions only discovers "
            f"workflows at a repo's root, so move"
        )
        print(f"  {result.project_dir}/.github/workflows/desktop-build.yml")
        print("to")
        print(f"  {result.enclosing_git_root}/.github/workflows/desktop-build.yml")
        print(
            "(already generated with the right working-directory/artifact path "
            "for this nested layout -- moving it is all that's needed)"
        )
        print("or the workflow above will never run.")
    print()
    print("To build locally instead:")
    print(f"  cd {result.project_dir}")
    print("  make")
    print(f"  ./bin/{result.binary_name}")

    return 0


def _cmd_desktop_build(args: argparse.Namespace) -> int:
    try:
        result = desktop.build_project(args.project_dir, run=args.run)
    except DesktopError as exc:
        print(f"ARKlight desktop build failed: {exc}", file=sys.stderr)
        return 1

    print(f"ARKlight v{__version__} built {result.binary_path}")
    if result.ran:
        print(f"Ran {result.binary_path} -- exited normally.")
    else:
        print(f"Run it with: {result.binary_path}")
    print()
    print("ARKlight supports cross-platform targets as well -- try it with this cmd:")
    print("  arklight android scaffold <build-dir> -o <project-dir>")

    return 0


def _cmd_deploy(args: argparse.Namespace) -> int:
    """
    `arklight deploy [cloudflare]` -- build, check that Wrangler is
    there, then hand the build directory to it. See
    docs/Foundational/DEPLOYMENT-CLI.md, and `arklight.cli.deploy` for
    what this deliberately does *not* do (install Wrangler, authenticate,
    upload, capture Wrangler's output).

    Exit code: 0 on success; a failed build's own code; 1 for a problem
    ARKlight itself found (missing Wrangler, missing build directory);
    otherwise Wrangler's exit code, unchanged.
    """
    entry = Path(args.entry)
    output = Path(args.output)
    # Same rule `arklight build` uses to find `arklight.config.py`: the
    # project is the directory the site file lives in. It is also where
    # a project-owned `wrangler.jsonc` is looked for and where Wrangler
    # runs.
    project_dir = entry.resolve().parent

    if not project_dir.is_dir():
        print(f"ARKlight deploy failed: directory not found: {project_dir}", file=sys.stderr)
        return 1

    if args.skip_build:
        try:
            deploy.check_build_dir(output)
        except DeployError as exc:
            print(f"ARKlight deploy failed: {exc}", file=sys.stderr)
            return 1
    else:
        if not entry.is_file():
            print(
                f"ARKlight deploy failed: site file not found: {entry}. Pass "
                f"its path (`arklight deploy cloudflare path/to/site.py`), or "
                f"use --skip-build to deploy an existing build directory.",
                file=sys.stderr,
            )
            return 1
        # Deliberately re-enters the CLI rather than calling
        # `compiler.pipeline.build` directly: `arklight build` already
        # owns project config, CSP/experimental handling, alpha-warning
        # and experimental-API output, and Rei's log mode, and deploy
        # should build *exactly* like `arklight build` does -- not a
        # second copy of that logic that drifts. `--no-open` because
        # nobody wants a browser window in the middle of a deploy.
        build_code = main(["build", str(entry), "-o", str(output), "--no-open"])
        if build_code != 0:
            print(
                "ARKlight deploy: the build failed, so nothing was deployed.",
                file=sys.stderr,
            )
            return build_code

    try:
        wrangler = deploy.find_wrangler()
        plan = deploy.plan_cloudflare(
            wrangler=wrangler,
            output_dir=output,
            project_dir=project_dir,
            name=args.name,
        )
    except DeployError as exc:
        print(f"ARKlight deploy failed: {exc}", file=sys.stderr)
        if not args.skip_build:
            print(
                f"(The site was built -> {output}/, but nothing was deployed.)",
                file=sys.stderr,
            )
        return 1

    print(f"ARKlight v{__version__} deploying {output}/ to Cloudflare Workers with Wrangler.")
    if plan.uses_project_config:
        print(
            f"Using the Wrangler config in {project_dir}/ -- it decides what "
            f"gets deployed. (ARKlight does not check that its assets "
            f"directory is {output}/.)"
        )
    else:
        print(
            f"No Wrangler config in {project_dir}/, so deploying {output}/ as "
            f"Worker {plan.worker_name!r} (compatibility date "
            f"{plan.compatibility_date}). Add a wrangler.jsonc there to "
            f"control this yourself."
        )
    print(f"$ {plan.display}")

    if args.dry_run:
        print("--dry-run: Wrangler was not run.")
        return 0

    print()
    try:
        code = deploy.run_wrangler(plan)
    except DeployError as exc:
        print(f"ARKlight deploy failed: {exc}", file=sys.stderr)
        return 1

    if code != 0:
        print(
            f"ARKlight deploy: Wrangler exited with code {code} -- see its "
            f"output above for the reason.",
            file=sys.stderr,
        )
    return code


def _cmd_new(args: argparse.Namespace) -> int:
    # `--explain-architecture` is informational and doesn't require a
    # project name -- `arklight new --explain-architecture` alone just
    # prints the guide and exits, so it can be run before ever
    # scaffolding anything. If a name *is* given alongside it, fall
    # through and scaffold as normal, then print the guide after.
    if args.explain_architecture and args.name is None:
        print(_ARCHITECTURE_GUIDE)
        return 0

    if args.name is None:
        print("ARKlight new failed: the following arguments are required: name", file=sys.stderr)
        return 1

    try:
        result = new_project(args.name, template=args.template, dest_dir=args.dir)
    except ScaffoldError as exc:
        print(f"ARKlight new failed: {exc}", file=sys.stderr)
        return 1

    print(
        f"ARKlight v{__version__} scaffolded a {result.template!r} project "
        f"-> {result.project_dir}/"
    )
    for path in result.written_paths:
        print(f"  {path}")
    print()
    print("Next steps:")
    print(f"  cd {result.project_dir}")
    print("  arklight build site.py -o ARK")

    if result.template == "production":
        print()
        print(_PRODUCTION_ARCHITECTURE_NOTE)
        if args.explain_architecture:
            print()
            print(_ARCHITECTURE_GUIDE)

    return 0


def _cmd_search(args: argparse.Namespace) -> int:
    if args.retrieve_doc:
        if args.serve:
            print(
                "arklight search: --retrieve-doc and --serve are mutually "
                "exclusive -- --serve starts the component-lookup stdio "
                "server, which has nothing to do with doc retrieval.",
                file=sys.stderr,
            )
            return 1

        for notice in ignored_flag_notices(args):
            print(f"arklight search: {notice}", file=sys.stderr)

        try:
            output = run_retrieve_doc(args)
        except DocRetrievalError as exc:
            print(f"arklight search: {exc}", file=sys.stderr)
            return 1
        print(render_markdown(output, color=resolve_color(args.color)))
        return 0

    doc_flags_used = [folder.flag for folder in DOC_FOLDERS if getattr(args, folder.attr, False)]
    if args.file is not None:
        doc_flags_used.append("--file")
    if getattr(args, "section", None) is not None:
        doc_flags_used.append("--section")
    if getattr(args, "color", "auto") != "auto":
        doc_flags_used.append("--color")
    if doc_flags_used:
        print(
            f"arklight search: {', '.join(doc_flags_used)} only apply with "
            "--retrieve-doc and are ignored here.",
            file=sys.stderr,
        )

    if args.serve:
        if args.name is not None:
            print(
                "arklight search: 'name' and --serve are mutually exclusive -- "
                "--serve starts a long-lived stdio server and never looks up a "
                "single name itself; a client sends lookups as requests once "
                "it's running.",
                file=sys.stderr,
            )
            return 1
        # Reuses the process-wide engine so a --serve session shares its
        # knowledge base/usage graph/stats connection with anything else
        # in this process, and so `.accept()`/`.record_confusion()` calls
        # made through the endpoint are immediately visible to any other
        # default_engine() caller in the same process.
        return serve_stdio(default_engine())

    if args.name is None:
        print("arklight search: the 'name' argument is required unless --serve is given.", file=sys.stderr)
        return 1

    try:
        print(search_component(args.name, limit=args.limit, near=args.near))
    except SearchEngineError as exc:
        print(f"ARKlight search failed: {exc}", file=sys.stderr)
        return 1

    if args.accept:
        # Only record acceptance on an exact match -- accepting a
        # "did you mean" suggestion the user never confirmed would be
        # guessing at intent, which the usage-stats signal deliberately
        # never does (see arklight/search/stats.py).
        canonical = resolve_exact(args.name)
        if canonical is not None:
            record_acceptance(canonical)
        else:
            print(
                f"--accept ignored: {args.name!r} isn't an exact component "
                f"name, so there's nothing to record.",
                file=sys.stderr,
            )

    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="arklight", description="Python-first static site compiler.")
    parser.add_argument("--version", action="version", version=f"arklight {__version__}")
    parser.add_argument(
        "--upgrade-alpha",
        action="store_true",
        default=False,
        help="Switch this (git-checkout) install over to the 'alpha' branch: "
        "fetch, switch/create the local branch, pull, and reinstall in "
        "place (pip install -e .) so the CLI reflects it immediately. "
        "Only works for a git-checkout/editable install -- see the error "
        "message if this isn't one.",
    )

    subparsers = parser.add_subparsers(dest="command", required=False)

    build_parser = subparsers.add_parser("build", help="Compile a site file to static HTML + CSS.")
    build_parser.add_argument(
        "entry",
        help="Path to the Python site file (e.g. site.py), or a previously "
        "--emit-arklight'd .arklight binary IR snapshot (detected by "
        "extension or magic bytes) -- rebuilds straight from the snapshot, "
        "skipping the Python compiler pipeline entirely.",
    )
    build_parser.add_argument(
        "-o", "--output", default="ARK", help="Output directory (default: ARK)"
    )
    open_group = build_parser.add_mutually_exclusive_group()
    open_group.add_argument(
        "--open",
        dest="open",
        action="store_true",
        default=True,
        help="Open the built site in your default browser after building (default).",
    )
    open_group.add_argument(
        "--no-open",
        dest="open",
        action="store_false",
        help="Don't open a browser after building.",
    )
    build_parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        default=False,
        help="Print each compiler pipeline stage as it runs (discovery, "
        "normalization, validation, IR build, each backend, ...) -- "
        "useful for seeing exactly where a slow or failing build is spending time.",
    )
    build_parser.add_argument(
        "--debug",
        action="store_true",
        default=False,
        help="Like --verbose, plus print the full chained traceback (instead of "
        "a short message) if the build fails -- for tracing a compiler "
        "error back to the exact stage and Python frame that raised it.",
    )
    build_parser.add_argument(
        "--narrate",
        action="store_true",
        default=False,
        help="Like --verbose, but narrated in short natural-language sentences "
        "by Rei, ARKlight's compiler narrator, instead of '[ARKlight] ...' "
        "stage lines. Mutually exclusive with --verbose/--debug. A "
        "project can pin this as its default via arklight.config.py's "
        "CONFIG = {'rei': {'default_mode': 'narrate'}} instead of "
        "passing the flag every time -- see "
        "docs/Foundational/DESIGN-NOTES.md.",
    )
    build_parser.add_argument(
        "--max-width",
        dest="max_width",
        default=None,
        metavar="VALUE",
        help="Override the page's max content width (--ark-max-width), e.g. "
        "'90rem', '1400px', '100%%'. Takes precedence over Site(max_width=...) "
        "in the site file, without requiring an edit to it. Default: "
        "ARKlight's fluid min(100%% - 3rem, 75rem).",
    )
    build_parser.add_argument(
        "--bg",
        dest="bg",
        default=None,
        metavar="VALUE",
        help="Override the page background (--ark-bg), e.g. '#0f0f1a'. Takes "
        "precedence over Site(bg=...) in the site file, without requiring an "
        "edit to it.",
    )
    build_parser.add_argument(
        "--font-family",
        dest="font_family",
        default=None,
        metavar="VALUE",
        help="Override the page font stack (--ark-font-family), e.g. "
        "'Georgia, serif' or '\"Inter\", sans-serif'. Takes precedence over "
        "Site(font_family=...) in the site file, without requiring an edit "
        "to it. Default: ARKlight's stock system-font stack.",
    )
    build_parser.add_argument(
        "--lang",
        dest="lang",
        default=None,
        metavar="TAG",
        help="Override the <html lang=\"...\"> tag, e.g. 'es', 'ta', 'fr-CA'. "
        "Overrides Site(lang=...) without requiring a site-file edit -- a "
        "page's own Page(lang=...), if it sets one, still wins for that page. "
        "Default: 'en'.",
    )
    build_parser.add_argument(
        "--button-text",
        dest="button_text",
        default=None,
        metavar="VALUE",
        help="Override button text color (--ark-button-text), e.g. '#111827'. "
        "Takes precedence over Site(button_text=...) in the site file. "
        "Default: '#ffffff' -- worth setting explicitly if you also choose a "
        "light --ark-accent, since button background follows accent.",
    )
    build_parser.add_argument(
        "--emit-arklight",
        dest="emit_arklight",
        nargs="?",
        const="",
        default=None,
        metavar="PATH",
        help="Also write the compiled Website IR as a binary .arklight file "
        "(arklight.ir.binary -- magic bytes, format version, schema "
        "generation tag, deduped string table). Bare flag writes "
        "<output>/site.arklight; pass a path to choose your own, e.g. "
        "--emit-arklight=build/site.arklight. A standalone, versioned "
        "snapshot of the IR that can be read back and rebuilt into a full "
        "site (`arklight build <that file>.arklight`) without re-running "
        "the Python compiler pipeline.",
    )
    build_parser.set_defaults(func=_cmd_build)

    pack_parser = subparsers.add_parser(
        "pack",
        help="Pack a build directory into a single .ark bundle (sealed by default).",
    )
    pack_parser.add_argument("build_dir", help="Path to an `arklight build` output directory (e.g. ARK)")
    pack_parser.add_argument(
        "-o", "--output", default="site.ark", help="Output bundle path (default: site.ark)"
    )
    pack_parser.add_argument(
        "--plain",
        action="store_true",
        default=False,
        help=(
            "Leave the archive half a plain, generically-openable ZIP "
            "(the original v1 behavior) instead of sealing it. Off by default."
        ),
    )
    pack_parser.add_argument(
        "--passphrase",
        default=None,
        help=(
            "Seal with a passphrase-derived key instead of an embedded one, for "
            "real confidentiality (the same passphrase is required to unpack later). "
            "Ignored with --plain. Note: shell history/process listings may expose "
            "a passphrase passed this way."
        ),
    )
    pack_parser.set_defaults(func=_cmd_pack)

    unpack_parser = subparsers.add_parser(
        "unpack", help="Extract a .ark bundle's archive half back into a build directory."
    )
    unpack_parser.add_argument("bundle", help="Path to a .ark bundle produced by `arklight pack`")
    unpack_parser.add_argument(
        "-o", "--output", default="ARK", help="Output directory (default: ARK)"
    )
    unpack_parser.add_argument(
        "--passphrase",
        default=None,
        help="Passphrase the bundle was sealed with (only needed for passphrase-sealed bundles).",
    )
    unpack_parser.set_defaults(func=_cmd_unpack)

    pwa_parser = subparsers.add_parser(
        "pwa",
        help="Turn a build directory into an installable PWA (manifest + service worker).",
    )
    pwa_parser.add_argument(
        "build_dir", help="Path to an `arklight build` output directory (e.g. ARK)"
    )
    pwa_parser.add_argument("--name", required=True, help="Full app name for the manifest")
    pwa_parser.add_argument(
        "--short-name",
        default=None,
        help="Short app name for the manifest (default: first 12 chars of --name)",
    )
    pwa_parser.add_argument(
        "--start-url",
        default="index.html",
        help="Manifest start_url, relative to the build directory (default: index.html)",
    )
    pwa_parser.add_argument(
        "--theme-color", default="#000000", help="Manifest/meta theme color (default: #000000)"
    )
    pwa_parser.add_argument(
        "--background-color",
        default="#ffffff",
        help="Manifest background color (default: #ffffff)",
    )
    pwa_parser.add_argument(
        "--display",
        default="standalone",
        choices=["standalone", "fullscreen", "minimal-ui", "browser"],
        help="Manifest display mode (default: standalone)",
    )
    pwa_parser.add_argument(
        "--icon",
        action="append",
        dest="icon",
        metavar="SRC:SIZES[:TYPE]",
        help=(
            "Add an icon to the manifest's icons list. SRC is a path relative "
            "to the build directory (e.g. an icon already under assets/), "
            "SIZES is WIDTHxHEIGHT or 'any', and TYPE is an optional MIME "
            "type (inferred from SRC's extension if omitted). Repeatable, "
            "e.g. --icon assets/icon-192.png:192x192 --icon "
            "assets/icon-512.png:512x512."
        ),
    )
    pwa_parser.add_argument(
        "--install-button",
        action="store_true",
        help=(
            "EXPERIMENTAL (see docs/Foundational/EXPERIMENTAL-APIS.md): inject a native "
            "install-prompt button into every page, via the "
            "`beforeinstallprompt` browser event. Off by default -- prints "
            "an experimental-API warning when used, since browser support "
            "for `beforeinstallprompt` is neither standardized nor "
            "universal."
        ),
    )
    pwa_parser.set_defaults(func=_cmd_pwa)

    android_parser = subparsers.add_parser(
        "android",
        help="Package an `arklight build` output directory as a native Android app "
        "(see docs/Backends/ANDROID-BACKEND-IMPLEMENTATION.md).",
    )
    android_subparsers = android_parser.add_subparsers(dest="android_command", required=True)

    android_scaffold_parser = android_subparsers.add_parser(
        "scaffold",
        help="Generate an Android Studio / Gradle project (Application mode) from a "
        "build directory. Templating only -- no JDK/Android SDK required (Stage 1 "
        "of the design doc's CLI ladder). Includes a GitHub Actions workflow that "
        "builds a debug APK and smoke-tests it (install + launch on an emulator), "
        "in CI with no local toolchain (Stages 2/3); no release-build job (needs a "
        "keystore this tool won't provision for you -- see the generated project's "
        "README). `arklight android build`, `--install`, and `--release`, which do "
        "the same on this machine, are Stages 5/6/7 and not yet implemented.",
    )
    android_scaffold_parser.add_argument(
        "build_dir", help="An `arklight build` output directory (e.g. ARK)."
    )
    android_scaffold_parser.add_argument(
        "-o",
        "--output",
        required=True,
        help="Directory to create the Android Studio / Gradle project in. Must not "
        "already exist, or must be empty.",
    )
    android_scaffold_parser.add_argument(
        "--debug-keystore",
        help="Path to a debug keystore to pin as this project's debug signing key "
        "(copied in as app/debug.keystore, must use the standard "
        "androiddebugkey/android/android alias+passwords -- see "
        "`keytool -genkeypair ...` in the generated README.md's \"Debug signing\" "
        "section for the exact command). Without this, every machine (a fresh CI "
        "runner included) auto-generates its own debug key, so debug APKs from "
        "different builds won't share a signature and can't be installed as "
        "updates over each other on the same test device.",
    )
    android_scaffold_parser.add_argument(
        "--release",
        action="store_true",
        help="Also generate a signed release-build job (assemble-release) in the "
        "GitHub Actions workflow. Off by default -- explicit opt-in, since the job "
        "is a no-op until you configure the RELEASE_KEYSTORE_BASE64, "
        "RELEASE_KEYSTORE_PASSWORD, RELEASE_KEY_ALIAS, and RELEASE_KEY_PASSWORD "
        "repo secrets it reads its signing key from (see the generated README.md's "
        "\"Building a release APK\" section) and is skipped on pull_request runs.",
    )
    android_scaffold_parser.set_defaults(func=_cmd_android_scaffold)

    desktop_parser = subparsers.add_parser(
        "desktop",
        help="Package an `arklight build` output directory as a native desktop app "
        "(see docs/Backends/DESKTOP-BACKEND-IMPLEMENTATION.md). Linux only for now.",
    )
    desktop_subparsers = desktop_parser.add_subparsers(dest="desktop_command", required=True)

    desktop_scaffold_parser = desktop_subparsers.add_parser(
        "scaffold",
        help="Generate a native GTK3 + WebKit2GTK host project from a build directory. "
        "Templating + asset-embedding only -- no C toolchain required to run this "
        "command itself (Stage 1 of the design doc's staged plan). Build the "
        "generated project with `arklight desktop build <project-dir>` (Stage 2), "
        "or `cd` in and run `make` yourself -- see the generated README.md.",
    )
    desktop_scaffold_parser.add_argument(
        "build_dir", help="An `arklight build` output directory (e.g. ARK)."
    )
    desktop_scaffold_parser.add_argument(
        "-o",
        "--output",
        required=True,
        help="Directory to create the desktop host project in. Must not already "
        "exist, or must be empty.",
    )
    desktop_scaffold_parser.add_argument(
        "--target",
        choices=desktop.SUPPORTED_TARGETS,
        default="linux",
        help="Desktop platform to scaffold for. Only 'linux' is implemented so far "
        "(default: linux) -- see docs/Backends/DESKTOP-BACKEND-IMPLEMENTATION.md for "
        "Windows/macOS status.",
    )
    desktop_scaffold_parser.set_defaults(func=_cmd_desktop_scaffold)

    desktop_build_parser = desktop_subparsers.add_parser(
        "build",
        help="Build an already-scaffolded desktop project by shelling out to its own "
        "`make` (Stage 2 -- the local counterpart to `arklight desktop scaffold`). "
        "Needs a C compiler, pkg-config, and the GTK3/WebKit2GTK dev headers on "
        "this machine -- see the scaffolded project's own README.md.",
    )
    desktop_build_parser.add_argument(
        "project_dir", help="An `arklight desktop scaffold` output directory."
    )
    desktop_build_parser.add_argument(
        "--run",
        action="store_true",
        help="Launch the built binary once `make` succeeds.",
    )
    desktop_build_parser.set_defaults(func=_cmd_desktop_build)

    deploy_parser = subparsers.add_parser(
        "deploy",
        help="Build the site, then deploy it with the hosting provider's own CLI "
        "(Cloudflare Workers via Wrangler). See docs/Foundational/DEPLOYMENT-CLI.md.",
        description="Build the site, then hand the build directory to the hosting "
        "provider's own CLI. ARKlight does not install that CLI, authenticate, or "
        "upload anything itself: it runs `wrangler deploy` and Wrangler does the rest, "
        "with its output shown as-is. Bare `arklight deploy` is `arklight deploy "
        "cloudflare`. Name the provider before the site file: `arklight deploy "
        "cloudflare my_site.py`.",
    )
    deploy_parser.add_argument(
        "provider",
        nargs="?",
        choices=deploy.PROVIDERS,
        default=deploy.DEFAULT_PROVIDER,
        help="Where to deploy (default: %(default)s, the only provider so far).",
    )
    deploy_parser.add_argument(
        "entry",
        nargs="?",
        default="site.py",
        help="Path to the Python site file to build (default: site.py). Its directory "
        "is the project directory: where a wrangler.jsonc is looked for and where "
        "Wrangler runs.",
    )
    deploy_parser.add_argument(
        "-o", "--output", default="ARK", help="Build output directory to deploy (default: ARK)"
    )
    deploy_parser.add_argument(
        "--name",
        default=None,
        help="Cloudflare Worker name, passed to Wrangler as-is (Wrangler/Cloudflare "
        "validate it). Default: the project directory's name, lowercased, when the "
        "project has no wrangler config; with one, the config's own name is used "
        "unless you pass this.",
    )
    deploy_parser.add_argument(
        "--skip-build",
        action="store_true",
        default=False,
        help="Deploy the existing --output directory as it is, without running "
        "`arklight build` first.",
    )
    deploy_parser.add_argument(
        "--dry-run",
        action="store_true",
        default=False,
        help="Build (unless --skip-build) and check for Wrangler, then print the "
        "Wrangler command that would run instead of running it. Nothing is deployed.",
    )
    deploy_parser.set_defaults(func=_cmd_deploy)

    new_parser = subparsers.add_parser(
        "new", help="Scaffold a new ARKlight project from a built-in template."
    )
    new_parser.add_argument(
        "name",
        nargs="?",
        default=None,
        help="Name of the new project (also the directory created for it). "
        "Optional only when used with --explain-architecture alone.",
    )
    new_parser.add_argument(
        "--template",
        choices=sorted(TEMPLATES),
        default="simple",
        help="Project template to scaffold (default: simple)",
    )
    new_parser.add_argument(
        "--dir",
        default=None,
        help="Directory to create the project in (default: current directory)",
    )
    new_parser.add_argument(
        "--explain-architecture",
        action="store_true",
        default=False,
        help="Print guidance on structuring an ARKlight project as "
        "service-oriented, separated-by-concern modules with minimal "
        "boilerplate (routes/pages/components/content), and how to extend "
        "that layout. Run alone (no name) to just read the guide, or "
        "alongside a --template production scaffold to print it right after.",
    )
    new_parser.set_defaults(func=_cmd_new)

    search_parser = subparsers.add_parser(
        "search",
        help="Look up a built-in component's schema by name (required props, children rules).",
    )
    search_parser.add_argument(
        "name",
        nargs="?",
        default=None,
        help="Component name to look up, e.g. Picture. Omit when using --serve.",
    )
    search_parser.add_argument(
        "--limit",
        type=int,
        default=5,
        help="Max number of 'did you mean' suggestions to show on a miss (default: 5).",
    )
    search_parser.add_argument(
        "--near",
        metavar="NAME",
        default=None,
        help="Bias suggestion ranking toward components structurally close to "
        "NAME in this project's own usage (personalized PageRank seed). "
        "NAME must be a component the usage graph has actually seen used.",
    )
    search_parser.add_argument(
        "--accept",
        action="store_true",
        default=False,
        help="On an exact match, record it in the usage store so future "
        "searches rank it higher (closes the learning loop).",
    )
    search_parser.add_argument(
        "--serve",
        action="store_true",
        default=False,
        help="Start the Stage 9 line-delimited JSON stdio server (see "
        "arklight.search.endpoint) instead of doing a single lookup -- "
        "for an editor/IDE extension to launch as a long-lived subprocess, "
        "the same way an LSP client launches a language server. Runs "
        "until stdin closes. 'name' must be omitted when this is given.",
    )
    search_parser.add_argument(
        "--retrieve-doc",
        dest="retrieve_doc",
        action="store_true",
        default=False,
        help="Switch 'search' from component-schema lookup into doc-tree "
        "retrieval: bare, prints the root docs/README.md; add a folder "
        "flag (--foundational, --proposals, ...) to print that folder's "
        "own README.md index; add --file NAME to also print one file's "
        "full contents, or --file NAME --section QUERY for just one "
        "section of it. Mutually exclusive with a component 'name' lookup "
        "(the literal 'index' is accepted in its place) and with --serve.",
    )
    doc_folder_group = search_parser.add_mutually_exclusive_group()
    for _doc_folder in DOC_FOLDERS:
        doc_folder_group.add_argument(
            _doc_folder.flag,
            dest=_doc_folder.attr,
            action="store_true",
            default=False,
            help=f"With --retrieve-doc, print docs/{_doc_folder.path}/README.md "
            f"({_doc_folder.blurb}).",
        )
    search_parser.add_argument(
        "--file",
        dest="file",
        metavar="NAME",
        default=None,
        help="With --retrieve-doc and a directory flag, append that file's "
        "full contents after the folder index. Matched case-insensitively "
        "against the folder's filenames by stem, with spaces/hyphens/"
        "underscores normalized (e.g. --file architecture).",
    )
    search_parser.add_argument(
        "--section",
        dest="section",
        metavar="QUERY",
        default=None,
        help="With --retrieve-doc, --file NAME, and a folder flag, print "
        "only one `##` section of that file instead of the whole thing. "
        "QUERY is a section number (that heading's own '## N. Title' "
        "numbering if the file uses one, else its 1-based position in the "
        "file), a heading-text fragment (matched the same way --file "
        "matches filenames, with a 'did you mean' on a near miss), or both "
        "together, e.g. --section '3 terminology'.",
    )
    search_parser.add_argument(
        "--color",
        choices=("auto", "always", "never"),
        default="auto",
        help="With --retrieve-doc, control ANSI styling of the printed "
        "Markdown. 'auto' (default) styles it when stdout is a terminal "
        "and NO_COLOR isn't set; 'always' forces styling (e.g. piping to "
        "`less -R`); 'never' prints the raw Markdown bytes untouched.",
    )
    search_parser.set_defaults(func=_cmd_search)

    live_streaming.add_subparser(subparsers)

    args = parser.parse_args(argv)

    if args.upgrade_alpha:
        # Standalone action, same shape as --version: doesn't require
        # (or care about) a subcommand, and short-circuits before the
        # `command is None` help-text branch below so `arklight
        # --upgrade-alpha` alone does the upgrade rather than printing help.
        return upgrade_to_alpha()

    if args.command is None:
        # `arklight` with no subcommand -- print the same usage/help
        # text `arklight --help` shows (subcommands, flags, short
        # description of each) rather than argparse's terser
        # "error: the following arguments are required: command".
        # A first-time user typing just `arklight` should see how to
        # get started, not a bare error.
        parser.print_help()
        return 0

    # One-time GPLv3 + additional-terms acceptance gate -- see
    # arklight/cli/license_gate.py for why this lives here rather than
    # at `pip install` time.
    if not ensure_license_accepted():
        return 1

    # Once per version, a fresh/plain-reinstalled `arklight` prints its
    # release note here on the first real command it runs -- same
    # marker-file idea as the license gate just above, see
    # arklight/cli/whats_new.py. `--upgrade-alpha` already prints its
    # own copy immediately (force=True there), so this is a no-op for
    # that path once the marker is recorded. Note this deliberately
    # does NOT use the `__version__` imported above -- that's the
    # PEP 440-normalized string from installed-package metadata (e.g.
    # "0.641"), which would never match a "v0.0641.md" file; see
    # whats_new.read_version for why the raw pyproject.toml spelling
    # is what has to be looked up instead.
    _current_version = read_version()
    if _current_version is not None:
        show_release_notes_if_new(_current_version)

    try:
        return args.func(args)
    except Exception as exc:  # noqa: BLE001 -- last-resort safety net, see below
        # Every subcommand above already catches its own typed error
        # (CompileError, PackError, PWAError, ScaffoldError) and prints a
        # clean message. Reaching this handler means something outside
        # those known, handled failure modes happened -- uncharted
        # territory ARKlight hasn't specifically anticipated or tested
        # for. Rather than dumping a raw traceback (which used to be the
        # only thing that could happen here), say so plainly, and be
        # explicit that whatever was being produced (a build/, a .ark
        # bundle, a scaffolded project) may be incomplete or unreliable.
        print(
            f"ARKlight hit an unexpected error while running `arklight "
            f"{args.command}` -- this is outside its known, handled "
            f"failure modes, so treat any partial output as untrustworthy:\n"
            f"  {type(exc).__name__}: {exc}\n"
            f"This isn't a documented/recommended failure path -- if you "
            f"can reproduce it, please file an issue at "
            f"https://github.com/Rae-ARK/ARKlight/issues with the exact "
            f"command you ran.",
            file=sys.stderr,
        )
        return 1


if __name__ == "__main__":
    sys.exit(main())
