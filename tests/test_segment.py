from __future__ import annotations

from clausekit.segment import split_clauses


def test_english_articles_keep_sub_numbering_inside(english_contract):
    clauses = split_clauses(english_contract)
    assert clauses[0].kind == "preamble"
    body = [c for c in clauses if c.kind == "clause"]
    assert [c.number for c in body] == [str(n) for n in range(1, 10)]
    assert body[4].title == "Termination"
    # "5.1" and "5.2" stay inside Article 5 because the document uses keyword headings.
    assert "5.2 The Buyer may terminate" in body[4].text


def test_arabic_numeric_and_ordinal_headings(arabic_contract):
    body = [c for c in split_clauses(arabic_contract) if c.kind == "clause"]
    assert [c.number for c in body] == [str(n) for n in range(1, 10)]
    assert body[0].title == "موضوع العقد"  # from "المادة (١): موضوع العقد"
    assert body[3].title == "السرية"  # from "المادة الرابعة: السرية"


def test_arabic_compound_ordinals_and_feminine_forms():
    text = "البند الأول: التعريفات\nنص\nالبند الثاني عشر - الإخطارات\nنص\nالفقرة الحادية عشرة\nنص"
    clauses = split_clauses(text)
    assert [c.number for c in clauses] == ["1", "12", "11"]
    assert clauses[1].title == "الإخطارات"


def test_plain_numbering_with_split_level():
    text = "1. Scope\nThe work.\n1.1 Details here.\n2) Fees\nPay on time.\n3- Notices\nIn writing."
    top = split_clauses(text)
    assert [c.number for c in top] == ["1", "2", "3"]
    assert "1.1 Details here." in top[0].text

    nested = split_clauses(text, split_level=2)
    assert [c.number for c in nested] == ["1", "1.1", "2", "3"]
    assert nested[1].level == 2


def test_roman_sections_and_long_heading_line_is_body():
    text = "Section IV The Supplier shall deliver the goods to the Buyer's warehouse in Doha within the agreed period."
    [clause] = split_clauses(text)
    assert clause.number == "4"
    assert clause.title is None
    assert clause.text.startswith("The Supplier shall deliver")


def test_numbers_that_are_not_headings():
    text = "Preamble text.\n30 days after signing the parties meet.\n2026 is the first year."
    clauses = split_clauses(text)
    assert len(clauses) == 1
    assert clauses[0].kind == "preamble"
