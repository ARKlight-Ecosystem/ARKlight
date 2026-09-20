"""
`arklight deploy` (arklight/cli/deploy.py, arklight/cli/main.py's
`_cmd_deploy`) -- spec in docs/Foundational/DEPLOYMENT-CLI.md.

No test talks to Cloudflare or needs the real Wrangler. A stand-in
`wrangler` executable on `PATH` records exactly how it was invoked
(argv, working directory) and exits with whatever code the test asks
for, so what's checked is ARKlight's side of the boundary: which
command it builds, when it runs it, what it refuses to do, and that it
passes Wrangler's exit code through untouched.

The command shape itself was also checked by hand against a real
Wrangler (4.135.0) with `wrangler deploy --assets ... --name ...
--compatibility-date ... --dry-run`.
"""

from __future__ import annotations

import datetime
import json
import os
import stat
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

from arklight.cli import deploy
from arklight.cli.deploy import (
    DeployError,
    check_build_dir,
    derive_worker_name,
    find_wrangler,
    plan_cloudflare,
    project_wrangler_config,
    run_wrangler,
)
from arklight.cli.main import main

pytestmark = pytest.mark.skipif(
    sys.platform == "win32",
    reason="the stand-in `wrangler` is a POSIX script with a shebang line",
)

SITE = """\
# include <stdlib.ARKlight>
site = Site()

@site.page("/")
def home():
    return Page(Heading("Hi"), Text("Hello from ARKlight."))
"""

BROKEN_SITE = """\
# include <stdlib.ARKlight>
site = Site()

@site.page("/")
def home():
    return Page(NotARealComponent("x"))
"""

TODAY = datetime.date(2026, 9, 20)


# --------------------------------------------------------------------
# Fixtures / helpers
# --------------------------------------------------------------------


def _write_executable(path: Path, body: str) -> None:
    path.write_text(body)
    path.chmod(path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


@pytest.fixture
def project(tmp_path, monkeypatch):
    """A project directory with a valid site.py, used as the cwd."""
    proj = tmp_path / "My Site"
    proj.mkdir()
    (proj / "site.py").write_text(SITE)
    monkeypatch.chdir(proj)
    return proj


@pytest.fixture
def bin_dir(tmp_path, monkeypatch):
    """A `PATH` containing only this directory (so a real `wrangler`,
    `npm` or `npx` on the developer's machine can never leak in)."""
    d = tmp_path / "bin"
    d.mkdir()
    monkeypatch.setenv("PATH", str(d))
    return d


@pytest.fixture
def fake_wrangler(bin_dir, tmp_path, monkeypatch):
    """Install a stand-in `wrangler`. Returns a callable that reads back
    what it recorded. Exit code comes from FAKE_WRANGLER_EXIT."""
    log = tmp_path / "wrangler-calls.jsonl"
    _write_executable(
        bin_dir / "wrangler",
        f"#!{sys.executable}\n"
        + textwrap.dedent(
            """\
            import json, os, sys
            with open(os.environ["FAKE_WRANGLER_LOG"], "a") as f:
                f.write(json.dumps({"argv": sys.argv[1:], "cwd": os.getcwd()}) + "\\n")
            print("fake-wrangler-stdout-line")
            print("fake-wrangler-stderr-line", file=sys.stderr)
            sys.exit(int(os.environ.get("FAKE_WRANGLER_EXIT", "0")))
            """
        ),
    )
    monkeypatch.setenv("FAKE_WRANGLER_LOG", str(log))

    def calls() -> list[dict]:
        if not log.exists():
            return []
        return [json.loads(line) for line in log.read_text().splitlines()]

    return calls


def _install_installer_tripwires(bin_dir: Path, tmp_path: Path) -> Path:
    """`npm`/`npx`/`pnpm`/`yarn`/`corepack` stand-ins that record being run."""
    log = tmp_path / "installer-calls.txt"
    for name in ("npm", "npx", "pnpm", "yarn", "corepack"):
        _write_executable(
            bin_dir / name,
            f'#!/bin/sh\necho "{name} $@" >> "{log}"\nexit 0\n',
        )
    return log


# --------------------------------------------------------------------
# find_wrangler
# --------------------------------------------------------------------


def test_find_wrangler_returns_absolute_path_when_present(fake_wrangler, bin_dir):
    assert find_wrangler() == str(bin_dir / "wrangler")


def test_find_wrangler_missing_explains_install_and_login(bin_dir):
    with pytest.raises(DeployError) as excinfo:
        find_wrangler()
    message = str(excinfo.value)
    assert "Wrangler" in message
    assert "npm install --global wrangler" in message
    assert "wrangler login" in message
    assert "does not install it for you" in message


def test_find_wrangler_never_runs_an_installer(bin_dir, tmp_path):
    tripwire_log = _install_installer_tripwires(bin_dir, tmp_path)
    with pytest.raises(DeployError):
        find_wrangler()
    assert not tripwire_log.exists()


# --------------------------------------------------------------------
# derive_worker_name
# --------------------------------------------------------------------


@pytest.mark.parametrize(
    ("dirname", "expected"),
    [
        ("my-site", "my-site"),
        ("My Site", "my-site"),
        ("Rae's  Portfolio_2026", "rae-s-portfolio-2026"),
        ("--edge--", "edge"),
        ("UPPER", "upper"),
    ],
)
def test_derive_worker_name(tmp_path, dirname, expected):
    assert derive_worker_name(tmp_path / dirname) == expected


def test_derive_worker_name_is_capped_at_63_and_never_ends_with_dash(tmp_path):
    name = derive_worker_name(tmp_path / ("a" * 62 + " b"))
    assert len(name) <= 63
    assert not name.endswith("-")
    assert not name.startswith("-")


@pytest.mark.parametrize("dirname", ["___", "日本語", "..."])
def test_derive_worker_name_with_nothing_usable_asks_for_name(tmp_path, dirname):
    with pytest.raises(DeployError, match="--name"):
        derive_worker_name(tmp_path / dirname)


# --------------------------------------------------------------------
# plan_cloudflare
# --------------------------------------------------------------------


def test_plan_without_project_config_uses_documented_static_assets_form(tmp_path):
    proj = tmp_path / "blog"
    proj.mkdir()
    out = proj / "ARK"
    out.mkdir()

    plan = plan_cloudflare(
        wrangler="/usr/local/bin/wrangler",
        output_dir=out,
        project_dir=proj,
        today=TODAY,
    )

    assert plan.argv == (
        "/usr/local/bin/wrangler",
        "deploy",
        "--assets",
        str(out.resolve()),
        "--name",
        "blog",
        "--compatibility-date",
        "2026-09-20",
    )
    assert plan.cwd == proj.resolve()
    assert plan.uses_project_config is False
    assert plan.worker_name == "blog"
    assert plan.compatibility_date == "2026-09-20"


def test_plan_display_uses_plain_wrangler_not_the_resolved_path(tmp_path):
    proj = tmp_path / "blog"
    proj.mkdir()
    plan = plan_cloudflare(
        wrangler="/some/odd/place/wrangler", output_dir=proj / "ARK", project_dir=proj, today=TODAY
    )
    assert plan.display.startswith("wrangler deploy --assets ")
    assert "/some/odd/place" not in plan.display


def test_plan_explicit_name_is_passed_through_unvalidated(tmp_path):
    proj = tmp_path / "blog"
    proj.mkdir()
    # Cloudflare's rules are Cloudflare's to enforce; ARKlight must not
    # second-guess (or "fix") an explicit name.
    plan = plan_cloudflare(
        wrangler="wrangler",
        output_dir=proj / "ARK",
        project_dir=proj,
        name="Whatever_Name!",
        today=TODAY,
    )
    assert plan.argv[plan.argv.index("--name") + 1] == "Whatever_Name!"
    assert plan.worker_name == "Whatever_Name!"


def test_plan_display_shell_quotes_paths_with_spaces(tmp_path):
    proj = tmp_path / "has space"
    proj.mkdir()
    plan = plan_cloudflare(
        wrangler="wrangler", output_dir=proj / "ARK", project_dir=proj, today=TODAY
    )
    assert f"'{(proj / 'ARK').resolve()}'" in plan.display


@pytest.mark.parametrize("config_name", ["wrangler.jsonc", "wrangler.json", "wrangler.toml"])
def test_plan_with_project_config_is_plain_wrangler_deploy(tmp_path, config_name):
    proj = tmp_path / "blog"
    proj.mkdir()
    (proj / config_name).write_text("{}")

    plan = plan_cloudflare(
        wrangler="wrangler", output_dir=proj / "ARK", project_dir=proj, today=TODAY
    )

    assert plan.argv == ("wrangler", "deploy")
    assert plan.uses_project_config is True
    assert plan.compatibility_date is None
    assert plan.worker_name is None
    assert plan.cwd == proj.resolve()


def test_plan_with_project_config_forwards_only_an_explicit_name(tmp_path):
    proj = tmp_path / "blog"
    proj.mkdir()
    (proj / "wrangler.jsonc").write_text("{}")

    plan = plan_cloudflare(
        wrangler="wrangler",
        output_dir=proj / "ARK",
        project_dir=proj,
        name="override",
        today=TODAY,
    )

    assert plan.argv == ("wrangler", "deploy", "--name", "override")


def test_project_wrangler_config_finds_each_supported_name(tmp_path):
    assert project_wrangler_config(tmp_path) is None
    for name in ("wrangler.jsonc", "wrangler.json", "wrangler.toml"):
        (tmp_path / name).write_text("")
        assert project_wrangler_config(tmp_path) == tmp_path / name
        (tmp_path / name).unlink()


def test_plan_defaults_the_date_to_today_when_not_injected(tmp_path):
    proj = tmp_path / "blog"
    proj.mkdir()
    plan = plan_cloudflare(wrangler="wrangler", output_dir=proj / "ARK", project_dir=proj)
    assert plan.compatibility_date == datetime.date.today().isoformat()


# --------------------------------------------------------------------
# check_build_dir
# --------------------------------------------------------------------


def test_check_build_dir_rejects_missing_and_empty(tmp_path):
    with pytest.raises(DeployError, match="not found"):
        check_build_dir(tmp_path / "ARK")
    (tmp_path / "ARK").mkdir()
    with pytest.raises(DeployError, match="empty"):
        check_build_dir(tmp_path / "ARK")


def test_check_build_dir_accepts_a_populated_directory(tmp_path):
    (tmp_path / "ARK").mkdir()
    (tmp_path / "ARK" / "index.html").write_text("x")
    check_build_dir(tmp_path / "ARK")  # no exception


# --------------------------------------------------------------------
# run_wrangler
# --------------------------------------------------------------------


def _plan_for(tmp_path, wrangler_path: str):
    proj = tmp_path / "p"
    proj.mkdir(exist_ok=True)
    return plan_cloudflare(
        wrangler=wrangler_path, output_dir=proj / "ARK", project_dir=proj, today=TODAY
    )


def test_run_wrangler_returns_exit_code_unchanged(fake_wrangler, bin_dir, tmp_path, monkeypatch):
    plan = _plan_for(tmp_path, str(bin_dir / "wrangler"))
    monkeypatch.setenv("FAKE_WRANGLER_EXIT", "0")
    assert run_wrangler(plan) == 0
    monkeypatch.setenv("FAKE_WRANGLER_EXIT", "7")
    assert run_wrangler(plan) == 7


def test_run_wrangler_does_not_capture_output(fake_wrangler, bin_dir, tmp_path, capfd):
    run_wrangler(_plan_for(tmp_path, str(bin_dir / "wrangler")))
    captured = capfd.readouterr()
    assert "fake-wrangler-stdout-line" in captured.out
    assert "fake-wrangler-stderr-line" in captured.err


def test_run_wrangler_reports_a_signal_death_like_a_shell(tmp_path, monkeypatch):
    monkeypatch.setattr(
        subprocess, "run", lambda *a, **k: subprocess.CompletedProcess(a, returncode=-9)
    )
    assert run_wrangler(_plan_for(tmp_path, "wrangler")) == 137


def test_run_wrangler_maps_ctrl_c_to_130_without_a_traceback(tmp_path, monkeypatch):
    def interrupted(*args, **kwargs):
        raise KeyboardInterrupt

    monkeypatch.setattr(subprocess, "run", interrupted)
    assert run_wrangler(_plan_for(tmp_path, "wrangler")) == 130


def test_run_wrangler_reports_an_unlaunchable_binary(tmp_path):
    with pytest.raises(DeployError, match="Couldn't launch Wrangler"):
        run_wrangler(_plan_for(tmp_path, str(tmp_path / "does-not-exist")))


# --------------------------------------------------------------------
# The CLI, end to end
# --------------------------------------------------------------------


def test_bare_deploy_builds_then_runs_wrangler_once(project, fake_wrangler, capfd):
    code = main(["deploy"])

    assert code == 0
    assert (project / "ARK" / "index.html").is_file()

    calls = fake_wrangler()
    assert len(calls) == 1
    argv = calls[0]["argv"]
    assert argv[:2] == ["deploy", "--assets"]
    assert argv[2] == str((project / "ARK").resolve())
    assert argv[3:5] == ["--name", "my-site"]
    assert argv[5] == "--compatibility-date"
    assert argv[6] == datetime.date.today().isoformat()
    assert Path(calls[0]["cwd"]).resolve() == project.resolve()

    out = capfd.readouterr().out
    assert "fake-wrangler-stdout-line" in out  # forwarded, not swallowed


def test_deploy_cloudflare_is_the_same_as_bare_deploy(project, fake_wrangler):
    assert main(["deploy"]) == 0
    assert main(["deploy", "cloudflare"]) == 0
    first, second = fake_wrangler()
    assert first == second


def test_deploy_never_opens_a_browser(project, fake_wrangler, monkeypatch):
    import webbrowser

    opened = []
    monkeypatch.setattr(webbrowser, "open", lambda *a, **k: opened.append(a) or True)
    assert main(["deploy"]) == 0
    assert opened == []


def test_deploy_builds_before_it_looks_for_wrangler(project, bin_dir, capsys):
    # No wrangler on PATH: the build still happens (spec step 1), then
    # the missing tool is reported (step 2) and nothing is deployed.
    code = main(["deploy"])

    assert code == 1
    assert (project / "ARK" / "index.html").is_file()
    err = capsys.readouterr().err
    assert "Wrangler" in err
    assert "npm install --global wrangler" in err
    assert "nothing was deployed" in err


def test_deploy_without_wrangler_never_runs_an_installer(project, bin_dir, tmp_path):
    tripwire_log = _install_installer_tripwires(bin_dir, tmp_path)
    assert main(["deploy"]) == 1
    assert not tripwire_log.exists()


def test_deploy_passes_wrangler_exit_code_through(project, fake_wrangler, monkeypatch, capsys):
    monkeypatch.setenv("FAKE_WRANGLER_EXIT", "3")
    code = main(["deploy"])
    assert code == 3
    assert "Wrangler exited with code 3" in capsys.readouterr().err


def test_deploy_success_adds_no_failure_message(project, fake_wrangler, capsys):
    assert main(["deploy"]) == 0
    assert "exited with code" not in capsys.readouterr().err


def test_failed_build_never_invokes_wrangler(project, fake_wrangler, capsys):
    (project / "site.py").write_text(BROKEN_SITE)

    code = main(["deploy"])

    assert code == 1
    assert fake_wrangler() == []
    err = capsys.readouterr().err
    assert "nothing was deployed" in err


def test_deploy_missing_site_file_is_a_clean_error(project, fake_wrangler, capsys):
    (project / "site.py").unlink()
    code = main(["deploy"])
    assert code == 1
    assert fake_wrangler() == []
    err = capsys.readouterr().err
    assert "site file not found" in err
    assert "--skip-build" in err


def test_deploy_custom_entry_and_output(project, fake_wrangler):
    (project / "other.py").write_text(SITE)
    assert main(["deploy", "cloudflare", "other.py", "-o", "public"]) == 0
    assert (project / "public" / "index.html").is_file()
    assert not (project / "ARK").exists()
    argv = fake_wrangler()[0]["argv"]
    assert argv[argv.index("--assets") + 1] == str((project / "public").resolve())


def test_options_work_before_or_after_the_provider(project, fake_wrangler):
    assert main(["deploy", "-o", "one", "cloudflare"]) == 0
    assert main(["deploy", "cloudflare", "-o", "two"]) == 0
    first, second = fake_wrangler()
    assert first["argv"][2].endswith("/one")
    assert second["argv"][2].endswith("/two")


def test_explicit_name_flag_reaches_wrangler(project, fake_wrangler):
    assert main(["deploy", "--name", "chosen-name"]) == 0
    argv = fake_wrangler()[0]["argv"]
    assert argv[argv.index("--name") + 1] == "chosen-name"


def test_entry_in_another_directory_sets_the_project_directory(
    tmp_path, project, fake_wrangler
):
    other = tmp_path / "elsewhere"
    other.mkdir()
    (other / "site.py").write_text(SITE)
    (other / "wrangler.jsonc").write_text("{}")

    assert main(["deploy", "cloudflare", str(other / "site.py"), "-o", str(other / "ARK")]) == 0

    call = fake_wrangler()[0]
    assert call["argv"] == ["deploy"]  # the project's own config decides
    assert Path(call["cwd"]).resolve() == other.resolve()


def test_project_config_run_says_the_config_decides(project, fake_wrangler, capsys):
    (project / "wrangler.toml").write_text('name = "mine"\n')
    assert main(["deploy"]) == 0
    assert fake_wrangler()[0]["argv"] == ["deploy"]
    out = capsys.readouterr().out
    assert "Wrangler config" in out
    assert "decides" in out


def test_no_config_run_says_what_it_chose(project, fake_wrangler, capsys):
    assert main(["deploy"]) == 0
    out = capsys.readouterr().out
    assert "No Wrangler config" in out
    assert "'my-site'" in out
    assert "$ wrangler deploy --assets" in out


# --- --dry-run ------------------------------------------------------


def test_dry_run_prints_the_command_and_does_not_run_wrangler(project, fake_wrangler, capsys):
    code = main(["deploy", "--dry-run"])

    assert code == 0
    assert fake_wrangler() == []
    out = capsys.readouterr().out
    assert "$ wrangler deploy --assets" in out
    assert "--dry-run: Wrangler was not run." in out


def test_dry_run_still_builds(project, fake_wrangler):
    assert main(["deploy", "--dry-run"]) == 0
    assert (project / "ARK" / "index.html").is_file()


def test_dry_run_still_requires_wrangler(project, bin_dir, capsys):
    # A dry run that succeeds should mean a real run gets as far as
    # invoking Wrangler, so a missing Wrangler fails it the same way.
    assert main(["deploy", "--dry-run"]) == 1
    assert "Wrangler" in capsys.readouterr().err


# --- --skip-build ---------------------------------------------------


def test_skip_build_deploys_the_existing_directory_without_rebuilding(project, fake_wrangler):
    out = project / "ARK"
    out.mkdir()
    marker = out / "index.html"
    marker.write_text("<p>hand-made</p>")

    assert main(["deploy", "--skip-build"]) == 0

    assert marker.read_text() == "<p>hand-made</p>"  # not overwritten by a build
    assert not (out / "styles.css").exists()
    assert len(fake_wrangler()) == 1


def test_skip_build_with_no_build_directory_fails_before_wrangler(project, fake_wrangler, capsys):
    code = main(["deploy", "--skip-build"])
    assert code == 1
    assert fake_wrangler() == []
    assert "Build directory not found" in capsys.readouterr().err


def test_skip_build_does_not_need_the_site_file(project, fake_wrangler):
    (project / "site.py").unlink()
    (project / "ARK").mkdir()
    (project / "ARK" / "index.html").write_text("x")
    assert main(["deploy", "--skip-build"]) == 0


def test_skip_build_without_wrangler_omits_the_built_but_not_deployed_note(
    project, bin_dir, capsys
):
    (project / "ARK").mkdir()
    (project / "ARK" / "index.html").write_text("x")
    assert main(["deploy", "--skip-build"]) == 1
    err = capsys.readouterr().err
    assert "Wrangler" in err
    assert "The site was built" not in err


# --- argument handling ---------------------------------------------


def test_unknown_provider_is_rejected_by_argparse(project, fake_wrangler, capsys):
    with pytest.raises(SystemExit) as excinfo:
        main(["deploy", "netlify"])
    assert excinfo.value.code == 2
    assert "cloudflare" in capsys.readouterr().err
    assert fake_wrangler() == []


def test_a_site_file_needs_the_provider_named_first(project, fake_wrangler, capsys):
    # `arklight deploy site.py` is refused rather than guessed at; the
    # error names the one valid provider so the fix is obvious.
    with pytest.raises(SystemExit) as excinfo:
        main(["deploy", "site.py"])
    assert excinfo.value.code == 2
    assert "invalid choice" in capsys.readouterr().err
    assert fake_wrangler() == []


def test_deploy_is_listed_in_the_top_level_help(capsys):
    with pytest.raises(SystemExit):
        main(["--help"])
    assert "deploy" in capsys.readouterr().out


def test_deploy_help_names_the_boundary(capsys):
    with pytest.raises(SystemExit):
        main(["deploy", "--help"])
    out = capsys.readouterr().out
    assert "Wrangler" in out
    assert "--dry-run" in out
    assert "--skip-build" in out
    assert "cloudflare" in out


def test_deploy_module_never_imports_a_network_or_credential_library():
    # The provider boundary (DEPLOYMENT-CLI.md): no HTTP, no token
    # handling in ARKlight. A structural guard, not a behavioral one.
    source = Path(deploy.__file__).read_text()
    for forbidden in ("urllib", "http.client", "requests", "socket", "os.environ", "getpass"):
        assert forbidden not in source, forbidden
