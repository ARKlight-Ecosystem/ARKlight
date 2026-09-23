"""
Loads a user's ARKlight site file and returns the live `Site` object.

Static discovery (arklight.parser.discover) tells us *that* pages exist
and what they're called. To get the actual ARK AST -- the ARKNode trees
returned by each page function -- ARKlight needs those functions to run
in a real Python environment (name resolution, imports, loops,
conditionals, helper functions/components: all ordinary Python). So this
step executes the module source in an isolated namespace and hands back
the `Site` instance found there.

This is the same approach Flask, Pelican, and most Python site/app
frameworks use to load user code, and it keeps ARKlight's component
model to "just call a Python function" instead of reimplementing a
Python interpreter.

Every Python file ARKlight takes in gets its preamble read
(`arklight.parser.preamble`): the site file itself, and every project
module it imports -- `pages/`, `components/`, `content/`, an ACC
module living in the project -- through an import hook that is
installed for the duration of the load and scoped to the site file's
own directory. Anything outside that directory (the standard library,
pip-installed packages, ACC ones included) is imported by Python
exactly as before and never sees the hook. `arklight.config.py` goes
through the same `run_source` step.
"""

from __future__ import annotations

import contextlib
import importlib.abc
import importlib.machinery
import importlib.util
import os
import sys
import types
from pathlib import Path
from typing import Any, Callable, Iterator

from arklight.api import Site
from arklight.ir.components import unregister_components_under
from arklight.parser.discover import DiscoveredSite, discover
from arklight.parser.indentation import BracketIndentationError
from arklight.parser.preamble import (
    PreambleError,
    PreparedSource,
    check_namespace_shadowing,
    find_retired_star_imports,
    prepare_source,
    retired_star_import_notice,
)

# `prepare_source` can raise either: a malformed/unresolved preamble
# directive, or (see `arklight.parser.indentation`) a bracket-nesting
# indentation violation. Both are compiler-level, both should fail the
# load the same way, so every site handles them as one pair.
_PrepareSourceError = (PreambleError, BracketIndentationError)


class SiteLoadError(RuntimeError):
    pass


def _exec_prepared(namespace: dict[str, Any], prepared: PreparedSource, filename: str) -> None:
    """Run an already-prepared file in `namespace`: bind what its
    preamble resolved *before* its own code runs (so `Page`, `Button`,
    etc. are present by the time any top-level statement executes),
    execute the define-applied source, then compare the finished
    namespace with what the preamble bound. See
    arklight.parser.preamble for why the last step exists."""
    namespace.update(prepared.resolved.bindings)
    exec(compile(prepared.source, filename, "exec"), namespace)  # noqa: S102 -- intentional: this is the framework's job
    check_namespace_shadowing(
        prepared.resolved, namespace, source=prepared.source, filename=filename
    )


def run_source(
    namespace: dict[str, Any],
    source: str,
    *,
    filename: str,
    on_notice: Callable[[str], None] | None = None,
) -> None:
    """The whole "take in one Python file" step, for callers that have
    nothing to do between preparing and running it (project modules,
    `arklight.config.py`): retirement notices, preamble, defines, run,
    shadowing check. Raises `PreambleError` for a bad preamble; anything
    the file's own code raises propagates unchanged."""
    if on_notice is not None:
        for lineno in find_retired_star_imports(source):
            on_notice(retired_star_import_notice(filename, lineno))
    _exec_prepared(namespace, prepare_source(source, filename=filename), filename)


class _PreambleSourceLoader(importlib.machinery.SourceFileLoader):
    """Loads a project module the way Python would, except that its
    preamble is read first. Bypasses the bytecode cache on purpose: the
    code that runs is the define-applied source, and a cached
    compilation of the plain source must never stand in for it."""

    def __init__(
        self, fullname: str, path: str, on_notice: Callable[[str], None] | None
    ) -> None:
        super().__init__(fullname, path)
        self._on_notice = on_notice

    def exec_module(self, module: types.ModuleType) -> None:
        path = self.get_filename(module.__name__)
        source = importlib.util.decode_source(self.get_data(path))
        run_source(module.__dict__, source, filename=path, on_notice=self._on_notice)


class _ProjectFinder(importlib.abc.MetaPathFinder):
    """Finds modules exactly as Python's own path finder does, and only
    changes who *loads* the ones whose source file sits inside the
    project directory. Everything else is answered `None`, so the
    normal machinery handles it untouched."""

    def __init__(
        self, project_dir: Path, on_notice: Callable[[str], None] | None
    ) -> None:
        self._project_dir = project_dir.resolve()
        self._on_notice = on_notice

    def find_spec(self, fullname, path=None, target=None):  # noqa: ANN001
        spec = importlib.machinery.PathFinder.find_spec(fullname, path, target)
        if spec is None or not spec.origin:
            return None
        if not isinstance(spec.loader, importlib.machinery.SourceFileLoader):
            return None  # namespace package, extension module, ...
        try:
            Path(spec.origin).resolve().relative_to(self._project_dir)
        except ValueError:
            return None
        spec.loader = _PreambleSourceLoader(fullname, spec.origin, self._on_notice)
        return spec


@contextlib.contextmanager
def _project_imports(
    site_dir: str, on_notice: Callable[[str], None] | None
) -> Iterator[None]:
    """Everything that must be true while a site's own code and
    preambles run, and undone afterward.

    Package-shaped sites (e.g. the `arklight new --template production`
    scaffold: site.py + components/ + pages/ + content/) import sibling
    packages with ordinary absolute imports ("from pages.home import
    home"). Those only resolve if the site file's own directory is on
    sys.path -- true by accident when running `python site.py`
    directly, but NOT true for the installed `arklight` console
    script, whose sys.path[0] is wherever that script lives, not the
    user's project directory. So it is added here, once, and removed
    again afterward so repeated builds (e.g. in a test session) don't
    accumulate stale entries or leak one project's modules into
    another's. It is added *before* the site's preamble is resolved,
    so an `# include <acc.x>` naming a module that lives in the project
    resolves too -- and gets its own preamble read.

    The import hook goes in at the front of sys.meta_path for the same
    span. Package-shaped sites also commonly use generic top-level
    package names ("pages", "components", "content"). If two different
    projects are loaded in the same process, Python's import system
    caches the first one it sees in sys.modules and hands it back for
    the second project too -- even though that cached package's
    __path__ points at the *first* project's directory. Everything
    the load adds to sys.modules from inside the project is evicted
    again afterward, keeping each load_site() call isolated regardless
    of naming collisions between projects.

    That eviction makes the *next* `load_site()` call (a dev-server
    rebuild after the author edits a file, most commonly) re-import
    the project's modules from scratch -- including a `components/`
    module whose top-level `@component(...)` decorators run again.
    `arklight.ir.components.COMPONENT_REGISTRY` isn't a project-scoped
    cache the way `sys.modules` is, though: it's a plain module-level
    dict that isn't touched by the eviction above, so the fresh
    registration used to collide with the *previous* build's still-
    registered entry and raise `DuplicateComponentError` -- as if the
    author had two unrelated components fighting over one name, when
    really it was the same component surviving its own rebuild.
    `unregister_components_under`, called *before* `yield` (i.e.
    before the project's own modules run and re-register anything),
    clears out whatever an earlier load of this same site_dir left
    behind, so this load's own registrations land in a clean registry
    instead of needing `allow_redefine=True` as a workaround. It can't
    run in the `finally` block alongside the `sys.modules` eviction
    above: that would drop the registrations this very load just made,
    out from under the site object it's about to hand back to a caller
    (`compile_site_file`) that still needs to expand them.
    """
    added_to_path = site_dir not in sys.path
    if added_to_path:
        sys.path.insert(0, site_dir)
    finder = _ProjectFinder(Path(site_dir), on_notice)
    sys.meta_path.insert(0, finder)
    modules_before = set(sys.modules)
    unregister_components_under(site_dir)
    try:
        yield
    finally:
        with contextlib.suppress(ValueError):
            sys.meta_path.remove(finder)
        if added_to_path:
            sys.path.remove(site_dir)
        for mod_name in set(sys.modules) - modules_before:
            mod_file = getattr(sys.modules.get(mod_name), "__file__", None)
            if mod_file and str(Path(mod_file).resolve()).startswith(site_dir + os.sep):
                del sys.modules[mod_name]


def load_site(
    path: str | Path, *, on_notice: Callable[[str], None] | None = None
) -> tuple[Site, DiscoveredSite]:
    """
    Read, statically discover, and execute the site file at `path`.

    Returns (site, discovered) where `site` is the live Site object and
    `discovered` is the static-analysis result from the Python AST stage.
    Discovery and execution both see the file *after* its `# define`s
    are applied -- that is the source that actually runs.

    `on_notice`, if given, is called with a message for anything the
    compiler wants the author to know that isn't a failure -- currently
    a `from arklight import *` line (in the site file or any project
    module it imports), which is retired in favor of the preamble's
    `# include <stdlib.ARKlight>`. Nothing here prints on its own; the
    pipeline passes its stage logger, so this reaches the person
    running the build the same way every other notice does.
    """
    file_path = Path(path)
    if not file_path.exists():
        raise SiteLoadError(f"Site file not found: {file_path}")

    source = file_path.read_text(encoding="utf-8")
    filename = str(file_path)
    site_dir = str(file_path.resolve().parent)

    with _project_imports(site_dir, on_notice):
        try:
            prepared = prepare_source(source, filename=filename)
        except _PrepareSourceError as exc:
            raise SiteLoadError(str(exc)) from exc

        try:
            discovered = discover(prepared.source, filename=filename)
        except SyntaxError as exc:
            raise SiteLoadError(f"Could not parse {file_path}: {exc}") from exc
        except ValueError as exc:
            raise SiteLoadError(str(exc)) from exc

        if on_notice is not None:
            for lineno in find_retired_star_imports(source):
                on_notice(retired_star_import_notice(filename, lineno))

        module = types.ModuleType(file_path.stem)
        module.__file__ = filename

        try:
            module.__dict__.update(prepared.resolved.bindings)
            code = compile(prepared.source, filename, mode="exec")
            exec(code, module.__dict__)  # noqa: S102 -- intentional: this is the framework's job
        except _PrepareSourceError as exc:
            # A project module this file imported had a bad preamble,
            # or one of its lines failed the bracket-nesting check.
            raise SiteLoadError(f"Error while running {file_path}: {exc}") from exc
        except Exception as exc:  # noqa: BLE001 -- surface any user code error clearly
            raise SiteLoadError(f"Error while running {file_path}: {exc}") from exc

        # Everything above ran the file's own code, which is the one thing
        # the preamble can't see in advance: a `def`/assignment/import in
        # the file may have silently rebound a name the preamble bound.
        # Compare, and fail loudly like every other collision.
        try:
            check_namespace_shadowing(
                prepared.resolved, module.__dict__, source=prepared.source, filename=filename
            )
        except PreambleError as exc:
            raise SiteLoadError(str(exc)) from exc

    site_obj = module.__dict__.get(discovered.variable_name)
    if not isinstance(site_obj, Site):
        raise SiteLoadError(
            f"Expected `{discovered.variable_name}` to be a Site instance after "
            f"running {file_path}, but got {type(site_obj).__name__!r}."
        )

    if not site_obj.routes:
        raise SiteLoadError(f"Site `{discovered.variable_name}` has no registered pages.")

    return site_obj, discovered
