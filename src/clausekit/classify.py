"""Rule-based clause classifier for Arabic and English.

Each clause type has weighted keywords per language. A clause is scored by
summing the weights of the keywords found in its body, with title hits counted
three times because headings are the strongest signal a drafter gives. The
best type wins if it clears ``min_score``; otherwise the clause is ``other``.

Arabic keywords are written in their *normalised* form (no hamza on alef,
taa marbuta as haa) and matched as substrings, because Arabic attaches
prefixes such as و، ب، ل، ال directly to the word. English keywords are
matched on word boundaries.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from .normalize import normalize_for_matching

TERMINATION = "termination"
CONFIDENTIALITY = "confidentiality"
GOVERNING_LAW = "governing_law"
PAYMENT = "payment"
LIABILITY = "liability"
FORCE_MAJEURE = "force_majeure"
DISPUTE_RESOLUTION = "dispute_resolution"
OTHER = "other"

KEYWORDS: Dict[str, Dict[str, List[Tuple[str, float]]]] = {
    TERMINATION: {
        "en": [
            ("terminate", 2),
            ("termination", 3),
            ("terminated", 2),
            ("expiry", 1),
            ("rescind", 2),
            ("notice of termination", 2),
        ],
        "ar": [("انهاء", 3), ("فسخ", 3), ("انتهاء العقد", 2), ("انتهاء مده", 1)],
    },
    CONFIDENTIALITY: {
        "en": [
            ("confidential", 3),
            ("confidentiality", 3),
            ("non-disclosure", 3),
            ("disclose", 2),
            ("disclosure", 2),
            ("trade secret", 2),
        ],
        "ar": [("سريه", 3), ("السري", 2), ("افشاء", 3), ("الافصاح", 2)],
    },
    GOVERNING_LAW: {
        "en": [
            ("governing law", 4),
            ("governed by", 3),
            ("construed in accordance", 3),
            ("laws of", 1),
            ("applicable law", 2),
        ],
        "ar": [
            ("القانون الواجب التطبيق", 4),
            ("يخضع هذا العقد", 3),
            ("تخضع هذه الاتفاقيه", 3),
            ("وفقا لقوانين", 2),
            ("لقوانين", 1),
            ("القانون المطبق", 3),
        ],
    },
    PAYMENT: {
        "en": [
            ("payment", 3),
            ("pay", 2),
            ("invoice", 2),
            ("fees", 2),
            ("fee", 2),
            ("price", 2),
            ("remuneration", 2),
            ("instalment", 2),
            ("installment", 2),
        ],
        "ar": [
            ("دفع", 2),
            ("سداد", 3),
            ("فاتوره", 2),
            ("فواتير", 2),
            ("رسوم", 2),
            ("اتعاب", 2),
            ("المقابل المالي", 3),
            ("الدفعه", 2),
            ("اقساط", 2),
        ],
    },
    LIABILITY: {
        "en": [
            ("liability", 3),
            ("liable", 3),
            ("indemnify", 3),
            ("indemnification", 3),
            ("damages", 2),
            ("losses", 1),
        ],
        "ar": [("مسؤوليه", 3), ("مسؤول", 2), ("تعويض", 3), ("الاضرار", 2), ("الخسائر", 1)],
    },
    FORCE_MAJEURE: {
        "en": [
            ("force majeure", 5),
            ("act of god", 3),
            ("beyond its reasonable control", 3),
            ("beyond the reasonable control", 3),
            ("pandemic", 1),
        ],
        "ar": [
            ("القوه القاهره", 5),
            ("قوه قاهره", 5),
            ("خارجه عن اراده", 3),
            ("الظروف الطارئه", 2),
        ],
    },
    DISPUTE_RESOLUTION: {
        "en": [
            ("arbitration", 4),
            ("arbitral", 3),
            ("dispute", 2),
            ("disputes", 2),
            ("mediation", 3),
            ("courts", 1),
            ("amicably", 1),
        ],
        "ar": [
            ("تحكيم", 4),
            ("التحكيم", 4),
            ("نزاع", 2),
            ("منازعات", 2),
            ("خلاف", 2),
            ("المحاكم", 1),
            ("وديا", 1),
        ],
    },
}

TITLE_WEIGHT = 3.0


@dataclass(frozen=True)
class _Rule:
    clause_type: str
    pattern: re.Pattern[str]
    weight: float


def _compile_rules() -> List[_Rule]:
    rules: List[_Rule] = []
    for clause_type, langs in KEYWORDS.items():
        for keyword, weight in langs["en"]:
            pattern = re.compile(r"\b" + re.escape(keyword) + r"\b")
            rules.append(_Rule(clause_type, pattern, float(weight)))
        for keyword, weight in langs["ar"]:
            rules.append(_Rule(clause_type, re.compile(re.escape(keyword)), float(weight)))
    return rules


_RULES = _compile_rules()


@dataclass
class Classification:
    clause_type: str
    confidence: float
    scores: Dict[str, float]


def score_clause(text: str, title: Optional[str] = None) -> Dict[str, float]:
    """Return a raw score per clause type (only types with a non-zero score)."""
    body = normalize_for_matching(text)
    head = normalize_for_matching(title) if title else ""
    scores: Dict[str, float] = {}
    for rule in _RULES:
        hits = len(rule.pattern.findall(body))
        if head and rule.pattern.search(head):
            hits += TITLE_WEIGHT
        if hits:
            # Repeated keywords add evidence with diminishing returns.
            gained = rule.weight * min(hits, 3)
            scores[rule.clause_type] = scores.get(rule.clause_type, 0.0) + gained
    return scores


def classify_clause(
    text: str, title: Optional[str] = None, min_score: float = 3.0
) -> Classification:
    """Classify a clause into one of the known types, or ``other``."""
    scores = score_clause(text, title)
    if not scores:
        return Classification(OTHER, 0.0, {})
    best_type, best = max(scores.items(), key=lambda item: item[1])
    if best < min_score:
        return Classification(OTHER, 0.0, scores)
    confidence = round(best / sum(scores.values()), 3)
    return Classification(best_type, confidence, {k: round(v, 2) for k, v in scores.items()})
