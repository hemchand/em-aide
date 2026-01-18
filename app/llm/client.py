from __future__ import annotations
from typing import Protocol, Type, Any
import httpx
from pydantic import BaseModel
from app.settings import settings

class LLMClient(Protocol):
    def generate_structured(self, system: str, user: str, schema: Type[BaseModel]) -> BaseModel: ...
    def name(self) -> str: ...

class OpenAICompatibleClient:
    def __init__(self):
        if not settings.llm_api_key:
            raise RuntimeError("LLM_API_KEY is required for remote mode.")
        self.base_url = settings.llm_base_url.rstrip("/")
        self.api_key = settings.llm_api_key
        self.model = settings.llm_model
        self.timeout = settings.llm_timeout_seconds

    def name(self) -> str:
        return f"remote:{self.model}"

    def generate_structured(self, system: str, user: str, schema: Type[BaseModel]) -> BaseModel:
        # Uses Chat Completions compatible endpoint: /chat/completions
        # Uses "response_format" JSON schema if supported; otherwise relies on strict prompt.
        url = f"{self.base_url}/chat/completions"
        headers = {"Authorization": f"Bearer {self.api_key}"}
        payload: dict[str, Any] = {
            "model": self.model,
            "temperature": settings.llm_temperature,
            "max_tokens": settings.llm_max_tokens,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            # Best-effort: many OpenAI-compatible providers accept this; if not, it is ignored.
            "response_format": {"type": "json_object"},
        }
        with httpx.Client(timeout=self.timeout) as client:
            r = client.post(url, headers=headers, json=payload)
            r.raise_for_status()
            data = r.json()
        content = data["choices"][0]["message"]["content"]
        # Parse JSON into schema
        return schema.model_validate_json(content)

class OllamaClient:
    # Stub for Option A readiness (not used in MVP by default)
    def __init__(self):
        self.base_url = settings.ollama_base_url.rstrip("/")
        self.model = settings.ollama_model

    def name(self) -> str:
        return f"local:{self.model}"

    def generate_structured(self, system: str, user: str, schema: Type[BaseModel]) -> BaseModel:
        url = f"{self.base_url}/api/chat"
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "stream": False,
        }
        with httpx.Client(timeout=120) as client:
            r = client.post(url, json=payload)
            r.raise_for_status()
            data = r.json()
        content = data["message"]["content"]
        return schema.model_validate_json(content)

def get_llm_client() -> LLMClient:
    if settings.llm_mode.lower() == "local":
        return OllamaClient()
    return OpenAICompatibleClient()
