from typing import Literal
from pydantic import BaseModel, Field, HttpUrl

class Evidence(BaseModel):
    evidence_id: str
    name: str
    party: Literal["plaintiff", "defendant", "neutral"]
    text: str
    locator: str = ""

class Authority(BaseModel):
    authority_id: str
    title: str
    article: str
    excerpt: str
    effective_status: Literal["effective", "amended", "repealed", "unknown"] = "unknown"
    official_url: str | None = None
    jurisdiction: Literal["china", "wto", "other"] = "china"

class Issue(BaseModel):
    issue_id: str
    question: str
    burden_of_proof: str

class AgentModelRoute(BaseModel):
    """Public routing metadata only; credentials stay in server environment variables."""
    provider: Literal["mock", "ollama", "openai_compatible", "anthropic"] = "mock"
    model: str = "mock-legal-model"
    base_url: str | None = None
    api_key_env: str | None = None

class CaseRequest(BaseModel):
    case_id: str
    dispute_type: str
    facts: str
    issues: list[Issue] = Field(min_length=1)
    evidence: list[Evidence] = []
    authorities: list[Authority] = []
    rounds: int = Field(default=2, ge=1, le=3)
    routes: dict[Literal["plaintiff", "defendant", "judge"], AgentModelRoute] = {}

class Argument(BaseModel):
    party: Literal["plaintiff", "defendant"]
    issue_id: str
    position: str
    evidence_ids: list[str] = []
    authority_ids: list[str] = []
    caveats: list[str] = []

class Holding(BaseModel):
    issue_id: str
    outcome: Literal["supported", "partially_supported", "not_supported", "insufficient_evidence"]
    reasoning: str
    evidence_ids: list[str] = []
    authority_ids: list[str] = []
    missing_materials: list[str] = []
    human_review_required: bool = True

class CaseResult(BaseModel):
    case_id: str
    plaintiff_arguments: list[Argument]
    defendant_arguments: list[Argument]
    holdings: list[Holding]
    warnings: list[str]

class HumanReviewRequest(BaseModel):
    reviewer_id: str = Field(min_length=2, max_length=128)
    reviewer_role: Literal["lawyer", "legal_counsel", "supervisor"]
    conclusion: Literal["approved", "approved_with_reservations", "rejected"]
    notes: str = Field(min_length=2, max_length=8000)
    expected_audit_head_hash: str | None = None
    detached_signature: str | None = Field(default=None, max_length=16000)
