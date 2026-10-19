from __future__ import annotations

from pathlib import Path

import pytest

EXAMPLES = Path(__file__).resolve().parent.parent / "examples"


@pytest.fixture
def english_contract() -> str:
    return (EXAMPLES / "supply_agreement_en.txt").read_text(encoding="utf-8")


@pytest.fixture
def arabic_contract() -> str:
    return (EXAMPLES / "service_contract_ar.txt").read_text(encoding="utf-8")


@pytest.fixture
def bilingual_contract() -> str:
    return (EXAMPLES / "lease_bilingual.txt").read_text(encoding="utf-8")
