// Loaded before the inline UI script. Remote deployments use the same-origin
// reverse proxy; local development keeps the direct FastAPI default.
if (location.hostname === "app.nonsoft.com" && !localStorage.getItem("legalDebateApi")) {
  localStorage.setItem("legalDebateApi", `${location.origin}/legal-debate-api`);
}
