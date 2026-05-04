from typing import Literal, Optional
from pydantic import BaseModel, Field


Confidence = Literal["low", "medium", "high"]
Gender = Literal["male", "female", "other"]


class AnalyzeRequest(BaseModel):
    symptoms: str = Field(..., min_length=2, max_length=2000)
    age: Optional[int] = Field(None, ge=0, le=120)
    gender: Optional[Gender] = None
    history: Optional[str] = Field(None, max_length=2000)
    language: Optional[Literal["en", "ar", "auto"]] = "auto"


class Treatment(BaseModel):
    drug: str
    brands_in_egypt: list[str] = []
    price_egp: str = "—"
    notes: Optional[str] = None


class Diagnosis(BaseModel):
    name: str
    icd11: Optional[str] = None
    confidence: Confidence
    confidence_score: float = Field(..., ge=0.0, le=1.0)
    reason: str
    tests: list[str] = []
    treatments: list[Treatment] = []
    sources: list[str] = []
    matched_symptoms: list[str] = []  # input phrases that appear in supporting chunks


class AnalyzeResponse(BaseModel):
    diagnoses: list[Diagnosis]
    disclaimer: str
    query_language: str
    retrieval_quality: float = Field(..., ge=0.0, le=1.0)
