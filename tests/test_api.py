from fastapi.testclient import TestClient
from app.main import app

def test_mock_debate():
    client = TestClient(app)
    payload = {"case_id":"demo-1","dispute_type":"买卖合同纠纷","facts":"甲称乙未支付货款。","issues":[{"issue_id":"I-1","question":"乙是否逾期付款？","burden_of_proof":"甲证明合同与欠款；乙证明付款。"}],"evidence":[]}
    r = client.post("/cases/debate", json=payload)
    assert r.status_code == 200
    assert r.json()["holdings"][0]["outcome"] == "insufficient_evidence"

def test_authority_requires_official_url():
    client = TestClient(app)
    r = client.post("/authorities/import", json=[{"authority_id":"x", "title":"x", "article":"1", "excerpt":"x"}])
    assert r.status_code == 422
