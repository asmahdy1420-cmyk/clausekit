"""Text normalisation for bilingual (Arabic/English) contract text.

Two layers are exposed:

* ``to_ascii_digits`` maps Arabic-Indic (U+0660-0669) and Extended
  Arabic-Indic / Persian (U+06F0-06F9) digits to ASCII, and the Arabic
  decimal/thousands separators to ``.`` and ``,``. It is length-preserving.
* ``normalize_arabic`` strips tatweel and diacritics and, optionally, unifies
  letter variants (alef forms, alef maqsura, taa marbuta). It is used for
  matching only; output shown to users keeps the original spelling.
"""

from __future__ import annotations

import re
import unicodedata
from typing import List, Tuple

DIGIT_TABLE = {ord(c): str(i) for i, c in enumerate("٠١٢٣٤٥٦٧٨٩")}
DIGIT_TABLE.update({ord(c): str(i) for i, c in enumerate("۰۱۲۳۴۵۶۷۸۹")})
DIGIT_TABLE[0x066B] = "."  # ARABIC DECIMAL SEPARATOR
DIGIT_TABLE[0x066C] = ","  # ARABIC THOUSANDS SEPARATOR

TATWEEL = "\u0640"
# Harakat, tanween, shadda, sukun, superscript alef and Quranic marks.
DIACRITICS_RE = re.compile("[\u0610-\u061a\u064b-\u065f\u0670\u06d6-\u06ed]")

LETTER_TABLE = {
    ord("أ"): "ا",
    ord("إ"): "ا",
    ord("آ"): "ا",
    ord("ٱ"): "ا",
    ord("ى"): "ي",
    ord("ة"): "ه",
}

_ARABIC_LETTER_RE = re.compile("[\u0621-\u064a\u0671-\u06d3]")
_LATIN_LETTER_RE = re.compile("[A-Za-z]")
_WS_RE = re.compile("[ \t\u00a0\u200e\u200f]+")


def to_ascii_digits(text: str) -> str:
    """Convert Arabic-Indic digits and separators to their ASCII forms."""
    return text.translate(DIGIT_TABLE)


def strip_diacritics(text: str) -> str:
    """Remove tatweel and Arabic diacritics without touching letters."""
    return DIACRITICS_RE.sub("", text.replace(TATWEEL, ""))


def normalize_arabic(text: str, unify_letters: bool = True) -> str:
    """Normalise Arabic text for matching.

    Removes tatweel and diacritics, converts digits to ASCII and, when
    ``unify_letters`` is true, folds alef variants to bare alef, alef maqsura
    to yaa and taa marbuta to haa.
    """
    text = unicodedata.normalize("NFC", text)
    text = strip_diacritics(to_ascii_digits(text))
    if unify_letters:
        text = text.translate(LETTER_TABLE)
    return text


def normalize_for_matching(text: str) -> str:
    """Full normalisation used by the classifier and risk rules."""
    text = normalize_arabic(text).lower()
    return _WS_RE.sub(" ", text)


def normalize_with_map(text: str) -> Tuple[str, List[int]]:
    """Normalise like ``normalize_for_matching`` (minus whitespace folding).

    Returns the normalised string and, for each of its characters, the index
    of the character in ``text`` it came from. Callers match on the normalised
    string and slice the original with the map, so users see the original
    spelling of whatever was matched.
    """
    chars: List[str] = []
    index_map: List[int] = []
    for i, ch in enumerate(text):
        if ch == TATWEEL or DIACRITICS_RE.match(ch):
            continue
        ch = ch.translate(DIGIT_TABLE).translate(LETTER_TABLE)
        lowered = ch.lower()
        chars.append(lowered if len(lowered) == 1 else ch)
        index_map.append(i)
    return "".join(chars), index_map


def original_span(text: str, index_map: List[int], start: int, end: int) -> str:
    """Slice ``text`` using a span from the normalised string."""
    if start >= end or not index_map:
        return ""
    stop = index_map[end - 1] + 1
    # Keep trailing marks (tanween, tatweel) that belong to the last letter.
    while stop < len(text) and (text[stop] == TATWEEL or DIACRITICS_RE.match(text[stop])):
        stop += 1
    return text[index_map[start] : stop]


def count_scripts(text: str) -> tuple[int, int]:
    """Return ``(arabic_letters, latin_letters)`` found in ``text``."""
    return len(_ARABIC_LETTER_RE.findall(text)), len(_LATIN_LETTER_RE.findall(text))
