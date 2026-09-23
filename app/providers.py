import os
from dataclasses import dataclass
import httpx

@dataclass(frozen=True)
class ModelRoute:
    provider: str
    model: str
    base_url: str | None = None
    api_key_env: str | None = None

class ProviderError(RuntimeError): pass

class ChatProvider:
    async def complete(self, system: str, prompt: str) -> str: raise NotImplementedError

class MockProvider(ChatProvider):
    async def complete(self, system: str, prompt: str) -> str:
        return "MOCK: This is a deterministic development response; configure a real provider for legal analysis."

class OpenAICompatibleProvider(ChatProvider):
    def __init__(self, route: ModelRoute): self.route = route
    async def complete(self, system: str, prompt: str) -> str:
        key = os.getenv(self.route.api_key_env or "")
        if not key: raise ProviderError(f"Missing {self.route.api_key_env}")
        url = f"{(self.route.base_url or '').rstrip('/')}/chat/completions"
        payload = {"model": self.route.model, "messages": [{"role":"system","content":system},{"role":"user","content":prompt}], "temperature": 0.1}
        async with httpx.AsyncClient(timeout=90) as client:
            r = await client.post(url, json=payload, headers={"Authorization":f"Bearer {key}"})
            r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"]

class OllamaProvider(ChatProvider):
    def __init__(self, route: ModelRoute): self.route = route
    async def complete(self, system: str, prompt: str) -> str:
        base = self.route.base_url or os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
        async with httpx.AsyncClient(timeout=180) as client:
            r = await client.post(f"{base.rstrip('/')}/api/chat", json={"model":self.route.model,"stream":False,"messages":[{"role":"system","content":system},{"role":"user","content":prompt}]})
            r.raise_for_status()
        return r.json()["message"]["content"]

class AnthropicProvider(ChatProvider):
    """Native Messages API adapter; Claude is deliberately not routed through a fake OpenAI shim."""
    def __init__(self, route: ModelRoute): self.route = route
    async def complete(self, system: str, prompt: str) -> str:
        key = os.getenv(self.route.api_key_env or "ANTHROPIC_API_KEY")
        if not key: raise ProviderError(f"Missing {self.route.api_key_env or 'ANTHROPIC_API_KEY'}")
        async with httpx.AsyncClient(timeout=90) as client:
            r = await client.post(
                f"{(self.route.base_url or 'https://api.anthropic.com').rstrip('/')}/v1/messages",
                headers={"x-api-key": key, "anthropic-version": "2023-06-01"},
                json={"model": self.route.model, "max_tokens": 1600, "temperature": 0.1,
                      "system": system, "messages": [{"role": "user", "content": prompt}]},
            )
            r.raise_for_status()
        return r.json()["content"][0]["text"]

def get_provider(route: ModelRoute) -> ChatProvider:
    if route.provider == "mock": return MockProvider()
    if route.provider == "ollama": return OllamaProvider(route)
    if route.provider == "openai_compatible": return OpenAICompatibleProvider(route)
    if route.provider == "anthropic": return AnthropicProvider(route)
    raise ProviderError(f"Unsupported provider: {route.provider}. Add a native adapter if it is not OpenAI-compatible.")
