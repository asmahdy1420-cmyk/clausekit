from __future__ import annotations

import pytest

from clausekit.classify import classify_clause
from clausekit.risks import find_risks


@pytest.mark.parametrize(
    ("title", "text", "expected"),
    [
        (
            "Governing Law",
            "This Agreement is governed by the laws of the State of Qatar.",
            "governing_law",
        ),
        (None, "Any dispute shall be referred to arbitration in Dubai.", "dispute_resolution"),
        (None, "Neither party is liable for delay caused by force majeure.", "force_majeure"),
        ("السرية", "يلتزم الطرفان بعدم إفشاء المعلومات.", "confidentiality"),
        (None, "يحق لأي من الطرفين فسخ العقد بإخطار كتابي.", "termination"),
        ("المقابل المالي", "يتم السداد خلال ثلاثين يوماً من تاريخ الفاتورة.", "payment"),
        ("القوة القاهرة", "لا يسأل أي طرف عن التأخير.", "force_majeure"),
        (None, "The Contractor shall indemnify the Employer against all claims.", "liability"),
    ],
)
def test_classifier_both_languages(title, text, expected):
    assert classify_clause(text, title).clause_type == expected


def test_weak_signal_is_other():
    result = classify_clause("The parties agree on the following definitions.")
    assert result.clause_type == "other"
    assert result.confidence == 0.0


def test_diacritics_do_not_break_classification():
    plain = classify_clause("يخضع هذا العقد للقانون القطري", "القانون الواجب التطبيق")
    vowelled = classify_clause("يَخْضَعُ هذا العَقْدُ للقانون القطري", "القانونُ الواجبُ التطبيقِ")
    assert plain.clause_type == vowelled.clause_type == "governing_law"


def test_risk_flags_english():
    codes = {
        f.code
        for f in find_risks(
            "This Agreement shall renew automatically each year. "
            "The Client may terminate this Agreement for convenience. "
            "The Supplier has unlimited liability for data loss."
        )
    }
    assert codes == {"auto_renewal", "unilateral_termination", "unlimited_liability"}


def test_risk_flags_arabic_with_evidence_in_original_spelling():
    flags = find_risks("يتجدد هذا العقد تلقائياً لمدة مماثلة، ويحق للمؤجر إنهاء العقد من جانب واحد.")
    by_code = {f.code: f for f in flags}
    assert set(by_code) == {"auto_renewal", "unilateral_termination"}
    assert "إنهاء" in by_code["unilateral_termination"].evidence


def test_liability_cap_suppresses_unlimited_flag():
    capped = "The Supplier is liable for all losses, provided that its liability shall not exceed USD 10,000."
    assert find_risks(capped) == []
    assert find_risks("مسؤولية المورد بحد أقصى ٥٠٬٠٠٠ ريال قطري") == []
    assert [f.code for f in find_risks("تكون مسؤولية المقاول غير محدودة")] == [
        "unlimited_liability"
    ]


def test_mutual_termination_for_breach_is_not_flagged():
    assert (
        find_risks("Either party may terminate for material breach on 30 days written notice.")
        == []
    )
