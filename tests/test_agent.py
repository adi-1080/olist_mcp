"""
Integration Tests for Agent Layer (RuleBasedFallbackAgent & ILLMAgent).
"""

import pytest
from src.agent.fallback_agent import RuleBasedFallbackAgent
from src.agent.factory import get_agent

@pytest.mark.asyncio
async def test_fallback_agent_sample_queries():
    agent = RuleBasedFallbackAgent()

    # Query 1: Monthly revenue trend
    res1 = await agent.process_query("Show monthly revenue trend for 2017")
    assert res1.chart_type == "line"
    assert res1.tool_called == "get_order_trends"
    assert len(res1.raw_data) > 0

    # Query 2: Product categories
    res2 = await agent.process_query("Which product categories generate the most revenue?")
    assert res2.chart_type == "bar"
    assert res2.tool_called == "get_product_performance"

    # Query 3: Guardrail case
    res3 = await agent.process_query("What is the current stock price of Tesla?")
    assert res3.is_out_of_bounds is True
    assert res3.chart_type == "none"

@pytest.mark.asyncio
async def test_agent_factory():
    agent = get_agent()
    assert agent is not None
    res = await agent.process_query("What share of payments are credit card vs boleto?")
    assert res.chart_type in ["doughnut", "bar", "pie"]
