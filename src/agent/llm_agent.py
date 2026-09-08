"""
LLM-backed Agent implementation with native tool calling and configurable timeout.
If LLM API key is missing or call times out / errors, seamlessly delegates to RuleBasedFallbackAgent.
"""

import os
import json
import asyncio
import logging
from typing import Dict, Any, Optional
from src.agent.base import ILLMAgent, AgentResponse, out_of_bounds_response
from src.agent.fallback_agent import RuleBasedFallbackAgent
from src.agent.extractor import extract_parameters, check_out_of_bounds
from src.agent.chart_selector import recommend_chart_and_build_config
from src.mcp_server import tools

logger = logging.getLogger(__name__)

# List of tool declarations for OpenAI & Groq tool-calling API
TOOL_DECLARATIONS = [
    {
        "type": "function",
        "function": {
            "name": "get_order_trends",
            "description": "Query order volume, revenue, and delivery performance over time.",
            "parameters": {
                "type": "object",
                "properties": {
                    "start_date": {"type": ["string", "null"], "description": "Start date YYYY-MM-DD"},
                    "end_date": {"type": ["string", "null"], "description": "End date YYYY-MM-DD"},
                    "frequency": {"type": "string", "enum": ["monthly", "weekly"]}
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_product_performance",
            "description": "Query product/category revenue, review scores, and freight.",
            "parameters": {
                "type": "object",
                "properties": {
                    "category": {"type": ["string", "null"]},
                    "limit": {"type": "integer"},
                    "sort_by": {"type": "string", "enum": ["revenue", "review_score", "volume"]}
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_seller_performance",
            "description": "Query seller revenue, ratings, delivery speed, and location.",
            "parameters": {
                "type": "object",
                "properties": {
                    "state": {"type": ["string", "null"]},
                    "limit": {"type": "integer"},
                    "sort_by": {"type": "string", "enum": ["revenue", "review_score", "delivery_speed"]}
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_customer_reviews",
            "description": "Query customer review score distributions (1-5 stars) and response times.",
            "parameters": {
                "type": "object",
                "properties": {
                    "category": {"type": ["string", "null"]},
                    "state": {"type": ["string", "null"]},
                    "start_date": {"type": ["string", "null"]},
                    "end_date": {"type": ["string", "null"]}
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_payment_breakdown",
            "description": "Query payment method shares (credit card vs boleto vs voucher), installments, and value.",
            "parameters": {
                "type": "object",
                "properties": {
                    "start_date": {"type": ["string", "null"]},
                    "end_date": {"type": ["string", "null"]}
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_delivery_performance",
            "description": "Query delivery performance: estimated vs actual dates, delay days, and on-time rates by state.",
            "parameters": {
                "type": "object",
                "properties": {
                    "state": {"type": ["string", "null"]},
                    "start_date": {"type": ["string", "null"]},
                    "end_date": {"type": ["string", "null"]}
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_multi_tool_analysis",
            "description": "Perform joint multi-domain analysis across products, sellers, reviews, and delivery speed.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query_type": {
                        "type": "string",
                        "enum": [
                            "top_categories_review_comparison",
                            "monthly_orders_and_reviews",
                            "seller_delivery_vs_reviews",
                            "state_delay_vs_reviews"
                        ]
                    },
                    "start_date": {"type": ["string", "null"]},
                    "end_date": {"type": ["string", "null"]}
                },
                "required": ["query_type"]
            }
        }
    }
]

class LLMBackedAgent(ILLMAgent):
    """
    LLM-backed Agent using native tool calling with configurable timeout fallback.
    """

    def __init__(self, timeout_seconds: float = 15.0):
        self.timeout_seconds = timeout_seconds
        self.fallback_agent = RuleBasedFallbackAgent()

    async def _call_llm_with_timeout(self, query: str) -> Optional[Dict[str, Any]]:
        """Calls Groq or OpenAI API with timeout using tool calling."""
        from dotenv import load_dotenv
        if os.path.exists(".env"):
            load_dotenv(".env", override=True)
        elif os.path.exists(".env.example"):
            load_dotenv(".env.example", override=True)

        groq_key = os.getenv("GROQ_API_KEY")
        openai_key = os.getenv("OPENAI_API_KEY")
        api_key = groq_key or openai_key

        if not api_key:
            logger.warning("GROQ_API_KEY or OPENAI_API_KEY not found. Falling back to RuleBasedFallbackAgent.")
            return None

        try:
            from openai import AsyncOpenAI

            if groq_key:
                base_url = os.getenv("GROQ_BASE_URL", "https://api.groq.com/openai/v1")
                client = AsyncOpenAI(api_key=groq_key, base_url=base_url)
                candidate_models = [os.getenv("LLM_MODEL"), "openai/gpt-oss-120b", "openai/gpt-oss-20b", "llama-3.3-70b-versatile"]
            else:
                base_url = os.getenv("OPENAI_BASE_URL")
                client = AsyncOpenAI(api_key=openai_key, base_url=base_url) if base_url else AsyncOpenAI(api_key=openai_key)
                candidate_models = [os.getenv("LLM_MODEL"), "gpt-4o-mini", "gpt-4o"]

            # Filter unique non-None candidate models
            models_to_try = []
            for m in candidate_models:
                if m and m not in models_to_try:
                    models_to_try.append(m)

            messages = [
                {
                    "role": "system",
                    "content": "You are an E-Commerce Sales Analytics AI assistant. Select the appropriate tool to query the Brazilian Olist dataset."
                },
                {"role": "user", "content": query}
            ]

            response = None
            last_error = None
            for model_name in models_to_try:
                try:
                    logger.info(f"Sending LLM query to API using model '{model_name}'...")
                    response = await asyncio.wait_for(
                        client.chat.completions.create(
                            model=model_name,
                            messages=messages,
                            tools=TOOL_DECLARATIONS,
                            tool_choice="auto",
                            temperature=0.0
                        ),
                        timeout=self.timeout_seconds
                    )
                    if response:
                        break
                except Exception as model_err:
                    last_error = model_err
                    logger.warning(f"Model '{model_name}' failed: {model_err}. Trying next candidate...")

            if not response:
                if last_error:
                    logger.error(f"All LLM model candidates failed. Last error: {last_error}")
                return None

            msg = response.choices[0].message
            if msg.tool_calls:
                t_call = msg.tool_calls[0]
                raw_args = json.loads(t_call.function.arguments or "{}")
                # Filter out None values from tool arguments
                cleaned_args = {k: v for k, v in raw_args.items() if v is not None}
                return {
                    "name": t_call.function.name,
                    "args": cleaned_args
                }
        except asyncio.TimeoutError:
            logger.warning(f"LLM call timed out after {self.timeout_seconds}s. Delegating to Fallback Agent.")
        except Exception as e:
            logger.warning(f"LLM call failed: {e}. Delegating to Fallback Agent.")

        return None

    async def process_query(self, query: str) -> AgentResponse:
        # 1. Guardrail Check — never dispatch tools for off-domain questions
        if check_out_of_bounds(query):
            res = out_of_bounds_response(query, agent_mode="llm")
            return res

        # 2. Attempt LLM tool choice with timeout
        llm_decision = await self._call_llm_with_timeout(query)

        if not llm_decision:
            # Fallback to rule-based agent seamlessly
            res = await self.fallback_agent.process_query(query)
            res.agent_mode = "llm (fallback triggered)"
            return res

        tool_name = llm_decision["name"]
        tool_args = llm_decision["args"]
        params, assumptions = extract_parameters(query)

        # Merge extracted params with LLM args
        merged_params = {**params, **tool_args}

        # 3. Execute chosen tool
        res_data = []
        try:
            if tool_name == "get_order_trends":
                raw_res = tools.query_order_trends(**merged_params)
            elif tool_name == "get_product_performance":
                raw_res = tools.query_product_performance(**merged_params)
            elif tool_name == "get_seller_performance":
                raw_res = tools.query_seller_performance(**merged_params)
            elif tool_name == "get_customer_reviews":
                raw_res = tools.query_customer_reviews(**merged_params)
            elif tool_name == "get_payment_breakdown":
                raw_res = tools.query_payment_breakdown(**merged_params)
            elif tool_name == "get_delivery_performance":
                raw_res = tools.query_delivery_performance(**merged_params)
            elif tool_name == "get_multi_tool_analysis":
                raw_res = tools.query_multi_tool_join(**merged_params)
            else:
                return out_of_bounds_response(query, agent_mode="llm")

            res_data = raw_res.get("data", [])
        except Exception as e:
            logger.error(f"Tool execution error in LLM agent: {e}")
            res = await self.fallback_agent.process_query(query)
            res.agent_mode = "llm (tool error fallback)"
            return res

        if not res_data:
            return AgentResponse(
                query=query,
                agent_mode="llm",
                insight="No records match the query parameters.",
                assumptions=assumptions,
                chart_type="none",
                justification="No data returned.",
                chart_config={"type": "none"},
                raw_data=[],
                tool_called=tool_name,
                empty_result=True,
                error_message="Query produced empty results."
            )

        # 4. Recommend Chart & Config
        chart_type, justification, primary_config, alt_config, insight = recommend_chart_and_build_config(
            data=res_data,
            query_intent=query,
            tool_called=tool_name
        )

        return AgentResponse(
            query=query,
            agent_mode="llm",
            insight=insight,
            assumptions=assumptions,
            chart_type=chart_type,
            justification=justification,
            chart_config=primary_config,
            alternative_chart_config=alt_config,
            raw_data=res_data,
            tool_called=tool_name,
            tool_params=merged_params
        )
