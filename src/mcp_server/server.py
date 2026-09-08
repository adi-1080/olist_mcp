"""
MCP Server implementation using python mcp package (FastMCP).
Exposes dataset tools over stdio/HTTP JSON-RPC protocol.
"""

import json
import logging
from typing import Optional
from mcp.server.fastmcp import FastMCP
from src.mcp_server import tools

logger = logging.getLogger(__name__)

mcp = FastMCP("Olist E-Commerce Analytics MCP Server")

@mcp.tool()
def get_order_trends(start_date: Optional[str] = None, end_date: Optional[str] = None, frequency: str = "monthly") -> str:
    """Query order revenue, volume, and delivery performance trends over time."""
    res = tools.query_order_trends(start_date=start_date, end_date=end_date, frequency=frequency)
    return json.dumps(res)

@mcp.tool()
def get_product_performance(category: Optional[str] = None, limit: int = 10, sort_by: str = "revenue") -> str:
    """Query revenue, review score, freight, and volume by product category."""
    res = tools.query_product_performance(category=category, limit=limit, sort_by=sort_by)
    return json.dumps(res)

@mcp.tool()
def get_seller_performance(state: Optional[str] = None, limit: int = 10, sort_by: str = "revenue") -> str:
    """Query seller ratings, revenue, delivery speed, and location."""
    res = tools.query_seller_performance(state=state, limit=limit, sort_by=sort_by)
    return json.dumps(res)

@mcp.tool()
def get_customer_reviews(category: Optional[str] = None, state: Optional[str] = None, start_date: Optional[str] = None, end_date: Optional[str] = None) -> str:
    """Query customer review score distributions (1-5 stars) and response times."""
    res = tools.query_customer_reviews(category=category, state=state, start_date=start_date, end_date=end_date)
    return json.dumps(res)

@mcp.tool()
def get_payment_breakdown(start_date: Optional[str] = None, end_date: Optional[str] = None) -> str:
    """Query payment method shares (credit card vs boleto vs voucher), installments, and value."""
    res = tools.query_payment_breakdown(start_date=start_date, end_date=end_date)
    return json.dumps(res)

@mcp.tool()
def get_delivery_performance(state: Optional[str] = None, start_date: Optional[str] = None, end_date: Optional[str] = None) -> str:
    """Query delivery performance: estimated vs actual delivery dates, delay days, and on-time rates."""
    res = tools.query_delivery_performance(state=state, start_date=start_date, end_date=end_date)
    return json.dumps(res)

@mcp.tool()
def get_multi_tool_analysis(query_type: str, start_date: Optional[str] = None, end_date: Optional[str] = None) -> str:
    """Perform joint multi-domain analysis across products, sellers, reviews, and delivery speed."""
    res = tools.query_multi_tool_join(query_type=query_type, start_date=start_date, end_date=end_date)
    return json.dumps(res)

if __name__ == "__main__":
    mcp.run()
