import sys
import types

import pytest

from arklight.parser.loader import SiteLoadError, load_site
from arklight.parser.preamble import (
    PreambleCollisionError,
    PreambleError,
    resolve_preamble,
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


def test_define_disambiguates_a_collision(monkeypatch):
    fake_a = types.ModuleType("fake_acc_define_a")
    marker_a = object()
    fake_a.Button = marker_a
    fake_a.__all__ = ["Button"]
    fake_b = types.ModuleType("fake_acc_define_b")
    fake_b.Button = object()
    fake_b.__all__ = ["Button"]
    monkeypatch.setitem(sys.modules, "fake_acc_define_a", fake_a)
    monkeypatch.setitem(sys.modules, "fake_acc_define_b", fake_b)

    bindings = resolve_preamble(
        "# include <acc.fake_acc_define_a>\n"
        "# include <acc.fake_acc_define_b>\n"
        "# define Button -> acc.fake_acc_define_a.Button\n"
    )
    assert bindings["Button"] is marker_a


def test_define_bare_target_must_be_unambiguous():
    with pytest.raises(PreambleError, match="nothing included"):
        resolve_preamble("# define Alias -> Nonexistent\n")


def test_define_dotted_target_unknown_label_raises():
    with pytest.raises(PreambleError, match="no `# include"):
        resolve_preamble(
            "# include <stdlib.ARKlight>\n# define X -> acc.never_included.Foo\n"
        )


def test_define_dotted_target_unknown_name_raises():
    with pytest.raises(PreambleError, match="has no"):
        resolve_preamble(
            "# include <stdlib.ARKlight>\n"
            "# define X -> stdlib.ARKlight.NotARealName\n"
        )


def test_define_alias_from_stdlib_include():
    bindings = resolve_preamble(
        "# include <stdlib.ARKlight>\n# define Btn -> Button\n"
    )
    import arklight

    assert bindings["Btn"] is arklight.Button
    assert bindings["Button"] is arklight.Button


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
