"""
Abstract Base Class ILLMAgent and Pydantic response data schemas.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

class ChartConfig(BaseModel):
    chart_type: str
    justification: str
    config: Dict[str, Any]

class AgentResponse(BaseModel):
    query: str
    agent_mode: str
    insight: str
    assumptions: List[str] = Field(default_factory=list)
    chart_type: str
    justification: str
    chart_config: Dict[str, Any]
    alternative_chart_config: Optional[Dict[str, Any]] = None
    raw_data: List[Dict[str, Any]] = Field(default_factory=list)
    tool_called: str = ""
    tool_params: Dict[str, Any] = Field(default_factory=dict)
    is_out_of_bounds: bool = False
    empty_result: bool = False
    error_message: Optional[str] = None

def out_of_bounds_response(query: str, agent_mode: str) -> AgentResponse:
    """Structured guardrail payload: no chart, clear analyst-facing message."""
    return AgentResponse(
        query=query,
        agent_mode=agent_mode,
        insight=(
            "This question is outside the Brazilian E-Commerce dataset. "
            "Ask about orders, revenue, products, sellers, reviews, payments, or delivery."
        ),
        assumptions=["Guardrail: query does not map to Olist analytics tables."],
        chart_type="none",
        justification="No chart is generated for topics the dataset does not contain.",
        chart_config={"type": "none", "data": {}},
        raw_data=[],
        tool_called="none",
        is_out_of_bounds=True,
        error_message=(
            "The Olist dataset only covers 2016–2018 Brazilian e-commerce orders. "
            "It does not contain news, geopolitics, stock prices, weather, or demographics."
        ),
    )


class ILLMAgent(ABC):
    @abstractmethod
    async def process_query(self, query: str) -> AgentResponse:
        """Processes user natural language query and returns structured AgentResponse."""
        raise NotImplementedError
