"""
Verification Script: Executes all 11 required sample queries from the specification
and prints a formatted summary table of tool dispatches, chart types, insights, and guardrails.
"""

import asyncio
from src.agent.fallback_agent import RuleBasedFallbackAgent

SAMPLE_QUERIES = [
    # Single-tool queries
    "Show monthly revenue trend for 2017",
    "Which product categories generate the most revenue?",
    "Which states have the worst delivery performance?",
    "What share of payments are credit card vs boleto?",
    "Top 10 sellers by revenue in São Paulo",
    "Show review score distribution for electronics",
    # Multi-tool queries
    "Compare review scores across the top 5 categories by order volume",
    "Show monthly orders and average review score together for 2017",
    "Do sellers with faster delivery get better reviews?",
    "Show delivery delay and review score side by side by state",
    # Guardrail cases
    "What is the current stock price of Apple?",
    "iran war latest news",
]

async def main():
    agent = RuleBasedFallbackAgent()
    print("=" * 100)
    print("EXECUTING OLIST ANALYTICS SAMPLE QUERIES VERIFICATION SUITE")
    print("=" * 100)

    for i, q in enumerate(SAMPLE_QUERIES, 1):
        res = await agent.process_query(q)
        print(f"\nQUERY #{i}: \"{q}\"")
        print(f"  • Tool Called  : {res.tool_called}")
        print(f"  • Chart Type   : {res.chart_type}")
        print(f"  • Guardrail Out: {res.is_out_of_bounds}")
        print(f"  • Justification: {res.justification}")
        print(f"  • Key Insight  : {res.insight}")
        if res.assumptions:
            print(f"  • Assumptions  : {res.assumptions[0]}")
        print("-" * 100)

if __name__ == "__main__":
    asyncio.run(main())
