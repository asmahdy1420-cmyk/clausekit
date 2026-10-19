"""Split contract text into numbered clauses.

Detection runs on a normalised *probe* of each line (ASCII digits, no
diacritics, unified Arabic letters) while the stored text keeps the original
spelling. A per-character index map links the two so the heading title can be
sliced from the raw line.

Recognised headings:

* English keyword headings: ``Article 5``, ``Clause 3.1``, ``Section IV``
* Arabic keyword headings: ``المادة (٥)``, ``البند 3``, ``المادة الخامسة``,
  ``البند الأول``, ``الفقرة الثانية عشرة``
* Plain numbering: ``1.``, ``2)``, ``3-``, ``1.2``

When a document uses keyword headings, plain numbered lines inside them are
kept as part of the parent clause (``5.1`` under ``Article 5``). Otherwise plain
numbered lines start clauses up to ``split_level`` depth.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

from .normalize import normalize_with_map

_UNITS = [
    ("الاول", "الاولي"),
    ("الثاني", "الثانيه"),
    ("الثالث", "الثالثه"),
    ("الرابع", "الرابعه"),
    ("الخامس", "الخامسه"),
    ("السادس", "السادسه"),
    ("السابع", "السابعه"),
    ("الثامن", "الثامنه"),
    ("التاسع", "التاسعه"),
    ("العاشر", "العاشره"),
]


def _build_ordinals() -> dict:
    ordinals = {}
    for value, forms in enumerate(_UNITS, start=1):
        for form in forms:
            ordinals[form] = value
    for value, (masc, fem) in enumerate(_UNITS[:9], start=11):
        if value == 11:
            masc, fem = "الحادي", "الحاديه"
        ordinals[f"{masc} عشر"] = value
        ordinals[f"{fem} عشره"] = value
    ordinals["العشرون"] = 20
    ordinals["العشرين"] = 20
    return ordinals


ARABIC_ORDINALS = _build_ordinals()
_ORDINAL_ALT = "|".join(sorted(ARABIC_ORDINALS, key=len, reverse=True))

_AR_KEYWORD = r"(?P<kw>الماده|البند|الفقره)"
_AR_NUMERIC_RE = re.compile(_AR_KEYWORD + r"\s*[(\[]?\s*(?P<num>\d+(?:\.\d+)*)\s*[)\]]?")
_AR_ORDINAL_RE = re.compile(_AR_KEYWORD + r"\s+(?P<ord>" + _ORDINAL_ALT + r")(?!\w)")
_EN_KEYWORD_RE = re.compile(
    r"(?P<kw>article|clause|section)\s+(?P<num>\d+(?:\.\d+)*|[ivxlc]+)(?!\w)",
    re.IGNORECASE,
)
_PLAIN_RE = re.compile(r"(?P<num>\d{1,3}(?:\.\d{1,3})*)(?P<sep>[.)\-])?\s+(?=\S)")
_TITLE_STRIP = " \t:：-–—.)،"

_ROMAN = {"i": 1, "v": 5, "x": 10, "l": 50, "c": 100}


@dataclass
class RawClause:
    """A clause as found by the segmenter, before analysis."""

    index: int
    number: Optional[str]
    heading: Optional[str]
    title: Optional[str]
    level: int
    text: str
    kind: str = "clause"  # "preamble" or "clause"
    lines: List[str] = field(default_factory=list, repr=False)


@dataclass
class _Heading:
    number: str
    level: int
    style: str  # "keyword" or "plain"
    title: Optional[str]
    rest: str


def _roman_to_int(value: str) -> int:
    total, prev = 0, 0
    for ch in reversed(value.lower()):
        current = _ROMAN[ch]
        total = total - current if current < prev else total + current
        prev = max(prev, current)
    return total


def _split_title(rest: str) -> Tuple[Optional[str], str]:
    """Decide whether the remainder of a heading line is a title or body text."""
    rest = rest.strip().lstrip(_TITLE_STRIP).strip()
    if not rest:
        return None, ""
    if len(rest) <= 80 and not rest.endswith((".", "؛", ";")):
        return rest, ""
    return None, rest


def _match_heading(line: str) -> Optional[_Heading]:
    stripped = line.strip()
    if not stripped:
        return None
    probe, index_map = normalize_with_map(stripped)

    def raw_rest(end: int) -> str:
        if end >= len(probe):
            return ""
        return stripped[index_map[end] :]

    m = _AR_ORDINAL_RE.match(probe)
    if m:
        title, body = _split_title(raw_rest(m.end()))
        return _Heading(str(ARABIC_ORDINALS[m.group("ord")]), 1, "keyword", title, body)

    for regex in (_AR_NUMERIC_RE, _EN_KEYWORD_RE):
        m = regex.match(probe)
        if m:
            num = m.group("num")
            if num.isalpha():
                num = str(_roman_to_int(num))
            title, body = _split_title(raw_rest(m.end()))
            return _Heading(num, num.count(".") + 1, "keyword", title, body)

    m = _PLAIN_RE.match(probe)
    if m and (m.group("sep") or "." in m.group("num")):
        num = m.group("num")
        title, body = _split_title(raw_rest(m.end()))
        return _Heading(num, num.count(".") + 1, "plain", title, body)
    return None


def split_clauses(text: str, split_level: int = 1) -> List[RawClause]:
    """Split ``text`` into a preamble (if any) followed by clauses."""
    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    headings = [_match_heading(line) for line in lines]
    has_keyword = any(h is not None and h.style == "keyword" for h in headings)

    def starts_clause(h: Optional[_Heading]) -> bool:
        if h is None:
            return False
        if h.style == "keyword":
            return True
        return not has_keyword and h.level <= split_level

    clauses: List[RawClause] = []
    current: Optional[RawClause] = None
    preamble_lines: List[str] = []

    for line, heading in zip(lines, headings):
        if starts_clause(heading):
            assert heading is not None
            current = RawClause(
                index=len(clauses),
                number=heading.number,
                heading=line.strip(),
                title=heading.title,
                level=heading.level,
                text="",
            )
            if heading.rest:
                current.lines.append(heading.rest)
            clauses.append(current)
        elif current is None:
            preamble_lines.append(line)
        else:
            current.lines.append(line)

    for clause in clauses:
        clause.text = "\n".join(clause.lines).strip()

    preamble = "\n".join(preamble_lines).strip()
    result: List[RawClause] = []
    if preamble:
        result.append(
            RawClause(
                index=0,
                number=None,
                heading=None,
                title=None,
                level=0,
                text=preamble,
                kind="preamble",
            )
        )
    result.extend(clauses)
    for i, clause in enumerate(result):
        clause.index = i
    return result
