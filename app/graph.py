import asyncio
from .models import CaseRequest, CaseResult, Argument, Holding, AgentModelRoute
from .providers import ModelRoute, get_provider

SYSTEM = """You are a legal research assistant. Never invent a fact, evidence ID, law, article, or URL.
This output is litigation research, not a judicial decision or legal representation."""

def _sources(c: CaseRequest) -> str:
    evidence = "\n".join(f"[{x.evidence_id}] {x.name}: {x.text} @ {x.locator}" for x in c.evidence) or "(none)"
    laws = "\n".join(f"[{x.authority_id}] {x.title} {x.article}, status={x.effective_status}: {x.excerpt}" for x in c.authorities) or "(none)"
    return f"FACTS:\n{c.facts}\nEVIDENCE:\n{evidence}\nAUTHORITIES:\n{laws}"

async def _arg(c: CaseRequest, party: str, issue_id: str, role: str, route: ModelRoute) -> Argument:
    issue = next(x for x in c.issues if x.issue_id == issue_id)
    prompt = f"{_sources(c)}\nISSUE {issue.issue_id}: {issue.question}\nBURDEN: {issue.burden_of_proof}\nAct as {role}. Provide a concise grounded position. Cite IDs in brackets; disclose missing evidence."
    text = await get_provider(route).complete(SYSTEM, prompt)
    return Argument(party=party, issue_id=issue_id, position=text)

async def run_case(c: CaseRequest, route: ModelRoute, audit=None) -> CaseResult:
    def resolve(role: str) -> ModelRoute:
        configured: AgentModelRoute | None = c.routes.get(role)  # type: ignore[arg-type]
        if not configured: return route
        return ModelRoute(provider=configured.provider, model=configured.model, base_url=configured.base_url, api_key_env=configured.api_key_env)

    work = []
    for issue in c.issues:
        work += [_arg(c, "plaintiff", issue.issue_id, "plaintiff counsel", resolve("plaintiff")), _arg(c, "defendant", issue.issue_id, "defendant counsel", resolve("defendant"))]
    arguments = await asyncio.gather(*work)
    p = [x for x in arguments if x.party == "plaintiff"]
    d = [x for x in arguments if x.party == "defendant"]
    holdings = []
    for issue in c.issues:
        prompt = f"{_sources(c)}\nISSUE: {issue.question}\nPLAINTIFF: {next(x.position for x in p if x.issue_id==issue.issue_id)}\nDEFENDANT: {next(x.position for x in d if x.issue_id==issue.issue_id)}\nReturn a neutral, evidence-grounded analysis; if evidence is missing say so."
        reasoning = await get_provider(resolve("judge")).complete(SYSTEM, prompt)
        holdings.append(Holding(issue_id=issue.issue_id, outcome="insufficient_evidence", reasoning=reasoning))
    result = CaseResult(case_id=c.case_id, plaintiff_arguments=p, defendant_arguments=d, holdings=holdings, warnings=["仅供法律研究与庭审准备；须由中国执业律师/有权机关复核。", "法律法规与案例引用应回链国家法律法规数据库或最高人民法院官方来源核验。"])
    if audit: audit.record_run(c, result)
    return result
