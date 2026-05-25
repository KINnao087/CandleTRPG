"""AI host integration package."""

from .llm_client import get_llm
from .services import resolve_turn

__all__ = ["get_llm", "resolve_turn"]
