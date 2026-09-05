import pytest

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
