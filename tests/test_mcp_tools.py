"""
Unit & Integration Tests for MCP Tools layer.
"""

import pytest
from src.mcp_server import tools
from src.database.loader import build_sqlite_database, DB_PATH

@pytest.fixture(autouse=True)
def ensure_db():
    if not DB_PATH.exists():
        build_sqlite_database()

def test_query_order_trends():
    res = tools.query_order_trends(start_date="2017-01-01", end_date="2017-12-31")
    assert res["status"] == "success"
    assert len(res["data"]) > 0
    assert "period" in res["data"][0]
    assert "total_revenue" in res["data"][0]

def test_query_product_performance():
    res = tools.query_product_performance(limit=5, sort_by="revenue")
    assert res["status"] == "success"
    assert len(res["data"]) <= 5
    assert "category_english" in res["data"][0]
    assert "total_revenue" in res["data"][0]

def test_query_seller_performance():
    res = tools.query_seller_performance(state="SP", limit=5)
    assert res["status"] == "success"
    assert len(res["data"]) > 0
    assert res["data"][0]["seller_state"] == "SP"

def test_query_customer_reviews():
    res = tools.query_customer_reviews()
    assert res["status"] == "success"
    assert "summary" in res
    assert res["summary"]["total_reviews"] > 0

def test_query_payment_breakdown():
    res = tools.query_payment_breakdown()
    assert res["status"] == "success"
    assert len(res["data"]) > 0
    assert "payment_type" in res["data"][0]

def test_query_delivery_performance():
    res = tools.query_delivery_performance(state="SP")
    assert res["status"] == "success"
    assert len(res["data"]) > 0
    assert "on_time_rate_pct" in res["data"][0]

def test_query_multi_tool_join():
    res = tools.query_multi_tool_join(query_type="top_categories_review_comparison")
    assert res["status"] == "success"
    assert len(res["data"]) > 0
    assert "category" in res["data"][0]
    assert "avg_review_score" in res["data"][0]
