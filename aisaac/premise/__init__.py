"""Premise discovery engine — identifies which assumptions to question."""

from .reframer import PremiseReframer, PATTERNS, BreakthroughPattern
from .premise_ranker import PremiseRanker, RankingResult
from .report_generator import PremiseReportGenerator

__all__ = [
    "PremiseReframer",
    "PremiseRanker",
    "PremiseReportGenerator",
    "RankingResult",
    "PATTERNS",
    "BreakthroughPattern",
]
