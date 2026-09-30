"""
Guard for the Desktop-backend exclusion on `main`.

Sibling of `test_android_exclusion.py`. `alpha` grew a Linux-only
Desktop backend mid-range (`be519fd`); `main`'s own roadmap places it at
`v0.100`, after Android (`v0.080`), so the v0.070 sync excludes it (see
`docs/syncing main with alpha branch/MAIN TO ALPHA V0.070.md`, Stage 12).
If the maintainer later decides to land it early, delete this file in
the same change (that is Stage 12a in the plan) -- a failing guard is
the intended prompt to do so deliberately.

Not checked, on purpose: the word "desktop" in prose (e.g. "phone vs
desktop" CSS examples) or as a backend *name* in the shared Platform API
IR (`BACKEND_PLATFORM_API_SUPPORT["desktop"]`), which `alpha` shares and
which names a backend without implementing it.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

import arklight
from arklight import config

ROOT = Path(arklight.__file__).resolve().parent.parent

# Every Desktop-only path `alpha` has (verified against `23ebc24`).
ALPHA_DESKTOP_PATHS = [
    "arklight/backend/desktop",
    "arklight/cli/desktop.py",
    "examples/hello_desktop",
    "docs/Backends/ARKLIGHT_DESKTOP_BACKEND_PROPOSAL.md",
    "docs/Backends/DESKTOP-BACKEND-IMPLEMENTATION.md",
    "tests/test_desktop.py",
]


@pytest.mark.parametrize("rel", ALPHA_DESKTOP_PATHS)
def test_desktop_only_path_is_absent(rel):
    assert not (ROOT / rel).exists(), rel


def test_desktop_is_not_a_known_config_section():
    assert "desktop" not in config._KNOWN_SECTIONS
    assert "desktop" not in config._KNOWN_KEYS


def test_cli_main_does_not_import_or_wire_desktop():
    source = (ROOT / "arklight" / "cli" / "main.py").read_text(encoding="utf-8").lower()
    assert "desktop" not in source


def test_scaffolded_config_does_not_advertise_desktop():
    source = (ROOT / "arklight" / "cli" / "templates" / "_common.py").read_text(encoding="utf-8").lower()
    assert "desktop" not in source


@pytest.mark.parametrize("args", [["desktop"], ["desktop", "scaffold", "x"], ["desktop", "build", "x"]])
def test_desktop_is_not_a_cli_subcommand(args):
    proc = subprocess.run(
        [sys.executable, "-m", "arklight.cli.main", *args],
        capture_output=True,
        text=True,
        env={**os.environ, "ARKLIGHT_ACCEPT_LICENSE": "1"},
    )
    assert proc.returncode != 0
    assert "invalid choice" in proc.stderr


def test_main_only_workflow_is_untouched():
    assert (ROOT / ".github" / "workflows" / "apt-repo.yml").is_file()
