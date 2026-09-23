const defaultApi = `${location.origin}/legal-debate-api`;
let api = localStorage.getItem("legalDebateApi") || defaultApi;
const timeline = document.querySelector("#timeline");
const button = document.querySelector("#debate");
const payload = {case_id:"CIVIL-2026-0001",dispute_type:"买卖合同纠纷",facts:"甲称乙未按合同约定支付货款。",issues:[{issue_id:"I-01",question:"乙是否逾期付款？",burden_of_proof:"甲证明合同、履行与到期欠款；乙证明付款或其他抗辩。"}],evidence:[],authorities:[]};
const esc = value => String(value).replace(/[&<>"]/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;","\"":"&quot;"}[c]));
document.querySelector("#endpoint").addEventListener("click", () => {
  const next = prompt("输入 LegalDebateAgents API 地址", api);
  if (next) { api = next.replace(/\/$/, ""); localStorage.setItem("legalDebateApi", api); }
});
document.querySelector("#evidence").addEventListener("click", () => alert("后端接口：POST /cases/{case_id}/evidence（上传并登记哈希）"));
button.addEventListener("click", async () => {
  button.disabled = true; button.textContent = "辩论中…";
  try {
    const response = await fetch(`${api}/cases/debate`, {method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(payload)});
    if (!response.ok) throw new Error(await response.text());
    const result = await response.json();
    const p = result.plaintiff_arguments[0]?.position || "无原告陈述";
    const d = result.defendant_arguments[0]?.position || "无被告陈述";
    const h = result.holdings[0];
    timeline.innerHTML = `<div class="turn"><span class="tag pl">原告代理人</span><p>${esc(p)}</p></div><div class="turn"><span class="tag df">被告代理人</span><p>${esc(d)}</p></div><div class="turn"><span class="tag jd">法官 Agent · ${esc(h.outcome)}</span><p>${esc(h.reasoning)}</p></div>`;
    document.querySelector("#holding").textContent = h.reasoning;
  } catch (error) { alert(`无法连接 API：${error.message}`); }
  finally { button.disabled = false; button.textContent = "运行下一轮辩论"; }
});
