from arklight.ir.platform_api import PLATFORM_API_REGISTRY
from arklight.ir.schema import (
    ACTION_REGISTRY,
    BEHAVIOR_REGISTRY,
    DERIVATION_REGISTRY,
    MODIFIER_REGISTRY,
    PREDICATE_REGISTRY,
    REVEAL_REGISTRY,
    SCHEMA,
)
from arklight.search.knowledge import (
    STATE_KEYWORDS,
    SymbolFact,
    build_knowledge_base,
)
from arklight.search._tokenize import tokenize


def test_knowledge_base_contains_every_schema_entry():
    # Was equality before the search-knowledge-state-and-keywords
    # capability fix folded STATE_KEYWORDS and the closed registries
    # in too -- the kb is now a strict superset of SCHEMA, not equal
    # to it.
    kb = build_knowledge_base()
    assert set(SCHEMA) <= set(kb)


def test_knowledge_base_includes_state_keywords():
    kb = build_knowledge_base()
    for name, required_props in STATE_KEYWORDS.items():
        assert name in kb
        fact = kb[name]
        assert fact.required_props == required_props
        assert fact.allow_children is False
        assert fact.text_only_children is False


def test_knowledge_base_includes_every_closed_registry():
    kb = build_knowledge_base()
    for registry in (
        BEHAVIOR_REGISTRY,
        REVEAL_REGISTRY,
        ACTION_REGISTRY,
        MODIFIER_REGISTRY,
        DERIVATION_REGISTRY,
        PREDICATE_REGISTRY,
        PLATFORM_API_REGISTRY,
    ):
        for name in registry:
            assert name in kb, f"{name!r} missing from knowledge base"
            assert kb[name].tokens == tuple(tokenize(name))


def test_knowledge_base_state_keywords_do_not_shadow_schema():
    # No real collision exists (SCHEMA is PascalCase node names,
    # STATE_KEYWORDS happens to also be PascalCase -- "State" isn't a
    # SCHEMA entry) but the precedence rule should hold regardless.
    kb = build_knowledge_base()
    for name in STATE_KEYWORDS:
        if name in SCHEMA:
            assert kb[name].required_props == SCHEMA[name].required_props


def test_knowledge_base_facts_mirror_schema_fields():
    kb = build_knowledge_base()
    for name, spec in SCHEMA.items():
        fact = kb[name]
        assert isinstance(fact, SymbolFact)
        assert fact.name == name
        assert fact.required_props == spec.required_props
        assert fact.allow_children == spec.allow_children
        assert fact.text_only_children == spec.text_only_children


def test_knowledge_base_does_not_mutate_schema():
    before = {name: spec.required_props for name, spec in SCHEMA.items()}
    build_knowledge_base()
    after = {name: spec.required_props for name, spec in SCHEMA.items()}
    assert before == after


def test_knowledge_base_tokens_are_lowercase_and_split():
    kb = build_knowledge_base()
    assert kb["TableRow"].tokens == ("table", "row")
    assert kb["HorizontalRule"].tokens == ("horizontal", "rule")


def test_tokenize_handles_snake_and_kebab_case():
    assert tokenize("tbl_row") == ["tbl", "row"]
    assert tokenize("tbl-row") == ["tbl", "row"]
    assert tokenize("TableRow") == ["table", "row"]


def test_knowledge_base_is_rebuilt_fresh_each_call():
    kb1 = build_knowledge_base()
    kb2 = build_knowledge_base()
    assert kb1 == kb2
    assert kb1 is not kb2
