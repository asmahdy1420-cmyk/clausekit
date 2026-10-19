"""clausekit: bilingual Arabic/English contract clause extraction."""

from __future__ import annotations

__version__ = "0.1.0"

from .classify import classify_clause
from .extractor import ContractAnalysis, analyze
from .language import detect_language
from .normalize import normalize_arabic, to_ascii_digits
from .segment import split_clauses

__all__ = [
    "ContractAnalysis",
    "__version__",
    "analyze",
    "classify_clause",
    "detect_language",
    "normalize_arabic",
    "split_clauses",
    "to_ascii_digits",
]
