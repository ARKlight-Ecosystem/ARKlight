"""
Keeps the root `README.md` a thing that cannot go stale.

The same file is rendered on GitHub *and* as the PyPI project page. On
PyPI a relative link or image has nothing to resolve against, so every
link and image must be a full URL. Full URLs can rot silently when a
file moves, so each one that points into this repo is checked against
the working tree. And the README states nothing that changes release to
release (versions, release notes, roadmap): that lives in `CHANGELOG.md`,
`PROGRESS.md` and `docs/`, each the single source for its kind of record.
"""

import re
from pathlib import Path
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[1]
README = (ROOT / "README.md").read_text(encoding="utf-8")

_REPO = "https://github.com/ARKlight-Ecosystem/ARKlight"
_RAW = "https://raw.githubusercontent.com/ARKlight-Ecosystem/ARKlight"

_MD_LINK = re.compile(r"!?\[[^\]]*\]\(([^)\s]+)\)")
_HTML_SRC = re.compile(r"""(?:src|href)=["']([^"']+)["']""")


def _targets() -> list[str]:
    return _MD_LINK.findall(README) + _HTML_SRC.findall(README)


def test_every_link_and_image_is_a_full_url():
    relative = [t for t in _targets() if not t.startswith(("https://", "http://"))]
    assert not relative, (
        "README.md is rendered on PyPI, where relative targets don't resolve; "
        f"use full URLs instead of: {relative}"
    )


def test_repo_links_point_at_main_and_resolve_in_the_tree():
    checked = 0
    for target in _targets():
        for prefix, kinds in ((f"{_REPO}/", ("blob/main/", "tree/main/")), (f"{_RAW}/main/", ("",))):
            if not target.startswith(prefix):
                continue
            rest = target[len(prefix):]
            for kind in kinds:
                if kind and not rest.startswith(kind):
                    continue
                path = unquote(rest[len(kind):].split("#", 1)[0])
                assert (ROOT / path).exists(), f"README link points at a missing path: {target}"
                checked += 1
                break
            else:
                raise AssertionError(f"README repo link must target the main branch: {target}")
    assert checked, "expected README.md to link into the repo"


def test_readme_states_nothing_that_changes_per_release():
    lowered = README.lower()
    assert "current release" not in lowered
    assert "already shipped" not in lowered
    assert "next up" not in lowered
    assert not re.search(r"\bv?0\.\d{2,3}(\.\d+)?\b", README), (
        "README.md must not name version numbers; that record lives in CHANGELOG.md/PROGRESS.md"
    )
