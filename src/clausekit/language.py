"""Script-ratio language detection.

Contracts in the Gulf are usually Arabic, English, or both side by side. A
letter-count ratio is enough to tell those apart and needs no model.
"""

from __future__ import annotations

from .normalize import count_scripts

ARABIC = "ar"
ENGLISH = "en"
MIXED = "mixed"
UNKNOWN = "unknown"


def detect_language(text: str, threshold: float = 0.7) -> str:
    """Return ``"ar"``, ``"en"``, ``"mixed"`` or ``"unknown"``.

    ``threshold`` is the share of letters one script needs to win outright.
    """
    arabic, latin = count_scripts(text)
    total = arabic + latin
    if total == 0:
        return UNKNOWN
    if arabic / total >= threshold:
        return ARABIC
    if latin / total >= threshold:
        return ENGLISH
    return MIXED
