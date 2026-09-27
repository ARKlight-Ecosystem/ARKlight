"""
Tests for `Provider`, stages 1-3 of 6 (`v0.065`-`v0.067`, see
`arklight/provider.py` and `docs/version history/v0.065.md`): the
contract itself -- `Provider.declare(name=..., capabilities=[...])`,
validated against a closed vocabulary, attached with
`Site(provider=...)`, and gated as the `provider-integration`
experimental feature -- plus (stage 3) the read-only
`window.ARKLIGHT_PROVIDER` config object in `arklight.js`.
"""

from __future__ import annotations

import dataclasses
import os

import pytest

import arklight
from arklight import Page, Heading, Provider, Site, experimental
from arklight.compiler.pipeline import build, compile_site_file
from arklight.ir.validate import ValidationError, validate_page, validate_provider
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
# `Provider` stage 2 of 6 (v0.066): IR threading + `ir/validate.py`
# ---------------------------------------------------------------------------


def test_validate_provider_is_a_no_op_for_none():
    validate_provider(None)  # must not raise


def test_validate_provider_is_a_no_op_for_a_valid_declaration():
    validate_provider(_declare(capabilities=["auth", "write"]))  # must not raise


def test_validate_provider_catches_a_declaration_built_around_its_own_post_init():
    # `Provider.declare(...)`/`ProviderDeclaration(...)` can never hold an
    # invalid value (see the "hand-built declaration" tests above) -- the
    # only way to reach this path is going around the frozen dataclass's
    # own `__post_init__`, e.g. via `object.__setattr__`. `validate_provider`
    # is the pipeline's defense-in-depth check for exactly that case.
    decl = _declare()
    object.__setattr__(decl, "capabilities", ("nope", "also-nope"))
    with pytest.raises(ValidationError, match=r"unknown capabilities \['also-nope', 'nope'\]"):
        validate_provider(decl)


def test_validate_provider_names_a_single_unknown_capability_in_the_singular():
    decl = _declare()
    object.__setattr__(decl, "capabilities", ("auth", "nope"))
    with pytest.raises(ValidationError, match=r"unknown capability \['nope'\]"):
        validate_provider(decl)


def test_validate_provider_raises_the_shared_validation_error_not_value_error():
    decl = _declare()
    object.__setattr__(decl, "capabilities", ("nope",))
    with pytest.raises(ValidationError):
        validate_provider(decl)
    # And, being the shared type every other schema check in this module
    # raises, it is not left with a `component_name` -- that field is
    # reserved for SCHEMA-lookup sites (unknown component type / missing
    # required prop), which this isn't.
    try:
        validate_provider(decl)
    except ValidationError as exc:
        assert exc.component_name is None


def test_ir_threads_the_declaration_itself_not_just_the_usage(tmp_path):
    site_file = tmp_path / "site.py"
    site_file.write_text(_SITE_WITH)
    ir = compile_site_file(site_file)
    assert ir.provider == ProviderDeclaration(name="firebase", capabilities=("auth", "read"))


def test_ir_provider_is_none_when_the_site_declares_none(tmp_path):
    site_file = tmp_path / "site.py"
    site_file.write_text(_SITE_WITHOUT)
    ir = compile_site_file(site_file)
    assert ir.provider is None


def test_website_ir_defaults_provider_to_none():
    from arklight.ir.build import WebsiteIR

    assert WebsiteIR(site_name="Test").provider is None


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


def test_a_declared_provider_changes_only_arklight_js_and_sbom(tmp_path):
    # The pages and stylesheet are byte-identical with and without a
    # Provider. The only two files that change are arklight.js (the
    # devtools console reminder and, from stage 3, the config object)
    # and sbom.txt (the experimental-feature entry).
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


# ---------------------------------------------------------------------------
# Stage 3 of 6 (`v0.067`): the config object in arklight.js
# ---------------------------------------------------------------------------

import json
import shutil
import subprocess

from arklight.backend.js.render import JSBackend, _provider_config_js

_PAGE_SITE = (
    "from arklight import *\n"
    "site = Site(name='T'{extra})\n"
    "@site.page('/')\n"
    "def home():\n"
    "    return Page(Heading('Hi'))\n"
)


def _js(tmp_path, provider_src: str | None = None, name: str = "site") -> str:
    extra = f", provider={provider_src}" if provider_src else ""
    site_file = tmp_path / f"{name}.py"
    site_file.write_text(_PAGE_SITE.format(extra=extra))
    return JSBackend().render(compile_site_file(site_file))["arklight.js"]


_DECL = "Provider.declare(name='firebase', capabilities=['auth', 'read'])"


def test_no_provider_ships_no_config_object(tmp_path):
    assert "ARKLIGHT_PROVIDER" not in _js(tmp_path)


def test_provider_config_helper_returns_nothing_for_none():
    assert _provider_config_js(None) == ""


def test_a_declared_provider_ships_its_name_and_capabilities_in_order(tmp_path):
    js = _js(tmp_path, _DECL)
    assert "window.ARKLIGHT_PROVIDER = Object.freeze({" in js
    assert 'name: "firebase"' in js
    assert 'capabilities: Object.freeze(["auth", "read"])' in js


def test_the_config_object_ships_even_when_the_devtools_reminder_is_off(tmp_path):
    (tmp_path / "site.py").write_text(_PAGE_SITE.format(extra=f", provider={_DECL}"))
    ir = compile_site_file(tmp_path / "site.py")
    ir.devtools_console_reminder = False
    js = JSBackend().render(ir)["arklight.js"]
    assert "ARKLIGHT_PROVIDER" in js
    assert "provider-integration" not in js  # the reminder really is off


def test_the_config_block_contains_nothing_that_touches_the_network_or_loads_code():
    block = _provider_config_js(_declare())
    for token in ("fetch", "XMLHttpRequest", "WebSocket", "import", "eval", "Function(", "src"):
        assert token not in block


def test_the_config_object_carries_only_name_and_capabilities():
    block = _provider_config_js(_declare())
    assert block.count(":") == 2  # `name:` and `capabilities:` -- no hooks, no state keys


def test_pages_and_stylesheet_still_never_mention_the_provider(tmp_path):
    (tmp_path / "with.py").write_text(_SITE_WITH)
    build(tmp_path / "with.py", tmp_path / "out")
    for name, data in _files(tmp_path / "out").items():
        if name.endswith((".html", ".css")):
            assert b"ARKLIGHT_PROVIDER" not in data and b"firebase" not in data


def _run_in_node(js_path) -> dict:
    """Run the generated script against a stub DOM and report what it
    left in `window.ARKLIGHT_PROVIDER`, after attempting to mutate it."""
    script = """
    global.window = global;
    global.document = { addEventListener() {}, body: { addEventListener() {} },
                        querySelectorAll() { return []; } };
    require("vm").runInThisContext(require("fs").readFileSync(process.argv[1], "utf8"));
    var p = window.ARKLIGHT_PROVIDER;
    var frozen = Object.isFrozen(p) && Object.isFrozen(p.capabilities);
    try { p.name = "changed"; } catch (e) {}
    try { p.capabilities.push("write"); } catch (e) {}
    process.stdout.write("\\n@@" + JSON.stringify({ value: p, frozen: frozen }) + "\\n");
    """
    result = subprocess.run(
        [shutil.which("node"), "-e", script, str(js_path)],
        capture_output=True, text=True, check=True,
    )
    line = next(l for l in result.stdout.split("\n") if l.startswith("@@"))
    return json.loads(line[2:])


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_node_can_read_the_config_object_and_it_is_frozen(tmp_path):
    js = _js(tmp_path, _DECL)
    path = tmp_path / "arklight.js"
    path.write_text(js)
    out = _run_in_node(path)
    assert out["frozen"] is True
    # The mutation attempts inside _run_in_node changed nothing.
    assert out["value"] == {"name": "firebase", "capabilities": ["auth", "read"]}


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
@pytest.mark.parametrize(
    "label",
    ['fire"base', "back\\slash", "</script>", "line\u2028sep", "caf\u00e9 \U0001f525", "it's"],
)
def test_node_round_trips_awkward_provider_names_exactly(tmp_path, label):
    decl = ProviderDeclaration(name=label, capabilities=("auth",))
    path = tmp_path / "arklight.js"
    path.write_text("(function () {\n" + _provider_config_js(decl) + "})();\n")
    assert _run_in_node(path)["value"]["name"] == label


def test_config_object_is_set_before_a_script_extension_appended_after_it(tmp_path):
    js = _js(tmp_path, _DECL)
    # A ScriptExtension is appended after the whole runtime, so anything
    # it reads must already exist -- i.e. sit before the closing of the IIFE.
    assert js.index("window.ARKLIGHT_PROVIDER") < js.rindex("})();")


# ---------------------------------------------------------------------------
# Stage 4 of 6 (v0.068): external script loading -- Page(scripts=[...])
# ---------------------------------------------------------------------------


def _page_with_scripts(scripts):
    return Page(Heading("Hi"), scripts=scripts)


def test_scripts_entry_requires_src():
    page = _page_with_scripts([{"defer": "true"}])
    with pytest.raises(ValidationError, match='"src"'):
        validate_page("/", page)


def test_scripts_rejects_a_javascript_url():
    page = _page_with_scripts([{"src": "javascript:alert(1)"}])
    with pytest.raises(ValidationError, match="javascript:"):
        validate_page("/", page)


def test_scripts_entry_must_be_a_non_empty_dict():
    with pytest.raises(ValidationError, match="non-empty"):
        validate_page("/", _page_with_scripts([{}]))


def test_scripts_must_be_a_non_empty_list():
    with pytest.raises(ValidationError, match="non-empty list"):
        validate_page("/", _page_with_scripts([]))


def test_scripts_attribute_values_must_be_strings():
    with pytest.raises(ValidationError, match="string value"):
        validate_page("/", _page_with_scripts([{"src": "https://example.com/sdk.js", "async": True}]))


def test_a_valid_scripts_entry_passes_validation():
    validate_page("/", _page_with_scripts([{"src": "https://example.com/sdk.js", "defer": "true"}]))


def test_provider_scripts_is_a_registered_feature():
    assert "provider-scripts" in experimental.FEATURES


def test_provider_scripts_never_trips_the_heavy_reliance_nudge():
    assert experimental.FEATURES["provider-scripts"].upstream_candidate is False


_SITE_WITH_SCRIPTS = (
    "from arklight import Site, Page, Heading\n"
    "site = Site(name='Test')\n"
    "@site.page('/')\n"
    "def home():\n"
    "    return Page(Heading('Hi'), scripts=[{'src': 'https://example.com/sdk.js'}])\n"
)


def test_a_page_with_scripts_records_provider_scripts_usage(tmp_path):
    site_file = tmp_path / "site.py"
    site_file.write_text(_SITE_WITH_SCRIPTS)
    ir = compile_site_file(site_file)
    assert [u.feature_id for u in ir.experimental_usages] == ["provider-scripts"]


def test_provider_scripts_is_gated_separately_from_provider_integration(tmp_path):
    # A Provider declaration with no Page(scripts=...) records only
    # provider-integration; a Page(scripts=...) with no declared
    # Provider records only provider-scripts. The two are independent
    # gates, per PROVIDER-SDK-ADDENDUM.md's stage 4 note.
    site_file = tmp_path / "site.py"
    site_file.write_text(_SITE_WITH)
    ir = compile_site_file(site_file)
    assert "provider-scripts" not in [u.feature_id for u in ir.experimental_usages]


def test_build_renders_the_script_tag_in_the_page(tmp_path):
    site_file = tmp_path / "site.py"
    site_file.write_text(_SITE_WITH_SCRIPTS)
    build(site_file, tmp_path / "ARK")
    html = (tmp_path / "ARK" / "index.html").read_text()
    assert '<script src="https://example.com/sdk.js"></script>' in html


def test_a_build_with_scripts_prints_the_provider_scripts_banner(tmp_path):
    site_file = tmp_path / "site.py"
    site_file.write_text(_SITE_WITH_SCRIPTS)
    messages: list[str] = []
    build(site_file, tmp_path / "ARK", on_stage=messages.append)
    banners = [m for m in messages if m.startswith("\u26a0")]
    assert len(banners) == 1
    assert "provider-scripts" in banners[0]
