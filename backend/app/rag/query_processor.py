from dataclasses import dataclass

from langdetect import detect, DetectorFactory, LangDetectException

from app.schemas import AnalyzeRequest

DetectorFactory.seed = 0

# Curated AR→EN symptom lexicon. Production should expand this from a clinical glossary.
AR_EN_SYMPTOMS: dict[str, str] = {
    "حمى": "fever",
    "حرارة": "fever",
    "سخونية": "fever",
    "سعال": "cough",
    "كحة": "cough",
    "صداع": "headache",
    "ألم في الرأس": "headache",
    "ألم في الصدر": "chest pain",
    "ضيق في التنفس": "shortness of breath",
    "زكام": "common cold",
    "رشح": "runny nose",
    "التهاب الحلق": "sore throat",
    "إسهال": "diarrhea",
    "إمساك": "constipation",
    "غثيان": "nausea",
    "قيء": "vomiting",
    "ألم في البطن": "abdominal pain",
    "دوخة": "dizziness",
    "إرهاق": "fatigue",
    "تعب": "fatigue",
    "طفح جلدي": "skin rash",
    "حكة": "itching",
    "ألم في المفاصل": "joint pain",
    "ألم في الظهر": "back pain",
    "ضغط الدم المرتفع": "high blood pressure",
    "سكر": "diabetes",
}


@dataclass
class NormalizedQuery:
    query_text: str
    language: str  # "en" or "ar"


def detect_language(text: str) -> str:
    try:
        lang = detect(text)
    except LangDetectException:
        return "en"
    return "ar" if lang == "ar" else "en"


def translate_arabic_symptoms(text: str) -> str:
    """Token-level swap for known AR symptoms — keeps the rest verbatim.
    For an MVP this is good enough; replace with an MT model in production."""
    out = text
    for ar, en in AR_EN_SYMPTOMS.items():
        out = out.replace(ar, en)
    return out


def process_query(req: AnalyzeRequest) -> NormalizedQuery:
    raw = req.symptoms.strip()
    if not raw:
        raise ValueError("Symptoms cannot be empty.")

    lang = detect_language(raw) if req.language == "auto" else req.language

    query_text = raw
    if lang == "ar":
        query_text = translate_arabic_symptoms(raw)

    enriched = [query_text]
    if req.age is not None:
        enriched.append(f"age {req.age}")
    if req.gender:
        enriched.append(f"gender {req.gender}")
    if req.history:
        enriched.append(f"history: {req.history}")

    return NormalizedQuery(query_text=" | ".join(enriched), language=lang)
