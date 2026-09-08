"""
Rule-Based Fallback Agent implementation (No LLM).
Uses deterministic keyword matching, parameter extraction, and direct MCP tool dispatch.
Activated when AGENT_MODE=fallback or when LLM service is unavailable/times out.
"""

import logging
from typing import Dict, Any, List
from src.agent.base import ILLMAgent, AgentResponse, out_of_bounds_response
from src.agent.extractor import extract_parameters, check_out_of_bounds
from src.agent.chart_selector import recommend_chart_and_build_config
from src.mcp_server import tools

logger = logging.getLogger(__name__)

class RuleBasedFallbackAgent(ILLMAgent):
    """
    Deterministic rule-based agent that matches keywords to MCP tools and generates chart configs.
    """

    async def process_query(self, query: str) -> AgentResponse:
        logger.info(f"RuleBasedFallbackAgent processing query: '{query}'")

        # 1. Guardrail Check: Out-of-bounds topic
        if check_out_of_bounds(query):
            return out_of_bounds_response(query, agent_mode="fallback")

        # 2. Extract Parameters & Assumptions
        params, assumptions = extract_parameters(query)
        q_lower = query.lower()

        tool_called = ""
        res_data: List[Dict[str, Any]] = []

        # 3. Keyword-to-Tool Router (Specific multi-tool patterns matched first)
        try:
            if "compare review scores across" in q_lower or "top 5 categories by order volume" in q_lower:
                tool_called = "get_multi_tool_analysis"
                raw_res = tools.query_multi_tool_join(query_type="top_categories_review_comparison")
                res_data = raw_res.get("data", [])

            elif "monthly orders and average review" in q_lower or ("monthly orders" in q_lower and "review score" in q_lower):
                tool_called = "get_multi_tool_analysis"
                raw_res = tools.query_multi_tool_join(
                    query_type="monthly_orders_and_reviews",
                    start_date=params.get("start_date"),
                    end_date=params.get("end_date")
                )
                res_data = raw_res.get("data", [])

            elif "faster delivery" in q_lower or "delivery get better reviews" in q_lower:
                tool_called = "get_multi_tool_analysis"
                raw_res = tools.query_multi_tool_join(query_type="seller_delivery_vs_reviews")
                res_data = raw_res.get("data", [])

            elif "delivery delay and review score" in q_lower or "side by side by state" in q_lower:
                tool_called = "get_multi_tool_analysis"
                raw_res = tools.query_multi_tool_join(query_type="state_delay_vs_reviews")
                res_data = raw_res.get("data", [])

            elif "monthly revenue" in q_lower or "revenue trend" in q_lower or "orders over time" in q_lower or "monthly trend" in q_lower:
                tool_called = "get_order_trends"
                raw_res = tools.query_order_trends(
                    start_date=params.get("start_date"),
                    end_date=params.get("end_date"),
                    frequency="monthly"
                )
                res_data = raw_res.get("data", [])

            elif "payment" in q_lower or "credit card" in q_lower or "boleto" in q_lower or "voucher" in q_lower:
                tool_called = "get_payment_breakdown"
                raw_res = tools.query_payment_breakdown(
                    start_date=params.get("start_date"),
                    end_date=params.get("end_date")
                )
                res_data = raw_res.get("data", [])

            elif "review score distribution" in q_lower or "score distribution" in q_lower or "reviews for" in q_lower:
                tool_called = "get_customer_reviews"
                raw_res = tools.query_customer_reviews(
                    category=params.get("category"),
                    state=params.get("state"),
                    start_date=params.get("start_date"),
                    end_date=params.get("end_date")
                )
                res_data = raw_res.get("data", [])

            elif "seller" in q_lower or "sellers in" in q_lower or "top 10 sellers" in q_lower:
                tool_called = "get_seller_performance"
                raw_res = tools.query_seller_performance(
                    state=params.get("state"),
                    limit=params.get("limit", 10),
                    sort_by=params.get("sort_by", "revenue")
                )
                res_data = raw_res.get("data", [])

            elif "delivery performance" in q_lower or "worst delivery" in q_lower or "delivery delay" in q_lower:
                tool_called = "get_delivery_performance"
                raw_res = tools.query_delivery_performance(
                    state=params.get("state"),
                    start_date=params.get("start_date"),
                    end_date=params.get("end_date")
                )
                res_data = raw_res.get("data", [])

            elif "product categories" in q_lower or "category" in q_lower or "most revenue" in q_lower:
                tool_called = "get_product_performance"
                raw_res = tools.query_product_performance(
                    category=params.get("category"),
                    limit=params.get("limit", 10),
                    sort_by=params.get("sort_by", "revenue")
                )
                res_data = raw_res.get("data", [])

            else:
                return out_of_bounds_response(query, agent_mode="fallback")

        except Exception as e:
            logger.error(f"Fallback agent execution error: {e}")
            return AgentResponse(
                query=query,
                agent_mode="fallback",
                insight="An error occurred while querying the database.",
                assumptions=assumptions,
                chart_type="none",
                justification="Execution failure.",
                chart_config={"type": "none"},
                raw_data=[],
                tool_called=tool_called,
                error_message=str(e)
            )

        # 4. Handle Empty Results
        if not res_data:
            return AgentResponse(
                query=query,
                agent_mode="fallback",
                insight="No records match the requested filter criteria.",
                assumptions=assumptions,
                chart_type="none",
                justification="No data available to construct a chart.",
                chart_config={"type": "none", "data": {}},
                raw_data=[],
                tool_called=tool_called,
                empty_result=True,
                error_message="Query produced empty results."
            )

        # 5. Build Chart Recommendation & Config
        chart_type, justification, primary_config, alt_config, insight = recommend_chart_and_build_config(
            data=res_data,
            query_intent=query,
            tool_called=tool_called
        )

        return AgentResponse(
            query=query,
            agent_mode="fallback",
            insight=insight,
            assumptions=assumptions,
            chart_type=chart_type,
            justification=justification,
            chart_config=primary_config,
            alternative_chart_config=alt_config,
            raw_data=res_data,
            tool_called=tool_called,
            tool_params=params
        )
