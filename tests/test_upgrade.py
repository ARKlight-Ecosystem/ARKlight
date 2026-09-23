"""
`arklight --upgrade-alpha`'s reinstall step (`arklight/cli/upgrade.py`).

On a system Python with no virtualenv, pip 23.0+ refuses to install
into an "externally managed" environment (PEP 668), which used to
dead-end the whole flow. The reinstall now retries once with
`--break-system-packages` -- only after pip has asked for it.
"""

import subprocess
import sys

import pytest

from arklight.cli import upgrade
from arklight.cli.upgrade import UpgradeError, _pip_install_editable

_PEP_668_STDERR = (
    "error: externally-managed-environment\n\n"
    "\u00d7 This environment is externally managed\n"
    "hint: See PEP 668 for the detailed specification.\n"
)


def _fake_run(responses, calls):
    """A stand-in for `upgrade._run` that records each command and, per
    call, either returns or raises the next scripted outcome."""

    def fake(args, *, cwd):
        calls.append(list(args))
        outcome = responses[len(calls) - 1]
        if isinstance(outcome, Exception):
            raise outcome
        return outcome

    return fake


def _pip_failure(stderr):
    return UpgradeError(f"`pip install` failed:\n  {stderr}")


def test_plain_install_succeeds_without_the_flag(monkeypatch, tmp_path):
    calls = []
    monkeypatch.setattr(upgrade, "_run", _fake_run([""], calls))
    _pip_install_editable(tmp_path)
    assert len(calls) == 1
    assert "--break-system-packages" not in calls[0]
    assert calls[0][:4] == [sys.executable, "-m", "pip", "install"]
    assert str(tmp_path) in calls[0]


def test_externally_managed_error_retries_once_with_the_flag(monkeypatch, tmp_path, capsys):
    calls = []
    monkeypatch.setattr(
        upgrade, "_run", _fake_run([_pip_failure(_PEP_668_STDERR), ""], calls)
    )
    _pip_install_editable(tmp_path)
    assert len(calls) == 2
    assert "--break-system-packages" not in calls[0]
    assert calls[1] == [*calls[0], "--break-system-packages"]
    assert "--break-system-packages" in capsys.readouterr().out


def test_other_pip_failures_are_not_retried(monkeypatch, tmp_path):
    calls = []
    monkeypatch.setattr(
        upgrade, "_run", _fake_run([_pip_failure("ERROR: No matching distribution")], calls)
    )
    with pytest.raises(UpgradeError, match="No matching distribution"):
        _pip_install_editable(tmp_path)
    assert len(calls) == 1


def test_a_failing_retry_propagates(monkeypatch, tmp_path):
    calls = []
    monkeypatch.setattr(
        upgrade,
        "_run",
        _fake_run([_pip_failure(_PEP_668_STDERR), _pip_failure("ERROR: build failed")], calls),
    )
    with pytest.raises(UpgradeError, match="build failed"):
        _pip_install_editable(tmp_path)
    assert len(calls) == 2


def test_run_wraps_pip_stderr_so_the_marker_survives(tmp_path):
    """The retry keys off pip's stderr making it into UpgradeError's
    message, so pin that `_run` really carries stderr through."""
    script = f"import sys; sys.stderr.write({_PEP_668_STDERR!r}); sys.exit(1)"
    with pytest.raises(UpgradeError) as excinfo:
        upgrade._run([sys.executable, "-c", script], cwd=tmp_path)
    assert upgrade._EXTERNALLY_MANAGED in str(excinfo.value)


def test_upgrade_to_alpha_uses_the_retrying_installer(monkeypatch, tmp_path):
    """The full flow reinstalls through `_pip_install_editable`, not a
    bare pip command, after the git steps."""
    repo = tmp_path / "repo"
    (repo / ".git").mkdir(parents=True)
    (repo / "pyproject.toml").write_text('[project]\nversion = "0.0"\n', encoding="utf-8")

    import arklight

    monkeypatch.setattr(arklight, "__file__", str(repo / "arklight" / "__init__.py"))
    commands = []
    installed = []

    def fake_run(args, *, cwd):
        commands.append(args)
        return "  alpha" if args[:3] == ["git", "branch", "--list"] else "x"

    monkeypatch.setattr(upgrade, "_run", fake_run)
    monkeypatch.setattr(upgrade, "_pip_install_editable", installed.append)
    monkeypatch.setattr(upgrade, "show_release_notes_if_new", lambda *a, **k: None)

    assert upgrade.upgrade_to_alpha() == 0
    assert installed == [repo.resolve()]
    assert not any("pip" in command for command in commands)
