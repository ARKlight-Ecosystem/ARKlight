"""
`arklight deploy` -- a thin hand-off from a built ARKlight site to a
hosting provider's own CLI. Spec: docs/Foundational/DEPLOYMENT-CLI.md.

    arklight deploy                      # same as `arklight deploy cloudflare`
    arklight deploy cloudflare [entry] [-o OUTPUT] [--name NAME]
                               [--skip-build] [--dry-run]

Cloudflare Workers (static assets) is the only provider so far, and it
is deployed by Wrangler, never by ARKlight. This module is deliberately
small and stays that way: it *plans* one `wrangler deploy` command and
*runs* it, and that is all.

    ARKlight owns:   Python source -> build -> a static output directory
    Wrangler owns:   that directory -> Cloudflare (auth, upload, config,
                     versions, the deployed URL, its error messages)

What this module must never do (DEPLOYMENT-CLI.md's "Provider
Boundary"):

  - install Wrangler, or run anything that could (`npm`/`npx`). A
    missing Wrangler is a `DeployError` that says how to install it;
    installing it is the user's decision. It is looked up on `PATH`
    only, never through `npx`, because `npx` will fetch a package it
    can't find.
  - authenticate, upload, or talk to Cloudflare's API. There is no
    token handling, no HTTP, no credential file access here.
  - validate what Cloudflare accepts. An explicit `--name` is passed to
    Wrangler untouched, so Cloudflare's own rules (which can change)
    are enforced by Cloudflare's own tool, with its own message.
  - capture Wrangler's output. stdin/stdout/stderr are inherited, so
    prompts (`wrangler login`), progress and the deployed URL reach the
    terminal exactly as Wrangler wrote them.

The one thing ARKlight *does* fill in is the minimum Wrangler needs when
the project has no Wrangler config of its own: an assets directory
(the build output), a Worker name, and a compatibility date. If the
project already has a `wrangler.jsonc`/`wrangler.json`/`wrangler.toml`
next to its site file, that config is the user's and is not overridden:
Wrangler is run as a plain `wrangler deploy` from that directory.
"""

from __future__ import annotations

import datetime
import re
import shlex
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

PROVIDERS = ("cloudflare",)
DEFAULT_PROVIDER = "cloudflare"

# The executable ARKlight looks for on PATH. Not configurable on
# purpose: pointing this at something else would make ARKlight a
# generic command runner, which is not what this subcommand is.
WRANGLER_EXECUTABLE = "wrangler"

# The names Wrangler itself reads its project config from. Only used to
# decide whether the project already owns its Cloudflare configuration
# -- ARKlight never opens or parses these.
WRANGLER_CONFIG_NAMES = ("wrangler.jsonc", "wrangler.json", "wrangler.toml")

# Cloudflare Worker names are DNS-label-like. This is only the fallback
# used to *derive* a name from a directory name when none was given; it
# is not a validator (see the module docstring), and it never runs on an
# explicit `--name`.
_MAX_DERIVED_NAME_LENGTH = 63

_WRANGLER_MISSING_MESSAGE = (
    "Wrangler (Cloudflare's own deployment CLI) was not found on your PATH. "
    "`arklight deploy cloudflare` hands the deployment to Wrangler and does "
    "not install it for you. Install and sign in to it yourself, then run "
    "this again:\n"
    "  npm install --global wrangler\n"
    "  wrangler login\n"
    "See https://developers.cloudflare.com/workers/wrangler/install-and-update/"
)


class DeployError(Exception):
    """A deploy failure ARKlight itself detected (missing Wrangler, a bad
    argument, a missing build directory). Anything that goes wrong inside
    Wrangler is Wrangler's to report -- it is not wrapped in this."""


@dataclass(frozen=True)
class CloudflarePlan:
    """The single Wrangler invocation `arklight deploy cloudflare` will
    make. Built without running anything, so `--dry-run` can print
    exactly what a real run would execute."""

    # argv[0] is the resolved absolute path to Wrangler (needed on
    # Windows, where it is a `.cmd` shim); `display` shows plain
    # `wrangler ...` instead so output reads the same on every machine.
    argv: tuple[str, ...]
    display: str
    cwd: Path
    assets_dir: Path
    # True when the project's own Wrangler config decides what gets
    # deployed, and ARKlight added no assets/name/date flags of its own.
    uses_project_config: bool
    worker_name: str | None
    compatibility_date: str | None


def find_wrangler() -> str:
    """Absolute path to Wrangler on `PATH`, or a `DeployError` saying how
    to install it. Never installs anything."""
    found = shutil.which(WRANGLER_EXECUTABLE)
    if found is None:
        raise DeployError(_WRANGLER_MISSING_MESSAGE)
    return found


def project_wrangler_config(project_dir: Path) -> Path | None:
    """The project's own Wrangler config file next to its site file, if
    it has one."""
    for name in WRANGLER_CONFIG_NAMES:
        candidate = project_dir / name
        if candidate.is_file():
            return candidate
    return None


def derive_worker_name(project_dir: Path) -> str:
    """A default Worker name from the project directory's name: lowercased,
    every run of characters outside `a-z0-9` collapsed to one `-`, trimmed
    of leading/trailing `-`, capped at 63 characters.

    Raises `DeployError` if nothing usable is left (a directory named
    `___`, say) rather than inventing a name -- a Worker name becomes part
    of the public URL, so a made-up one is worse than asking.
    """
    slug = re.sub(r"[^a-z0-9]+", "-", project_dir.name.lower()).strip("-")
    slug = slug[:_MAX_DERIVED_NAME_LENGTH].rstrip("-")
    if not slug:
        raise DeployError(
            f"Couldn't derive a Cloudflare Worker name from the directory "
            f"name {project_dir.name!r}. Pass one explicitly with --name."
        )
    return slug


def plan_cloudflare(
    *,
    wrangler: str,
    output_dir: Path,
    project_dir: Path,
    name: str | None = None,
    today: datetime.date | None = None,
) -> CloudflarePlan:
    """
    Decide the one `wrangler deploy` command to run.

    No project Wrangler config -> zero-config static-assets form, the
    exact flags Cloudflare documents for deploying a directory as a
    Workers static-assets site:

        wrangler deploy --assets <output> --name <name> --compatibility-date <today>

    A project Wrangler config -> plain `wrangler deploy` from the project
    directory; the config decides what is deployed. `--name` is forwarded
    only if the user explicitly gave one (Wrangler lets a CLI name
    override the config's), and no assets/date flags are added.

    `output_dir` is made absolute so the command means the same thing
    regardless of the directory Wrangler runs in. `today` exists so tests
    are deterministic.
    """
    assets_dir = output_dir.resolve()
    project_dir = project_dir.resolve()

    if project_wrangler_config(project_dir) is not None:
        args = ["deploy"]
        if name is not None:
            args += ["--name", name]
        worker_name = name
        compat = None
        uses_config = True
    else:
        worker_name = name if name is not None else derive_worker_name(project_dir)
        compat = (today or datetime.date.today()).isoformat()
        args = [
            "deploy",
            "--assets",
            str(assets_dir),
            "--name",
            worker_name,
            "--compatibility-date",
            compat,
        ]
        uses_config = False

    return CloudflarePlan(
        argv=(wrangler, *args),
        display=_display_command(args),
        cwd=project_dir,
        assets_dir=assets_dir,
        uses_project_config=uses_config,
        worker_name=worker_name,
        compatibility_date=compat,
    )


def _display_command(args: list[str]) -> str:
    return " ".join(shlex.quote(part) for part in [WRANGLER_EXECUTABLE, *args])


def check_build_dir(output_dir: Path) -> None:
    """For `--skip-build`: the directory to deploy must already exist and
    have something in it. (What counts as a complete site is the build's
    concern, not deploy's -- this only refuses to hand Wrangler nothing.)"""
    if not output_dir.is_dir():
        raise DeployError(
            f"Build directory not found: {output_dir}. Run `arklight build` "
            f"first, or drop --skip-build to let `arklight deploy` build it."
        )
    if not any(output_dir.iterdir()):
        raise DeployError(
            f"Build directory is empty: {output_dir}. Run `arklight build` "
            f"first, or drop --skip-build to let `arklight deploy` build it."
        )


def run_wrangler(plan: CloudflarePlan) -> int:
    """
    Run the planned command and return Wrangler's own exit code.

    stdin/stdout/stderr are inherited (not captured, not filtered) so
    Wrangler's prompts, progress and result reach the terminal untouched
    -- same reasoning as `arklight desktop build`'s `make` call. `check`
    is off on purpose: a non-zero exit is Wrangler's verdict to report
    and pass through, not an ARKlight exception.

    Ctrl-C is reported as the conventional exit code 130 rather than a
    traceback; Wrangler, in the same foreground process group, has
    already received the same signal.
    """
    try:
        completed = subprocess.run(list(plan.argv), cwd=plan.cwd, check=False)
    except FileNotFoundError as exc:
        # `find_wrangler` found it a moment ago; this is the executable
        # vanishing (or not being runnable) between lookup and launch.
        raise DeployError(
            f"Couldn't launch Wrangler at {plan.argv[0]}: {exc}"
        ) from exc
    except KeyboardInterrupt:
        return 130
    # A negative code means Wrangler was killed by a signal (POSIX
    # `subprocess` convention); report it the way a shell would.
    if completed.returncode < 0:
        return 128 - completed.returncode
    return completed.returncode
