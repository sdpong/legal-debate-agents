# LegalDebateAgents

面向中国民事争议研究的原告—被告对抗式 Agent MVP。它是**法律研究与庭审准备工具**，不是法院、律师或自动裁判器。

## Provider 路由

| Provider | 配置方式 |
|---|---|
| Ollama | `DEFAULT_PROVIDER=ollama`，`DEFAULT_MODEL=qwen3:8b` |
| DeepSeek / Kimi / GLM / MiniMax / Grok / MiMo | `DEFAULT_PROVIDER=openai_compatible`，同时配置对应 `DEFAULT_BASE_URL`、`DEFAULT_API_KEY_ENV` 和模型名 |
| Claude | `DEFAULT_PROVIDER=anthropic`，`DEFAULT_MODEL=...`，默认读取 `ANTHROPIC_API_KEY` |
| Mock | 默认，无 Key、用于 API/工作流测试 |

为每个 Agent 扩展独立 `ModelRoute` 即可实现“原告用模型 A、被告用模型 B、法官用模型 C”。生产环境应把路由放入数据库/配置中心，并启用审批与审计。

接口请求可带 `routes` 来覆盖角色的默认模型，只有 Key 的**环境变量名**可出现，绝不能提交真实 Key：

```json
{
  "routes": {
    "plaintiff": {"provider":"openai_compatible","model":"deepseek-reasoner","base_url":"https://api.deepseek.com","api_key_env":"DEEPSEEK_API_KEY"},
    "defendant": {"provider":"ollama","model":"qwen3:8b"},
    "judge": {"provider":"anthropic","model":"claude-sonnet-4-5","api_key_env":"ANTHROPIC_API_KEY"}
  }
}
```

各 OpenAI-compatible 服务的实际模型名与 Base URL 以供应商当日官方文档为准；服务端只读取指定环境变量，浏览器和日志不应保存 Key。

## 本地运行（macOS）

```bash
cd /Volumes/S7/Codex/legal-debate-agents
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
pytest -q
```

默认 `mock` 模式不需要网络或 Key。复制 `.env.example` 到本机未追踪的 `.env` 后再接入实际供应商；不要把 Key 提交到 Git。

## 法律知识库 MVP

`POST /authorities/import` 导入已核验的法规/案例条目；每条均强制携带 `official_url` 和效力状态。`GET /authorities/search?q=买卖合同` 提供依赖为零的中文双字切分关键词召回；辩论接口会将检索结果作为**候选依据**补入上下文，不覆盖用户提交依据。

先复制 `data/authorities.example.json` 为本机的 `data/authorities.json` 体验。生产版本应以国家法律法规数据库、最高法及人民法院案例库为主数据源，同步时保存原文哈希、抓取时间、效力状态和官方 URL；将这里的轻量召回替换为 OpenSearch BM25 + 向量库 + reranker。

### WTO 世界贸易争议知识包

`data/wto_authorities.json` 提供可导入的 WTO 核心协定索引：DSU、GATT 1994、反倾销协定、SCM 协定及保障措施协定。导入后通过 `GET /authorities/search?q=补贴&jurisdiction=wto` 隔离检索，不与中国国内法混淆。该文件仅存研究索引和官方 URL；正式意见必须回链 WTO 原文，并按争端事实、成员承诺表及最新争端程序状态复核。

## 证据卷宗 MVP

`POST /cases/{case_id}/evidence` 用 multipart 上传 `file`、`evidence_id`、`party`。服务保存原件 SHA-256、原始文件名、提取状态与脱敏后文本；PDF 文本按 `[p.N]` 写入定位。扫描件或无法提取文字的 PDF 会标记 `needs_ocr`，不能被静默当作已读证据。

原件是敏感材料：生产部署应将 `data/evidence` 改为加密对象存储、设置案件级访问控制和保留期限；基础正则脱敏只用于减少模型暴露面，不能替代人工检查。

## 前端联调

先启动 API：`uvicorn app.main:app --reload`。工作台的“连接 API”默认使用 `http://127.0.0.1:8000`，也可填入已部署的 HTTPS API 地址。生产环境通过 `CORS_ORIGINS` 设置允许访问的工作台域名（英文逗号分隔），不要使用通配符。

## Docker 与 app.nonsoft.com 测试部署

```bash
cd legal-debate-agents
cp .env.example .env
docker compose up -d --build
curl http://127.0.0.1:8188/legal-debate/
curl http://127.0.0.1:8188/legal-debate-api/health
```

容器把工作台暴露在本机 `127.0.0.1:8188/legal-debate/`，API 暴露在 `127.0.0.1:8188/legal-debate-api/`。将 `deploy/Caddyfile.snippet` 合并进 `app.nonsoft.com` 的既有 Caddy 站点配置并 reload 后，外网入口即为 `https://app.nonsoft.com/legal-debate/`。不要直接暴露 8000 端口，且在上线真实 Key 前先设置 `CORS_ORIGINS`。

## 人工复核与审计链

每次 `/cases/debate` 完成后，系统会向 `data/audit/{case_id}.jsonl` 追加一条哈希链记录。它保存证据文本哈希、法条效力状态与官方 URL、角色模型路由、输出哈希和前序哈希；原始证据与提示词不会复制进审计日志。用 `GET /cases/{case_id}/audit` 读取记录并验证链完整性。生产环境应把该目录迁移到 WORM/对象锁存储，并为律师复核结论单独追加签名事件。

人工复核使用 `POST /cases/{case_id}/reviews`。请求需携带审计链头 `expected_audit_head_hash`；若辩论结果或其他复核已更新链头，提交会以 409 拒绝，避免“看了旧卷宗却签了新结论”。`detached_signature` 仅作为外部签名凭据的引用字段；本项目本身不提供或宣称符合《电子签名法》的可靠电子签名服务。

## 生产前必做

1. 用国家法律法规数据库核验每条法条的效力和原文链接。
2. 用最高法/人民法院案例库核验案例来源，不把“相似案例”当作自动结论。
3. 所有事实必须绑定证据 ID 与页码/时间戳；未绑定的只可作为待核验陈述。
4. 刑事、家事、未成年人、行政处罚等案件强制人工律师复核。
