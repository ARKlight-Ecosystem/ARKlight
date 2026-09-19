import sys
import types

import pytest

from arklight.ir.components import COMPONENT_REGISTRY
from arklight.parser.loader import SiteLoadError, load_site
from arklight.parser.preamble import (
    PreambleCollisionError,
    PreambleError,
    find_retired_star_imports,
    normalize_preamble,
    parse_preamble,
    resolve_preamble,
    validate_preamble,
)


def write_site(tmp_path, source: str):
    path = tmp_path / "site.py"
    path.write_text(source)
    return path


# ---------------------------------------------------------------------------
# resolve_preamble -- stdlib include
# ---------------------------------------------------------------------------


def test_no_directives_resolves_empty():
    assert resolve_preamble("from arklight import *\nsite = 1\n") == {}


def test_stdlib_include_resolves_arklight_vocabulary():
    bindings = resolve_preamble("# include <stdlib.ARKlight>\n")
    import arklight

    assert bindings["Button"] is arklight.Button
    assert bindings["Page"] is arklight.Page
    assert set(arklight.__all__).issubset(bindings.keys())


def test_include_directive_can_be_preceded_by_ordinary_comments():
    source = "#!/usr/bin/env python\n# a normal remark\n# include <stdlib.ARKlight>\n"
    bindings = resolve_preamble(source)
    assert "Button" in bindings


def test_directives_after_first_statement_are_ignored():
    source = "site = 1\n# include <stdlib.ARKlight>\n"
    assert resolve_preamble(source) == {}


# ---------------------------------------------------------------------------
# malformed / unresolvable directives
# ---------------------------------------------------------------------------


def test_unknown_include_label_raises():
    with pytest.raises(PreambleError, match="unrecognized"):
        resolve_preamble("# include <nonsense>\n")


def test_acc_include_missing_module_raises():
    with pytest.raises(PreambleError, match="could not import"):
        resolve_preamble("# include <acc.this_module_does_not_exist_xyz>\n")


def test_acc_include_requires_dunder_all(monkeypatch):
    fake = types.ModuleType("fake_acc_no_all")
    fake.Widget = object()
    monkeypatch.setitem(sys.modules, "fake_acc_no_all", fake)
    with pytest.raises(PreambleError, match="__all__"):
        resolve_preamble("# include <acc.fake_acc_no_all>\n")


def test_acc_include_with_dunder_all_resolves(monkeypatch):
    fake = types.ModuleType("fake_acc_with_all")
    marker = object()
    fake.Widget = marker
    fake._private = "hidden"
    fake.__all__ = ["Widget"]
    monkeypatch.setitem(sys.modules, "fake_acc_with_all", fake)

    bindings = resolve_preamble("# include <acc.fake_acc_with_all>\n")

    assert bindings == {"Widget": marker}


# ---------------------------------------------------------------------------
# collisions -- the actual "last import wins" bug this module fixes
# ---------------------------------------------------------------------------


def test_two_includes_agreeing_on_a_name_do_not_collide(monkeypatch):
    shared = object()
    fake_a = types.ModuleType("fake_acc_a")
    fake_a.Thing = shared
    fake_a.__all__ = ["Thing"]
    fake_b = types.ModuleType("fake_acc_b")
    fake_b.Thing = shared  # same object -- not a real disagreement
    fake_b.__all__ = ["Thing"]
    monkeypatch.setitem(sys.modules, "fake_acc_a", fake_a)
    monkeypatch.setitem(sys.modules, "fake_acc_b", fake_b)

    bindings = resolve_preamble(
        "# include <acc.fake_acc_a>\n# include <acc.fake_acc_b>\n"
    )
    assert bindings["Thing"] is shared


def test_two_includes_disagreeing_on_a_name_raises_collision(monkeypatch):
    fake_a = types.ModuleType("fake_acc_collide_a")
    fake_a.Button = object()
    fake_a.__all__ = ["Button"]
    fake_b = types.ModuleType("fake_acc_collide_b")
    fake_b.Button = object()  # a *different* object, same name
    fake_b.__all__ = ["Button"]
    monkeypatch.setitem(sys.modules, "fake_acc_collide_a", fake_a)
    monkeypatch.setitem(sys.modules, "fake_acc_collide_b", fake_b)

    with pytest.raises(PreambleCollisionError, match="Button"):
        resolve_preamble(
            "# include <acc.fake_acc_collide_a>\n"
            "# include <acc.fake_acc_collide_b>\n"
        )


# ---------------------------------------------------------------------------
# integration through load_site
# ---------------------------------------------------------------------------


def test_load_site_binds_stdlib_include_without_star_import(tmp_path):
    path = write_site(
        tmp_path,
        """
# include <stdlib.ARKlight>
site = Site()

@site.page("/")
def home():
    return Page(Heading("Hi"))
""",
    )
    site, _discovered = load_site(path)
    assert "/" in site.routes


def test_load_site_wraps_preamble_collision_as_site_load_error(tmp_path, monkeypatch):
    fake_a = types.ModuleType("fake_acc_loader_a")
    fake_a.Button = object()
    fake_a.__all__ = ["Button"]
    fake_b = types.ModuleType("fake_acc_loader_b")
    fake_b.Button = object()
    fake_b.__all__ = ["Button"]
    monkeypatch.setitem(sys.modules, "fake_acc_loader_a", fake_a)
    monkeypatch.setitem(sys.modules, "fake_acc_loader_b", fake_b)

    path = write_site(
        tmp_path,
        """
# include <acc.fake_acc_loader_a>
# include <acc.fake_acc_loader_b>
site = Site()

@site.page("/")
def home():
    return None
""",
    )
    with pytest.raises(SiteLoadError, match="bound by more than one"):
        load_site(path)


def test_load_site_still_supports_raw_star_import(tmp_path):
    """Purely additive: a site that never uses `# include`/`# define`
    keeps working exactly as before."""
    path = write_site(
        tmp_path,
        """
from arklight import *
site = Site()

@site.page("/")
def home():
    return Page(Heading("Hi"))
""",
    )
    site, _discovered = load_site(path)
    assert "/" in site.routes


# ---------------------------------------------------------------------------
# what counts as the preamble
# ---------------------------------------------------------------------------


def test_directive_shaped_comments_in_between_or_at_end_are_not_preamble():
    """Only recognised comments *above the file's contents* are
    preamble. The same comment between statements, or at the end of
    the file, is an ordinary comment to ARKlight."""
    source = (
        "# include <stdlib.ARKlight>\n"
        "x = 1\n"
        "# include <acc.does_not_exist_anywhere>\n"  # in between
        "y = 2\n"
        "# define Btn -> Button\n"  # at the end
    )
    assert parse_preamble(source) == parse_preamble("# include <stdlib.ARKlight>\n")
    bindings = resolve_preamble(source)  # would raise if the ones below counted
    assert "Btn" not in bindings


def test_a_module_docstring_ends_the_preamble():
    source = '"""Docs."""\n# include <stdlib.ARKlight>\n'
    assert parse_preamble(source) == []


# ---------------------------------------------------------------------------
# normalization handles `# define`; validation is what raises
# ---------------------------------------------------------------------------


def test_normalization_records_a_failed_include_instead_of_raising():
    normalized = normalize_preamble(parse_preamble("# include <nonsense>\n"))
    assert len(normalized.problems) == 1
    with pytest.raises(PreambleError, match="unrecognized"):
        validate_preamble(normalized)


# ---------------------------------------------------------------------------
# names the site file itself rebinds after the preamble bound them
# ---------------------------------------------------------------------------

_SITE_TAIL = """
site = Site()

@site.page("/")
def home():
    return Page(Heading("Hi"))
"""


@pytest.fixture
def clean_component_registry():
    saved = dict(COMPONENT_REGISTRY)
    yield
    COMPONENT_REGISTRY.clear()
    COMPONENT_REGISTRY.update(saved)


def test_own_function_shadowing_included_vocabulary_is_rejected(tmp_path):
    path = write_site(
        tmp_path,
        "# include <stdlib.ARKlight>\n\ndef Button(label):\n    return label\n" + _SITE_TAIL,
    )
    with pytest.raises(SiteLoadError) as excinfo:
        load_site(path)
    message = str(excinfo.value)
    assert "`Button`" in message
    assert "stdlib.ARKlight" in message
    assert "line 3: function definition" in message


def test_own_assignment_shadowing_included_vocabulary_is_rejected(tmp_path):
    path = write_site(tmp_path, "# include <stdlib.ARKlight>\nText = 5\n" + _SITE_TAIL)
    with pytest.raises(SiteLoadError, match="line 2: assignment"):
        load_site(path)


def test_import_of_a_different_object_shadowing_vocabulary_is_rejected(tmp_path, monkeypatch):
    fake = types.ModuleType("fake_shadow_import")
    fake.Button = object()
    monkeypatch.setitem(sys.modules, "fake_shadow_import", fake)
    path = write_site(
        tmp_path,
        "# include <stdlib.ARKlight>\nfrom fake_shadow_import import Button\n" + _SITE_TAIL,
    )
    with pytest.raises(SiteLoadError, match="line 2: import"):
        load_site(path)


def test_leftover_star_import_shadowing_vocabulary_is_rejected(tmp_path, monkeypatch):
    fake = types.ModuleType("fake_shadow_star")
    fake.Button = object()
    fake.__all__ = ["Button"]
    monkeypatch.setitem(sys.modules, "fake_shadow_star", fake)
    path = write_site(
        tmp_path,
        "# include <stdlib.ARKlight>\nfrom fake_shadow_star import *\n" + _SITE_TAIL,
    )
    with pytest.raises(SiteLoadError, match="from fake_shadow_star import"):
        load_site(path)


def test_importing_the_same_object_again_is_not_shadowing(tmp_path):
    path = write_site(
        tmp_path,
        "# include <stdlib.ARKlight>\nfrom arklight import Button\n" + _SITE_TAIL,
    )
    site, _ = load_site(path)
    assert "/" in site.routes


def test_names_that_dont_collide_with_vocabulary_are_untouched(tmp_path):
    path = write_site(
        tmp_path,
        "# include <stdlib.ARKlight>\n\ndef my_helper():\n    return 1\n\nTAGLINE = 'x'\n"
        + _SITE_TAIL,
    )
    site, _ = load_site(path)
    assert "/" in site.routes


def test_component_with_allow_redefine_is_a_deliberate_override(tmp_path, clean_component_registry):
    path = write_site(
        tmp_path,
        "# include <stdlib.ARKlight>\n\n"
        "@component(allow_redefine=True)\ndef Container():\n    return Text('x')\n" + _SITE_TAIL,
    )
    site, _ = load_site(path)
    assert "/" in site.routes


def test_component_without_allow_redefine_cannot_take_a_builtin_name(tmp_path, clean_component_registry):
    path = write_site(
        tmp_path,
        "# include <stdlib.ARKlight>\n\n@component()\ndef Container():\n    return Text('x')\n"
        + _SITE_TAIL,
    )
    with pytest.raises(SiteLoadError, match="would shadow the built-in"):
        load_site(path)


def test_sites_without_a_preamble_get_no_shadowing_check(tmp_path):
    """Nothing was bound by a preamble, so there is nothing to shadow --
    unchanged behavior for a site that never adopts `# include`."""
    path = write_site(
        tmp_path,
        "from arklight import *\n\ndef Container():\n    return 1\n" + _SITE_TAIL,
    )
    site, _ = load_site(path)
    assert "/" in site.routes


# ---------------------------------------------------------------------------
# retired: `from arklight import *`
# ---------------------------------------------------------------------------


def test_find_retired_star_imports_reports_line_numbers():
    source = "x = 1\nfrom arklight import *\n"
    assert find_retired_star_imports(source) == [2]


def test_find_retired_star_imports_ignores_everything_else():
    source = (
        "import arklight\n"
        "from arklight import Button\n"
        "from arklight.api import *\n"
        "from other_pkg import *\n"
    )
    assert find_retired_star_imports(source) == []


def test_load_site_reports_star_import_through_on_notice_and_still_loads(tmp_path):
    path = write_site(tmp_path, "from arklight import *\n" + _SITE_TAIL)
    notices: list[str] = []
    site, _ = load_site(path, on_notice=notices.append)
    assert "/" in site.routes  # still works
    assert len(notices) == 1
    assert f"{path}:1" in notices[0]
    assert "# include <stdlib.ARKlight>" in notices[0]
    assert "retired" in notices[0]


def test_preamble_site_produces_no_notice(tmp_path):
    path = write_site(tmp_path, "# include <stdlib.ARKlight>\n" + _SITE_TAIL)
    notices: list[str] = []
    load_site(path, on_notice=notices.append)
    assert notices == []


def test_load_site_without_on_notice_stays_silent_about_star_import(tmp_path, capsys):
    path = write_site(tmp_path, "from arklight import *\n" + _SITE_TAIL)
    load_site(path)
    captured = capsys.readouterr()
    assert captured.out == "" and captured.err == ""


def test_star_import_notice_reaches_the_build_log(tmp_path):
    from arklight.compiler.pipeline import compile_site_file

    path = write_site(tmp_path, "from arklight import *\n" + _SITE_TAIL)
    messages: list[str] = []
    compile_site_file(path, on_stage=messages.append)
    assert any("`from arklight import *` is retired" in m for m in messages)


def test_star_import_notice_prints_without_verbose(capsys):
    """The CLI shows any message starting with the warning glyph
    regardless of --verbose; the notice must qualify."""
    from arklight.cli.main import _stage_logger
    from arklight.parser.preamble import retired_star_import_notice

    _stage_logger(retired_star_import_notice("site.py", 1), verbose=False)
    assert "retired" in capsys.readouterr().out
