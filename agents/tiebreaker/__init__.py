"""
Tiebreaker Agent

Resolves scenarios where a combo matches multiple brands.
"""

from .tools import (
    resolve_multi_match,
    analyze_narrative_similarity,
    compare_mccid_alignment,
    calculate_match_confidence
)
from .agentcore_handler import tiebreaker_agent, handler

__all__ = [
    "resolve_multi_match",
    "analyze_narrative_similarity",
    "compare_mccid_alignment",
    "calculate_match_confidence",
    "tiebreaker_agent",
    "handler"
]
