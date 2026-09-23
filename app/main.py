import os
from fastapi import FastAPI, HTTPException, Query, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from .models import CaseRequest, CaseResult, Authority, Evidence, HumanReviewRequest
from .providers import ModelRoute, ProviderError
from .graph import run_case
from .knowledge import AuthorityStore
from .evidence_store import EvidenceStore
from .audit import AuditStore

app = FastAPI(title="LegalDebateAgents", version="0.1.0")
app.add_middleware(CORSMiddleware, allow_origins=os.getenv("CORS_ORIGINS", "http://127.0.0.1:8000,http://localhost:8000").split(","), allow_credentials=False, allow_methods=["GET", "POST"], allow_headers=["Content-Type"])
store = AuthorityStore(os.getenv("AUTHORITY_STORE_PATH", "data/authorities.json"))
evidence_store = EvidenceStore(os.getenv("EVIDENCE_STORE_PATH", "data/evidence"))
audit_store = AuditStore(os.getenv("AUDIT_STORE_PATH", "data/audit"))

@app.get("/health")
def health(): return {"status":"ok", "default_provider":os.getenv("DEFAULT_PROVIDER", "mock")}

@app.post("/authorities/import")
def import_authorities(authorities: list[Authority]):
    """Import only records already verified against an official source."""
    try: return {"imported": store.upsert(authorities)}
    except ValueError as e: raise HTTPException(status_code=422, detail=str(e))

@app.get("/authorities/search", response_model=list[Authority])
def search_authorities(q: str = Query(min_length=2), limit: int = Query(default=8, ge=1, le=30), jurisdiction: str | None = Query(default=None, pattern="^(china|wto|other)$")):
    return store.search(q, limit, jurisdiction=jurisdiction)

@app.post("/cases/{case_id}/evidence", response_model=Evidence)
async def upload_evidence(case_id: str, evidence_id: str = Form(), party: str = Form(), file: UploadFile = File()):
    if party not in {"plaintiff", "defendant", "neutral"}:
        raise HTTPException(status_code=422, detail="party must be plaintiff, defendant, or neutral")
    try:
        evidence = await evidence_store.save(case_id, evidence_id, party, file)
        return evidence
    except ValueError as e: raise HTTPException(status_code=422, detail=str(e))

@app.get("/cases/{case_id}/audit")
def case_audit(case_id: str):
    return {"verification": audit_store.verify(case_id), "events": audit_store.events(case_id)}

@app.post("/cases/{case_id}/reviews")
def submit_human_review(case_id: str, review: HumanReviewRequest):
    try:
        event = audit_store.record_review(case_id, review)
        return {"recorded": True, "sequence": event["sequence"], "event_hash": event["event_hash"]}
    except ValueError as e: raise HTTPException(status_code=409, detail=str(e))

@app.post("/cases/debate", response_model=CaseResult)
async def debate(case: CaseRequest):
    # Retrieval assists counsel but never silently replaces user-provided law.
    retrieved = store.search(" ".join([case.facts, *(x.question for x in case.issues)]))
    known = {x.authority_id for x in case.authorities}
    case.authorities.extend(x for x in retrieved if x.authority_id not in known)
    route = ModelRoute(provider=os.getenv("DEFAULT_PROVIDER", "mock"), model=os.getenv("DEFAULT_MODEL", "mock-legal-model"), base_url=os.getenv("DEFAULT_BASE_URL"), api_key_env=os.getenv("DEFAULT_API_KEY_ENV"))
    try: return await run_case(case, route, audit_store)
    except ProviderError as e: raise HTTPException(status_code=503, detail=str(e))
