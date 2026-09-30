from __future__ import annotations

import pytest

from arklight.config import ConfigError, find_config, load_config, section


def test_find_config_returns_none_when_absent(tmp_path):
    assert find_config(tmp_path) is None


def test_load_config_returns_empty_dict_when_absent(tmp_path):
    assert load_config(tmp_path) == {}


def test_load_config_reads_config_dict(tmp_path):
    (tmp_path / "arklight.config.py").write_text(
        'CONFIG = {"live_streaming": {"port": 9000}}\n', encoding="utf-8"
    )
    config = load_config(tmp_path)
    assert config == {"live_streaming": {"port": 9000}}


def test_load_config_raises_on_syntax_error(tmp_path):
    (tmp_path / "arklight.config.py").write_text("CONFIG = {\n", encoding="utf-8")
    with pytest.raises(ConfigError):
        load_config(tmp_path)


def test_load_config_raises_when_config_missing(tmp_path):
    (tmp_path / "arklight.config.py").write_text("X = 1\n", encoding="utf-8")
    with pytest.raises(ConfigError):
        load_config(tmp_path)


def test_load_config_raises_when_config_not_a_dict(tmp_path):
    (tmp_path / "arklight.config.py").write_text("CONFIG = [1, 2]\n", encoding="utf-8")
    with pytest.raises(ConfigError):
        load_config(tmp_path)


def test_section_returns_defaults_when_absent():
    assert section({}, "live_streaming", {"port": 8347}) == {"port": 8347}


def test_section_merges_project_values_over_defaults():
    config = {"live_streaming": {"port": 9000}}
    merged = section(config, "live_streaming", {"host": "127.0.0.1", "port": 8347})
    assert merged == {"host": "127.0.0.1", "port": 9000}


def test_section_raises_when_section_not_a_dict():
    with pytest.raises(ConfigError):
        section({"live_streaming": "nope"}, "live_streaming", {})


def test_section_experimental_heavy_reliance_nudge_defaults_true():
    assert section({}, "experimental", {"heavy_reliance_nudge": True}) == {
        "heavy_reliance_nudge": True
    }


def test_section_experimental_heavy_reliance_nudge_can_be_disabled():
    config = {"experimental": {"heavy_reliance_nudge": False}}
    merged = section(config, "experimental", {"heavy_reliance_nudge": True})
    assert merged == {"heavy_reliance_nudge": False}


# --- warnings for names that match nothing; live_streaming validation --------

from arklight.config import (  # noqa: E402
    _KNOWN_KEYS,
    _KNOWN_SECTIONS,
    config_warnings,
    emit_config_warnings,
    validate_live_streaming,
)


def _write_config(tmp_path, body: str) -> None:
    (tmp_path / "arklight.config.py").write_text(body, encoding="utf-8")


def test_a_correct_config_produces_no_warnings(tmp_path):
    # Note: an `"android": {...}` section is deliberately absent here,
    # since `android` is not a known config section on `main` (standing
    # Android-exclusion policy; see the sync-plan folder under `docs/`),
    # so including it would make `config_warnings` correctly flag it as unknown and
    # break this test's own "no warnings" assertion.
    _write_config(
        tmp_path,
        'CONFIG = {"live_streaming": {"port": 9001}, "csp": {"strict_csp": True}, '
        '"rei": {"default_mode": "plain"}, '
        '"overdrive": True}\n',
    )
    assert config_warnings(load_config(tmp_path), tmp_path) == []


def test_unknown_section_warns_with_a_suggestion(tmp_path):
    _write_config(tmp_path, 'CONFIG = {"live_streamin": {"port": 9001}}\n')
    (message,) = config_warnings(load_config(tmp_path), tmp_path)
    assert "unknown section 'live_streamin'" in message
    assert "Did you mean 'live_streaming'?" in message


def test_unknown_key_in_a_known_section_warns_with_a_suggestion(tmp_path):
    _write_config(tmp_path, 'CONFIG = {"live_streaming": {"prot": 9001}}\n')
    (message,) = config_warnings(load_config(tmp_path), tmp_path)
    assert "unknown key 'prot' in section 'live_streaming'" in message
    assert "Did you mean 'port'?" in message


def test_the_overdrive_top_level_flag_is_never_flagged_as_an_unknown_section(tmp_path):
    _write_config(tmp_path, 'CONFIG = {"overdrive": True}\n')
    assert config_warnings(load_config(tmp_path), tmp_path) == []


def test_unknown_names_are_still_passed_through_not_rejected(tmp_path):
    """Forward compatibility is unchanged: warn, never fail or drop."""
    _write_config(tmp_path, 'CONFIG = {"from_the_future": {"x": 1}}\n')
    config = load_config(tmp_path)
    assert config == {"from_the_future": {"x": 1}}
    assert len(config_warnings(config, tmp_path)) == 1


@pytest.mark.parametrize(
    "name", ["config.js", "config.ts", "arklight.config.json", "arklight.config.toml"]
)
def test_a_foreign_config_file_without_arklight_config_py_warns(tmp_path, name):
    (tmp_path / name).write_text("{}", encoding="utf-8")
    (message,) = config_warnings(load_config(tmp_path), tmp_path)
    assert name in message and "arklight.config.py" in message


def test_a_foreign_config_file_is_quiet_when_a_real_config_exists(tmp_path):
    _write_config(tmp_path, "CONFIG = {}\n")
    (tmp_path / "config.js").write_text("{}", encoding="utf-8")
    assert config_warnings(load_config(tmp_path), tmp_path) == []


def test_emit_config_warnings_prints_to_stderr(tmp_path, capsys):
    _write_config(tmp_path, 'CONFIG = {"nope": {}}\n')
    emit_config_warnings(load_config(tmp_path), tmp_path)
    err = capsys.readouterr().err
    assert err.startswith("ARKlight warning: arklight.config.py: unknown section 'nope'")


def test_known_key_table_matches_the_readers_own_defaults():
    """The table is hand-maintained; this stops it drifting from the
    modules that actually read each section.

    Note: the `android`/`desktop` entries (`arklight.cli.android`/`desktop`)
    are not checked. Those backends are excluded from `main` as standing policy, so
    `_KNOWN_KEYS` has no `"android"`/`"desktop"` entries to check here
    -- only the `live_streaming` assertions apply.
    """
    from arklight.cli import live_streaming

    assert _KNOWN_KEYS["live_streaming"] == {"host", "port", "poll_interval"}
    assert live_streaming._DEFAULT_PORT and live_streaming._DEFAULT_HOST
    assert set(_KNOWN_KEYS) <= _KNOWN_SECTIONS


_GOOD_LIVE = {"host": "127.0.0.1", "port": 8347, "poll_interval": 0.5}


def test_validate_live_streaming_accepts_the_defaults():
    validate_live_streaming(dict(_GOOD_LIVE))


@pytest.mark.parametrize("port", ["9001", 99999, 0, -1, True, 8347.5, None])
def test_validate_live_streaming_rejects_a_bad_port(port):
    with pytest.raises(ConfigError, match=r"\['port'\]` must be an integer from 1 to 65535"):
        validate_live_streaming({**_GOOD_LIVE, "port": port})


@pytest.mark.parametrize("host", ["", "  ", 5, None])
def test_validate_live_streaming_rejects_a_bad_host(host):
    with pytest.raises(ConfigError, match=r"\['host'\]` must be a non-empty string"):
        validate_live_streaming({**_GOOD_LIVE, "host": host})


@pytest.mark.parametrize("interval", [0, -1, "1", True, float("inf"), float("nan")])
def test_validate_live_streaming_rejects_a_bad_poll_interval(interval):
    with pytest.raises(ConfigError, match=r"\['poll_interval'\]` must be a positive number"):
        validate_live_streaming({**_GOOD_LIVE, "poll_interval": interval})


def test_live_streaming_command_reports_a_bad_port_instead_of_crashing(tmp_path, capsys):
    from arklight.cli.main import main

    (tmp_path / "site.py").write_text(
        "# include <stdlib.ARKlight>\nsite = Site()\n"
        '@site.page("/")\ndef home():\n    return Page(Heading("x"))\n'
    )
    _write_config(tmp_path, 'CONFIG = {"live_streaming": {"port": "9001"}}\n')

    code = main(["live-streaming", "--subscribe", str(tmp_path / "site.py")])

    assert code == 1
    err = capsys.readouterr().err
    assert "must be an integer from 1 to 65535" in err
    assert "unexpected error" not in err
