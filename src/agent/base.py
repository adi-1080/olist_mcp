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

class ILLMAgent(ABC):
    @abstractmethod
    async def process_query(self, query: str) -> AgentResponse:
        """Processes user natural language query and returns structured AgentResponse."""
        pass
