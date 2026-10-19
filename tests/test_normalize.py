from __future__ import annotations

from clausekit.language import detect_language
from clausekit.normalize import normalize_arabic, normalize_with_map, original_span, to_ascii_digits


def test_arabic_indic_digits_and_separators():
    assert to_ascii_digits("٢٠٢٦/٠٣/١٥") == "2026/03/15"
    assert to_ascii_digits("١٢٬٥٠٠٫٧٥") == "12,500.75"
    assert to_ascii_digits("۱۲۳") == "123"  # Persian / Urdu forms


def test_removes_tatweel_and_diacritics():
    assert normalize_arabic("عقـــد") == "عقد"
    assert normalize_arabic("مُسْتَأْجِرٌ", unify_letters=False) == "مستأجر"


def test_unifies_alef_yaa_and_taa_marbuta():
    assert normalize_arabic("إنهاء") == "انهاء"
    assert normalize_arabic("الأولى") == "الاولي"
    assert normalize_arabic("المادة") == "الماده"
    assert normalize_arabic("آجل") == "اجل"


def test_index_map_recovers_original_spelling():
    raw = "مدة ٣٠ يومـاً"
    norm, imap = normalize_with_map(raw)
    start = norm.index("30")
    assert original_span(raw, imap, start, start + 2) == "٣٠"


def test_detect_language():
    assert detect_language("The Buyer shall pay the price.") == "en"
    assert detect_language("يلتزم المشتري بسداد الثمن.") == "ar"
    assert detect_language("Rent الإيجار السنوي annual rent") == "mixed"
    assert detect_language("12/12/2026") == "unknown"
