from __future__ import annotations

from clausekit.entities import extract_amounts, extract_dates, extract_durations, extract_parties


def test_dates_in_both_digit_systems_and_formats():
    values = [
        d.value
        for d in extract_dates(
            "Signed on 12 January 2026, effective 2026-02-01, renewal by March 3, 2027 "
            "وتاريخ التسليم ٠١/٠٤/٢٠٢٦ أو ١٥ مارس ٢٠٢٦"
        )
    ]
    assert values == ["2026-01-12", "2026-02-01", "2027-03-03", "2026-04-01", "2026-03-15"]


def test_invalid_dates_are_skipped():
    assert extract_dates("31/02/2026 and 45/01/2026") == []


def test_amounts_with_gulf_currencies():
    amounts = extract_amounts(
        "QAR 150,000 and 2,500.50 AED and $1,200 and BHD 75 and "
        "مبلغ ٢٥٬٠٠٠ ريال سعودي و ٣٠٠٠ ريال قطري"
    )
    assert [(a.amount, a.currency) for a in amounts] == [
        ("150000", "QAR"),
        ("2500.50", "AED"),
        ("1200", "USD"),
        ("75", "BHD"),
        ("25000", "SAR"),
        ("3000", "QAR"),
    ]
    assert amounts[4].text == "٢٥٬٠٠٠ ريال سعودي"


def test_durations_english_arabic_and_dual_forms():
    found = [
        (d.value, d.unit)
        for d in extract_durations(
            "within thirty (30) days, 5 business days, 2 years; خلال (٩٠) يوماً ولمدة سنتين و ٦ أشهر"
        )
    ]
    assert found == [
        (30, "day"),
        (5, "business_day"),
        (2, "year"),
        (90, "day"),
        (2, "year"),
        (6, "month"),
    ]


def test_parties_from_english_between_sentence():
    parties = extract_parties(
        "This Agreement is made between Al Waha Medical Supplies W.L.L., a company registered "
        'in Doha ("the Supplier"), and Corniche Clinics Group LLC ("the Buyer").'
    )
    assert [(p.name, p.role) for p in parties] == [
        ("Al Waha Medical Supplies W.L.L.", "Supplier"),
        ("Corniche Clinics Group LLC", "Buyer"),
    ]


def test_parties_from_arabic_labels():
    parties = extract_parties(
        'الطرف الأول: شركة الريان للاستشارات ذ.م.م، ويشار إليها فيما بعد بـ "المورد"\n'
        "الطرف الثاني: مؤسسة النخيل العقارية، ومقرها الرياض"
    )
    assert [(p.name, p.role) for p in parties] == [
        ("شركة الريان للاستشارات ذ.م.م", "المورد"),
        ("مؤسسة النخيل العقارية", "الطرف الثاني"),
    ]
