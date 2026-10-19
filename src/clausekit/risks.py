"""Risk flags: contract patterns a reviewer should look at twice.

Each rule is a list of regular expressions over normalised text. A flag
carries the clause it came from and the matched snippet as evidence, so a
reviewer can jump straight to the wording.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List, Optional

from .normalize import normalize_with_map, original_span

HIGH = "high"
MEDIUM = "medium"


@dataclass(frozen=True)
class RiskRule:
    code: str
    severity: str
    message_en: str
    message_ar: str
    patterns: List[re.Pattern[str]]
    # A match on any of these cancels the flag (for example an explicit cap).
    exceptions: List[re.Pattern[str]]


def _rx(*patterns: str) -> List[re.Pattern[str]]:
    # Literal spaces match any whitespace run, so wording split across lines still hits.
    return [re.compile(p.replace(" ", r"\s+"), re.DOTALL) for p in patterns]


RULES: List[RiskRule] = [
    RiskRule(
        code="unlimited_liability",
        severity=HIGH,
        message_en="Liability appears to be uncapped.",
        message_ar="يبدو أن المسؤولية غير محددة بسقف.",
        patterns=_rx(
            r"\bunlimited liability\b",
            r"\bliab\w*\b.{0,60}\bwithout (?:any )?(?:limit|limitation|cap)\b",
            r"\bliable for (?:any and )?all (?:losses|damages|claims)\b",
            r"\bno (?:cap|limit) (?:on|to) (?:its |the )?liability\b",
            r"مسؤول\w* .{0,40}غير محدود",
            r"مسؤول\w* .{0,40}(?:دون|بدون|بلا) (?:اي )?(?:حد|سقف)",
            r"جميع الاضرار والخسائر .{0,30}(?:دون|بدون|بلا) (?:حد|سقف)",
        ),
        exceptions=_rx(
            r"\bshall not exceed\b",
            r"\bin no event shall\b.{0,80}\bexceed\b",
            r"لا تتجاوز",
            r"لا يتجاوز",
            r"بحد اقصي",
        ),
    ),
    RiskRule(
        code="auto_renewal",
        severity=MEDIUM,
        message_en="Contract renews automatically; diarise the notice window.",
        message_ar="يتجدد العقد تلقائياً؛ يجب تسجيل مهلة الإخطار.",
        patterns=_rx(
            r"\bautomatically (?:be )?renew",
            r"\brenew(?:s|ed)? automatically\b",
            r"\bauto-?renew",
            r"\btacit(?:ly)? renew",
            r"\bevergreen\b",
            r"تجد\w*.{0,30}تلقائي\w*",
            r"تلقائي.{0,30}تجد\w*",
        ),
        exceptions=[],
    ),
    RiskRule(
        code="unilateral_termination",
        severity=HIGH,
        message_en="One party may terminate at will or without cause.",
        message_ar="يجوز لطرف واحد إنهاء العقد بإرادته المنفردة أو دون سبب.",
        patterns=_rx(
            r"\bterminat\w*.{0,80}\b(?:at any time|for any reason|without cause|for convenience"
            r"|at its sole discretion|in its sole discretion|without (?:prior )?notice)\b",
            r"\b(?:at any time|at its sole discretion|in its sole discretion|for convenience)\b"
            r".{0,60}\bterminat",
            r"(?:فسخ|انهاء).{0,80}(?:بارادته المنفرده|بارادتها المنفرده|من جانب واحد"
            r"|دون ابداء (?:اي )?اسباب|في اي وقت|دون سابق انذار|دون اخطار)",
            r"(?:بارادته المنفرده|بارادتها المنفرده|من جانب واحد).{0,60}(?:فسخ|انهاء)",
        ),
        exceptions=[],
    ),
]


@dataclass
class RiskFlag:
    code: str
    severity: str
    message: str
    message_ar: str
    evidence: str
    clause_index: Optional[int] = None
    clause_number: Optional[str] = None


def find_risks(
    text: str, clause_index: Optional[int] = None, clause_number: Optional[str] = None
) -> List[RiskFlag]:
    """Return every risk rule that fires on ``text`` (at most one flag per rule)."""
    norm, imap = normalize_with_map(text)
    flags: List[RiskFlag] = []
    for rule in RULES:
        if any(ex.search(norm) for ex in rule.exceptions):
            continue
        for pattern in rule.patterns:
            m = pattern.search(norm)
            if m:
                flags.append(
                    RiskFlag(
                        code=rule.code,
                        severity=rule.severity,
                        message=rule.message_en,
                        message_ar=rule.message_ar,
                        evidence=" ".join(original_span(text, imap, m.start(), m.end()).split()),
                        clause_index=clause_index,
                        clause_number=clause_number,
                    )
                )
                break
    return flags
