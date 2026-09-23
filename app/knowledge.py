"""Offline-first authority store.

Production ingestion must obtain the original text and effective status from an
official source; this module deliberately does not scrape public websites.
"""
import json
import re
from pathlib import Path
from .models import Authority

class AuthorityStore:
    def __init__(self, path: str = "data/authorities.json"):
        self.path = Path(path)
        self.items: dict[str, Authority] = {}
        self.load()

    def load(self) -> None:
        if self.path.exists():
            self.items = {x["authority_id"]: Authority.model_validate(x) for x in json.loads(self.path.read_text())}

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps([x.model_dump(mode="json") for x in self.items.values()], ensure_ascii=False, indent=2))

    def upsert(self, authorities: list[Authority]) -> int:
        for item in authorities:
            if not item.official_url:
                raise ValueError(f"{item.authority_id}: official_url is required")
            self.items[item.authority_id] = item
        self.save()
        return len(authorities)

    @staticmethod
    def _tokens(text: str) -> set[str]:
        # Chinese has no whitespace token boundary; character bi-grams give a
        # dependency-free lexical baseline. Replace with BM25 + reranker in prod.
        plain = re.sub(r"\s+", "", text.lower())
        return {plain[i:i + 2] for i in range(max(0, len(plain) - 1))}

    def search(self, query: str, limit: int = 8, effective_only: bool = True, jurisdiction: str | None = None) -> list[Authority]:
        q = self._tokens(query)
        ranked = []
        for authority in self.items.values():
            if effective_only and authority.effective_status == "repealed":
                continue
            if jurisdiction and authority.jurisdiction != jurisdiction:
                continue
            text = f"{authority.title}{authority.article}{authority.excerpt}"
            score = len(q & self._tokens(text))
            if score: ranked.append((score, authority))
        return [item for _, item in sorted(ranked, key=lambda row: row[0], reverse=True)[:limit]]
