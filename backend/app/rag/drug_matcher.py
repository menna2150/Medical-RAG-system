from __future__ import annotations

import json
from pathlib import Path

from app.schemas import Treatment

DEFAULT_DB = Path(__file__).resolve().parents[1] / "data" / "medications_egypt.json"


class DrugMatcher:
    """Maps generic drug names / classes to brands available in the Egyptian market.

    The DB is a curated JSON list, never produced by the LLM. Anything the LLM
    proposes that doesn't resolve here is dropped — this prevents hallucinated drugs.
    """

    def __init__(self, entries: list[dict]):
        self.entries = entries
        self._by_generic: dict[str, dict] = {}
        self._by_class: dict[str, list[dict]] = {}
        for e in entries:
            self._by_generic[e["generic_name"].lower()] = e
            for cls in e.get("classes", []):
                self._by_class.setdefault(cls.lower(), []).append(e)

    @classmethod
    def from_default(cls) -> "DrugMatcher":
        with DEFAULT_DB.open(encoding="utf-8") as f:
            return cls(json.load(f))

    def resolve(self, term: str) -> list[Treatment]:
        """Look up by generic name first, then drug class. Returns at most 3 matches."""
        if not term:
            return []
        key = term.strip().lower()
        if key in self._by_generic:
            e = self._by_generic[key]
            return [self._to_treatment(e)]
        if key in self._by_class:
            return [self._to_treatment(e) for e in self._by_class[key][:3]]
        # Last-resort fuzzy: substring on generic
        partial = [e for g, e in self._by_generic.items() if key in g or g in key]
        return [self._to_treatment(e) for e in partial[:3]]

    @staticmethod
    def _to_treatment(e: dict) -> Treatment:
        return Treatment(
            drug=e["generic_name"],
            brands_in_egypt=e.get("brands_egypt", []),
            price_egp=e.get("price_egp", "—"),
            notes=e.get("notes"),
        )
