import pytest
from types import SimpleNamespace

from ai import sql_generator
from ai.sql_generator import validate_select_sql


def test_validate_select_sql_allows_safe_select():
    sql = 'SELECT "order_id", "revenue" FROM "orders" WHERE "revenue" > 100 LIMIT 10'
    assert validate_select_sql(sql) == sql


def test_validate_select_sql_rejects_mutation_queries():
    with pytest.raises(ValueError, match="Only SELECT"):
        validate_select_sql('DELETE FROM "orders"')


def test_validate_select_sql_rejects_multi_statement_sql():
    with pytest.raises(ValueError, match="single read-only SELECT"):
        validate_select_sql('SELECT 1; DELETE FROM "orders"')


def test_generate_sql_retries_when_provider_returns_empty_content(monkeypatch):
    contents = iter([None, 'SELECT COUNT(*) AS "row_count" FROM "session_table"'])
    token_limits = []

    class FakeCompletions:
        def create(self, **kwargs):
            token_limits.append(kwargs["max_tokens"])
            return SimpleNamespace(choices=[SimpleNamespace(
                message=SimpleNamespace(content=next(contents)),
                finish_reason="stop",
            )])

    fake_client = SimpleNamespace(chat=SimpleNamespace(completions=FakeCompletions()))
    monkeypatch.setattr(sql_generator, "_build_schema_context", lambda *_: 'Table: "session_table"')
    monkeypatch.setattr(sql_generator, "get_groq_client", lambda: fake_client)
    monkeypatch.setattr(sql_generator, "_try_execute", lambda *_: [{"row_count": 4}])

    generated = sql_generator.generate_sql("How many rows are there?", "12345678-session", object())

    assert generated == 'SELECT COUNT(*) AS "row_count" FROM "session_table"'
    assert token_limits == [1024, 1024]


def test_generate_sql_returns_clear_error_after_repeated_empty_content(monkeypatch):
    class FakeCompletions:
        def create(self, **kwargs):
            return SimpleNamespace(choices=[SimpleNamespace(
                message=SimpleNamespace(content=None),
                finish_reason="length",
            )])

    fake_client = SimpleNamespace(chat=SimpleNamespace(completions=FakeCompletions()))
    monkeypatch.setattr(sql_generator, "_build_schema_context", lambda *_: 'Table: "session_table"')
    monkeypatch.setattr(sql_generator, "get_groq_client", lambda: fake_client)

    with pytest.raises(ValueError, match="AI provider returned no SQL after multiple attempts"):
        sql_generator.generate_sql("How many rows are there?", "12345678-session", object())
