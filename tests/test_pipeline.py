from __future__ import annotations

import json

import pytest

from clausekit import analyze
from clausekit.cli import main


def _types(result):
    return {c.number: c.type for c in result.clauses if c.kind == "clause"}


def test_english_contract_end_to_end(english_contract):
    result = analyze(english_contract)
    assert result.language == "en"
    assert _types(result) == {
        "1": "other",
        "2": "other",
        "3": "payment",
        "4": "confidentiality",
        "5": "termination",
        "6": "liability",
        "7": "force_majeure",
        "8": "governing_law",
        "9": "dispute_resolution",
    }
    assert {(r.code, r.clause_number) for r in result.risks} == {
        ("auto_renewal", "2"),
        ("unilateral_termination", "5"),
        ("unlimited_liability", "6"),
    }


def test_arabic_contract_end_to_end(arabic_contract):
    result = analyze(arabic_contract)
    assert result.language == "ar"
    assert [p.role for p in result.parties] == ["مقدم الخدمة", "العميل"]
    types = _types(result)
    assert types["3"] == "payment"
    assert types["5"] == "termination"
    assert types["7"] == "force_majeure"
    assert types["8"] == "governing_law"
    assert types["9"] == "dispute_resolution"
    # Clause 6 caps liability (بحد أقصى), so no unlimited-liability flag.
    assert {r.code for r in result.risks} == {"auto_renewal", "unilateral_termination"}
    assert result.summary["high_risk_count"] == 1


def test_bilingual_clauses_detected_as_mixed(bilingual_contract):
    result = analyze(bilingual_contract)
    assert result.language == "mixed"
    rent = next(c for c in result.clauses if c.number == "1")
    assert rent.language == "mixed"
    assert rent.type == "payment"
    assert {a["currency"] for a in rent.entities["amounts"]} == {"BHD"}
    assert result.risks == []  # liability is capped, termination needs cause


def test_output_is_json_serialisable(arabic_contract):
    payload = json.dumps(analyze(arabic_contract).to_dict(), ensure_ascii=False)
    assert "مقدم الخدمة" in payload


def test_cli_risks_only(tmp_path, capsys, english_contract):
    source = tmp_path / "contract.txt"
    source.write_text(english_contract, encoding="utf-8")
    assert main(["analyze", str(source), "--risks-only"]) == 0
    data = json.loads(capsys.readouterr().out)
    assert set(data) == {"language", "parties", "risks", "summary"}
    assert data["summary"]["risk_count"] == 3


def test_cli_missing_file(capsys):
    assert main(["analyze", "does-not-exist.txt"]) == 2
    assert "cannot read" in capsys.readouterr().err


def test_api_analyze(arabic_contract):
    pytest.importorskip("fastapi")
    pytest.importorskip("httpx")
    from fastapi.testclient import TestClient

    from clausekit.api import app

    client = TestClient(app)
    assert client.get("/health").json()["status"] == "ok"

    response = client.post("/analyze", json={"text": arabic_contract, "risks_only": True})
    assert response.status_code == 200
    assert response.json()["summary"]["risk_count"] == 2

    assert client.post("/analyze", json={"text": ""}).status_code == 422
