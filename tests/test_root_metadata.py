"""
Stage 13 guard (docs/syncing main with alpha branch/MAIN TO ALPHA V0.070.md):
root metadata after the v0.070 catch-up.

Locks the three things that stage is responsible for, so a later stage's
patch regeneration cannot silently undo them:

* ``pyproject.toml`` uses the ``0.MMM.PP`` version scheme and reads
  ``0.070.0`` (``importlib.metadata`` normalizes this to ``0.70.0``,
  which is what ``arklight --version`` prints).
* ``.github/workflows/apt-repo.yml`` -- the one ``main``-only file --
  is still present and non-empty.
* ``main``-only root differences from ``alpha`` were kept on purpose:
  the SPDX ``license`` string / empty ``classifiers`` in ``pyproject.toml``
  and the ``ARK/`` line in ``.gitignore``.
"""

import re
import tomllib
from importlib.metadata import version as installed_version
from pathlib import Path

import arklight

ROOT = Path(__file__).resolve().parent.parent


def _pyproject():
    return tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))


def test_pyproject_version_is_v0070_in_the_mmm_pp_scheme():
    version = _pyproject()["project"]["version"]
    assert re.fullmatch(r"0\.\d{3}\.\d+", version), version
    assert version == "0.070.0"


def test_installed_metadata_is_the_pep440_normalization_of_pyproject():
    # "0.070.0" -> "0.70.0": leading zeros are dropped by PEP 440
    # normalization, and that is what --version reports.
    assert installed_version("arklight") == "0.70.0"
    assert arklight.__version__ == "0.70.0"


def test_channel_is_still_main():
    assert arklight.CHANNEL == "main"


def test_apt_repo_workflow_is_untouched_and_present():
    workflow = ROOT / ".github" / "workflows" / "apt-repo.yml"
    assert workflow.is_file()
    assert workflow.read_text(encoding="utf-8").strip()


def test_main_only_pyproject_license_metadata_is_kept():
    project = _pyproject()["project"]
    assert project["license"] == "GPL-3.0-or-later"
    assert project["classifiers"] == []


def test_main_only_gitignore_entry_is_kept():
    lines = (ROOT / ".gitignore").read_text(encoding="utf-8").splitlines()
    assert "ARK/" in lines
