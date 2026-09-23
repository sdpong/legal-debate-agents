"""Append-only, tamper-evident audit trail for legal research runs."""
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

def _digest(value: Any) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(raw).hexdigest()

class AuditStore:
    def __init__(self, root: str = "data/audit"):
        self.root = Path(root)

    def _path(self, case_id: str) -> Path:
        safe = "".join(ch if ch.isalnum() or ch in "_-" else "_" for ch in case_id)
        if not safe: raise ValueError("invalid case ID")
        return self.root / f"{safe}.jsonl"

    def events(self, case_id: str) -> list[dict[str, Any]]:
        path = self._path(case_id)
        return [] if not path.exists() else [json.loads(line) for line in path.read_text().splitlines() if line]

    def append(self, case_id: str, kind: str, payload: dict[str, Any]) -> dict[str, Any]:
        prior = self.events(case_id)
        prev_hash = prior[-1]["event_hash"] if prior else None
        event = {"sequence": len(prior) + 1, "at": datetime.now(timezone.utc).isoformat(), "kind": kind,
                 "previous_hash": prev_hash, "payload": payload}
        event["event_hash"] = _digest(event)
        path = self._path(case_id); path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as f: f.write(json.dumps(event, ensure_ascii=False, sort_keys=True) + "\n")
        return event

    def verify(self, case_id: str) -> dict[str, Any]:
        prior = None
        for event in self.events(case_id):
            stored = event.pop("event_hash")
            valid = event["previous_hash"] == prior and _digest(event) == stored
            event["event_hash"] = stored
            if not valid: return {"valid": False, "broken_at": event["sequence"]}
            prior = stored
        return {"valid": True, "events": len(self.events(case_id)), "head_hash": prior}

    def record_run(self, case, result) -> dict[str, Any]:
        evidence = [{"id": x.evidence_id, "locator": x.locator, "text_hash": _digest(x.text)} for x in case.evidence]
        authorities = [{"id": x.authority_id, "status": x.effective_status, "url": x.official_url} for x in case.authorities]
        routes = {role: route.model_dump() for role, route in case.routes.items()}
        return self.append(case.case_id, "debate_completed", {"evidence": evidence, "authorities": authorities,
            "routes": routes, "result_hash": _digest(result.model_dump())})

    def record_review(self, case_id: str, review) -> dict[str, Any]:
        head = self.verify(case_id).get("head_hash")
        if review.expected_audit_head_hash and review.expected_audit_head_hash != head:
            raise ValueError("audit chain advanced; reload the case before signing")
        return self.append(case_id, "human_review", {"reviewer_id": review.reviewer_id,
            "reviewer_role": review.reviewer_role, "conclusion": review.conclusion, "notes_hash": _digest(review.notes),
            "reviewed_audit_head_hash": head, "detached_signature_present": bool(review.detached_signature)})
