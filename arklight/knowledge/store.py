"""
`.arklight/` -- the Project Knowledge directory (stage 1 of 8, `v0.071`).

Design record: `docs/Proposals/PROJECT-KNOWELEDGE-PROPOSAL.md`; landing
order: `docs/Implementation/PROJECT-KNOWLEDGE-ADDENDUM.md`.

This module is the foundation and nothing else. It owns a
project-local directory, `.arklight/`, and gives later stages safe
helpers to put plain-text facts in it and read them back. It has no
providers, no facts about Git, no build history and no diagnostics
-- those are `v0.072`-`v0.077`. **Nothing in the compiler imports this
module yet**, so a build neither reads nor creates `.arklight/`, and
deleting the directory is a no-op for buildability (proposal §2, §14).

What a stage-1 directory looks like::

    .arklight/
      PROJECT            <- the format marker (`knowledge_format=1`)
      <other files>      <- whatever later stages write, via `write()`

Every file is UTF-8 text, one `key=value` per line, `#` comments and
blank lines ignored, so a developer can open it in an ordinary editor
and see what ARKlight knows (proposal §4). No database, no binary.

Safety rules, and why they exist
--------------------------------
* **The directory is untrusted input.** A cloned repository can ship
  its own `.arklight/`, including one that is a symlink pointing
  somewhere the compiler has no business writing. So the directory
  and every file and subdirectory under it must be real (not
  symlinks), and a name handed to `read()`/`write()` can only ever
  resolve inside it.
* **Writes are atomic.** A file is written to a sibling temp name and
  swapped in with `os.replace`, so a crash mid-write leaves the old
  file or the new one, never half of one.
* **Writes need a current-format directory.** If `.arklight/` was made
  by a newer ARKlight (`knowledge_format` higher than this one knows)
  this version will not write into it, because it cannot know what
  the newer files mean. Stale or unreadable knowledge is *reported*
  here, not repaired -- proposal §17 prefers regeneration over a
  migration framework, and deciding when to regenerate belongs to the
  stages that have something to regenerate.
* **Size cap.** A knowledge file over `MAX_FILE_BYTES` is refused.
  Facts are small; a huge file is a corrupt or hostile one.

Error contract for later stages
-------------------------------
Everything that can go wrong with the *directory* (missing permissions,
a read-only checkout, a corrupt file, an incompatible format) raises a
`KnowledgeError`. Persistent knowledge is an enhancement, never a
dependency (proposal §14), so a caller should treat `KnowledgeError` as
"carry on without it". Misuse by the *caller* -- a bad file name, a key
with a space in it, a non-string value -- raises plain `ValueError`/
`TypeError`, deliberately not a `KnowledgeError`, so catching
`KnowledgeError` to stay non-fatal can never hide a bug in the caller.
"""

from __future__ import annotations

import enum
import os
import re
import stat
import uuid
from pathlib import Path
from typing import Mapping, Optional, Union

KNOWLEDGE_DIRNAME = ".arklight"
"""Name of the directory, relative to the project root."""

MARKER_NAME = "PROJECT"
"""File inside `.arklight/` that carries the format marker."""

FORMAT_KEY = "knowledge_format"
"""Key in `MARKER_NAME` holding the knowledge-format version."""

KNOWLEDGE_FORMAT = 1
"""The format version this ARKlight reads and writes (proposal §17)."""

MAX_FILE_BYTES = 1024 * 1024
"""Largest knowledge file `read()`/`write()` will handle (1 MiB)."""

_MARKER_HEADER = (
    "ARKlight Project Knowledge -- derived by the compiler, safe to delete.\n"
    "Deleting this directory never changes what the project builds."
)

# Keys and file-name segments share one shape: they start with a letter,
# digit or underscore (so never `.`/`..`/hidden/option-looking) and
# continue with letters, digits, `_`, `.` or `-`. The proposal's own
# examples (`git.head`, `knowledge_format`, `COMPONENTS`) all fit.
# `\Z`, not `$`: `$` also matches just before a trailing newline, which
# would let `"BUILD\n"` through as a file name.
_TOKEN = re.compile(r"[A-Za-z0-9_][A-Za-z0-9_.-]*\Z")
_MAX_FORMAT_DIGITS = 9


class KnowledgeError(Exception):
    """The `.arklight/` directory (or its contents) cannot be used.

    Base class for everything this package raises about the directory.
    Treat as "proceed without persistent knowledge" -- see the module
    docstring's error contract.
    """


class KnowledgeFormatError(KnowledgeError):
    """A knowledge file's content is malformed, oversized or not UTF-8."""


class KnowledgeStateError(KnowledgeError):
    """The directory is in a state this operation refuses to work in
    (symlinked, not a directory, incompatible format, or the write
    hit an operating-system error such as a read-only checkout)."""


class KnowledgeStatus(enum.Enum):
    """What `KnowledgeStore.status()` found at `<project>/.arklight`.

    Mirrors proposal §17's "current; readable but outdated;
    incompatible; safely regeneratable" classification.
    """

    ABSENT = "absent"
    """No `.arklight/` yet. `write()`/`ensure()` will create it."""

    UNUSABLE = "unusable"
    """Something is there but it is not a real directory (a file, or a
    symlink -- refused on purpose, see the module docstring)."""

    UNMARKED = "unmarked"
    """A real directory with no `PROJECT` marker. `ensure()` adopts it
    by writing the marker; nothing else is touched."""

    CORRUPT = "corrupt"
    """The marker exists but cannot be read as a format version.
    Regeneratable; not repaired here."""

    CURRENT = "current"
    """Marker present, `knowledge_format` equals `KNOWLEDGE_FORMAT`."""

    OUTDATED = "outdated"
    """Marker present, written by an older format. Readable; this
    version will not write into it."""

    INCOMPATIBLE = "incompatible"
    """Marker present, written by a *newer* format. Neither read nor
    written -- this version cannot know what the files mean."""


# --------------------------------------------------------------------------
# Text format
# --------------------------------------------------------------------------


def parse_knowledge_text(text: str) -> dict[str, str]:
    """Parse knowledge-file text into an ordered ``{key: value}`` dict.

    One ``key=value`` per line. Blank lines and lines whose first
    non-space character is ``#`` are skipped. The value is everything
    after the *first* ``=``, verbatim (a trailing ``\\r`` from a
    Windows editor is dropped). A line that is not blank, not a
    comment and not a valid ``key=value``, or a repeated key, raises
    `KnowledgeFormatError` naming the line -- the compiler's usual
    fail-loudly rule, not a silent "last one wins".
    """
    facts: dict[str, str] = {}
    for number, raw in enumerate(text.split("\n"), start=1):
        line = raw[:-1] if raw.endswith("\r") else raw
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        key, sep, value = line.partition("=")
        if not sep or not _TOKEN.match(key):
            raise KnowledgeFormatError(
                f"line {number}: expected `key=value` with a key made of "
                f"letters, digits, `_`, `.` or `-`, got {line[:60]!r}"
            )
        if key in facts:
            raise KnowledgeFormatError(f"line {number}: duplicate key {key!r}")
        facts[key] = value
    return facts


def render_knowledge_text(
    facts: Mapping[str, str], *, header: Optional[str] = None
) -> str:
    """Render ``facts`` as knowledge-file text (the inverse of
    `parse_knowledge_text`).

    ``header``, if given, is written first as ``#`` comment lines. Keys
    must match the key shape and values must be single-line strings;
    anything else is a caller bug and raises `ValueError`/`TypeError`
    (not a `KnowledgeError` -- see the module docstring).
    """
    lines: list[str] = []
    if header:
        for comment in header.split("\n"):
            lines.append(f"# {comment}".rstrip())
    for key, value in facts.items():
        if not isinstance(key, str) or not _TOKEN.match(key):
            raise ValueError(
                f"invalid knowledge key {key!r}: use letters, digits, `_`, "
                f"`.` or `-`, starting with a letter, digit or `_`"
            )
        if not isinstance(value, str):
            raise TypeError(
                f"knowledge value for {key!r} must be a str, got "
                f"{type(value).__name__}"
            )
        if "\n" in value or "\r" in value or "\0" in value:
            raise ValueError(
                f"knowledge value for {key!r} must be a single line "
                f"(no newline or NUL characters)"
            )
        lines.append(f"{key}={value}")
    return "\n".join(lines) + "\n" if lines else ""


# --------------------------------------------------------------------------
# Filesystem helpers
# --------------------------------------------------------------------------


def _lstat(path: Path) -> Optional[os.stat_result]:
    try:
        return os.lstat(path)
    except FileNotFoundError:
        return None
    except OSError as exc:
        raise KnowledgeStateError(f"cannot inspect {path}: {exc}") from exc


def _is_real_dir(st: os.stat_result) -> bool:
    return stat.S_ISDIR(st.st_mode)  # lstat: a symlink reports S_ISLNK


def _is_real_file(st: os.stat_result) -> bool:
    return stat.S_ISREG(st.st_mode)


def _read_bounded(path: Path) -> str:
    """Read one knowledge file as UTF-8, refusing oversize/non-UTF-8."""
    try:
        with open(path, "rb") as fh:
            data = fh.read(MAX_FILE_BYTES + 1)
    except OSError as exc:
        raise KnowledgeStateError(f"cannot read {path}: {exc}") from exc
    if len(data) > MAX_FILE_BYTES:
        raise KnowledgeFormatError(
            f"{path} is larger than {MAX_FILE_BYTES} bytes; refusing to read it"
        )
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise KnowledgeFormatError(f"{path} is not valid UTF-8: {exc}") from exc


def _write_atomic(path: Path, text: str) -> None:
    """Write ``text`` to ``path`` via a sibling temp file + `os.replace`."""
    data = text.encode("utf-8")
    if len(data) > MAX_FILE_BYTES:
        raise ValueError(
            f"knowledge file would be {len(data)} bytes; the limit is "
            f"{MAX_FILE_BYTES}"
        )
    tmp = path.with_name(f".{path.name}.{uuid.uuid4().hex[:8]}.tmp")
    try:
        # O_EXCL: never write through a pre-planted file/symlink at the
        # temp name. Mode 0o666 lets the process umask pick permissions,
        # like any ordinary file the project's tools create.
        fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o666)
        with os.fdopen(fd, "wb") as fh:
            fh.write(data)
        os.replace(tmp, path)
    except OSError as exc:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise KnowledgeStateError(f"cannot write {path}: {exc}") from exc


# --------------------------------------------------------------------------
# The store
# --------------------------------------------------------------------------


class KnowledgeStore:
    """Safe access to one project's `.arklight/` directory.

    ``KnowledgeStore(project_root)`` does no I/O. Which directory is
    "the project root" is the caller's decision -- stage 1 wires this
    into nothing, so it takes a path rather than guessing.

    ``status()`` and ``read()`` never create or change anything.
    ``ensure()`` and ``write()`` create the directory (and, for
    ``write()``, any subdirectory its name implies) on demand.
    """

    def __init__(self, project_root: Union[str, "os.PathLike[str]"]) -> None:
        self._root = Path(project_root)
        self._dir = self._root / KNOWLEDGE_DIRNAME

    @property
    def path(self) -> Path:
        """`<project_root>/.arklight` (it may not exist)."""
        return self._dir

    # -- inspection ------------------------------------------------------

    def status(self) -> KnowledgeStatus:
        """Classify the directory. Read-only; never raises for a bad
        directory -- bad states are the return value."""
        try:
            st = _lstat(self._dir)
        except KnowledgeStateError:
            return KnowledgeStatus.UNUSABLE
        if st is None:
            return KnowledgeStatus.ABSENT
        if not _is_real_dir(st):
            return KnowledgeStatus.UNUSABLE
        return self._marker_status()

    def _marker_status(self) -> KnowledgeStatus:
        marker = self._dir / MARKER_NAME
        try:
            st = _lstat(marker)
        except KnowledgeStateError:
            return KnowledgeStatus.CORRUPT
        if st is None:
            return KnowledgeStatus.UNMARKED
        if not _is_real_file(st):
            return KnowledgeStatus.CORRUPT
        try:
            facts = parse_knowledge_text(_read_bounded(marker))
        except KnowledgeError:
            return KnowledgeStatus.CORRUPT
        raw = facts.get(FORMAT_KEY, "")
        if not (raw.isascii() and raw.isdigit()) or len(raw) > _MAX_FORMAT_DIGITS:
            return KnowledgeStatus.CORRUPT
        version = int(raw)
        if version == KNOWLEDGE_FORMAT:
            return KnowledgeStatus.CURRENT
        return (
            KnowledgeStatus.OUTDATED
            if version < KNOWLEDGE_FORMAT
            else KnowledgeStatus.INCOMPATIBLE
        )

    # -- creation --------------------------------------------------------

    def ensure(self) -> KnowledgeStatus:
        """Detect-or-create `.arklight/` and its format marker.

        Creates the directory if absent and writes the marker if the
        directory has none. Anything else (an outdated, newer, corrupt
        or non-directory `.arklight`) is left exactly as found and
        reported through the returned status -- ``ensure()`` never
        overwrites or deletes existing knowledge. Returns the status
        after the call: `CURRENT` when the directory is ready to use.
        """
        status = self.status()
        if status is KnowledgeStatus.ABSENT:
            try:
                self._dir.mkdir(exist_ok=True)  # parents=False: the root must exist
            except OSError as exc:
                raise KnowledgeStateError(
                    f"cannot create {self._dir}: {exc}"
                ) from exc
            status = KnowledgeStatus.UNMARKED
        if status is KnowledgeStatus.UNMARKED:
            _write_atomic(
                self._dir / MARKER_NAME,
                render_knowledge_text(
                    {FORMAT_KEY: str(KNOWLEDGE_FORMAT)}, header=_MARKER_HEADER
                ),
            )
            status = self.status()
        return status

    # -- reading and writing ----------------------------------------------

    def read(self, name: str) -> Optional[dict[str, str]]:
        """Return the facts in knowledge file ``name``, or ``None`` if
        the directory or the file does not exist.

        ``name`` is a file name inside `.arklight/`, optionally with
        subdirectories (``"KNOWLEDGE/COMPONENTS"``). Raises
        `KnowledgeStateError` if the directory is unusable, in an
        incompatible format, or the file is not a regular file;
        `KnowledgeFormatError` if its content is malformed. Never
        creates anything.
        """
        segments = _split_name(name)
        status = self.status()
        if status is KnowledgeStatus.ABSENT:
            return None
        if status not in (KnowledgeStatus.CURRENT, KnowledgeStatus.OUTDATED):
            raise KnowledgeStateError(
                f"{self._dir} is {status.value}; refusing to read {name!r}"
            )
        target = self._checked_path(segments)
        st = _lstat(target)
        if st is None:
            return None
        if not _is_real_file(st):
            raise KnowledgeStateError(f"{target} is not a regular file")
        return parse_knowledge_text(_read_bounded(target))

    def write(
        self,
        name: str,
        facts: Mapping[str, str],
        *,
        header: Optional[str] = None,
    ) -> Path:
        """Atomically replace knowledge file ``name`` with ``facts``,
        creating `.arklight/` (and any subdirectory) first if needed.
        Returns the file's path.

        Refuses, with `KnowledgeStateError`, unless the directory is in
        the current format once ``ensure()`` has run -- so it never
        writes into knowledge a newer ARKlight made. The format marker
        (`PROJECT`) is managed by ``ensure()`` and cannot be written
        through here.
        """
        segments = _split_name(name)
        if segments == [MARKER_NAME]:
            raise ValueError(
                f"{MARKER_NAME!r} is the format marker, managed by ensure(); "
                f"it cannot be written with write()"
            )
        # Validate content before touching the filesystem, so a caller
        # bug never leaves a freshly-created empty directory behind.
        text = render_knowledge_text(facts, header=header)
        status = self.ensure()
        if status is not KnowledgeStatus.CURRENT:
            raise KnowledgeStateError(
                f"{self._dir} is {status.value}; refusing to write {name!r}"
            )
        target = self._checked_path(segments)
        parent = target.parent
        if parent != self._dir:
            self._make_subdirs(segments[:-1])
        st = _lstat(target)
        if st is not None and not _is_real_file(st):
            raise KnowledgeStateError(f"{target} exists and is not a regular file")
        _write_atomic(target, text)
        return target

    # -- internals -------------------------------------------------------

    def _checked_path(self, segments: list[str]) -> Path:
        """Path for ``segments`` under `.arklight/`, refusing any existing
        intermediate component that is a symlink or not a directory.
        (The final component is checked by the caller.)"""
        current = self._dir
        for segment in segments[:-1]:
            current = current / segment
            st = _lstat(current)
            if st is None:
                continue
            if not _is_real_dir(st):
                raise KnowledgeStateError(
                    f"{current} is not a real directory; refusing to follow it"
                )
        return self._dir.joinpath(*segments)

    def _make_subdirs(self, segments: list[str]) -> None:
        current = self._dir
        for segment in segments:
            current = current / segment
            try:
                current.mkdir(exist_ok=True)
            except OSError as exc:
                raise KnowledgeStateError(
                    f"cannot create {current}: {exc}"
                ) from exc
            st = _lstat(current)
            if st is None or not _is_real_dir(st):
                raise KnowledgeStateError(
                    f"{current} is not a real directory; refusing to use it"
                )


def _split_name(name: str) -> list[str]:
    """Validate a knowledge-file name and split it into path segments.

    Names are ``/``-separated segments, each matching the key shape. No
    empty segment, `.`, `..`, backslash, drive letter or absolute path
    can get through, so a name always resolves inside `.arklight/`.
    """
    if not isinstance(name, str):
        raise TypeError(f"knowledge file name must be a str, got {type(name).__name__}")
    segments = name.split("/")
    if not name or not all(_TOKEN.match(s) for s in segments):
        raise ValueError(
            f"invalid knowledge file name {name!r}: use `/`-separated parts "
            f"made of letters, digits, `_`, `.` or `-`, each starting with a "
            f"letter, digit or `_`"
        )
    return segments
