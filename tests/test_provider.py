"""
Tests for `Provider`, stage 1 of 6 (`v0.065`, see `arklight/provider.py`
and `docs/version history/v0.065.md`): the contract itself --
`Provider.declare(name=..., capabilities=[...])`, validated against a
closed vocabulary, attached with `Site(provider=...)`, and gated as the
`provider-integration` experimental feature.
"""

from __future__ import annotations

import dataclasses
import os

import pytest

import arklight
from arklight import Page, Heading, Provider, Site, experimental
from arklight.compiler.pipeline import build, compile_site_file
from arklight.provider import PROVIDER_CAPABILITIES, ProviderDeclaration


def _declare(**overrides):
    kwargs = {"name": "firebase", "capabilities": ["auth", "read"]}
    kwargs.update(overrides)
    return Provider.declare(**kwargs)


# ---------------------------------------------------------------------------
# The contract: Provider.declare / ProviderDeclaration
# ---------------------------------------------------------------------------


def test_declare_returns_a_declaration_with_capabilities_as_a_tuple_in_order():
    decl = _declare(capabilities=["write", "auth", "read"])
    assert decl == ProviderDeclaration(name="firebase", capabilities=("write", "auth", "read"))
    assert isinstance(decl.capabilities, tuple)


def test_declare_accepts_a_tuple_of_capabilities():
    assert _declare(capabilities=("auth",)).capabilities == ("auth",)


def test_the_provisional_vocabulary_is_the_four_the_proposal_names():
    assert PROVIDER_CAPABILITIES == ("auth", "read", "write", "subscribe")


def test_every_vocabulary_name_is_accepted():
    assert _declare(capabilities=list(PROVIDER_CAPABILITIES)).capabilities == PROVIDER_CAPABILITIES


def test_declare_is_keyword_only():
    with pytest.raises(TypeError):
        Provider.declare("firebase", ["auth"])  # type: ignore[misc]


def test_name_is_a_free_label_not_a_fixed_list_of_vendors():
    for label in ("firebase", "my-flask-api", "local store", "x"):
        assert _declare(name=label).name == label


@pytest.mark.parametrize("bad_name", ["", "   ", "\t\n", None, 5, ["firebase"]])
def test_name_must_be_a_non_empty_string(bad_name):
    with pytest.raises(ValueError, match=r"Provider\.declare\(name=\.\.\.\) needs a non-empty string"):
        _declare(name=bad_name)


def test_a_bare_string_is_not_read_as_a_list_of_one_letter_capabilities():
    with pytest.raises(ValueError, match=r"needs a list of capability names"):
        _declare(capabilities="auth")


@pytest.mark.parametrize("bad", [None, {"auth"}, {"auth": 1}, 5])
def test_capabilities_must_be_a_list_or_tuple(bad):
    with pytest.raises(ValueError, match=r"needs a list of capability names"):
        _declare(capabilities=bad)


@pytest.mark.parametrize("empty", [[], ()])
def test_capabilities_must_not_be_empty(empty):
    with pytest.raises(ValueError, match=r"at least one capability"):
        _declare(capabilities=empty)


def test_capability_entries_must_be_strings():
    with pytest.raises(ValueError, match=r"entries must be strings, got \[3\]"):
        _declare(capabilities=["auth", 3])


def test_an_unknown_capability_fails_and_names_the_known_ones():
    with pytest.raises(ValueError) as info:
        _declare(capabilities=["auth", "raed"])
    message = str(info.value)
    assert "unknown capability ['raed']" in message
    for known in PROVIDER_CAPABILITIES:
        assert known in message


def test_every_unknown_capability_is_reported_at_once():
    with pytest.raises(ValueError, match=r"unknown capabilities \['x', 'y'\]"):
        _declare(capabilities=["x", "auth", "y"])


def test_the_vocabulary_is_case_sensitive():
    with pytest.raises(ValueError, match=r"unknown capability \['Auth'\]"):
        _declare(capabilities=["Auth"])


def test_a_repeated_capability_fails():
    with pytest.raises(ValueError, match=r"lists \['read'\] more than once"):
        _declare(capabilities=["read", "auth", "read"])


def test_a_hand_built_declaration_is_validated_too():
    # Validation lives on the dataclass, not only on `Provider.declare`,
    # so there is no way to hold an invalid declaration.
    with pytest.raises(ValueError, match="unknown capability"):
        ProviderDeclaration(name="x", capabilities=("nope",))
    with pytest.raises(ValueError, match="non-empty string"):
        ProviderDeclaration(name="", capabilities=("auth",))


def test_a_hand_built_declaration_normalizes_a_list_to_a_tuple():
    assert ProviderDeclaration(name="x", capabilities=["auth"]).capabilities == ("auth",)


def test_a_declaration_is_immutable_and_hashable():
    decl = _declare()
    with pytest.raises(dataclasses.FrozenInstanceError):
        decl.name = "other"  # type: ignore[misc]
    assert hash(decl) == hash(_declare())
    assert len({decl, _declare()}) == 1


def test_the_callers_list_is_not_kept_by_reference():
    caps = ["auth", "read"]
    decl = _declare(capabilities=caps)
    caps.append("write")
    assert decl.capabilities == ("auth", "read")


# ---------------------------------------------------------------------------
# Site(provider=...)
# ---------------------------------------------------------------------------


def test_a_site_without_a_provider_records_nothing():
    site = Site()
    assert site.provider is None
    assert site.experimental_usages == []


def test_a_site_stores_the_declaration_and_records_one_experimental_usage():
    decl = _declare()
    site = Site(provider=decl)
    assert site.provider is decl
    assert [u.feature_id for u in site.experimental_usages] == ["provider-integration"]


@pytest.mark.parametrize("bad", ["firebase", {"name": "x", "capabilities": ["auth"]}, ("x", ("auth",)), 5])
def test_site_provider_must_be_a_declaration(bad):
    with pytest.raises(ValueError, match=r"Site\(provider=\.\.\.\) needs the value Provider\.declare"):
        Site(provider=bad)


def test_an_invalid_declaration_never_reaches_the_site():
    with pytest.raises(ValueError):
        Site(provider=_declare(capabilities=["nope"]))


# ---------------------------------------------------------------------------
# Experimental gating
# ---------------------------------------------------------------------------


def test_provider_integration_is_a_registered_feature():
    feature = experimental.FEATURES["provider-integration"]
    assert feature.id == "provider-integration"
    assert "does not implement, audit, or guarantee" in feature.inline_note
    assert feature.detail_lines and feature.legacy_note


def test_the_summary_block_disclaims_responsibility_for_the_external_service():
    block = experimental.format_summary_block("provider-integration")
    assert "Feature : provider-integration" in block
    assert "does not implement, audit, or guarantee" in block
    assert "entirely the responsibility of whatever concrete implementation" in block


def test_the_inline_banner_names_the_feature():
    banner = experimental.format_inline_banner(experimental.emit("provider-integration"))
    assert "[EXPERIMENTAL FEATURE ACTIVE]" in banner
    assert "provider-integration" in banner


def test_provider_integration_never_trips_the_heavy_reliance_nudge():
    # A Provider is a deliberate boundary, not a missing feature -- "open
    # a pull request for your missing feature" would be the wrong advice.
    assert experimental.FEATURES["provider-integration"].upstream_candidate is False
    usages = [experimental.emit("provider-integration") for _ in range(10)]
    assert experimental.heavy_reliance_nudge(usages) is None


# ---------------------------------------------------------------------------
# Through the real pipeline
# ---------------------------------------------------------------------------

_SITE_WITH = (
    "from arklight import Site, Page, Heading, Provider\n"
    "site = Site(name='Test', provider=Provider.declare(name='firebase', capabilities=['auth', 'read']))\n"
    "@site.page('/')\n"
    "def home():\n"
    "    return Page(Heading('Hi'))\n"
)
_SITE_WITHOUT = (
    "from arklight import Site, Page, Heading\n"
    "site = Site(name='Test')\n"
    "@site.page('/')\n"
    "def home():\n"
    "    return Page(Heading('Hi'))\n"
)


def _files(root):
    return {
        os.path.relpath(os.path.join(d, f), root): open(os.path.join(d, f), "rb").read()
        for d, _, names in os.walk(root)
        for f in names
    }


def test_compile_threads_the_usage_into_the_ir(tmp_path):
    site_file = tmp_path / "site.py"
    site_file.write_text(_SITE_WITH)
    ir = compile_site_file(site_file)
    assert [u.feature_id for u in ir.experimental_usages] == ["provider-integration"]


def test_a_build_prints_exactly_one_inline_banner(tmp_path):
    site_file = tmp_path / "site.py"
    site_file.write_text(_SITE_WITH)
    messages: list[str] = []
    build(site_file, tmp_path / "ARK", on_stage=messages.append)
    banners = [m for m in messages if m.startswith("\u26a0")]
    assert len(banners) == 1
    assert "provider-integration" in banners[0]


def test_a_site_file_can_use_the_preamble_name(tmp_path):
    site_file = tmp_path / "site.py"
    site_file.write_text(
        "# include <stdlib.ARKlight>\n"
        "site = Site(name='Test', provider=Provider.declare(name='f', capabilities=['write']))\n"
        "@site.page('/')\n"
        "def home():\n"
        "    return Page(Heading('Hi'))\n"
    )
    ir = compile_site_file(site_file)
    assert [u.feature_id for u in ir.experimental_usages] == ["provider-integration"]


def test_an_invalid_declaration_in_a_site_file_fails_the_build_with_the_message(tmp_path):
    site_file = tmp_path / "site.py"
    site_file.write_text(_SITE_WITH.replace("'read'", "'raed'"))
    with pytest.raises(Exception, match="unknown capability"):
        compile_site_file(site_file)


def test_a_declared_provider_adds_no_markup_config_or_script_of_its_own(tmp_path):
    # Stage 1 is the contract only: the pages and stylesheet are
    # byte-identical with and without a Provider. The only two files that
    # change are the reports every gated experimental feature already
    # gets -- the devtools console reminder in arklight.js and an entry
    # in sbom.txt.
    (tmp_path / "with.py").write_text(_SITE_WITH)
    (tmp_path / "without.py").write_text(_SITE_WITHOUT)
    build(tmp_path / "with.py", tmp_path / "out_with")
    build(tmp_path / "without.py", tmp_path / "out_without")
    with_files, without_files = _files(tmp_path / "out_with"), _files(tmp_path / "out_without")
    assert with_files.keys() == without_files.keys()
    changed = {name for name in with_files if with_files[name] != without_files[name]}
    assert changed == {"arklight.js", "sbom.txt"}
    assert b"provider-integration" in with_files["sbom.txt"]
    assert b"provider-integration" in with_files["arklight.js"]
    # Nothing Provider-specific -- no capability names, no vendor label --
    # leaks into any page or the stylesheet.
    for name, data in with_files.items():
        if name.endswith((".html", ".css")):
            assert b"firebase" not in data
            assert b"capabilit" not in data.lower()


# ---------------------------------------------------------------------------
# Public surface
# ---------------------------------------------------------------------------


def test_provider_is_exported_from_the_package():
    assert arklight.Provider is Provider
    assert "Provider" in arklight.__all__


def test_star_import_binds_provider():
    namespace: dict = {}
    exec("from arklight import *", namespace)  # noqa: S102 -- test-only
    assert namespace["Provider"] is Provider


def test_the_provider_module_holds_no_network_or_vendor_code():
    # "No shipped implementations" (proposal, section 2): the contract
    # module imports nothing beyond the standard library's dataclasses.
    import ast
    import inspect

    import arklight.provider as provider_module

    tree = ast.parse(inspect.getsource(provider_module))
    imported = {
        (node.module if isinstance(node, ast.ImportFrom) else alias.name)
        for node in ast.walk(tree)
        if isinstance(node, (ast.Import, ast.ImportFrom))
        for alias in (node.names if isinstance(node, ast.Import) else [None])
    }
    assert imported <= {"__future__", "dataclasses"}, imported
