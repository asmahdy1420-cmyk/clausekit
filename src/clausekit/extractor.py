"""The pipeline: segment -> detect language -> classify -> extract -> flag."""

from __future__ import annotations

from collections import Counter
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional

from . import __version__
from .classify import classify_clause
from .entities import Party, extract_entities, extract_parties
from .language import detect_language
from .risks import RiskFlag, find_risks
from .segment import split_clauses


@dataclass
class Clause:
    index: int
    kind: str
    number: Optional[str]
    heading: Optional[str]
    title: Optional[str]
    level: int
    language: str
    type: str
    confidence: float
    type_scores: Dict[str, float]
    text: str
    entities: Dict[str, list]
    risks: List[RiskFlag] = field(default_factory=list)


@dataclass
class ContractAnalysis:
    language: str
    parties: List[Party]
    clauses: List[Clause]
    risks: List[RiskFlag]
    summary: Dict[str, Any]
    version: str = __version__

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def analyze(text: str, split_level: int = 1, min_score: float = 3.0) -> ContractAnalysis:
    """Analyse a contract and return a structured, JSON-serialisable result."""
    raw_clauses = split_clauses(text, split_level=split_level)
    clauses: List[Clause] = []
    parties: List[Party] = []

    for raw in raw_clauses:
        if raw.kind == "preamble":
            parties = extract_parties(raw.text)
            ctype, confidence, scores = "preamble", 1.0, {}
        else:
            result = classify_clause(raw.text, raw.title, min_score=min_score)
            ctype, confidence, scores = result.clause_type, result.confidence, result.scores
        full_text = "\n".join(part for part in (raw.title, raw.text) if part)
        clauses.append(
            Clause(
                index=raw.index,
                kind=raw.kind,
                number=raw.number,
                heading=raw.heading,
                title=raw.title,
                level=raw.level,
                language=detect_language(full_text),
                type=ctype,
                confidence=confidence,
                type_scores=scores,
                text=raw.text,
                entities=extract_entities(raw.text),
                risks=[]
                if raw.kind == "preamble"
                else find_risks(full_text, raw.index, raw.number),
            )
        )

    all_risks = [flag for clause in clauses for flag in clause.risks]
    types = Counter(c.type for c in clauses if c.kind == "clause")
    summary = {
        "clause_count": sum(1 for c in clauses if c.kind == "clause"),
        "types": dict(sorted(types.items())),
        "risk_count": len(all_risks),
        "high_risk_count": sum(1 for r in all_risks if r.severity == "high"),
    }
    return ContractAnalysis(
        language=detect_language(text),
        parties=parties,
        clauses=clauses,
        risks=all_risks,
        summary=summary,
    )
