"""
Agent Factory function with runtime mode switching support.
Instantiates and returns the appropriate ILLMAgent implementation based on runtime or environment mode.
"""

import os
import logging
from typing import Optional
from src.agent.base import ILLMAgent
from src.agent.llm_agent import LLMBackedAgent
from src.agent.fallback_agent import RuleBasedFallbackAgent
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

# Default global mode state
_CURRENT_MODE: Optional[str] = None

def _init_env():
    if os.path.exists(".env"):
        load_dotenv(".env", override=True)
    elif os.path.exists(".env.example"):
        load_dotenv(".env.example", override=True)
    else:
        load_dotenv(override=True)

def get_current_mode() -> str:
    """Returns the current active agent mode ('llm' or 'fallback')."""
    global _CURRENT_MODE
    if _CURRENT_MODE is None:
        _init_env()
        _CURRENT_MODE = os.getenv("AGENT_MODE", "fallback").lower().strip()
    return _CURRENT_MODE

def set_current_mode(mode: str) -> str:
    """Updates the active agent mode at runtime."""
    global _CURRENT_MODE
    mode_clean = mode.lower().strip()
    if mode_clean in ["llm", "fallback"]:
        _CURRENT_MODE = mode_clean
        logger.info(f"Agent mode switched to: '{_CURRENT_MODE}'")
    return get_current_mode()

def get_agent(override_mode: Optional[str] = None) -> ILLMAgent:
    """
    Returns an instance of ILLMAgent based on dynamic runtime mode or specified override.
    """
    _init_env()
    selected_mode = (override_mode or get_current_mode()).lower().strip()
    timeout = float(os.getenv("LLM_TIMEOUT", "15.0"))

    if selected_mode == "llm":
        logger.info("Initializing LLMBackedAgent (mode=llm)")
        return LLMBackedAgent(timeout_seconds=timeout)
    else:
        logger.info("Initializing RuleBasedFallbackAgent (mode=fallback)")
        return RuleBasedFallbackAgent()
