"""FastAPI application exposing the analyser over HTTP.

Run with:  uvicorn clausekit.api:app --reload
"""

from __future__ import annotations

from typing import Any, Dict

from fastapi import FastAPI
from pydantic import BaseModel, Field

from . import __version__
from .extractor import analyze

MAX_CHARS = 500_000

app = FastAPI(
    title="clausekit",
    version=__version__,
    description="Bilingual Arabic/English contract clause extraction.",
)


class AnalyzeRequest(BaseModel):
    text: str = Field(
        ...,
        min_length=1,
        max_length=MAX_CHARS,
        description="Contract text, Arabic, English or both.",
    )
    split_level: int = Field(1, ge=1, le=4)
    min_score: float = Field(3.0, ge=0.0)
    risks_only: bool = False


@app.get("/health")
def health() -> Dict[str, str]:
    return {"status": "ok", "version": __version__}


@app.post("/analyze")
def analyze_contract(request: AnalyzeRequest) -> Dict[str, Any]:
    # Plain `def`: the analysis is CPU-bound, so FastAPI runs it in a worker thread.
    result = analyze(
        request.text, split_level=request.split_level, min_score=request.min_score
    ).to_dict()
    if request.risks_only:
        return {k: result[k] for k in ("language", "parties", "risks", "summary")}
    return result
