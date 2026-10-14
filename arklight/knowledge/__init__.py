"""
Project Knowledge -- `.arklight/`, ARKlight's compiler-owned,
project-local knowledge directory.

Stage 1 of 8 (`v0.071`): the directory, its format marker and safe
read/write helpers, and nothing else. Nothing in the compiler uses this
package yet. See `arklight/knowledge/store.py` for the full contract and
`docs/Implementation/PROJECT-KNOWLEDGE-ADDENDUM.md` for the ladder.

Deliberately *not* re-exported from the top-level `arklight` package:
it is compiler infrastructure, not part of the authoring vocabulary a
site file imports.
"""

from arklight.knowledge.store import (
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

__all__ = [
    "FORMAT_KEY",
    "KNOWLEDGE_DIRNAME",
    "KNOWLEDGE_FORMAT",
    "MARKER_NAME",
    "MAX_FILE_BYTES",
    "KnowledgeError",
    "KnowledgeFormatError",
    "KnowledgeStateError",
    "KnowledgeStatus",
    "KnowledgeStore",
    "parse_knowledge_text",
    "render_knowledge_text",
]
