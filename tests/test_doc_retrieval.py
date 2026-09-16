import argparse

import pytest

from arklight.cli.doc_retrieval import (
    DOC_FOLDERS,
    DocRetrievalError,
    ignored_flag_notices,
    run_retrieve_doc,
)


def _args(**overrides):
    defaults = dict(
        name=None,
        file=None,
        limit=5,
        near=None,
        accept=False,
    )
    for folder in DOC_FOLDERS:
        defaults[folder.attr] = False
    defaults.update(overrides)
    return argparse.Namespace(**defaults)


def test_bare_retrieve_doc_prints_root_readme_and_footer():
    output = run_retrieve_doc(_args())

    assert output.startswith("# ARKlight Documentation")
    assert "Go deeper with a folder flag:" in output
    assert "--foundational" in output
    assert "--file NAME to print one file" in output


def test_retrieve_doc_index_positional_is_same_as_bare():
    assert run_retrieve_doc(_args(name="index")) == run_retrieve_doc(_args())


def test_retrieve_doc_rejects_a_real_component_name():
    with pytest.raises(DocRetrievalError) as excinfo:
        run_retrieve_doc(_args(name="Picture"))
    assert "'Picture'" in str(excinfo.value)


def test_folder_flag_alone_prints_folder_readme_and_files_footer():
    output = run_retrieve_doc(_args(foundational=True))

    assert output.startswith("# Foundational")
    assert "Files in docs/Foundational/ (use --file NAME):" in output
    assert "architecture" in output
    assert "design-notes" in output


def test_every_folder_flag_resolves_without_error():
    for folder in DOC_FOLDERS:
        output = run_retrieve_doc(_args(**{folder.attr: True}))
        assert f"Files in docs/{folder.path}/" in output


def test_folder_plus_file_appends_full_file_contents():
    output = run_retrieve_doc(_args(foundational=True, file="architecture"))

    assert output.startswith("# Foundational")
    assert "=" * 80 in output
    assert "docs/Foundational/ARCHITECTURE.md" in output
    # No "go deeper" footer once a specific file has been printed.
    assert "Files in docs/Foundational/" not in output


def test_file_matching_is_case_and_punctuation_insensitive():
    canonical = run_retrieve_doc(_args(foundational=True, file="architecture"))
    for variant in ("Architecture", "ARCHITECTURE", "architecture "):
        assert run_retrieve_doc(_args(foundational=True, file=variant)) == canonical


def test_file_matching_normalizes_hyphens_underscores_and_spaces():
    canonical = run_retrieve_doc(_args(foundational=True, file="user-defined-components"))
    for variant in ("user_defined_components", "user defined components", "User-Defined-Components"):
        assert run_retrieve_doc(_args(foundational=True, file=variant)) == canonical


def test_unmatched_file_suggests_close_matches():
    with pytest.raises(DocRetrievalError) as excinfo:
        run_retrieve_doc(_args(foundational=True, file="architectur"))
    assert "Did you mean" in str(excinfo.value)
    assert "architecture" in str(excinfo.value)


def test_completely_unrelated_file_says_nothing_close():
    with pytest.raises(DocRetrievalError) as excinfo:
        run_retrieve_doc(_args(foundational=True, file="zzzznotarealdocatall"))
    assert "nothing close enough to suggest" in str(excinfo.value)


def test_file_without_folder_flag_is_a_hard_error():
    with pytest.raises(DocRetrievalError) as excinfo:
        run_retrieve_doc(_args(file="architecture"))
    message = str(excinfo.value)
    assert "--file requires a folder flag" in message
    assert "ARCHITECTURE.md lives in docs/Foundational/" in message
    assert "--foundational --file architecture" in message


def test_file_without_folder_flag_and_no_match_is_generic():
    with pytest.raises(DocRetrievalError) as excinfo:
        run_retrieve_doc(_args(file="zzzznotarealdocatall"))
    message = str(excinfo.value)
    assert "--file requires a folder flag" in message
    assert "lives in" not in message


def test_ignored_flag_notices_empty_for_defaults():
    assert ignored_flag_notices(_args()) == []


def test_ignored_flag_notices_flag_near_and_accept():
    notices = ignored_flag_notices(_args(near="Heading", accept=True))
    assert any("--near" in notice for notice in notices)
    assert any("--accept" in notice for notice in notices)


def test_ignored_flag_notices_flag_non_default_limit():
    notices = ignored_flag_notices(_args(limit=10))
    assert any("--limit" in notice for notice in notices)


def test_version_history_folder_parses_despite_different_header_column():
    output = run_retrieve_doc(_args(version_history=True))
    assert "v0.001" in output
    assert "v0.063" in output
