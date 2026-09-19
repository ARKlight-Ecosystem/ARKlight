"""Every Python file ARKlight takes in gets its preamble read -- not
just the site file -- and `# include <stdlib.ARKlight>` gives the whole
public API."""

import inspect
import sys

import pytest

import arklight
import arklight.api as api
from arklight.config import ConfigError, load_config
from arklight.parser.loader import SiteLoadError, load_site


def _project(tmp_path, files: dict[str, str]):
    for name, body in files.items():
        target = tmp_path / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(body)
    return tmp_path / "site.py"


_SITE = """\
# include <stdlib.ARKlight>

from pages.home import home as home_page

site = Site()


@site.page("/")
def home():
    return home_page()
"""


# ---------------------------------------------------------------------------
# Project modules
# ---------------------------------------------------------------------------


def test_a_project_module_can_use_the_preamble(tmp_path):
    site_path = _project(
        tmp_path,
        {
            "site.py": _SITE,
            "pages/__init__.py": "",
            "pages/home.py": "# include <stdlib.ARKlight>\n\ndef home():\n    return Page(Heading('Hi'))\n",
        },
    )
    site, _ = load_site(site_path)
    assert site.routes["/"]().type == "Page"


def test_a_project_module_can_use_define(tmp_path):
    site_path = _project(
        tmp_path,
        {
            "site.py": _SITE,
            "pages/__init__.py": "",
            "pages/home.py": (
                "# include <stdlib.ARKlight>\n# define LEVEL -> 4\n\n"
                "def home():\n    return Page(Heading('Hi', level=LEVEL))\n"
            ),
        },
    )
    site, _ = load_site(site_path)
    assert site.routes["/"]().children[0].props == {"level": 4}


def test_a_module_reached_through_a_package_init_gets_the_preamble_too(tmp_path):
    site_path = _project(
        tmp_path,
        {
            "site.py": (
                "# include <stdlib.ARKlight>\nfrom pages import home as home_page\nsite = Site()\n\n"
                "@site.page('/')\ndef home():\n    return home_page()\n"
            ),
            "pages/__init__.py": (
                "# include <stdlib.ARKlight>\n\ndef home():\n    return Page(Heading('Hi'))\n"
            ),
        },
    )
    site, _ = load_site(site_path)
    assert "/" in site.routes


def test_a_project_module_without_a_preamble_behaves_as_before(tmp_path):
    site_path = _project(
        tmp_path,
        {
            "site.py": _SITE,
            "pages/__init__.py": "",
            "pages/home.py": "from arklight import *\n\ndef home():\n    return Page(Heading('Hi'))\n",
        },
    )
    site, _ = load_site(site_path)
    assert "/" in site.routes


def test_the_shadowing_check_runs_in_project_modules_too(tmp_path):
    site_path = _project(
        tmp_path,
        {
            "site.py": _SITE,
            "pages/__init__.py": "",
            "pages/home.py": (
                "# include <stdlib.ARKlight>\n\n"
                "def Button():\n    return 1\n\n"
                "def home():\n    return Page(Heading('Hi'))\n"
            ),
        },
    )
    with pytest.raises(SiteLoadError, match="rebinds name"):
        load_site(site_path)


def test_a_bad_preamble_in_a_project_module_names_that_file(tmp_path):
    site_path = _project(
        tmp_path,
        {
            "site.py": _SITE,
            "pages/__init__.py": "",
            "pages/home.py": "# include <nonsense>\n\ndef home():\n    return 1\n",
        },
    )
    with pytest.raises(SiteLoadError, match=r"pages[/\\]home\.py.*unrecognized `# include <nonsense>`"):
        load_site(site_path)


def test_star_import_notice_covers_project_modules(tmp_path):
    site_path = _project(
        tmp_path,
        {
            "site.py": _SITE,
            "pages/__init__.py": "",
            "pages/home.py": "from arklight import *\n\ndef home():\n    return Page(Heading('Hi'))\n",
        },
    )
    notices: list[str] = []
    load_site(site_path, on_notice=notices.append)
    assert len(notices) == 1
    assert "home.py:1" in notices[0]


def test_a_local_acc_module_in_the_project_can_be_included_and_has_a_preamble(tmp_path):
    site_path = _project(
        tmp_path,
        {
            "site.py": (
                "# include <stdlib.ARKlight>\n# include <acc.local_acc>\n\n"
                "site = Site()\n\n@site.page('/')\ndef home():\n    return Page(Badge('x'))\n"
            ),
            "local_acc.py": (
                "# include <stdlib.ARKlight>\n\n__all__ = ['Badge']\n\n"
                "def Badge(text):\n    return Text(text)\n"
            ),
        },
    )
    site, _ = load_site(site_path)
    assert site.routes["/"]().children[0].type == "Text"


def test_the_hook_and_the_modules_it_loaded_are_gone_afterwards(tmp_path):
    hooks_before = list(sys.meta_path)
    site_path = _project(
        tmp_path,
        {
            "site.py": _SITE,
            "pages/__init__.py": "",
            "pages/home.py": "# include <stdlib.ARKlight>\n\ndef home():\n    return Page(Heading('Hi'))\n",
        },
    )
    load_site(site_path)
    assert sys.meta_path == hooks_before
    assert str(tmp_path) not in sys.path
    assert not [m for m in sys.modules if m == "pages" or m.startswith("pages.")]


def test_the_hook_is_removed_even_when_the_load_fails(tmp_path):
    hooks_before = list(sys.meta_path)
    site_path = _project(tmp_path, {"site.py": "# include <nonsense>\nsite = 1\n"})
    with pytest.raises(SiteLoadError):
        load_site(site_path)
    assert sys.meta_path == hooks_before


def test_files_outside_the_project_are_left_to_normal_python(tmp_path):
    site_path = _project(
        tmp_path,
        {
            "site.py": (
                "# include <stdlib.ARKlight>\nimport json, os.path\n"
                "site = Site()\n\n@site.page('/')\ndef home():\n"
                "    return Page(Heading(json.dumps(1)))\n"
            ),
        },
    )
    site, _ = load_site(site_path)
    assert "/" in site.routes
    # the stdlib's own loader still owns json: not ours
    import json

    assert "_PreambleSourceLoader" not in type(json.__loader__).__name__


# ---------------------------------------------------------------------------
# arklight.config.py
# ---------------------------------------------------------------------------


def test_the_config_file_gets_its_preamble_too(tmp_path):
    (tmp_path / "arklight.config.py").write_text(
        "# define PORT -> 9123\n\nCONFIG = {'live_streaming': {'port': PORT}}\n"
    )
    assert load_config(tmp_path) == {"live_streaming": {"port": 9123}}


def test_a_bad_directive_in_the_config_is_not_reported_as_invalid_python(tmp_path):
    (tmp_path / "arklight.config.py").write_text("# use <UI.ARKlight>\nCONFIG = {}\n")
    with pytest.raises(ConfigError) as excinfo:
        load_config(tmp_path)
    assert "reserved for a proposal" in str(excinfo.value)
    assert "invalid Python" not in str(excinfo.value)


def test_a_plain_syntax_error_in_the_config_is_still_invalid_python(tmp_path):
    (tmp_path / "arklight.config.py").write_text("CONFIG = {\n")
    with pytest.raises(ConfigError, match="invalid Python"):
        load_config(tmp_path)


# ---------------------------------------------------------------------------
# `# include <stdlib.ARKlight>` gives the whole public API
# ---------------------------------------------------------------------------


def _public_names_defined_in_api() -> set[str]:
    return {
        name
        for name, value in vars(api).items()
        if not name.startswith("_") and getattr(value, "__module__", None) == api.__name__
    }


def test_every_public_name_arklight_api_defines_is_in_the_stdlib():
    missing = _public_names_defined_in_api() - set(arklight.__all__)
    assert not missing, f"public in arklight.api but not in arklight.__all__: {sorted(missing)}"


def test_the_errors_the_public_api_raises_are_in_the_stdlib():
    for name in ("CSSSyntaxError", "DuplicateStyleNameError", "ComponentError", "DuplicateComponentError"):
        assert name in arklight.__all__
        assert inspect.isclass(getattr(arklight, name))


def test_stdlib_all_has_no_duplicates_and_every_name_resolves():
    assert len(arklight.__all__) == len(set(arklight.__all__))
    assert [n for n in arklight.__all__ if not hasattr(arklight, n)] == []


def test_the_stdlib_include_binds_exactly_the_star_import_surface(tmp_path):
    from arklight.parser.preamble import resolve_preamble

    star = {}
    exec("from arklight import *", star)
    star.pop("__builtins__")
    assert set(resolve_preamble("# include <stdlib.ARKlight>\n")) == set(star)
