"""Entity extraction: dates, monetary amounts, durations and parties.

All matching runs on normalised text, so ``١٥/٠٣/٢٠٢٦`` and ``15/03/2026`` are
the same date and ``ريال قطري`` matches with or without diacritics.
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Dict, List, Optional, Tuple

from .normalize import (
    normalize_with_map,
    original_span,
    strip_diacritics,
    to_ascii_digits,
)

# --------------------------------------------------------------------------- dates

_EN_MONTHS = {
    name: i
    for i, names in enumerate(
        [
            ("january", "jan"),
            ("february", "feb"),
            ("march", "mar"),
            ("april", "apr"),
            ("may",),
            ("june", "jun"),
            ("july", "jul"),
            ("august", "aug"),
            ("september", "sep", "sept"),
            ("october", "oct"),
            ("november", "nov"),
            ("december", "dec"),
        ],
        start=1,
    )
    for name in names
}
# Gulf (Gregorian loan-word) month names and Levantine names, normalised.
_AR_MONTHS = {
    "يناير": 1,
    "فبراير": 2,
    "مارس": 3,
    "ابريل": 4,
    "مايو": 5,
    "يونيو": 6,
    "يوليو": 7,
    "اغسطس": 8,
    "سبتمبر": 9,
    "اكتوبر": 10,
    "نوفمبر": 11,
    "ديسمبر": 12,
    "كانون الثاني": 1,
    "شباط": 2,
    "اذار": 3,
    "نيسان": 4,
    "ايار": 5,
    "حزيران": 6,
    "تموز": 7,
    "اب": 8,
    "ايلول": 9,
    "تشرين الاول": 10,
    "تشرين الثاني": 11,
    "كانون الاول": 12,
}


def _alt(names) -> str:
    return "|".join(sorted(names, key=len, reverse=True))


_NUMERIC_DMY_RE = re.compile(r"(?<!\d)(\d{1,2})[/.\-](\d{1,2})[/.\-](\d{4})(?!\d)")
_ISO_RE = re.compile(r"(?<!\d)(\d{4})-(\d{2})-(\d{2})(?!\d)")
_EN_DMY_RE = re.compile(
    r"\b(\d{1,2})(?:st|nd|rd|th)?\s+(?:of\s+)?(" + _alt(_EN_MONTHS) + r")\.?,?\s+(\d{4})\b"
)
_EN_MDY_RE = re.compile(
    r"\b(" + _alt(_EN_MONTHS) + r")\.?\s+(\d{1,2})(?:st|nd|rd|th)?,?\s+(\d{4})\b"
)
_AR_DMY_RE = re.compile(
    r"(?<!\d)(\d{1,2})\s+(?:من\s+)?(?:شهر\s+)?("
    + _alt(_AR_MONTHS)
    + r")\s+(?:لعام\s+|عام\s+|سنه\s+)?(\d{4})(?!\d)"
)

# --------------------------------------------------------------------------- money

# Maps a normalised currency token to its ISO 4217 code.
CURRENCY_ALIASES: Dict[str, str] = {
    "qar": "QAR",
    "qr": "QAR",
    "qatari riyals": "QAR",
    "qatari riyal": "QAR",
    "ريال قطري": "QAR",
    "ريالا قطريا": "QAR",
    "ر.ق": "QAR",
    "aed": "AED",
    "dirhams": "AED",
    "uae dirhams": "AED",
    "emirati dirhams": "AED",
    "درهم اماراتي": "AED",
    "درهما اماراتيا": "AED",
    "درهم": "AED",
    "د.ا": "AED",
    "sar": "SAR",
    "saudi riyals": "SAR",
    "saudi riyal": "SAR",
    "ريال سعودي": "SAR",
    "ريالا سعوديا": "SAR",
    "ر.س": "SAR",
    "bhd": "BHD",
    "bahraini dinars": "BHD",
    "bahraini dinar": "BHD",
    "دينار بحريني": "BHD",
    "دينارا بحرينيا": "BHD",
    "د.ب": "BHD",
    "usd": "USD",
    "us$": "USD",
    "$": "USD",
    "us dollars": "USD",
    "dollars": "USD",
    "دولار امريكي": "USD",
    "دولارا امريكيا": "USD",
    "دولار": "USD",
}
_CUR_ALT = "|".join(re.escape(c) for c in sorted(CURRENCY_ALIASES, key=len, reverse=True))
_NUM = r"\d{1,3}(?:,\d{3})+(?:\.\d+)?|\d+(?:\.\d+)?"
_AMOUNT_BEFORE_RE = re.compile(r"(?<![\w$])(" + _CUR_ALT + r")\s?(" + _NUM + r")(?!\d)")
_AMOUNT_AFTER_RE = re.compile(r"(?<![\d,.])(" + _NUM + r")\s?(" + _CUR_ALT + r")(?!\w)")

# --------------------------------------------------------------------------- durations

_EN_UNITS = {
    "day": "day",
    "days": "day",
    "business day": "business_day",
    "business days": "business_day",
    "working days": "business_day",
    "week": "week",
    "weeks": "week",
    "month": "month",
    "months": "month",
    "year": "year",
    "years": "year",
}
_AR_UNITS = {
    "يوم": "day",
    "يوما": "day",
    "ايام": "day",
    "يوم عمل": "business_day",
    "ايام عمل": "business_day",
    "يوما عمل": "business_day",
    "اسبوع": "week",
    "اسبوعا": "week",
    "اسابيع": "week",
    "شهر": "month",
    "شهرا": "month",
    "اشهر": "month",
    "شهور": "month",
    "سنه": "year",
    "سنوات": "year",
    "عام": "year",
    "عاما": "year",
    "اعوام": "year",
}
_AR_DUALS = {
    "يومين": ("day", 2),
    "اسبوعين": ("week", 2),
    "شهرين": ("month", 2),
    "سنتين": ("year", 2),
    "عامين": ("year", 2),
}
_EN_DURATION_RE = re.compile(
    r"\(?(?<![\d.])(\d{1,4})\)?\s+(?:calendar\s+)?(" + _alt(_EN_UNITS) + r")\b"
)
_AR_DURATION_RE = re.compile(r"\(?(?<![\d.])(\d{1,4})\)?\s+(" + _alt(_AR_UNITS) + r")(?!\w)")
_AR_DUAL_RE = re.compile(r"(?<!\w)(?:ل|ب|و)?(" + _alt(_AR_DUALS) + r")(?!\w)")


@dataclass
class DateEntity:
    text: str
    value: str  # ISO 8601


@dataclass
class AmountEntity:
    text: str
    amount: str  # decimal string, no separators
    currency: str


@dataclass
class DurationEntity:
    text: str
    value: int
    unit: str


@dataclass
class Party:
    name: str
    role: Optional[str] = None


def _src(text: str, imap: List[int], m: re.Match[str], group: int = 0) -> str:
    """Return the original-text slice behind a match on normalised text."""
    return original_span(text, imap, m.start(group), m.end(group))


def _safe_date(y: int, m: int, d: int) -> Optional[str]:
    try:
        return date(y, m, d).isoformat()
    except ValueError:
        return None


def _dedupe_spans(found: List[Tuple[int, int, object]]) -> List[object]:
    """Keep the earliest, longest non-overlapping matches."""
    found.sort(key=lambda item: (item[0], -(item[1] - item[0])))
    kept: List[object] = []
    last_end = -1
    for start, end, value in found:
        if start >= last_end:
            kept.append(value)
            last_end = end
    return kept


def extract_dates(text: str) -> List[DateEntity]:
    norm, imap = normalize_with_map(text)
    found: List[Tuple[int, int, object]] = []
    for m in _ISO_RE.finditer(norm):
        iso = _safe_date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        if iso:
            found.append((m.start(), m.end(), DateEntity(_src(text, imap, m), iso)))
    for m in _NUMERIC_DMY_RE.finditer(norm):
        # Gulf contracts write day first.
        iso = _safe_date(int(m.group(3)), int(m.group(2)), int(m.group(1)))
        if iso:
            found.append((m.start(), m.end(), DateEntity(_src(text, imap, m), iso)))
    for m in _EN_DMY_RE.finditer(norm):
        iso = _safe_date(int(m.group(3)), _EN_MONTHS[m.group(2)], int(m.group(1)))
        if iso:
            found.append((m.start(), m.end(), DateEntity(_src(text, imap, m), iso)))
    for m in _EN_MDY_RE.finditer(norm):
        iso = _safe_date(int(m.group(3)), _EN_MONTHS[m.group(1)], int(m.group(2)))
        if iso:
            found.append((m.start(), m.end(), DateEntity(_src(text, imap, m), iso)))
    for m in _AR_DMY_RE.finditer(norm):
        iso = _safe_date(int(m.group(3)), _AR_MONTHS[m.group(2)], int(m.group(1)))
        if iso:
            found.append((m.start(), m.end(), DateEntity(_src(text, imap, m), iso)))
    return _dedupe_spans(found)  # type: ignore[return-value]


def _to_decimal(raw: str) -> Optional[str]:
    try:
        return str(Decimal(raw.replace(",", "")))
    except InvalidOperation:
        return None


def extract_amounts(text: str) -> List[AmountEntity]:
    norm, imap = normalize_with_map(text)
    found: List[Tuple[int, int, object]] = []
    for m in _AMOUNT_BEFORE_RE.finditer(norm):
        value = _to_decimal(m.group(2))
        if value is not None:
            entity = AmountEntity(_src(text, imap, m), value, CURRENCY_ALIASES[m.group(1)])
            found.append((m.start(), m.end(), entity))
    for m in _AMOUNT_AFTER_RE.finditer(norm):
        value = _to_decimal(m.group(1))
        if value is not None:
            entity = AmountEntity(_src(text, imap, m), value, CURRENCY_ALIASES[m.group(2)])
            found.append((m.start(), m.end(), entity))
    return _dedupe_spans(found)  # type: ignore[return-value]


def extract_durations(text: str) -> List[DurationEntity]:
    norm, imap = normalize_with_map(text)
    found: List[Tuple[int, int, object]] = []
    for m in _EN_DURATION_RE.finditer(norm):
        entity = DurationEntity(_src(text, imap, m).strip(), int(m.group(1)), _EN_UNITS[m.group(2)])
        found.append((m.start(), m.end(), entity))
    for m in _AR_DURATION_RE.finditer(norm):
        entity = DurationEntity(_src(text, imap, m).strip(), int(m.group(1)), _AR_UNITS[m.group(2)])
        found.append((m.start(), m.end(), entity))
    for m in _AR_DUAL_RE.finditer(norm):
        unit, value = _AR_DUALS[m.group(1)]
        found.append((m.start(), m.end(), DurationEntity(_src(text, imap, m, 1), value, unit)))
    return _dedupe_spans(found)  # type: ignore[return-value]


# --------------------------------------------------------------------------- parties

_QUOTE = "\"“”«»'‘’"
_EN_BETWEEN_RES = (
    # Prefer splitting after the first party's role definition: "X ("the Seller"), and Y".
    re.compile(r"\bbetween\b[:\s]+(.+?\))\s*[,;]?\s*\band\b\s+(.+)", re.IGNORECASE),
    re.compile(r"\bbetween\b[:\s]+(.+?)\s*,?\s+\band\b\s+(.+)", re.IGNORECASE),
)
_EN_LABEL_RE = re.compile(
    r"^\s*(first|second|third)\s+party\s*[:\-]\s*(.+)$", re.IGNORECASE | re.MULTILINE
)
_AR_LABEL_RE = re.compile(
    r"^\s*(?:\d+\s*[\-.)]\s*)?(الطرف\s+ال(?:[اأإ]ول|ثاني|ثالث))\s*[:\-]\s*(.+)$", re.MULTILINE
)
_ROLE_RE = re.compile(
    r"(?:referred\s+to\s+as|hereinafter|ويشار\s+[اإ]لي(?:ه|ها)(?:\s+فيما\s+بعد)?\s+ب)\s*"
    r"(?:the\s+)?[" + _QUOTE + r"]\s*(?:the\s+)?([^" + _QUOTE + r"]{2,40})[" + _QUOTE + r"]",
    re.IGNORECASE,
)
_QUOTED_ROLE_RE = re.compile(
    r"\(\s*(?:the\s+)?["
    + _QUOTE
    + r"]\s*(?:the\s+)?([^"
    + _QUOTE
    + r"]{2,40})["
    + _QUOTE
    + r"]\s*\)",
    re.IGNORECASE,
)
_NAME_CUT_RE = re.compile(
    r"\s*(?:[,،(]|\bwhose\b|\ba company\b|\bwith\b|ومقرها|ومقره|\bو?يمثلها\b)"
)


def _clean_name(fragment: str) -> str:
    fragment = " ".join(fragment.split())
    cut = _NAME_CUT_RE.search(fragment)
    name = fragment[: cut.start()] if cut else fragment
    return name.strip(" :;-" + _QUOTE)


def _role_of(fragment: str) -> Optional[str]:
    m = _ROLE_RE.search(fragment) or _QUOTED_ROLE_RE.search(fragment)
    return m.group(1).strip() if m else None


def extract_parties(preamble: str) -> List[Party]:
    """Find contracting parties in a preamble.

    Supports labelled lines (``First Party: ...`` / ``الطرف الأول: ...``) and
    the English ``between X ... and Y ...`` sentence. Names keep their original
    spelling; only digits, tatweel and diacritics are normalised.
    """
    text = strip_diacritics(to_ascii_digits(preamble))
    parties: List[Party] = []

    for regex in (_AR_LABEL_RE, _EN_LABEL_RE):
        for m in regex.finditer(text):
            fragment = m.group(2)
            name = _clean_name(fragment)
            if name:
                label = " ".join(m.group(1).split())
                parties.append(Party(name=name, role=_role_of(fragment) or label))
    if parties:
        return parties

    flat = " ".join(text.split())
    m = _EN_BETWEEN_RES[0].search(flat) or _EN_BETWEEN_RES[1].search(flat)
    if m:
        first, rest = m.group(1), m.group(2)
        second = re.split(r"\.\s|\bwhereas\b", rest, maxsplit=1, flags=re.IGNORECASE)[0]
        for fragment in (first, second):
            name = _clean_name(fragment)
            if name:
                parties.append(Party(name=name, role=_role_of(fragment)))
    return parties


def extract_entities(text: str) -> Dict[str, list]:
    """Extract dates, amounts and durations as plain dictionaries."""
    return {
        "dates": [asdict(e) for e in extract_dates(text)],
        "amounts": [asdict(e) for e in extract_amounts(text)],
        "durations": [asdict(e) for e in extract_durations(text)],
    }


__all__ = [
    "AmountEntity",
    "DateEntity",
    "DurationEntity",
    "Party",
    "extract_amounts",
    "extract_dates",
    "extract_durations",
    "extract_entities",
    "extract_parties",
]
