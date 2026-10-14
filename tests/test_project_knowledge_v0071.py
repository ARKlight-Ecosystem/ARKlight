"""
Project Knowledge, stage 1 of 8 (`v0.071`): the `.arklight/` foundation.

Covers `arklight/knowledge/` -- the text format, the directory status
classification, `ensure()`, and the safe `read()`/`write()` helpers --
and the stage's central promise (proposal §2, §14): nothing in the
compiler depends on the directory, so a build neither creates it nor
changes with or without it.
"""

import os
import re
from pathlib import Path

import pytest

import arklight
from arklight.compiler.pipeline import build
from arklight.knowledge import (
    FORMAT_KEY,
    KNOWLEDGE_DIRNAME,
    KNOWLEDGE_FORMAT,
    MARKER_NAME,
    MAX_FILE_BYTES,
    KnowledgeError,
    KnowledgeFormatError,
    KnowledgeStateError,
    KnowledgeStatus,
    KnowledgeStore,
    parse_knowledge_text,
    render_knowledge_text,
)

needs_symlinks = pytest.mark.skipif(
    not hasattr(os, "symlink"), reason="platform has no symlinks"
)


@pytest.fixture
def store(tmp_path):
    return KnowledgeStore(tmp_path)


def make_dir(tmp_path, marker=None):
    """A real `.arklight/`, optionally with a hand-written marker."""
    d = tmp_path / KNOWLEDGE_DIRNAME
    d.mkdir()
    if marker is not None:
        (d / MARKER_NAME).write_text(marker, encoding="utf-8")
    return d


# --------------------------------------------------------------------------
# Constants
# --------------------------------------------------------------------------


def test_constants_match_the_proposal():
    assert KNOWLEDGE_DIRNAME == ".arklight"
    assert KNOWLEDGE_FORMAT == 1
    assert MARKER_NAME == "PROJECT"
    assert FORMAT_KEY == "knowledge_format"


# --------------------------------------------------------------------------
# Text format
# --------------------------------------------------------------------------


def test_parse_reads_key_value_lines_in_order():
    facts = parse_knowledge_text("b=2\na=1\n")
    assert facts == {"b": "2", "a": "1"}
    assert list(facts) == ["b", "a"]


def test_parse_skips_comments_and_blank_lines():
    text = "# a comment\n\n   \n  # indented comment\nkey=value\n"
    assert parse_knowledge_text(text) == {"key": "value"}


def test_parse_value_is_everything_after_the_first_equals():
    assert parse_knowledge_text("k=a=b=c\n") == {"k": "a=b=c"}


def test_parse_empty_value_and_empty_text():
    assert parse_knowledge_text("k=\n") == {"k": ""}
    assert parse_knowledge_text("") == {}


def test_parse_value_whitespace_is_verbatim():
    assert parse_knowledge_text("k= padded \n") == {"k": " padded "}


def test_parse_tolerates_windows_line_endings():
    assert parse_knowledge_text("a=1\r\nb=2\r\n") == {"a": "1", "b": "2"}


def test_parse_accepts_the_proposals_own_example_keys():
    text = "repository.present=true\ngit.head=8f31c2a\nlast_timestamp=2026-09-16T18:42:11\n"
    assert parse_knowledge_text(text)["git.head"] == "8f31c2a"


@pytest.mark.parametrize(
    "bad",
    [
        "just words\n",  # no `=`
        "=value\n",  # empty key
        "has space=1\n",  # key with a space
        " lead=1\n",  # leading space in key
        "-dash=1\n",  # key may not start with `-`
        ".dot=1\n",  # ...or `.`
        "k\u00e9y=1\n",  # non-ASCII key
    ],
)
def test_parse_rejects_malformed_lines_naming_the_line(bad):
    with pytest.raises(KnowledgeFormatError, match="line 1"):
        parse_knowledge_text(bad)


def test_parse_reports_the_right_line_number():
    with pytest.raises(KnowledgeFormatError, match="line 3"):
        parse_knowledge_text("a=1\n# c\nnonsense\n")


def test_parse_rejects_duplicate_keys_instead_of_last_wins():
    with pytest.raises(KnowledgeFormatError, match="duplicate key 'a'"):
        parse_knowledge_text("a=1\na=2\n")


def test_render_round_trips_through_parse():
    facts = {"z": "last", "a": "first", "git.head": "8f31c2a", "e": "", "x": "a=b"}
    assert parse_knowledge_text(render_knowledge_text(facts)) == facts


def test_render_uses_unix_newlines_and_one_line_per_fact():
    assert render_knowledge_text({"a": "1", "b": "2"}) == "a=1\nb=2\n"


def test_render_empty_mapping_is_empty_text():
    assert render_knowledge_text({}) == ""


def test_render_header_becomes_comment_lines_and_is_ignored_on_parse():
    text = render_knowledge_text({"a": "1"}, header="line one\nline two")
    assert text == "# line one\n# line two\na=1\n"
    assert parse_knowledge_text(text) == {"a": "1"}


@pytest.mark.parametrize("key", ["", "has space", "a=b", "-x", ".x", "k\n", "caf\u00e9"])
def test_render_rejects_bad_keys_as_caller_bugs(key):
    with pytest.raises(ValueError):
        render_knowledge_text({key: "v"})


@pytest.mark.parametrize("value", ["two\nlines", "cr\rhere", "nul\0byte"])
def test_render_rejects_multiline_values(value):
    with pytest.raises(ValueError, match="single line"):
        render_knowledge_text({"k": value})


@pytest.mark.parametrize("value", [1, True, None, ["a"], b"bytes"])
def test_render_rejects_non_string_values(value):
    with pytest.raises(TypeError):
        render_knowledge_text({"k": value})


def test_caller_bugs_are_not_knowledge_errors():
    # Catching KnowledgeError to stay non-fatal must never swallow a
    # bug in the caller (see the module docstring's error contract).
    assert not issubclass(ValueError, KnowledgeError)
    with pytest.raises(ValueError) as excinfo:
        render_knowledge_text({"bad key": "v"})
    assert not isinstance(excinfo.value, KnowledgeError)


def test_error_hierarchy():
    assert issubclass(KnowledgeFormatError, KnowledgeError)
    assert issubclass(KnowledgeStateError, KnowledgeError)


# --------------------------------------------------------------------------
# status() / ensure()
# --------------------------------------------------------------------------


def test_path_is_dot_arklight_under_the_project_root(tmp_path):
    assert KnowledgeStore(tmp_path).path == tmp_path / ".arklight"


def test_constructing_a_store_does_no_io(tmp_path):
    KnowledgeStore(tmp_path)
    assert list(tmp_path.iterdir()) == []


def test_status_absent_and_it_does_not_create(store, tmp_path):
    assert store.status() is KnowledgeStatus.ABSENT
    assert not (tmp_path / ".arklight").exists()


def test_ensure_creates_the_directory_and_marker(store, tmp_path):
    assert store.ensure() is KnowledgeStatus.CURRENT
    marker = tmp_path / ".arklight" / "PROJECT"
    assert marker.is_file()
    assert parse_knowledge_text(marker.read_text(encoding="utf-8")) == {
        "knowledge_format": "1"
    }


def test_marker_is_plain_human_readable_text(store, tmp_path):
    store.ensure()
    text = (tmp_path / ".arklight" / "PROJECT").read_text(encoding="utf-8")
    assert "knowledge_format=1" in text
    assert "safe to delete" in text
    assert text.endswith("\n")


def test_ensure_is_idempotent_and_does_not_rewrite_the_marker(store, tmp_path):
    store.ensure()
    marker = tmp_path / ".arklight" / "PROJECT"
    before = (marker.read_bytes(), marker.stat().st_mtime_ns)
    assert store.ensure() is KnowledgeStatus.CURRENT
    assert (marker.read_bytes(), marker.stat().st_mtime_ns) == before


def test_ensure_adopts_an_unmarked_directory_without_touching_its_files(store, tmp_path):
    d = make_dir(tmp_path)
    (d / "OTHER").write_text("keep=me\n", encoding="utf-8")
    assert store.status() is KnowledgeStatus.UNMARKED
    assert store.ensure() is KnowledgeStatus.CURRENT
    assert (d / "OTHER").read_text(encoding="utf-8") == "keep=me\n"


def test_ensure_does_not_create_missing_project_roots(tmp_path):
    missing = KnowledgeStore(tmp_path / "does" / "not" / "exist")
    with pytest.raises(KnowledgeStateError):
        missing.ensure()
    assert not (tmp_path / "does").exists()


@pytest.mark.parametrize(
    "marker, expected",
    [
        ("knowledge_format=1\n", KnowledgeStatus.CURRENT),
        ("# comment\nknowledge_format=1\nfuture_key=ok\n", KnowledgeStatus.CURRENT),
        ("knowledge_format=0\n", KnowledgeStatus.OUTDATED),
        ("knowledge_format=2\n", KnowledgeStatus.INCOMPATIBLE),
        ("knowledge_format=999999999\n", KnowledgeStatus.INCOMPATIBLE),
        ("", KnowledgeStatus.CORRUPT),  # no key at all
        ("something_else=1\n", KnowledgeStatus.CORRUPT),
        ("knowledge_format=\n", KnowledgeStatus.CORRUPT),
        ("knowledge_format=one\n", KnowledgeStatus.CORRUPT),
        ("knowledge_format=-1\n", KnowledgeStatus.CORRUPT),
        ("knowledge_format=1.5\n", KnowledgeStatus.CORRUPT),
        ("knowledge_format=\u0661\n", KnowledgeStatus.CORRUPT),  # Arabic-Indic digit
        ("knowledge_format=" + "9" * 40 + "\n", KnowledgeStatus.CORRUPT),
        ("not key value\n", KnowledgeStatus.CORRUPT),
        ("knowledge_format=1\nknowledge_format=1\n", KnowledgeStatus.CORRUPT),
    ],
)
def test_status_classifies_every_marker_shape(tmp_path, marker, expected):
    make_dir(tmp_path, marker)
    assert KnowledgeStore(tmp_path).status() is expected


def test_status_corrupt_when_marker_is_not_utf8(tmp_path):
    d = make_dir(tmp_path)
    (d / "PROJECT").write_bytes(b"\xff\xfe\x00bad")
    assert KnowledgeStore(tmp_path).status() is KnowledgeStatus.CORRUPT


def test_status_corrupt_when_marker_is_a_directory(tmp_path):
    d = make_dir(tmp_path)
    (d / "PROJECT").mkdir()
    assert KnowledgeStore(tmp_path).status() is KnowledgeStatus.CORRUPT


def test_status_corrupt_when_marker_is_oversize(tmp_path):
    d = make_dir(tmp_path)
    (d / "PROJECT").write_text("#" * (MAX_FILE_BYTES + 10), encoding="utf-8")
    assert KnowledgeStore(tmp_path).status() is KnowledgeStatus.CORRUPT


def test_status_unusable_when_dot_arklight_is_a_file(tmp_path):
    (tmp_path / ".arklight").write_text("i am a file")
    assert KnowledgeStore(tmp_path).status() is KnowledgeStatus.UNUSABLE


@needs_symlinks
def test_status_unusable_when_dot_arklight_is_a_symlink(tmp_path):
    # A cloned repo could point `.arklight` anywhere; refuse to follow it.
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    (elsewhere / "PROJECT").write_text("knowledge_format=1\n")
    root = tmp_path / "project"
    root.mkdir()
    os.symlink(elsewhere, root / ".arklight")
    assert KnowledgeStore(root).status() is KnowledgeStatus.UNUSABLE


@needs_symlinks
def test_status_corrupt_when_marker_is_a_symlink(tmp_path):
    d = make_dir(tmp_path)
    real = tmp_path / "real_marker"
    real.write_text("knowledge_format=1\n")
    os.symlink(real, d / "PROJECT")
    assert KnowledgeStore(tmp_path).status() is KnowledgeStatus.CORRUPT


@pytest.mark.parametrize(
    "marker",
    ["knowledge_format=0\n", "knowledge_format=2\n", "garbage\n"],
)
def test_ensure_leaves_a_non_current_directory_exactly_as_found(tmp_path, marker):
    d = make_dir(tmp_path, marker)
    (d / "BUILD").write_text("result=success\n", encoding="utf-8")
    store = KnowledgeStore(tmp_path)
    before = store.status()
    assert before is not KnowledgeStatus.CURRENT
    assert store.ensure() is before
    assert (d / "PROJECT").read_text(encoding="utf-8") == marker
    assert (d / "BUILD").read_text(encoding="utf-8") == "result=success\n"


def test_ensure_leaves_a_symlink_or_file_in_place(tmp_path):
    (tmp_path / ".arklight").write_text("i am a file")
    assert KnowledgeStore(tmp_path).ensure() is KnowledgeStatus.UNUSABLE
    assert (tmp_path / ".arklight").read_text() == "i am a file"


# --------------------------------------------------------------------------
# read()
# --------------------------------------------------------------------------


def test_read_returns_none_when_there_is_no_directory_and_creates_nothing(store, tmp_path):
    assert store.read("BUILD") is None
    assert not (tmp_path / ".arklight").exists()


def test_read_returns_none_for_a_missing_file(store):
    store.ensure()
    assert store.read("BUILD") is None


def test_read_returns_what_write_stored(store):
    store.write("BUILD", {"last_result": "success", "last_revision": "71a8e4d"})
    assert store.read("BUILD") == {"last_result": "success", "last_revision": "71a8e4d"}


def test_read_can_read_the_marker_itself(store):
    store.ensure()
    assert store.read("PROJECT") == {"knowledge_format": "1"}


def test_read_works_on_hand_edited_files(store, tmp_path):
    store.ensure()
    (tmp_path / ".arklight" / "NOTES").write_text(
        "# edited by hand\nowner=me\r\n", encoding="utf-8"
    )
    assert store.read("NOTES") == {"owner": "me"}


def test_read_malformed_file_raises_format_error(store, tmp_path):
    store.ensure()
    (tmp_path / ".arklight" / "BAD").write_text("not a fact\n", encoding="utf-8")
    with pytest.raises(KnowledgeFormatError):
        store.read("BAD")


def test_read_non_utf8_file_raises_format_error(store, tmp_path):
    store.ensure()
    (tmp_path / ".arklight" / "BAD").write_bytes(b"\xff\xfe")
    with pytest.raises(KnowledgeFormatError, match="UTF-8"):
        store.read("BAD")


def test_read_oversize_file_is_refused(store, tmp_path):
    store.ensure()
    (tmp_path / ".arklight" / "HUGE").write_text(
        "k=" + "x" * MAX_FILE_BYTES, encoding="utf-8"
    )
    with pytest.raises(KnowledgeFormatError, match="larger than"):
        store.read("HUGE")


def test_read_reads_an_outdated_directory(tmp_path):
    d = make_dir(tmp_path, "knowledge_format=0\n")
    (d / "BUILD").write_text("result=success\n", encoding="utf-8")
    assert KnowledgeStore(tmp_path).read("BUILD") == {"result": "success"}


@pytest.mark.parametrize("marker", ["knowledge_format=2\n", "garbage\n", None])
def test_read_refuses_incompatible_corrupt_and_unmarked_directories(tmp_path, marker):
    d = make_dir(tmp_path, marker)
    (d / "BUILD").write_text("result=success\n", encoding="utf-8")
    with pytest.raises(KnowledgeStateError):
        KnowledgeStore(tmp_path).read("BUILD")


def test_read_refuses_when_dot_arklight_is_a_file(tmp_path):
    (tmp_path / ".arklight").write_text("x")
    with pytest.raises(KnowledgeStateError):
        KnowledgeStore(tmp_path).read("BUILD")


def test_read_refuses_a_directory_named_like_a_file(store, tmp_path):
    store.ensure()
    (tmp_path / ".arklight" / "BUILD").mkdir()
    with pytest.raises(KnowledgeStateError, match="not a regular file"):
        store.read("BUILD")


@needs_symlinks
def test_read_refuses_a_symlinked_file(store, tmp_path):
    store.ensure()
    secret = tmp_path / "secret.txt"
    secret.write_text("token=hunter2\n")
    os.symlink(secret, tmp_path / ".arklight" / "LEAK")
    with pytest.raises(KnowledgeStateError):
        store.read("LEAK")


@needs_symlinks
def test_read_refuses_to_walk_through_a_symlinked_subdirectory(store, tmp_path):
    store.ensure()
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "FILE").write_text("token=hunter2\n")
    os.symlink(outside, tmp_path / ".arklight" / "KNOWLEDGE")
    with pytest.raises(KnowledgeStateError):
        store.read("KNOWLEDGE/FILE")


# --------------------------------------------------------------------------
# write()
# --------------------------------------------------------------------------


def test_write_creates_the_directory_marker_and_file(store, tmp_path):
    path = store.write("BUILD", {"last_result": "success"})
    assert path == tmp_path / ".arklight" / "BUILD"
    assert path.read_text(encoding="utf-8") == "last_result=success\n"
    assert store.status() is KnowledgeStatus.CURRENT
    assert (tmp_path / ".arklight" / "PROJECT").is_file()


def test_write_replaces_the_whole_file(store):
    store.write("BUILD", {"a": "1", "b": "2"})
    store.write("BUILD", {"c": "3"})
    assert store.read("BUILD") == {"c": "3"}


def test_write_supports_the_proposals_nested_layout(store, tmp_path):
    for name in ("KNOWLEDGE/COMPONENTS", "KNOWLEDGE/DEPENDENCIES", "KNOWLEDGE/OBSERVATIONS"):
        store.write(name, {"k": name})
    assert (tmp_path / ".arklight" / "KNOWLEDGE").is_dir()
    assert store.read("KNOWLEDGE/DEPENDENCIES") == {"k": "KNOWLEDGE/DEPENDENCIES"}


def test_write_header_is_a_comment(store, tmp_path):
    path = store.write("CONTEXT", {"git.head": "8f31c2a"}, header="derived facts")
    assert path.read_text(encoding="utf-8") == "# derived facts\ngit.head=8f31c2a\n"
    assert store.read("CONTEXT") == {"git.head": "8f31c2a"}


def test_write_round_trips_unicode_values(store):
    store.write("NOTES", {"title": "r\u00e9sum\u00e9 \u2014 \u65e5\u672c\u8a9e"})
    assert store.read("NOTES") == {"title": "r\u00e9sum\u00e9 \u2014 \u65e5\u672c\u8a9e"}


def test_write_returns_a_path_inside_the_directory(store, tmp_path):
    path = store.write("KNOWLEDGE/OBSERVATIONS", {})
    assert (tmp_path / ".arklight") in path.parents


def test_write_leaves_no_temp_files_behind(store, tmp_path):
    store.write("BUILD", {"a": "1"})
    store.write("BUILD", {"a": "2"})
    store.write("KNOWLEDGE/X", {"a": "3"})
    leftovers = [p for p in (tmp_path / ".arklight").rglob("*") if p.name.endswith(".tmp")]
    assert leftovers == []


def test_write_is_atomic_when_the_swap_fails(store, tmp_path, monkeypatch):
    store.write("BUILD", {"result": "success"})

    def boom(src, dst):
        raise OSError("simulated disk failure")

    monkeypatch.setattr("arklight.knowledge.store.os.replace", boom)
    with pytest.raises(KnowledgeStateError, match="cannot write"):
        store.write("BUILD", {"result": "failure"})
    monkeypatch.undo()

    # Old content intact, no temp file stranded.
    assert store.read("BUILD") == {"result": "success"}
    assert [p for p in (tmp_path / ".arklight").iterdir() if p.name.endswith(".tmp")] == []


def test_write_failure_on_a_readonly_checkout_is_a_knowledge_error(tmp_path, monkeypatch):
    def boom(*args, **kwargs):
        raise PermissionError("read-only file system")

    monkeypatch.setattr("arklight.knowledge.store.os.open", boom)
    with pytest.raises(KnowledgeError):
        KnowledgeStore(tmp_path).write("BUILD", {"a": "1"})


def test_write_refuses_to_overwrite_the_format_marker(store):
    with pytest.raises(ValueError, match="format marker"):
        store.write("PROJECT", {"knowledge_format": "99"})
    assert store.status() is KnowledgeStatus.ABSENT  # and it created nothing


@pytest.mark.parametrize(
    "name",
    [
        "",
        "/",
        "/etc/passwd",
        "..",
        ".",
        "../escape",
        "a/../b",
        "a//b",
        "a/",
        "/a",
        "a\\b",
        ".hidden",
        "-flag",
        "C:/x",
        "a b",
        "nul\0byte",
        "k\u00e9y",
        "BUILD\n",
        "KNOWLEDGE/COMPONENTS\n",
    ],
)
def test_write_and_read_reject_names_that_could_leave_the_directory(store, tmp_path, name):
    with pytest.raises(ValueError):
        store.write(name, {"k": "v"})
    with pytest.raises(ValueError):
        store.read(name)
    assert not (tmp_path / ".arklight").exists()


def test_non_string_names_are_a_type_error(store):
    with pytest.raises(TypeError):
        store.write(None, {"k": "v"})  # type: ignore[arg-type]
    with pytest.raises(TypeError):
        store.read(5)  # type: ignore[arg-type]


def test_write_validates_content_before_creating_anything(store, tmp_path):
    with pytest.raises(ValueError):
        store.write("BUILD", {"bad key": "v"})
    with pytest.raises(TypeError):
        store.write("BUILD", {"k": 1})  # type: ignore[dict-item]
    assert not (tmp_path / ".arklight").exists()


def test_write_oversize_is_refused_and_does_not_replace_the_old_file(store):
    store.write("BUILD", {"result": "success"})
    with pytest.raises(ValueError, match="limit"):
        store.write("BUILD", {"k": "x" * (MAX_FILE_BYTES + 1)})
    assert store.read("BUILD") == {"result": "success"}


@pytest.mark.parametrize(
    "marker", ["knowledge_format=0\n", "knowledge_format=2\n", "garbage\n"]
)
def test_write_refuses_non_current_directories_and_changes_nothing(tmp_path, marker):
    d = make_dir(tmp_path, marker)
    with pytest.raises(KnowledgeStateError):
        KnowledgeStore(tmp_path).write("BUILD", {"a": "1"})
    assert sorted(p.name for p in d.iterdir()) == ["PROJECT"]
    assert (d / "PROJECT").read_text(encoding="utf-8") == marker


def test_write_refuses_when_dot_arklight_is_a_file(tmp_path):
    (tmp_path / ".arklight").write_text("x")
    with pytest.raises(KnowledgeStateError):
        KnowledgeStore(tmp_path).write("BUILD", {"a": "1"})
    assert (tmp_path / ".arklight").read_text() == "x"


def test_write_refuses_when_a_directory_sits_where_the_file_goes(store, tmp_path):
    store.ensure()
    (tmp_path / ".arklight" / "BUILD").mkdir()
    with pytest.raises(KnowledgeStateError, match="not a regular file"):
        store.write("BUILD", {"a": "1"})


def test_write_refuses_when_a_file_sits_where_a_subdirectory_goes(store, tmp_path):
    store.write("KNOWLEDGE", {"a": "1"})  # a *file* called KNOWLEDGE
    with pytest.raises(KnowledgeStateError):
        store.write("KNOWLEDGE/COMPONENTS", {"a": "1"})
    assert store.read("KNOWLEDGE") == {"a": "1"}


@needs_symlinks
def test_write_never_follows_a_symlinked_subdirectory_out_of_the_directory(store, tmp_path):
    store.ensure()
    outside = tmp_path / "outside"
    outside.mkdir()
    os.symlink(outside, tmp_path / ".arklight" / "KNOWLEDGE")
    with pytest.raises(KnowledgeStateError):
        store.write("KNOWLEDGE/COMPONENTS", {"a": "1"})
    assert list(outside.iterdir()) == []


@needs_symlinks
def test_write_never_writes_through_a_symlinked_file(store, tmp_path):
    store.ensure()
    victim = tmp_path / "victim.txt"
    victim.write_text("precious\n")
    os.symlink(victim, tmp_path / ".arklight" / "BUILD")
    with pytest.raises(KnowledgeStateError):
        store.write("BUILD", {"a": "1"})
    assert victim.read_text() == "precious\n"


@needs_symlinks
def test_write_never_follows_a_symlinked_dot_arklight(tmp_path):
    outside = tmp_path / "outside"
    outside.mkdir()
    root = tmp_path / "project"
    root.mkdir()
    os.symlink(outside, root / ".arklight")
    with pytest.raises(KnowledgeStateError):
        KnowledgeStore(root).write("BUILD", {"a": "1"})
    assert list(outside.iterdir()) == []


def test_two_stores_on_one_project_see_each_others_writes(tmp_path):
    KnowledgeStore(tmp_path).write("BUILD", {"a": "1"})
    assert KnowledgeStore(tmp_path).read("BUILD") == {"a": "1"}


def test_accepts_str_and_pathlike_roots(tmp_path):
    assert KnowledgeStore(str(tmp_path)).path == KnowledgeStore(tmp_path).path


# --------------------------------------------------------------------------
# Regeneration: deleting `.arklight/` is always safe (proposal §14)
# --------------------------------------------------------------------------


def test_deleting_the_directory_returns_to_absent_and_it_can_be_rebuilt(store, tmp_path):
    import shutil

    store.write("BUILD", {"result": "success"})
    shutil.rmtree(tmp_path / ".arklight")
    assert store.status() is KnowledgeStatus.ABSENT
    assert store.read("BUILD") is None
    store.write("BUILD", {"result": "success"})
    assert store.status() is KnowledgeStatus.CURRENT


# --------------------------------------------------------------------------
# Stage-1 scope: nothing in the compiler depends on it
# --------------------------------------------------------------------------

SITE = """
# include <stdlib.ARKlight>

site = Site()

@site.page("/")
def home():
    return Page(Heading("Hello"), Text("Knowledge is optional."), title="Hello")
"""


def _build(tmp_path: Path, name: str) -> Path:
    project = tmp_path / name
    project.mkdir()
    (project / "site.py").write_text(SITE)
    out = project / "dist"
    build(project / "site.py", out)
    return project


def _snapshot(directory: Path) -> dict:
    return {
        str(p.relative_to(directory)): p.read_bytes()
        for p in sorted(directory.rglob("*"))
        if p.is_file()
    }


def test_a_build_does_not_create_dot_arklight(tmp_path):
    project = _build(tmp_path, "plain")
    assert not (project / ".arklight").exists()


def test_a_build_neither_changes_nor_depends_on_an_existing_dot_arklight(tmp_path):
    # Same source, one project with no `.arklight/`, one with a populated
    # directory, one with a corrupt/incompatible one: byte-identical output
    # (proposal §13, §14: knowledge never silently affects generated output,
    # and deleting it never makes a project unbuildable).
    plain = _build(tmp_path, "plain")

    populated = tmp_path / "populated"
    populated.mkdir()
    (populated / "site.py").write_text(SITE)
    KnowledgeStore(populated).write("BUILD", {"last_result": "success"})
    build(populated / "site.py", populated / "dist")

    hostile = tmp_path / "hostile"
    hostile.mkdir()
    (hostile / "site.py").write_text(SITE)
    (hostile / ".arklight").mkdir()
    (hostile / ".arklight" / "PROJECT").write_text("knowledge_format=99\nnonsense")
    build(hostile / "site.py", hostile / "dist")

    expected = _snapshot(plain / "dist")
    assert expected, "the build produced no files"
    assert _snapshot(populated / "dist") == expected
    assert _snapshot(hostile / "dist") == expected

    # ...and the build left those directories as it found them.
    assert (hostile / ".arklight" / "PROJECT").read_text() == "knowledge_format=99\nnonsense"
    assert KnowledgeStore(populated).read("BUILD") == {"last_result": "success"}


def test_no_other_arklight_module_imports_the_knowledge_package_yet():
    # Stage 1 is the foundation with nothing depending on it. When a
    # later rung (v0.072+) wires it in, this test is the one to update --
    # on purpose, in the same change.
    root = Path(arklight.__file__).parent
    pattern = re.compile(r"^\s*(?:from|import)\s+arklight\.knowledge\b|^\s*from\s+arklight\s+import\s+.*\bknowledge\b", re.M)
    offenders = [
        str(p.relative_to(root))
        for p in root.rglob("*.py")
        if "knowledge" not in p.relative_to(root).parts[:1]
        and pattern.search(p.read_text(encoding="utf-8"))
    ]
    assert offenders == []


def test_knowledge_is_not_part_of_the_authoring_vocabulary():
    assert "KnowledgeStore" not in arklight.__all__
    assert "knowledge" not in arklight.__all__
