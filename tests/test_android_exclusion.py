"""
Guard for the standing Android exclusion on `main`.

`main` deliberately ships no Android backend or CLI (see
`docs/syncing main with alpha branch/MAIN TO ALPHA V0.070.md`,
Stage 11). The sync from `alpha` is done in many patches, and a
wholesale-copied file (`cli/main.py`, `config.py`, `templates/_common.py`)
can quietly bring Android wiring back in. This makes the Stage 11
checklist re-runnable by the test suite instead of by hand.

Deliberately NOT checked: the word "android" appearing in prose or as a
backend *name* (`BACKEND_PLATFORM_API_SUPPORT["android"]`,
`register_backend("android")`, docstrings). Those are the shared
Platform API IR / component-dispatch vocabulary, identical on `alpha`,
and they name a backend `main` does not have without implementing it.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

import arklight
from arklight import config

ROOT = Path(arklight.__file__).resolve().parent.parent


def test_android_backend_package_is_absent():
    assert not (ROOT / "arklight" / "backend" / "android").exists()


def test_android_cli_module_is_absent():
    assert not (ROOT / "arklight" / "cli" / "android.py").exists()


def test_android_and_desktop_are_not_known_config_sections():
    assert "android" not in config._KNOWN_SECTIONS
    assert "android" not in config._KNOWN_KEYS


def test_android_test_files_are_not_carried_over():
    stray = sorted(p.name for p in (ROOT / "tests").glob("test_android*.py") if p.name != Path(__file__).name)
    assert stray == []


def test_cli_main_does_not_import_or_wire_android():
    source = (ROOT / "arklight" / "cli" / "main.py").read_text(encoding="utf-8").lower()
    assert "android" not in source


def test_scaffolded_config_does_not_advertise_android():
    source = (ROOT / "arklight" / "cli" / "templates" / "_common.py").read_text(encoding="utf-8").lower()
    assert "android" not in source


def test_root_readme_has_no_android_command_examples():
    readme = (ROOT / "README.md").read_text(encoding="utf-8").lower()
    assert "arklight android" not in readme


@pytest.mark.parametrize("args", [["android"], ["android", "scaffold", "x"]])
def test_android_is_not_a_cli_subcommand(args):
    proc = subprocess.run(
        [sys.executable, "-m", "arklight.cli.main", *args],
        capture_output=True,
        text=True,
        env={**__import__("os").environ, "ARKLIGHT_ACCEPT_LICENSE": "1"},
    )
    assert proc.returncode != 0
    assert "invalid choice" in proc.stderr
